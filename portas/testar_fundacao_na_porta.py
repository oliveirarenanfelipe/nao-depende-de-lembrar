#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Teste do `fundacao_na_porta.py`, no padrao da casa (igual ao testar_bash_na_porta):

  0. SANDBOX       - prova, com assert, que nada aqui toca ~/Projeto nem o
                     estado real. Ja houve nesta casa um teste "isolado" que
                     apontava para a mente REAL (2x no mesmo dia).
  1. DEVE BLOQUEAR - os casos que o gate existe para pegar.
  2. DEVE PASSAR   - senao o gate vira pedra no caminho e alguem o desliga.
  3. MUTACAO       - desarma cada detector e exige que os casos DEIXEM de ser
                     pegos. Gate verde nao prova nada; mutacao prova que ele
                     esta armado.
  4. CONTROLE      - com tudo no lugar, os casos voltam a ser pegos.

RODAR: python ~/.claude/hooks/testar_fundacao_na_porta.py
"""

import io
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fundacao_na_porta as gate  # noqa: E402

PASS = 0
FALHA = 0


def marcar(nome, ok, extra=""):
    global PASS, FALHA
    if ok:
        PASS += 1
        print("  PASS  " + nome)
    else:
        FALHA += 1
        print("  FALHA " + nome + ("   " + extra if extra else ""))


# -- 0. SANDBOX, provado -----------------------------------------------------
SANDBOX = tempfile.mkdtemp(prefix="fundacao_teste_")
REAL = os.path.abspath(os.path.join(os.path.expanduser("~"), "Projeto"))

print("== 0. SANDBOX (provado, nao prometido) ==")
assert os.path.normcase(SANDBOX) != os.path.normcase(REAL), \
    "sandbox == ~/Projeto"
assert not os.path.normcase(SANDBOX).startswith(os.path.normcase(REAL)), \
    "sandbox esta DENTRO de ~/Projeto"
print("  sandbox: %s" % SANDBOX)
print("  ~/Projeto real: %s  (intocado)" % REAL)
marcar("sandbox fora de ~/Projeto", True)

# redireciona o gate para o sandbox e para um estado descartavel
gate.RAIZ_PROJETOS = SANDBOX
gate.ESTADO = os.path.join(SANDBOX, "estado.json")
assert not os.path.normcase(gate.ESTADO).startswith(
    os.path.normcase(os.path.dirname(os.path.abspath(gate.__file__)))), \
    "o estado do teste apontaria para a pasta real de hooks"
marcar("estado do teste fora de ~/.claude/hooks", True)

YML_BOM = """nome: projeto-teste
owner: a casa
lifecycle: experimental
o_que_e: >
  Um projeto de teste, para exercitar o gate.
efeito_no_mundo: nenhum
dado_de_cliente: nao
onde_roda: local
teste: automatizado
ci: sim
trabalho_aberto: pendencias_ativas
"""

YML_INCOMPLETO = """nome: projeto-teste
owner: a casa
lifecycle: experimental
"""

YML_VALOR_INVALIDO = YML_BOM.replace("lifecycle: experimental",
                                     "lifecycle: producao_total")


def montar(nome, yml=None, com_git=True):
    """Cria um projeto falso no sandbox. Devolve o caminho de um arquivo .py."""
    pasta = os.path.join(SANDBOX, nome)
    os.makedirs(os.path.join(pasta, "scripts"), exist_ok=True)
    if com_git:
        os.makedirs(os.path.join(pasta, ".git"), exist_ok=True)
    if yml is not None:
        with io.open(os.path.join(pasta, "projeto.yml"), "w",
                     encoding="utf-8") as fh:
            fh.write(yml)
    alvo = os.path.join(pasta, "scripts", "codigo.py")
    with io.open(alvo, "w", encoding="utf-8") as fh:
        fh.write("print('oi')\n")
    return alvo


def rodar(alvo, sessao="s1"):
    """Chama o gate como o harness chama e devolve (bloqueou, motivo)."""
    entrada = json.dumps({"session_id": sessao,
                          "tool_name": "Write",
                          "tool_input": {"file_path": alvo}})
    stdin_antigo, stdout_antigo = sys.stdin, sys.stdout
    captura = io.StringIO()
    try:
        sys.stdin = type("F", (), {"buffer": io.BytesIO(entrada.encode())})()
        sys.stdout = captura
        gate.main()
    finally:
        sys.stdin, sys.stdout = stdin_antigo, stdout_antigo
    saida = captura.getvalue().strip()
    if not saida:
        return False, ""
    try:
        d = json.loads(saida)
    except ValueError:
        return False, saida
    h = d.get("hookSpecificOutput") or {}
    return h.get("permissionDecision") == "deny", \
        h.get("permissionDecisionReason", "")


# -- 1. DEVE BLOQUEAR --------------------------------------------------------
print("\n== 1. DEVE BLOQUEAR ==")

CASOS_BLOQUEIO = [
    ("projeto sem projeto.yml nenhum",
     montar("sem-yml", yml=None)),
    ("projeto.yml existe mas faltam campos",
     montar("yml-incompleto", yml=YML_INCOMPLETO)),
    ("projeto.yml com valor fora do dominio (lifecycle invalido)",
     montar("yml-invalido", yml=YML_VALOR_INVALIDO)),
    ("projeto SEM git (cai no filho direto de ~/Projeto)",
     montar("sem-git", yml=None, com_git=False)),
]

for i, (nome, alvo) in enumerate(CASOS_BLOQUEIO):
    bloqueou, motivo = rodar(alvo, sessao="bloq%d" % i)
    marcar(nome, bloqueou, "(passou e nao devia)")

# o caso do valor invalido tem de DIZER qual campo esta errado
_, motivo_inv = rodar(montar("yml-invalido2", yml=YML_VALOR_INVALIDO),
                      sessao="inv2")
marcar("a recusa nomeia o campo invalido",
       "lifecycle" in motivo_inv and "producao_total" in motivo_inv,
       "(motivo: %r)" % motivo_inv[:80])

# a recusa tem de entregar o CAMINHO do arquivo a criar, nao so o nome da regra
_, motivo_sem = rodar(montar("sem-yml2", yml=None), sessao="sem2")
marcar("a recusa entrega o caminho do projeto.yml a criar",
       "projeto.yml" in motivo_sem and "sem-yml2" in motivo_sem)


# -- 2. DEVE PASSAR ----------------------------------------------------------
print("\n== 2. DEVE PASSAR (senao o gate vira pedra e alguem o desliga) ==")

alvo_ok = montar("completo", yml=YML_BOM)
bloqueou, _ = rodar(alvo_ok, sessao="ok1")
marcar("projeto com os 10 campos respondidos", not bloqueou)

# 2a tentativa no MESMO projeto passa (padrao da casa)
alvo_2a = montar("segunda-vez", yml=None)
rodar(alvo_2a, sessao="dupla")
bloqueou2, _ = rodar(alvo_2a, sessao="dupla")
marcar("2a tentativa no mesmo projeto passa", not bloqueou2)

# sessao diferente volta a barrar (senao o gate morre depois do 1o dia)
bloqueou3, _ = rodar(alvo_2a, sessao="outra-sessao")
marcar("sessao nova volta a barrar o mesmo projeto", bloqueou3)

pasta_md = os.path.join(SANDBOX, "completo")
alvo_md = os.path.join(pasta_md, "LEIAME.md")
with io.open(alvo_md, "w", encoding="utf-8") as fh:
    fh.write("# nao e codigo\n")
bloqueou_md, _ = rodar(alvo_md, sessao="md")
marcar("arquivo que nao e codigo (.md) passa", not bloqueou_md)

pasta_nm = os.path.join(SANDBOX, "sem-yml", "node_modules", "x")
os.makedirs(pasta_nm, exist_ok=True)
alvo_nm = os.path.join(pasta_nm, "lib.js")
with io.open(alvo_nm, "w", encoding="utf-8") as fh:
    fh.write("//\n")
bloqueou_nm, _ = rodar(alvo_nm, sessao="nm")
marcar("codigo em node_modules passa (nao e nosso)", not bloqueou_nm)

pasta_t = os.path.join(SANDBOX, "sem-yml", "tests")
os.makedirs(pasta_t, exist_ok=True)
alvo_t = os.path.join(pasta_t, "test_x.py")
with io.open(alvo_t, "w", encoding="utf-8") as fh:
    fh.write("#\n")
bloqueou_t, _ = rodar(alvo_t, sessao="t")
marcar("arquivo de teste passa (teste escreve qualquer coisa)", not bloqueou_t)

fora = os.path.join(tempfile.gettempdir(), "fora_de_projeto.py")
with io.open(fora, "w", encoding="utf-8") as fh:
    fh.write("#\n")
bloqueou_f, _ = rodar(fora, sessao="fora")
marcar("arquivo fora de ~/Projeto passa", not bloqueou_f)

# entrada quebrada nao pode travar o dia (fail-open declarado)
stdin_antigo, stdout_antigo = sys.stdin, sys.stdout
cap = io.StringIO()
try:
    sys.stdin = type("F", (), {"buffer": io.BytesIO(b"isto nao e json")})()
    sys.stdout = cap
    gate.main()
    quebrou = False
except Exception:  # noqa: BLE001,S110 - sem stdout nao ha para onde avisar
    quebrou = True
finally:
    sys.stdin, sys.stdout = stdin_antigo, stdout_antigo
marcar("entrada invalida nao levanta excecao (fail-open)", not quebrou)


# -- 3. MUTACAO --------------------------------------------------------------
print("\n== 3. MUTACAO (desarma o detector; os casos tem de DEIXAR de ser pegos) ==")

# GUARD, e ele nasceu de um erro real da sessao que o escreveu:
# na 1a rodada o gate nao bloqueava NADA (um ISENTO errado engolia o sandbox),
# e mesmo assim as 4 mutacoes vieram "DETECTADAS" - porque desarmar um detector
# que ja pegava zero continua pegando zero. Mutacao sobre baseline morto e
# falso positivo. Se a secao 1 falhou, a secao 3 nao vale nada e nao roda.
if FALHA:
    print("  PULADA - a secao 1 teve %d falha(s): o baseline esta morto." % FALHA)
    print("           Desarmar detector que ja pega zero continua pegando zero.")
    print("           Conserte o bloqueio antes de acreditar em qualquer mutacao.")
    print("\n=== RESULTADO: %d PASS / %d FALHA / mutacao NAO AVALIADA ==="
          % (PASS, FALHA))
    shutil.rmtree(SANDBOX, ignore_errors=True)
    sys.exit(1)

OBRIG_ORIG = gate.OBRIGATORIOS
VALORES_ORIG = dict(gate.VALORES)
LER_ORIG = gate.ler_projeto_yml
CODIGO_ORIG = gate.CODIGO


def mut_sem_obrigatorios():
    gate.OBRIGATORIOS = ()


def mut_sem_dominio():
    gate.VALORES = {}


def mut_yml_sempre_completo():
    # Tem de devolver valores VALIDOS, nao "x" em tudo. Descoberto rodando
    # medido: com "x" a mutacao "sobrevivia", mas nao porque o gate fosse
    # fraco - e porque o SEGUNDO detector (dominio de valores) pegava o "x".
    # O gate tem dois detectores independentes; para medir o leitor, os outros
    # tem de ser satisfeitos. Mutacao mal construida acusa forca onde nao ha e
    # esconde fraqueza onde ha.
    falso = {c: "preenchido" for c in OBRIG_ORIG}
    for campo, aceitos in VALORES_ORIG.items():
        falso[campo] = aceitos[0]
    gate.ler_projeto_yml = lambda pasta: dict(falso)


def mut_codigo_vazio():
    gate.CODIGO = ()


def restaurar():
    gate.OBRIGATORIOS = OBRIG_ORIG
    gate.VALORES = dict(VALORES_ORIG)
    gate.ler_projeto_yml = LER_ORIG
    gate.CODIGO = CODIGO_ORIG


MUTACOES = [
    ("lista de campos obrigatorios esvaziada",
     "se nada e obrigatorio, o yml incompleto deixa de ser incompleto",
     mut_sem_obrigatorios,
     [("yml-incompleto", YML_INCOMPLETO)]),
    ("dominio de valores esvaziado",
     "sem dominio, `lifecycle: producao_total` vira valor aceitavel",
     mut_sem_dominio,
     [("yml-invalido", YML_VALOR_INVALIDO)]),
    ("leitor do yml sempre devolve tudo preenchido",
     "e o modo de falha mais perigoso: o gate roda, fica verde, e nao ve nada",
     mut_yml_sempre_completo,
     [("sem-yml", None), ("yml-incompleto", YML_INCOMPLETO)]),
    ("lista de extensoes de codigo esvaziada",
     "se nada e codigo, o gate nunca dispara",
     mut_codigo_vazio,
     [("sem-yml", None)]),
]

sobreviveram = []
for i, (nome, porque, aplicar, casos) in enumerate(MUTACOES):
    restaurar()
    aplicar()
    ainda_pegos = 0
    for j, (sufixo, yml) in enumerate(casos):
        alvo = montar("mut%d_%d_%s" % (i, j, sufixo), yml=yml)
        bloqueou, _ = rodar(alvo, sessao="mut%d_%d" % (i, j))
        if bloqueou:
            ainda_pegos += 1
    detectada = ainda_pegos == 0
    if not detectada:
        sobreviveram.append(nome)
    print("  [%s] %s" % ("DETECTADA" if detectada else "SOBREVIVEU", nome))
    print("           " + porque)
    print("           %d de %d caso(s) continuaram sendo pegos"
          % (ainda_pegos, len(casos)))
restaurar()


# -- 3b. A CONFIG DE LINTER QUE JA EXISTE ------------------------------------
# 🔴 Adotado de um repositorio de referencia. A regra dele cabe numa frase —
# *conserte o codigo, nao afrouxe a regra* — e a prova mede os DOIS lados,
# porque so o segundo impede que ela vire pedra: criar a primeira config de um
# projeto e legitimo e tem de passar.
print("\n== 3b. config de linter: afrouxar o que ja vale ==")

_cfg = os.path.join(SANDBOX, "proj-cfg")
os.makedirs(_cfg, exist_ok=True)


def _com_config(nome, existe=True):
    p = os.path.join(_cfg, nome)
    if existe:
        io.open(p, "w", encoding="utf-8").write("[regras]\n")
    elif os.path.isfile(p):
        os.remove(p)
    return p


for _nome in ("ruff.toml", ".eslintrc.json", ".prettierrc", ".flake8",
              "biome.json", ".editorconfig"):
    _alvo = _com_config(_nome)
    _bloqueou, _motivo = rodar(_alvo, sessao="cfg-%s" % _nome)
    marcar("BLOQUEIA editar `%s` que ja existe" % _nome, _bloqueou,
           "motivo=%r" % _motivo[:60])

# ⚠️ O LADO QUE IMPEDE A PEDRA. Cada um destes e uma escrita legitima, e uma
# delas — criar a primeira config — e justamente o que um projeto novo faz.
_novo = _com_config("ruff.toml", existe=False)
_bloqueou, _ = rodar(_novo, sessao="cfg-novo")
marcar("passa: CRIAR config que ainda nao existe", not _bloqueou)

_qualquer = os.path.join(_cfg, "config.json")
io.open(_qualquer, "w", encoding="utf-8").write("{}\n")
_bloqueou, _ = rodar(_qualquer, sessao="cfg-outro")
marcar("passa: arquivo de config que NAO e de linter", not _bloqueou)

_com_config("ruff.toml")
_bloqueou, _ = rodar(os.path.join(_cfg, "ruff.toml"), sessao="cfg-2a")
_bloqueou2, _ = rodar(os.path.join(_cfg, "ruff.toml"), sessao="cfg-2a")
marcar("a 1a tentativa barra e a 2a passa, com o motivo no registro",
       _bloqueou and not _bloqueou2)

# A MUTACAO: esvaziar a lista tem de CEGAR o gate. Se ele continuar barrando
# com a lista vazia, quem barra e outra coisa e esta regra nao existe.
_lista_orig = gate.CONFIGS_PROTEGIDAS
try:
    gate.CONFIGS_PROTEGIDAS = frozenset()
    _cego, _ = rodar(_com_config("ruff.toml"), sessao="cfg-mut")
    _det = not _cego
finally:
    gate.CONFIGS_PROTEGIDAS = _lista_orig
print("  [%s] lista de configs esvaziada deixa a edicao passar"
      % ("DETECTADA" if _det else "SOBREVIVEU"))
if not _det:
    FALHA += 1

# E a 2a mutacao, que separa "existe" de "nao existe": se o gate parar de
# olhar o disco, ele barra ate a CRIACAO — e ai vira pedra.
_isfile_orig = gate.os.path.isfile
try:
    gate.os.path.isfile = lambda p: True
    _pedra, _ = rodar(_com_config("ruff.toml", existe=False), sessao="cfg-mut2")
    _det2 = _pedra
finally:
    gate.os.path.isfile = _isfile_orig
print("  [%s] sem olhar o disco, o gate barra ate a CRIACAO"
      % ("DETECTADA" if _det2 else "SOBREVIVEU"))
if not _det2:
    FALHA += 1


# -- 4. CONTROLE -------------------------------------------------------------
print("\n== 4. controle: com tudo no lugar, os casos voltam a ser pegos ==")
for i, (sufixo, yml) in enumerate([("sem-yml", None),
                                   ("yml-incompleto", YML_INCOMPLETO),
                                   ("yml-invalido", YML_VALOR_INVALIDO)]):
    alvo = montar("ctrl%d_%s" % (i, sufixo), yml=yml)
    bloqueou, _ = rodar(alvo, sessao="ctrl%d" % i)
    marcar("controle: %s volta a ser pego" % sufixo, bloqueou)


# -- fim ---------------------------------------------------------------------
print("\n== prova final: ~/Projeto continua intocado ==")
marcar("nenhum projeto.yml novo na raiz de ~/Projeto por conta do teste",
       not os.path.exists(os.path.join(REAL, "projeto.yml")))

shutil.rmtree(SANDBOX, ignore_errors=True)

print("\n=== RESULTADO: %d PASS / %d FALHA / %d mutacao(oes) sobreviveram ==="
      % (PASS, FALHA, len(sobreviveram)))
for nome in sobreviveram:
    print("   mutacao nao detectada: " + nome)
sys.exit(1 if (FALHA or sobreviveram) else 0)
