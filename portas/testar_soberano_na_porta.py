# -*- coding: utf-8 -*-
r"""Prova do `soberano_na_porta.py` — o portao barra E nao cobra pedagio.

🔴 POR QUE ESTE ARQUIVO NASCEU DEPOIS DA PECA. O `inventario.py` acusou a
propria casa: **7 das 14 pecas sem teste, 6 delas PORTAS** — as que interrompem
o trabalho todo dia sem nenhuma prova de que ainda interrompem. Gate que nao se
prova pode ja ter morrido sem ninguem notar, porque ele simplesmente **para de
reclamar**, e silencio le igual a "esta tudo certo".

E este gate em particular ja viveu isso: nasceu INERTE e ficou assim por
porque lia o stdin no locale do Windows e o payload chegava mojibake
`[medido: mesmo payload, sem PYTHONIOENCODING passa / com utf-8 nega]`. Um gate
inerte e indistinguivel de um gate que aprovou.

O que se prova aqui, nesta ordem (o rito da casa, igual ao
`testar_fundacao_na_porta.py`):

  0. SANDBOX       - provado com assert que o CLAUDE.md REAL nao e tocado.
  1. DEVE BLOQUEAR - os 6 casos que o gate existe para pegar.
  2. NAO PODE BARRAR - o grupo que pega falso positivo, e que costuma faltar.
                     Gate que estorva no caso legitimo e gate que alguem desliga.
  3. MUTACAO       - desarma cada detector e exige que os casos DEIXEM de ser
                     pegos. So roda se a secao 1 passou inteira:
                     [[concept-mutacao-sobre-baseline-morto]].
  4. CONTROLE      - restaurado, tudo volta a ser pego.

CHAMADOR: o `inventario.py` (lista `PECAS`), que o verificador diario de
saude da casa roda todo dia.

RODAR: python -B ~/.claude/hooks/testar_soberano_na_porta.py
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import soberano_na_porta as gate  # noqa: E402

PASS = 0
FALHA = 0
MARCA = "sob%d" % int(time.time() * 1000)


def marcar(nome, ok, extra=""):
    global PASS, FALHA
    if ok:
        PASS += 1
        print("  PASS  " + nome)
    else:
        FALHA += 1
        print("  FALHA " + nome + ("   " + extra if extra else ""))


# -- 0. SANDBOX, provado -----------------------------------------------------
SANDBOX = tempfile.mkdtemp(prefix="soberano_teste_")
REAL = os.path.normcase(os.path.abspath(
    os.path.join(os.path.expanduser("~"), "Projeto", "CLAUDE.md")))
FALSO = os.path.join(SANDBOX, "CLAUDE.md")

print("== 0. SANDBOX (provado, nao prometido) ==")
assert os.path.normcase(os.path.abspath(FALSO)) != REAL, \
    "o alvo do teste E o CLAUDE.md real"
marcar("alvo do teste fora de ~/Projeto", True)

# O gate passa a considerar soberano o arquivo do sandbox. Sem isto o teste
# precisaria escrever no CLAUDE.md de verdade para exercitar qualquer caminho.
gate.SOBERANO = os.path.normcase(os.path.abspath(FALSO))
assert gate.SOBERANO != REAL, "redirecionamento do sandbox falhou"
marcar("gate redirecionado para o sandbox", True)

# O gate grava no `gates.log` REAL a cada negacao. Um teste que roda todo dia
# encheria o log de entradas que nunca foram bloqueio de trabalho nenhum — e o
# painel da mente leria isso como a mente se autocontrolando. Silenciado aqui,
# de proposito e por escrito.
gate._log_gate = lambda *a, **k: None
marcar("log real do gate silenciado durante o teste", True)

TAM_REAL_ANTES = os.path.getsize(REAL) if os.path.exists(REAL) else -1

SECAO = gate.SECAO
ITEM_ABERTO = "- 🔴 **#001abc** — gancho curto do item ainda aberto"

# Um soberano COM a secao da fila (o formato antigo), para
# exercitar os tres detectores de dentro da secao.
COM_FILA = (
    "# Soberano de mentira\n\nTexto comum de cabecalho.\n\n"
    + SECAO + "\n\n" + ITEM_ABERTO + "\n\n"
    "## Outra secao\n\nMais texto comum.\n"
)

# Um soberano SEM a secao (o formato de hoje): teto de pendencia e ZERO.
SEM_FILA = (
    "# Soberano de mentira\n\nTexto comum de cabecalho.\n\n"
    "## Pendencias — onde elas vivem\n\n"
    "A fila-mestra saiu daqui, e nao deve voltar.\n\n"
    "## Outra secao\n\nMais texto comum.\n"
)


def escrever_soberano(conteudo):
    with io.open(FALSO, "w", encoding="utf-8") as fh:
        fh.write(conteudo)


def rodar(tool_input, sessao):
    """Chama o gate como o harness chama. Devolve (negou, motivo)."""
    entrada = json.dumps({"session_id": MARCA + sessao,
                          "tool_name": "Write",
                          "tool_input": tool_input})
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


def edit(novo, velho=ITEM_ABERTO):
    return {"file_path": FALSO, "old_string": velho, "new_string": novo}


def write(conteudo):
    return {"file_path": FALSO, "content": conteudo}


# Os casos, cada um com o estado de disco que ele exige.
PENDENCIA_NOVA = "- 🔴 **#999zzz** — pendencia nova entrando no soberano"
ITEM_FECHADO = "- ✅ **#002def** — item ja fechado entrando de volta"
ITEM_GORDO = "- 🔴 **#003ghi** — " + ("detalhe medido que e da micro mente " * 8)
NARRATIVA = "> " + ("resumo de sessao que e do brief e nao do soberano " * 6)
ENCHIMENTO = ("linha de texto comum, sem pendencia nenhuma dentro dela.\n"
              * 6000)                       # > ARQUIVO_MAX (150.000 chars)

assert len(ITEM_GORDO) > gate.FILA_ITEM_MAX, "o item gordo nao passa do teto"
assert len(ITEM_FECHADO) <= gate.FILA_ITEM_MAX, \
    "o item fechado passa do teto e dois detectores disputariam o mesmo caso"
assert len(NARRATIVA) > gate.NARRATIVA_MAX, "a narrativa nao passa do teto"
assert len(ENCHIMENTO) > gate.ARQUIVO_MAX, "o enchimento nao passa do teto"

CASOS_BLOQUEIO = [
    ("Edit: pendencia entrando num soberano SEM fila (teto zero)",
     SEM_FILA, edit(PENDENCIA_NOVA, velho="Texto comum de cabecalho."), "b1"),
    ("Write: arquivo inteiro trazendo pendencia de volta",
     SEM_FILA, write(SEM_FILA + "\n" + PENDENCIA_NOVA + "\n"), "b2"),
    ("Write: arquivo acima do teto do harness (150k chars)",
     SEM_FILA, write(ENCHIMENTO), "b3"),
    ("Edit: item FECHADO (marcado resolvido) entrando na fila",
     COM_FILA, edit(ITEM_FECHADO), "b4"),
    ("Edit: item de pendencia acima do teto de chars",
     COM_FILA, edit(ITEM_GORDO), "b5"),
    ("Edit: bloco narrativo longo dentro da fila",
     COM_FILA, edit(NARRATIVA), "b6"),
]

# -- 1. DEVE BLOQUEAR --------------------------------------------------------
print("\n== 1. DEVE BLOQUEAR ==")
for nome, disco, ti, sess in CASOS_BLOQUEIO:
    escrever_soberano(disco)
    negou, _ = rodar(ti, sess)
    marcar(nome, negou, "(passou e nao devia)")

# A recusa tem de DIZER onde a pendencia vive agora, senao ela so atrapalha.
escrever_soberano(SEM_FILA)
_, motivo = rodar(edit(PENDENCIA_NOVA, velho="Texto comum de cabecalho."), "b7")
# ⚠️ A asserção pergunta pelo ENDEREÇO, não pela data. Ela exigia a data no
# texto, e isso amarrava a prova a um detalhe que não é a garantia: a garantia
# e que a recusa diga ONDE escrever. Pego ao destilar a peca — a data
# saiu da mensagem e o teste reprovou, apontando para o lugar certo pelo motivo
# errado. Prova presa a detalhe cosmetico envelhece junto com ele.
marcar("a recusa entrega o endereco novo da pendencia",
       "pendencias_ativas.md" in motivo and "micro mente" in motivo.lower(),
       "(motivo: %r)" % motivo[:90])

escrever_soberano(COM_FILA)
_, motivo_g = rodar(edit(ITEM_GORDO), "b8")
marcar("a recusa nomeia o id e o tamanho do item gordo",
       "#003ghi" in motivo_g and str(len(ITEM_GORDO)) in motivo_g,
       "(motivo: %r)" % motivo_g[:90])


# -- 2. NAO PODE BARRAR ------------------------------------------------------
print("\n== 2. NAO PODE BARRAR (senao o gate vira pedra e alguem o desliga) ==")

escrever_soberano(SEM_FILA)
outro = os.path.join(SANDBOX, "outro.md")
negou, _ = rodar({"file_path": outro, "content": PENDENCIA_NOVA}, "p1")
marcar("arquivo que nao e o soberano passa", not negou)

negou, _ = rodar(edit("Texto comum reescrito, sem pendencia nenhuma.",
                      velho="Texto comum de cabecalho."), "p2")
marcar("edicao comum no soberano passa", not negou)

negou, _ = rodar(write(SEM_FILA + "\nMais uma linha de prosa comum.\n"), "p3")
marcar("Write comum, dentro do teto, passa", not negou)

negou, _ = rodar(edit("- **negrito qualquer** — isto nao e uma pendencia",
                      velho="Texto comum de cabecalho."), "p4")
marcar("bullet com negrito que NAO e item de pendencia passa", not negou)

escrever_soberano(COM_FILA)
negou, _ = rodar(edit("- 🔴 **#004jkl** — gancho curto, dentro do teto"), "p5")
marcar("item aberto e curto dentro da fila passa", not negou)

negou, _ = rodar(edit("> nota curta dentro da fila"), "p6")
marcar("bloco narrativo curto dentro da fila passa", not negou)

escrever_soberano(SEM_FILA)
ti_rep = edit(PENDENCIA_NOVA, velho="Texto comum de cabecalho.")
primeira, _ = rodar(ti_rep, "p7")
segunda, _ = rodar(ti_rep, "p7")
marcar("2a tentativa da MESMA edicao passa (padrao da casa)",
       primeira and not segunda,
       "(1a=%s, 2a=%s)" % (primeira, segunda))

terceira, _ = rodar(ti_rep, "p8")
marcar("sessao nova volta a barrar a mesma edicao", terceira)

# entrada quebrada nao pode travar o dia (fail-open declarado)
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
print("\n== 3. MUTACAO (desarma o detector; os casos tem de DEIXAR de ser pegos) ==")

if FALHA:
    print("  PULADA - a secao 1/2 teve %d falha(s): o baseline esta morto." % FALHA)
    print("           Desarmar detector que ja pega zero continua pegando zero.")
    print("\n=== RESULTADO: %d PASS / %d FALHA / mutacao NAO AVALIADA ==="
          % (PASS, FALHA))
    shutil.rmtree(SANDBOX, ignore_errors=True)
    sys.exit(1)

ITEM_ORIG = gate.ITEM
FECHADO_ORIG = gate.FECHADO
MAX_ORIG = gate.FILA_ITEM_MAX
NARR_ORIG = gate.NARRATIVA_MAX
ARQ_ORIG = gate.ARQUIVO_MAX
LISTA_ORIG = gate._itens_de_pendencia

NUNCA = re.compile(r"(?!x)x()()")           # nunca casa; 2 grupos como o ITEM


def restaurar():
    gate.ITEM = ITEM_ORIG
    gate.FECHADO = FECHADO_ORIG
    gate.FILA_ITEM_MAX = MAX_ORIG
    gate.NARRATIVA_MAX = NARR_ORIG
    gate.ARQUIVO_MAX = ARQ_ORIG
    gate._itens_de_pendencia = LISTA_ORIG


MUTACOES = [
    ("reconhecedor de item de pendencia cego",
     "sem o ITEM, nenhuma linha e pendencia: a fila volta a crescer calada",
     lambda: setattr(gate, "ITEM", NUNCA),
     [(SEM_FILA, edit(PENDENCIA_NOVA, velho="Texto comum de cabecalho."), "m0a"),
      (COM_FILA, edit(ITEM_GORDO), "m0b")]),
    ("lista de status FECHADO esvaziada",
     "sem ela, o item ja resolvido volta a entrar no soberano",
     lambda: setattr(gate, "FECHADO", ()),
     [(COM_FILA, edit(ITEM_FECHADO), "m1")]),
    ("teto de chars do item elevado",
     "sem teto, o detalhe [medido] da micro mente volta a morar aqui",
     lambda: setattr(gate, "FILA_ITEM_MAX", 10 ** 9),
     [(COM_FILA, edit(ITEM_GORDO), "m2")]),
    ("teto do bloco narrativo elevado",
     "sem teto, o resumo de sessao volta a ser colado no soberano",
     lambda: setattr(gate, "NARRATIVA_MAX", 10 ** 9),
     [(COM_FILA, edit(NARRATIVA), "m3")]),
    ("teto do arquivo elevado",
     "e o teto do proprio harness: passando dele o soberano e CORTADO",
     lambda: setattr(gate, "ARQUIVO_MAX", 10 ** 9),
     [(SEM_FILA, write(ENCHIMENTO), "m4")]),
    ("coletor de pendencia sempre devolve lista vazia",
     "o modo de falha mais perigoso: o gate roda, fica verde, e nao ve nada",
     lambda: setattr(gate, "_itens_de_pendencia", lambda linhas: []),
     [(SEM_FILA, edit(PENDENCIA_NOVA, velho="Texto comum de cabecalho."), "m5a"),
      (SEM_FILA, write(SEM_FILA + "\n" + PENDENCIA_NOVA + "\n"), "m5b")]),
]

sobreviveram = []
for i, (nome, porque, aplicar, casos) in enumerate(MUTACOES):
    restaurar()
    aplicar()
    ainda_pegos = 0
    for j, (disco, ti, sess) in enumerate(casos):
        escrever_soberano(disco)
        negou, _ = rodar(ti, "mut%d_%d_%s" % (i, j, sess))
        if negou:
            ainda_pegos += 1
    detectada = ainda_pegos == 0
    if not detectada:
        sobreviveram.append(nome)
    print("  [%s] %s" % ("DETECTADA" if detectada else "SOBREVIVEU", nome))
    print("           " + porque)
    print("           %d de %d caso(s) continuaram sendo pegos"
          % (ainda_pegos, len(casos)))
restaurar()


# -- 4. CONTROLE -------------------------------------------------------------
print("\n== 4. controle: com tudo no lugar, os casos voltam a ser pegos ==")
for nome, disco, ti, sess in CASOS_BLOQUEIO:
    escrever_soberano(disco)
    negou, _ = rodar(ti, "ctrl_" + sess)
    marcar("controle: " + nome, negou)


# -- fim ---------------------------------------------------------------------
print("\n== prova final: o CLAUDE.md real continua intocado ==")
tam_depois = os.path.getsize(REAL) if os.path.exists(REAL) else -1
marcar("o CLAUDE.md soberano nao mudou de tamanho",
       tam_depois == TAM_REAL_ANTES,
       "(antes=%d, depois=%d)" % (TAM_REAL_ANTES, tam_depois))

for f in glob.glob(os.path.join(tempfile.gettempdir(),
                                "soberano_porta_%s*.json" % MARCA)):
    try:
        os.remove(f)
    except OSError:
        pass
shutil.rmtree(SANDBOX, ignore_errors=True)

print("\n=== RESULTADO: %d PASS / %d FALHA / %d mutacao(oes) sobreviveram ==="
      % (PASS, FALHA, len(sobreviveram)))
for nome in sobreviveram:
    print("   mutacao nao detectada: " + nome)
sys.exit(1 if (FALHA or sobreviveram) else 0)
