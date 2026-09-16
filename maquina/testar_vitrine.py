# -*- coding: utf-8 -*-
"""Prova da `vitrine.py` — ela grava a verdade, ou nao grava nada.

O modo de falha desta peca nao e o erro: e o SUCESSO falso. Um template
quebrado gera uma pagina bonita, bem formatada, e vazia — e pagina vazia le
como casa saudavel. Ninguem abre uma vitrine limpa e desconfia dela. Por isso
a peca confere cada numero DENTRO do HTML antes de gravar, e por isso este
teste ataca justamente essa conferencia.

  0. SANDBOX   - casa de mentira; o HTML de verdade nao e tocado.
  1. DEVE GRAVAR   - e o que grava tem de conter o que foi medido.
  2. NAO PODE GRAVAR - quando a pagina perde um numero, ela NAO vai ao disco.
  3. MUTACAO   - quebra a pagina de tres jeitos e exige a recusa.
  4. CONTROLE

CHAMADOR: `maquina/inventario.py` (PECAS), rodado pelo bloco [6u].

RODAR: python -B maquina/testar_vitrine.py
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                           # noqa: BLE001
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import inventario as inv                                    # noqa: E402
import o_basico as ob                                       # noqa: E402
import vitrine as vt                                        # noqa: E402

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
SANDBOX = tempfile.mkdtemp(prefix="vitrine_teste_")
REAL_HTML = vt.DESTINO
ANTES = (os.path.getmtime(REAL_HTML) if os.path.exists(REAL_HTML) else -1)

print("== 0. SANDBOX (provado, nao prometido) ==")
marcar("sandbox fora de ~/Projeto",
       not os.path.normcase(SANDBOX).startswith(
           os.path.normcase(os.path.join(os.path.expanduser("~"), "Projeto"))))

RAIZ_ORIG = ob.RAIZ
ob.RAIZ = SANDBOX
DESTINO = os.path.join(SANDBOX, "vitrine.html")


def monta(nome):
    base = os.path.join(SANDBOX, nome)
    os.makedirs(base, exist_ok=True)
    io.open(os.path.join(base, "app.py"), "w",
            encoding="utf-8").write("print(1)\n")
    subprocess.run(["git", "init", "-q"], cwd=base, capture_output=True)
    subprocess.run(["git", "remote", "add", "origin",
                    "git@sandbox:%s/%s.git" % (ob.NOSSOS[0], nome)],
                   cwd=base, capture_output=True)
    return base


monta("alfa")
monta("beta")

# `inv.levantar` roda os testes das 15 pecas de verdade e leva minutos. Aqui o
# que se prova e a VITRINE, nao o inventario (que tem prova propria), entao ele
# e substituido por uma resposta fixa e conhecida. Teste que depende do mundo
# inteiro para rodar vira teste que ninguem roda.
LEVANTAR_ORIG = inv.levantar
PECAS_FALSAS = [
    dict(cat="porta", nome="porta_boa", onde="x", existe=True, teste="t.py",
         teste_existe=True, passa=True, chamador="settings.json"),
    dict(cat="medida", nome="peca_quebrada", onde="x", existe=True,
         teste="t2.py", teste_existe=True, passa=False, chamador="cron"),
]
inv.levantar = lambda rodar_testes=True: list(PECAS_FALSAS)

_d, _ = ob.medir()
marcar("o medidor enxerga os 2 projetos do sandbox", len(_d) == 2,
       "(viu %d)" % len(_d))
if len(_d) != 2:
    inv.levantar = LEVANTAR_ORIG
    ob.RAIZ = RAIZ_ORIG
    shutil.rmtree(SANDBOX, ignore_errors=True)
    sys.exit(1)


# -- 1. DEVE GRAVAR ----------------------------------------------------------
print("\n== 1. DEVE GRAVAR, e gravar a verdade ==")

caminho, numeros, faltando = vt.gravar(DESTINO)
marcar("gravou a pagina", caminho == DESTINO and not faltando,
       "(faltando: %s)" % faltando)
html = io.open(DESTINO, encoding="utf-8").read() if caminho else ""

marcar("   a pagina diz os 2 projetos medidos",
       "alfa" in html and "beta" in html)
marcar("   e traz o placar de cada um dos 7 itens",
       all(("placar_" + k) in numeros for k in ob.ITENS))
marcar("   a peca QUEBRADA aparece como REPROVA, nao escondida",
       "peca_quebrada" in html and "REPROVA" in html)
marcar("   e a peca boa aparece como passa", "porta_boa" in html)

# R4: artefato autocontido, zero CDN em runtime. Vitrine que depende de rede
# vira pagina em branco justamente no dia em que ele abre sem internet.
externo = [m for m in ("http://", "https://", "//cdn", "<script")
           if m in html]
marcar("ZERO recurso externo e zero script (autocontida)", not externo,
       "(achei: %s)" % externo)

marcar("   tem viewport (ele abre no celular tambem)",
       "viewport" in html and "width=device-width" in html)
marcar("   e responde ao tema do sistema",
       "prefers-color-scheme" in html)


# -- 2. NAO PODE GRAVAR ------------------------------------------------------
print("\n== 2. NAO PODE GRAVAR pagina que perdeu numero ==")

nome_perigoso = "proj<script>alert(1)</script>"
marcar("o escape de HTML esta armado",
       "&lt;script&gt;" in vt._esc(nome_perigoso)
       and "<script>" not in vt._esc(nome_perigoso))


# -- 3. MUTACAO --------------------------------------------------------------
print("\n== 3. MUTACAO (quebrar a pagina; ela tem de RECUSAR gravar) ==")

if FALHA:
    print("  PULADA - a secao 1/2 teve %d falha(s): baseline morto." % FALHA)
    print("\n=== RESULTADO: %d PASS / %d FALHA / mutacao NAO AVALIADA ==="
          % (PASS, FALHA))
    inv.levantar = LEVANTAR_ORIG
    ob.RAIZ = RAIZ_ORIG
    shutil.rmtree(SANDBOX, ignore_errors=True)
    sys.exit(1)

MONTAR_ORIG = vt.montar
html_bom, numeros_bom = MONTAR_ORIG()


def mut_pagina_vazia():
    vt.montar = lambda: ("<html><body><h1>A casa</h1></body></html>",
                         dict(numeros_bom))


def mut_perde_um_placar():
    # a pagina inteira, menos a linha do placar de `cit` — o caso realista:
    # alguem mexe no template e uma secao para de renderizar, calada.
    alvo = 'data-item="cit">%d/%d<' % (numeros_bom["placar_cit"],
                                       numeros_bom["projetos"])
    vt.montar = lambda: (html_bom.replace(alvo, 'data-item="cit"><', 1),
                         dict(numeros_bom))


def mut_numero_inventado():
    # a pagina certa, mas o resumo afirma um numero que ela nao mostra.
    falso = dict(numeros_bom)
    falso["projetos"] = 999
    vt.montar = lambda: (html_bom, falso)


MUTACOES = [
    ("pagina esvaziada (template morre calado)",
     "bonita, valida, e sem um numero dentro: e assim que vitrine mente",
     mut_pagina_vazia),
    ("uma linha do placar some do HTML",
     "o caso realista: mexem no template e uma secao para de renderizar",
     mut_perde_um_placar),
    ("o resumo afirma numero que a pagina nao mostra",
     "a prova tem de comparar os dois lados, nao confiar no resumo",
     mut_numero_inventado),
]

ALVO_MUT = os.path.join(SANDBOX, "mut.html")
sobreviveram = []
for nome, porque, aplicar in MUTACOES:
    vt.montar = MONTAR_ORIG
    aplicar()
    if os.path.exists(ALVO_MUT):
        os.remove(ALVO_MUT)
    caminho, _n, faltando = vt.gravar(ALVO_MUT)
    recusou = caminho is None and bool(faltando)
    limpo = not os.path.exists(ALVO_MUT)
    detectada = recusou and limpo
    if not detectada:
        sobreviveram.append(nome)
    print("  [%s] %s" % ("DETECTADA" if detectada else "SOBREVIVEU", nome))
    print("           " + porque)
    print("           recusou=%s  disco limpo=%s  nomeou: %s"
          % (recusou, limpo, (faltando or ["-"])[:3]))
vt.montar = MONTAR_ORIG


# -- 4. CONTROLE -------------------------------------------------------------
print("\n== 4. controle: restaurada, volta a gravar ==")
if os.path.exists(ALVO_MUT):
    os.remove(ALVO_MUT)
caminho, _n, faltando = vt.gravar(ALVO_MUT)
marcar("controle: a pagina volta a ser gravada",
       caminho == ALVO_MUT and not faltando, "(faltando: %s)" % faltando)

print("\n== prova final: a vitrine REAL nao foi tocada ==")
inv.levantar = LEVANTAR_ORIG
ob.RAIZ = RAIZ_ORIG
depois = (os.path.getmtime(REAL_HTML) if os.path.exists(REAL_HTML) else -1)
marcar("o vitrine.html de verdade tem a mesma data de modificacao",
       depois == ANTES, "(antes=%s, depois=%s)" % (ANTES, depois))

shutil.rmtree(SANDBOX, ignore_errors=True)

print("\n=== RESULTADO: %d PASS / %d FALHA / %d mutacao(oes) sobreviveram ==="
      % (PASS, FALHA, len(sobreviveram)))
for nome in sobreviveram:
    print("   mutacao nao detectada: " + nome)
sys.exit(1 if (FALHA or sobreviveram) else 0)
