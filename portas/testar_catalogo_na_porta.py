# -*- coding: utf-8 -*-
r"""Prova do `catalogo_na_porta.py` — o portao barra E nao cobra pedagio.

🔴 POR QUE ESTE ARQUIVO NASCEU DEPOIS DA PECA. O `inventario.py` acusou a
propria casa: **7 das 14 pecas sem teste, 6 delas PORTAS**. Esta e a porta que pergunta
*"quem vai CHAMAR esta peca?"* no instante em que um arquivo de codigo novo
nasce — e ela mesma nao tinha quem provasse que ainda pergunta.

A ironia e exata e vale registrar: o gate existe por causa do padrao que ele
nomeou como *"toda vez voce somente cria, nao usa"*, e ele proprio era uma
peca sem prova. Gate que para de reclamar e indistinguivel de gate que aprovou.

⚠️ O SANDBOX NAO PODE MORAR NO `temp`, e isto e medido, nao preferencia. O
`IGNORAR` do gate contem a pasta temporaria, entao TODO caminho dentro dela e
isento por desenho. Um teste montado la veria os 3 casos de bloqueio "passarem"
e imprimiria verde sobre um gate que nem foi consultado — o falso positivo mais
caro que existe aqui. O assert da secao 0 trava isso.

O que se prova, nesta ordem (o rito da casa):

  0. SANDBOX       - provado, inclusive que ele NAO cai nos isentos do gate.
  1. DEVE BLOQUEAR - criar codigo novo, e a mensagem que ele devolve.
  2. NAO PODE BARRAR - editar, prosa, isentos e a 2a tentativa.
  3. MUTACAO       - desarma cada detector e exige que o teste ACUSE. So roda
                     se a secao 1 passou: [[concept-mutacao-sobre-baseline-morto]].
  4. CONTROLE      - restaurado, tudo volta a ser pego.

CHAMADOR: o `inventario.py` (lista `PECAS`), que o verificador diario de
saude da casa roda todo dia.

RODAR: python -B ~/.claude/hooks/testar_catalogo_na_porta.py
"""
import glob
import io
import json
import os
import re
import shutil
import sys
import tempfile
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001,S110 - sem stdout nao ha para onde avisar
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import catalogo_na_porta as gate  # noqa: E402

PASS = 0
FALHA = 0
MARCA = "cat%d" % int(time.time() * 1000)


def marcar(nome, ok, extra=""):
    global PASS, FALHA
    if ok:
        PASS += 1
        print("  PASS  " + nome)
    else:
        FALHA += 1
        print("  FALHA " + nome + ("   " + extra if extra else ""))


# -- 0. SANDBOX, provado -----------------------------------------------------
SANDBOX = os.path.join(AQUI, "_sandbox_teste_catalogo_%d" % os.getpid())
PROJ = os.path.join(SANDBOX, "projeto-de-mentira")
SCRIPTS = os.path.join(PROJ, "scripts")
os.makedirs(SCRIPTS, exist_ok=True)
os.makedirs(os.path.join(PROJ, ".git"), exist_ok=True)   # ancora o os.walk

print("== 0. SANDBOX (provado, nao prometido) ==")

_sonda = os.path.join(SCRIPTS, "novo.py").lower()
_culpados = [x for x in gate.IGNORAR if x in _sonda]
# A mensagem CARREGA o termo culpado e o que fazer. Ela dizia so que o sandbox
# caia nos isentos — verdade, e inutil para quem bate nela: o teste mora ao
# lado da peca, entao o caminho e do disco de quem clonou, e ninguem adivinha
# qual dos 8 termos casou. Medido ao rodar isto de uma pasta com
# `scratchpad` no caminho: o assert disparou certo e eu tive de ir ler o
# codigo para saber por que.
assert not _culpados, (
    "o sandbox cai nos ISENTOS do gate por causa de %s no caminho:\n  %s\n"
    "O teste inteiro leria verde sem o gate ser consultado uma vez. Mova este "
    "repositorio para um caminho que nao contenha esse termo."
    % (", ".join("`%s`" % c for c in _culpados), _sonda))
marcar("sandbox NAO cai nos isentos do gate", True)

_temp = os.path.join(tempfile.gettempdir(), "p", "novo.py").lower()
marcar("e a pasta temporaria cairia (por isso o sandbox nao mora la)",
       any(x in _temp for x in gate.IGNORAR))

# O catalogo REAL tem 200+ linhas e muda toda semana: um teste que o
# lesse mediria o catalogo, nao o gate, e reprovaria sozinho no dia em que
# alguem escrevesse uma linha nova. Aqui o catalogo e fixo e conhecido.
MOC_REAL = gate.MOC
MOC_FALSO = os.path.join(SANDBOX, "_MOC_ferramentas.md")
with io.open(MOC_FALSO, "w", encoding="utf-8") as fh:
    fh.write(
        "| Ferramenta | Veredito | Uso |\n"
        "|---|---|---|\n"
        "| FerramentaOrfaDeTeste | adotar, validado em bancada | ainda nao |\n"
        "| FerramentaComChamador | adotar, validado | chamada em scripts/x.py:12 |\n"
        "| FerramentaDescartada | validado tecnicamente | descartado: nao serve |\n")
gate.MOC = MOC_FALSO
marcar("catalogo do teste e fixo (nao le o catalogo real)",
       gate.MOC != MOC_REAL)

# arquivo ja existente no projeto, para o detector de "nome parecido"
IRMAO = os.path.join(SCRIPTS, "motor_video.py")
with io.open(IRMAO, "w", encoding="utf-8") as fh:
    fh.write("def rodar():\n    return 1\n")


def rodar(alvo, sessao, tool="Write"):
    """Chama o gate como o harness chama. Devolve (negou, motivo)."""
    entrada = json.dumps({"session_id": MARCA + sessao, "tool_name": tool,
                          "tool_input": {"file_path": alvo,
                                         "content": "print('oi')\n"}})
    stdin_antigo, stdout_antigo = sys.stdin, sys.stdout
    captura = io.StringIO()
    try:
        sys.stdin = type("F", (), {"buffer": io.BytesIO(entrada.encode("utf-8"))})()
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
    return (h.get("permissionDecision") == "deny",
            h.get("permissionDecisionReason", ""))


NOVO_PY = os.path.join(SCRIPTS, "coletor_novo.py")
NOVO_SH = os.path.join(SCRIPTS, "instalar_novo.sh")
NOVO_TS = os.path.join(SCRIPTS, "cliente_novo.ts")
PARECIDO = os.path.join(SCRIPTS, "motor_video_novo.py")

CASOS_BLOQUEIO = [
    ("criar .py novo", NOVO_PY, "b1"),
    ("criar .sh novo", NOVO_SH, "b2"),
    ("criar .ts novo", NOVO_TS, "b3"),
]

# -- 1. DEVE BLOQUEAR --------------------------------------------------------
print("\n== 1. DEVE BLOQUEAR ==")
for nome, alvo, sess in CASOS_BLOQUEIO:
    negou, _ = rodar(alvo, sess)
    marcar(nome, negou, "(passou e nao devia)")

_, motivo = rodar(PARECIDO, "b4")
marcar("a recusa cobra o CHAMADOR em arquivo:linha",
       "arquivo:linha" in motivo, "(motivo: %r)" % motivo[:80])
marcar("a recusa mostra o arquivo de nome parecido que ja existe",
       "motor_video.py" in motivo, "(motivo: %r)" % motivo[-200:])

_, motivo2 = rodar(os.path.join(SCRIPTS, "outro_novo.py"), "b5")
marcar("a recusa lista a ferramenta aprovada e SEM uso",
       "FerramentaOrfaDeTeste" in motivo2, "(motivo: %r)" % motivo2[-200:])
marcar("e NAO lista a que ja tem chamador declarado",
       "FerramentaComChamador" not in motivo2)
marcar("nem a que foi descartada",
       "FerramentaDescartada" not in motivo2)


# -- 2. NAO PODE BARRAR ------------------------------------------------------
print("\n== 2. NAO PODE BARRAR (senao o gate vira pedra e alguem o desliga) ==")

negou, _ = rodar(IRMAO, "p1")
marcar("arquivo .py que JA EXISTE passa (editar nao e criar)", not negou)

negou, _ = rodar(os.path.join(PROJ, "LEIAME.md"), "p2")
marcar("arquivo de prosa (.md) passa", not negou)

for rotulo, pedaco in (("scratchpad", "scratchpad"),
                       ("node_modules", "node_modules"),
                       ("__pycache__", "__pycache__"),
                       ("graphify-out", "graphify-out")):
    alvo = os.path.join(SCRIPTS, pedaco, "gerado.py")
    negou, _ = rodar(alvo, "p_" + rotulo)
    marcar("caminho com `%s` passa (isento por desenho)" % rotulo, not negou)

primeira, _ = rodar(NOVO_PY, "p3")
segunda, _ = rodar(NOVO_PY, "p3")
marcar("2a tentativa no MESMO arquivo passa (padrao da casa)",
       primeira and not segunda, "(1a=%s, 2a=%s)" % (primeira, segunda))

terceira, _ = rodar(NOVO_PY, "p4")
marcar("sessao nova volta a barrar o mesmo arquivo", terceira)

negou, _ = rodar("", "p5")
marcar("payload sem file_path passa", not negou)

stdin_antigo, stdout_antigo = sys.stdin, sys.stdout
cap = io.StringIO()
try:
    sys.stdin = type("F", (), {"buffer": io.BytesIO(b"isto nao e json")})()
    sys.stdout = cap
    gate.main()
    quebrou = False
except Exception:                                           # noqa: BLE001
    quebrou = True
finally:
    sys.stdin, sys.stdout = stdin_antigo, stdout_antigo
marcar("entrada invalida nao levanta excecao (fail-open)", not quebrou)


# -- 3. MUTACAO --------------------------------------------------------------
print("\n== 3. MUTACAO (desarma o detector; o teste tem de ACUSAR) ==")

if FALHA:
    print("  PULADA - a secao 1/2 teve %d falha(s): o baseline esta morto." % FALHA)
    print("           Desarmar detector que ja pega zero continua pegando zero.")
    print("\n=== RESULTADO: %d PASS / %d FALHA / mutacao NAO AVALIADA ==="
          % (PASS, FALHA))
    shutil.rmtree(SANDBOX, ignore_errors=True)
    sys.exit(1)

CODIGO_ORIG = gate.CODIGO
IGNORAR_ORIG = gate.IGNORAR
JA_ORIG = gate._ja_perguntei
PARECIDOS_ORIG = gate.parecidos
MOC_ORIG = gate.MOC


def restaurar():
    gate.CODIGO = CODIGO_ORIG
    gate.IGNORAR = IGNORAR_ORIG
    gate._ja_perguntei = JA_ORIG
    gate.parecidos = PARECIDOS_ORIG
    gate.MOC = MOC_ORIG


def _nao_pega_mais(sufixo):
    """DETECTADA quando os 3 casos de bloqueio deixam de ser pegos."""
    return not any(rodar(a, "mut_%s_%s" % (sufixo, s))[0]
                   for _n, a, s in CASOS_BLOQUEIO)


MUTACOES = [
    ("lista de extensoes de codigo esvaziada",
     "se nada e codigo, a peca 29 nasce orfa sem ninguem perguntar nada",
     lambda: setattr(gate, "CODIGO", ()),
     lambda: _nao_pega_mais("ext")),
    ("marca de `ja perguntei` sempre respondendo SIM",
     "e o modo de falha silencioso: o gate roda, nunca interrompe, fica verde",
     lambda: setattr(gate, "_ja_perguntei", lambda s, a: True),
     lambda: _nao_pega_mais("marca")),
    ("lista de ISENTOS esvaziada (mutacao inversa)",
     "prova que os isentos estao vivos: sem eles, ate scratchpad passa a barrar",
     lambda: setattr(gate, "IGNORAR", ()),
     lambda: rodar(os.path.join(SCRIPTS, "scratchpad", "g.py"), "mut_isen")[0]),
    ("leitor do catalogo apontado para o vazio",
     "a lista de aprovadas-sem-uso some da recusa, e a porta perde a metade "
     "que responde *o que ja existe*",
     lambda: setattr(gate, "MOC", os.path.join(SANDBOX, "nao_existe.md")),
     lambda: "FerramentaOrfaDeTeste" not in
             rodar(os.path.join(SCRIPTS, "z1_novo.py"), "mut_moc")[1]),
    ("detector de nome parecido cego",
     "sem ele a recusa deixa de mostrar o irmao que ja faz a mesma coisa",
     lambda: setattr(gate, "parecidos", lambda alvo, limite=6: []),
     lambda: "motor_video.py" not in
             rodar(os.path.join(SCRIPTS, "motor_video_z2.py"), "mut_par")[1]),
]

sobreviveram = []
for nome, porque, aplicar, verificar in MUTACOES:
    restaurar()
    aplicar()
    try:
        detectada = bool(verificar())
    except Exception as e:                                  # noqa: BLE001
        detectada = False
        porque += "   (erro ao verificar: %s)" % type(e).__name__
    if not detectada:
        sobreviveram.append(nome)
    print("  [%s] %s" % ("DETECTADA" if detectada else "SOBREVIVEU", nome))
    print("           " + porque)
restaurar()


# -- 3b. O CAMINHO DO CATALOGO E DADO ----------------------------------------
# Ele estava escrito no codigo do gate, com o nome do usuario do
# disco no meio. Noutra maquina o caminho nao existiria, a leitura devolveria
# lista vazia, e o gate deixaria de lembrar de qualquer ferramenta — sem
# quebrar e sem avisar.
#
# ⚠️ Aqui a ausencia NAO levanta, ao contrario dos outros campos do
# `casa.json`, e a diferenca e deliberada: quem nao mantem um catalogo assim
# deixa o campo vazio e o gate segue barrando o resto. Gate que exige um habito
# que a pessoa nao tem e desinstalado no primeiro dia. Por isso o teste mede os
# DOIS lados: que o caminho valido e montado, e que a falta dele degrada em vez
# de explodir.
print("\n== 3b. o caminho do catalogo sai do codigo, e a falta dele DEGRADA ==")

_tmp_casa = tempfile.mkdtemp(prefix="casa_cat_")
try:
    _bom = os.path.join(_tmp_casa, "casa.json")
    io.open(_bom, "w", encoding="utf-8").write(
        '{"catalogo_de_ferramentas": "docs/catalogo.md"}')
    _lido = gate.catalogo_do_disco(_bom)
    marcar("caminho valido vira caminho absoluto sob o HOME",
           _lido.endswith(os.path.join("docs", "catalogo.md"))
           and os.path.isabs(_lido), _lido)

    _vazio = os.path.join(_tmp_casa, "vazio.json")
    io.open(_vazio, "w", encoding="utf-8").write(
        '{"catalogo_de_ferramentas": ""}')
    marcar("campo VAZIO devolve '' e nao levanta",
           gate.catalogo_do_disco(_vazio) == "")

    marcar("arquivo AUSENTE devolve '' e nao levanta",
           gate.catalogo_do_disco(
               os.path.join(_tmp_casa, "nao_existe.json")) == "")

    _torto = os.path.join(_tmp_casa, "torto.json")
    io.open(_torto, "w", encoding="utf-8").write("{isto nao e json")
    marcar("JSON quebrado devolve '' e nao derruba o gate",
           gate.catalogo_do_disco(_torto) == "")

    # E o nome do usuario do disco NAO esta mais na logica da peca.
    #
    # ⚠️ A BUSCA E POR TOKEN DE CAMINHO, nao por substring solta, e a diferenca
    # foi medida rodando o repositorio publicado com o `HOME` noutro lugar. O
    # usuario chamava-se `casa`, e a palavra `casa` aparece no codigo do gate
    # porque o arquivo de configuracao se chama `casa.json`. O teste reprovava
    # uma peca correta, na maquina de outra pessoa, sem nenhum defeito.
    #
    # 🔑 Um teste que reprova pelo NOME de quem o roda e pior que um teste que
    # falta: quem clonou ve vermelho, nao acha o defeito, e desconfia da peca
    # errada. O que importa aqui e o nome aparecer como pedaco de CAMINHO.
    _fonte = io.open(os.path.join(AQUI, "catalogo_na_porta.py"),
                     encoding="utf-8").read()
    _usuario = os.path.basename(os.path.expanduser("~"))
    _como_caminho = re.compile(
        r"[%s/\"']%s[%s/\"']" % (chr(92) * 2, re.escape(_usuario), chr(92) * 2))
    marcar("o nome do usuario do disco saiu do codigo do gate",
           not _como_caminho.search(_fonte), "(ainda la: %s)" % _usuario)
finally:
    shutil.rmtree(_tmp_casa, ignore_errors=True)


# -- 4. CONTROLE -------------------------------------------------------------
print("\n== 4. controle: com tudo no lugar, os casos voltam a ser pegos ==")
for nome, alvo, sess in CASOS_BLOQUEIO:
    negou, _ = rodar(alvo, "ctrl_" + sess)
    marcar("controle: " + nome, negou)
negou, _ = rodar(os.path.join(SCRIPTS, "scratchpad", "g.py"), "ctrl_isen")
marcar("controle: o isento volta a passar", not negou)


# -- fim ---------------------------------------------------------------------
print("\n== prova final: nada ficou no disco ==")
for f in glob.glob(os.path.join(tempfile.gettempdir(),
                                "catalogo_porta_%s*.json" % MARCA)):
    try:
        os.remove(f)
    except OSError:
        pass
shutil.rmtree(SANDBOX, ignore_errors=True)
marcar("sandbox removido de ~/.claude/hooks", not os.path.exists(SANDBOX))

print("\n=== RESULTADO: %d PASS / %d FALHA / %d mutacao(oes) sobreviveram ==="
      % (PASS, FALHA, len(sobreviveram)))
for nome in sobreviveram:
    print("   mutacao nao detectada: " + nome)
sys.exit(1 if (FALHA or sobreviveram) else 0)
