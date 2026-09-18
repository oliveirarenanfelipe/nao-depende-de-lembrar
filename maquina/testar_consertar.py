# -*- coding: utf-8 -*-
"""Prova do `consertar.py` — ele conserta, RECUSA o que nao provou, e nao
inventa numero.

Esta peca e a mais perigosa da maquina, e o teste existe por causa disso: ela
ESCREVE em 30 projetos. As tres formas de ela estragar a casa sao:

  1. gravar um artefato que nao funciona (um `.gitignore` que o git nao le, um
     TOML que o gitleaks nao parseia) — e o placar sobe mentindo;
  2. sobrescrever arquivo que ja existe no projeto de alguem;
  3. consertar o que NAO se conserta sozinho (`tst`, `dec`) e fazer o numero
     subir enquanto a casa piora.

Entao o teste tem os dois grupos de sempre — o que ela DEVE consertar e o que
ela NAO PODE tocar — mais mutacao em cada prova, porque aqui "verde" e
exatamente o que um conserto quebrado produz.

  0. SANDBOX   - projetos de mentira, com git de verdade (o `check-ignore`
                 precisa de um repo real para responder).
  1. DEVE CONSERTAR
  2. NAO PODE TOCAR
  3. MUTACAO   - quebra cada artefato e exige que a peca RECUSE gravar.
  4. CONTROLE

CHAMADOR: `maquina/inventario.py` (PECAS), rodado pelo bloco [6u] do
`mente_health.py`.

RODAR: python -B maquina/testar_consertar.py
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001,S110 - sem stdout nao ha para onde avisar
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import consertar as ct  # noqa: E402
import o_basico as ob  # noqa: E402

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


# -- 0. SANDBOX --------------------------------------------------------------
SANDBOX = tempfile.mkdtemp(prefix="consertar_teste_")
REAL = os.path.normcase(os.path.abspath(
    os.path.join(os.path.expanduser("~"), "Projeto")))

print("== 0. SANDBOX (provado, nao prometido) ==")
assert os.path.normcase(SANDBOX) != REAL, "sandbox == ~/Projeto"
assert not os.path.normcase(SANDBOX).startswith(REAL), \
    "sandbox esta DENTRO de ~/Projeto"
marcar("sandbox fora de ~/Projeto", True)

RAIZ_ORIG = ob.RAIZ
ob.RAIZ = SANDBOX
marcar("a peca redirecionada para o sandbox", ob.RAIZ != RAIZ_ORIG)


def monta(nome, com_ign=False, com_yml=False, com_leaks=False, com_teste=False):
    """Projeto de mentira com git DE VERDADE — o check-ignore exige repo real."""
    base = os.path.join(SANDBOX, nome)
    os.makedirs(base, exist_ok=True)
    io.open(os.path.join(base, "app.py"), "w",
            encoding="utf-8").write("print('oi')\n")
    subprocess.run(["git", "init", "-q"], cwd=base, capture_output=True)
    # sem remote "nosso", o `o_basico` classifica como repo de TERCEIRO e o
    # projeto some da conta — o teste mediria o vazio e imprimiria verde.
    subprocess.run(["git", "remote", "add", "origin",
                    "git@sandbox:%s/%s.git" % (ob.NOSSOS[0], nome)],
                   cwd=base, capture_output=True)
    if com_ign:
        io.open(os.path.join(base, ".gitignore"), "w",
                encoding="utf-8").write("# meu proprio\nsegredo.txt\n")
    if com_yml:
        io.open(os.path.join(base, "projeto.yml"), "w",
                encoding="utf-8").write("nome: %s\nowner: a casa\n" % nome)
    if com_leaks:
        io.open(os.path.join(base, ".gitleaks.toml"), "w",
                encoding="utf-8").write("# minha propria config\n")
    if com_teste:
        io.open(os.path.join(base, "testar_x.py"), "w",
                encoding="utf-8").write("import sys\nsys.exit(0)\n")
    return base


CRU = monta("cru")
COM_TUDO = monta("com-tudo", com_ign=True, com_yml=True, com_leaks=True)

# o sandbox e mesmo visto como 2 projetos nossos?
_dados, _ = ob.medir()
marcar("o medidor enxerga os 2 projetos do sandbox", len(_dados) == 2,
       "(viu %d: %s)" % (len(_dados), sorted(_dados)))
if len(_dados) != 2:
    print("\n  o sandbox nao foi reconhecido: o resto mediria o vazio.")
    shutil.rmtree(SANDBOX, ignore_errors=True)
    sys.exit(1)


# -- 1. DEVE CONSERTAR -------------------------------------------------------
print("\n== 1. DEVE CONSERTAR ==")

ok, det = ct.conserta_ign(CRU, "cru", aplicar=True)
marcar("escreve .gitignore E o git confirma que o le", ok is True, det)
marcar("   o arquivo existe no disco",
       os.path.isfile(os.path.join(CRU, ".gitignore")))

ok, det = ct.conserta_id(CRU, "cru", aplicar=True)
marcar("escreve projeto.yml com os 10 campos", ok is True, det)

# A prova CRUZADA: quem le o `projeto.yml` de verdade e o gate da porta, e e
# contra ele que o conserto tem de valer. Duas pecas concordando sobre o mesmo
# arquivo vale mais que uma peca concordando consigo mesma.
#
# ⚠️ O gate mora fora desta pasta, e legitimamente pode nao existir: ele nao
# vai junto quando a maquina e publicada. Entao a ausencia dele nao e falha —
# mas tambem NAO passa calada. Pular em silencio e como o teste vira enfeite:
# um dia o gate some da casa de verdade e ninguem fica sabendo. Achado ao
# rodar a maquina destilada com a casa vazia, onde isto quebrava com
# `ModuleNotFoundError` e derrubava a suite inteira.
sys.path.insert(0, os.path.join(os.path.expanduser("~"), ".claude", "hooks"))
try:
    import fundacao_na_porta as porta  # noqa: E402
except ImportError:
    porta = None

# O GUARDIAO DA LISTA DIGITADA. O `consertar` guarda os 10 campos numa
# constante, porque deriva-los do proprio `CONTRATO` faria a peca comparar o
# template consigo mesma — e a mutacao "contrato sem 8 dos 10 campos" passou a
# sobreviver quando tentei isso. Lista escrita precisa de quem a cobre, e e
# esta checagem: ela roda todo dia, e acusa no dia em que o template mudar.
do_template = sorted(ct._ler_contrato_fraco(ct.CONTRATO % {"nome": "x"}))
marcar("a lista de campos bate com o que o CONTRATO gera",
       sorted(ct.CAMPOS_DO_CONTRATO) == do_template,
       "lista=%s template=%s" % (sorted(ct.CAMPOS_DO_CONTRATO), do_template))

if porta is not None:
    marcar("   e bate com o que o GATE cobra",
           sorted(ct.CAMPOS_DO_CONTRATO) == sorted(porta.OBRIGATORIOS),
           str(sorted(porta.OBRIGATORIOS)))
    marcar("   o gate enxerga os 10 campos no que foi escrito",
           all(c in porta.ler_projeto_yml(CRU) for c in porta.OBRIGATORIOS))
    marcar("   e os campos estao VAZIOS (o rito nao inventa placeholder)",
           not any(porta.ler_projeto_yml(CRU).get(c)
                   for c in porta.OBRIGATORIOS if c != "nome"))
else:
    print("  (nao medido: o gate `fundacao_na_porta` nao esta nesta maquina.")
    print("   A prova cruzada do projeto.yml exige os dois lados, e este e o")
    print("   lado que vive fora desta pasta.)")
    # Sem o gate, o teste ainda exige que o arquivo escrito tenha os campos —
    # a checagem mais fraca, feita aqui na mao e dita como tal.
    escrito = io.open(os.path.join(CRU, "projeto.yml"),
                      encoding="utf-8").read()
    marcar("   (fraca) os campos do contrato estao no arquivo escrito",
           all(("\n" + c + ":") in escrito
               for c in ("nome", "owner", "lifecycle", "o_que_e")))

# 🔴 OS DOIS CAMINHOS, e ter so um foi o defeito. Em Python 3.9 e 3.10 nao
# existe `tomllib`, e sem parser a peca RECUSA gravar — que e o comportamento
# certo, porque config de scanner nao conferida faz o gitleaks abortar, e
# aborto le igual a nada encontrado.
#
# ⚠️ O teste so conhecia o caminho COM parser, entao ele reprovava nas versoes
# em que a peca acertava. Um teste assim empurra para o conserto errado: o
# caminho de menor resistencia seria voltar a gravar sem provar, para o verde
# voltar. Foi a matriz de versoes do CI que mostrou os dois lados.
ok, det = ct.conserta_sec(CRU, "cru", aplicar=True)
if ct.parser_de_toml() is None:
    marcar("SEM parser de TOML, recusa gravar e diz por que",
           ok is False and "parser" in det, det)
    marcar("   e o arquivo NAO foi criado",
           not os.path.isfile(os.path.join(CRU, ".gitleaks.toml")))
else:
    marcar("escreve .gitleaks.toml parseavel", ok is True, det)


# -- 2. NAO PODE TOCAR -------------------------------------------------------
print("\n== 2. NAO PODE TOCAR ==")

antes = {n: io.open(os.path.join(COM_TUDO, n), encoding="utf-8").read()
         for n in (".gitignore", "projeto.yml", ".gitleaks.toml")}
for chave, _rot, funcao in ct.CONSERTOS:
    if chave == "cit":
        continue
    feito, det = funcao(COM_TUDO, "com-tudo", aplicar=True)
    marcar("nao mexe no %s que o projeto ja tinha" % chave,
           feito is None, "(devolveu %r: %s)" % (feito, det))
depois = {n: io.open(os.path.join(COM_TUDO, n), encoding="utf-8").read()
          for n in (".gitignore", "projeto.yml", ".gitleaks.toml")}
marcar("   os 3 arquivos existentes estao byte a byte iguais", antes == depois)

feito, det = ct.conserta_cit(CRU, "cru", aplicar=True)
marcar("nao tenta ligar CI em projeto sem teste escrito", feito is None, det)

itens_consertaveis = {c for c, _r, _f in ct.CONSERTOS}
marcar("`tst` NUNCA esta entre os consertos automaticos",
       "tst" not in itens_consertaveis)
marcar("`dec` NUNCA esta entre os consertos automaticos",
       "dec" not in itens_consertaveis)
marcar("   e os dois estao declarados como recusa, com motivo escrito",
       {r[0] for r in ct.RECUSADOS} == {"tst", "dec"}
       and all(len(r[2]) > 30 for r in ct.RECUSADOS))

acoes, recusas, _a, _d, _n = ct.levantar(aplicar=False)
marcar("nenhuma acao proposta toca tst ou dec",
       not any(a["item"] in ("tst", "dec") for a in acoes))


# -- 3. MUTACAO --------------------------------------------------------------
print("\n== 3. MUTACAO (quebrar o artefato; a peca tem de RECUSAR gravar) ==")

if FALHA:
    print("  PULADA - a secao 1/2 teve %d falha(s): baseline morto." % FALHA)
    print("\n=== RESULTADO: %d PASS / %d FALHA / mutacao NAO AVALIADA ==="
          % (PASS, FALHA))
    ob.RAIZ = RAIZ_ORIG
    shutil.rmtree(SANDBOX, ignore_errors=True)
    sys.exit(1)

IGNORE_BASE_ORIG = list(ct.IGNORE_BASE)
IGNORE_PY_ORIG = list(ct.IGNORE_PY)
IGNORE_JS_ORIG = list(ct.IGNORE_JS)
CONTRATO_ORIG = ct.CONTRATO
GITLEAKS_ORIG = ct.GITLEAKS
PARSER_ORIG = ct.parser_de_toml


def restaurar():
    ct.IGNORE_BASE = list(IGNORE_BASE_ORIG)
    ct.IGNORE_PY = list(IGNORE_PY_ORIG)
    ct.IGNORE_JS = list(IGNORE_JS_ORIG)
    ct.CONTRATO = CONTRATO_ORIG
    ct.GITLEAKS = GITLEAKS_ORIG
    ct.parser_de_toml = PARSER_ORIG


def mut_ign_inerte():
    # `.gitignore` so de comentario: arquivo plausivel que o git le e que NAO
    # ignora nada. E o modo de falha desta familia — o medidor so pergunta se o
    # arquivo existe, entao o placar subiria sobre um arquivo inutil.
    ct.IGNORE_BASE = ["# nada aqui"]
    ct.IGNORE_PY = []
    ct.IGNORE_JS = []


def mut_contrato_capenga():
    ct.CONTRATO = "nome: %(nome)s\nowner:\n"      # faltam 8 dos 10 campos


def mut_toml_quebrado():
    ct.GITLEAKS = "[extend\nuseDefault = true\n"  # colchete nao fecha


def mut_sem_parser():
    """A mutacao que o CI achou e esta maquina nao conseguia achar sozinha.

    🔴 Em Python 3.9 e 3.10 o `tomllib` nao existe. A peca fazia
    `except ImportError: pass` e seguia "sem esta prova", o que significa
    gravar uma config de scanner que ninguem conferiu. Config invalida faz o
    gitleaks ABORTAR, e um scanner que aborta le igual a um scanner que nao
    achou nada.

    ⚠️ Esta mutacao NAO e sobre o TOML estar errado: e sobre a peca PERDER a
    capacidade de conferir e gravar assim mesmo. Nesta maquina, que roda
    3.12, o defeito era invisivel — o verde local dizia que estava tudo bem, e
    estava tudo bem AQUI. Foi a matriz de versoes do CI que mostrou, e a licao
    e da forma: uma suite que so roda numa versao prova aquela versao.
    """
    ct.parser_de_toml = lambda: None


MUTACOES = [
    ("`.gitignore` que o git le e que nao ignora nada",
     "a peca tem de perguntar ao git e DESFAZER o arquivo inutil",
     mut_ign_inerte, "ign"),
    ("contrato sem 8 dos 10 campos obrigatorios",
     "a peca tem de provar contra o leitor do proprio gate antes de gravar",
     mut_contrato_capenga, "id"),
    ("config de segredo com TOML invalido",
     "scanner que aborta le igual a scanner que nao achou nada",
     mut_toml_quebrado, "sec"),
    ("a peca perde o parser de TOML (Python < 3.11 sem `tomli`)",
     "sem como provar a config, a peca tem de RECUSAR gravar: scanner com "
     "config invalida aborta, e aborto le igual a nada encontrado",
     mut_sem_parser, "sec"),
]

sobreviveram = []
for i, (nome, porque, aplicar_mut, chave) in enumerate(MUTACOES):
    restaurar()
    aplicar_mut()
    alvo = monta("mut%d" % i)
    funcao = [f for c, _r, f in ct.CONSERTOS if c == chave][0]
    feito, det = funcao(alvo, "mut%d" % i, aplicar=True)
    recusou = feito is False
    # e nao pode ter deixado lixo no disco
    arq = {"ign": ".gitignore", "id": "projeto.yml",
           "sec": ".gitleaks.toml"}[chave]
    limpo = not os.path.isfile(os.path.join(alvo, arq))
    detectada = recusou and limpo
    if not detectada:
        sobreviveram.append(nome)
    print("  [%s] %s" % ("DETECTADA" if detectada else "SOBREVIVEU", nome))
    print("           " + porque)
    print("           recusou=%s  disco limpo=%s  (%s)" % (recusou, limpo, det))
restaurar()


# -- 4. CONTROLE -------------------------------------------------------------
print("\n== 4. controle: restaurado, os 3 voltam a gravar ==")
ctrl = monta("ctrl")
for chave in ("ign", "id", "sec"):
    funcao = [f for c, _r, f in ct.CONSERTOS if c == chave][0]
    feito, det = funcao(ctrl, "ctrl", aplicar=True)
    marcar("controle: %s volta a ser escrito" % chave, feito is True, det)

print("\n== prova final: ~/Projeto real intocado ==")
ob.RAIZ = RAIZ_ORIG
marcar("a raiz real voltou ao lugar", ob.RAIZ == RAIZ_ORIG)
marcar("nenhum projeto de mentira ficou em ~/Projeto",
       not os.path.isdir(os.path.join(RAIZ_ORIG, "cru")))

shutil.rmtree(SANDBOX, ignore_errors=True)

print("\n=== RESULTADO: %d PASS / %d FALHA / %d mutacao(oes) sobreviveram ==="
      % (PASS, FALHA, len(sobreviveram)))
for nome in sobreviveram:
    print("   mutacao nao detectada: " + nome)
sys.exit(1 if (FALHA or sobreviveram) else 0)
