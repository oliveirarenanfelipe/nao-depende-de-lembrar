# -*- coding: utf-8 -*-
r"""Prova de `regua_de_complexidade.py` — os dois grupos, mais mutacao.

O RITO DA CASA:
  1. DEVE dar COMPLEX  — tarefa que merece o processo inteiro
  2. NAO pode dar      — tarefa pequena; exigir rigor aqui e o modo de falha por
                         BUROCRACIA, que ensina a pular a Fase 0
  3. as BORDAS exatas  — 8->9 e 15->16 sao onde o limiar erra, e errar ali muda o
                         processo de uma tarefa real
  4. entrada invalida  — nota fora de 1..5, dimensao faltando, `True` (que em
                         Python passa por `int` e valeria 1 calado)
  5. as notas APARECEM — veredito sem as notas vira palpite com numero
  6. MUTACAO           — quebrar cada detector e exigir que o teste ACUSE

Chamador: declarado no `inventario.py` (lista `PECAS`), que o verificador
diario de saude roda todo dia. Peca cujo teste nao entra no mapa no mesmo
commit fica invisivel, e invisivel le igual a inexistente.

Rodar: python -B maquina/testar_regua_de_complexidade.py
"""
from __future__ import annotations

import io
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001,S110 - sem stdout nao ha para onde avisar
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

import regua_de_complexidade as rc  # noqa: E402

ALVO = os.path.join(AQUI, "regua_de_complexidade.py")
DIMS = [d for d, _, _ in rc.DIMENSOES]


def notas(*v):
    return dict(zip(DIMS, v))


# (notas, nivel esperado, por que)
CASOS = [
    # ── grupo 1: tem de exigir o processo inteiro ───────────────────────────
    (notas(5, 5, 5, 5, 5), rc.COMPLEX, "tudo no maximo: 25 de 25"),
    (notas(4, 3, 4, 3, 2), rc.COMPLEX, "16 — a borda de baixo do COMPLEX"),
    # Escrevi este caso esperando SIMPLE e o teste me reprovou: 1+1+1+1+5 = 9,
    # e 9 e STANDARD. A regua estava certa, o caso estava errado. Fica com o
    # valor medido, porque ele documenta a politica: risco CRITICO numa tarefa
    # minuscula puxa para STANDARD, nao para COMPLEX — a soma dilui um 5
    # solitario. Limite declarado no `ponytail:` da propria regua.
    (notas(1, 1, 1, 1, 5), rc.STANDARD,
     "risco 5 numa tarefa minuscula puxa para STANDARD, nao COMPLEX"),
    # ── grupo 2: NAO pode exigir ────────────────────────────────────────────
    (notas(1, 1, 1, 1, 1), rc.SIMPLE, "o minimo: 5 de 25, conserto de uma linha"),
    (notas(2, 1, 1, 2, 2), rc.SIMPLE, "8 — a borda de cima do SIMPLE"),
    # ── grupo 3: as BORDAS, uma a uma ───────────────────────────────────────
    (notas(2, 2, 1, 2, 2), rc.STANDARD, "9 — a borda de baixo do STANDARD"),
    (notas(3, 3, 3, 3, 3), rc.STANDARD, "15 — a borda de cima do STANDARD"),
]

# (nome, porque, de, para, casos que devem mudar de veredito)
MUTACOES = [
    ("o limiar do COMPLEX sobe de 16 para 17",
     "a borda exata: uma tarefa de 16 passaria a receber processo de STANDARD, "
     "sem a segunda critica nem o premortem",
     "    COMPLEX: (16, 25,",
     "    COMPLEX: (17, 25,",
     [(4, 3, 4, 3, 2)]),
    ("o limiar do STANDARD sobe de 9 para 10",
     "tarefa de 9 cairia para SIMPLE e perderia o PRD, a critica e o teste de "
     "integracao por etapa",
     "    STANDARD: (9, 15,",
     "    STANDARD: (10, 15,",
     # OS DOIS casos que somam 9, nao um. Declarar so um fazia o outro cair em
     # "fora do alvo" e a mutacao ler como sobrevivente — imprecisao minha, e o
     # criterio "nada alem do alvo" a pegou. O alvo de uma mutacao e todo caso
     # que ela DEVE mover, e isso se conta na aritmetica, nao na lembranca.
     [(2, 2, 1, 2, 2), (1, 1, 1, 1, 5)]),
    ("o nivel mais forte deixa de vencer (ordem invertida)",
     "a regua passaria a se dimensionar pelo caso medio e nao pelo pior: o "
     "teto de 25 seria avaliado como STANDARD",
     "    if total >= NIVEIS[COMPLEX][0]:\n        return COMPLEX, total",
     "    if total >= NIVEIS[STANDARD][0]:\n        return STANDARD, total",
     [(5, 5, 5, 5, 5), (4, 3, 4, 3, 2)]),
]


def main() -> int:
    falhas = []

    print("== 1. o nivel sai da conta (os dois grupos, e as bordas) ==")
    for n, esperado, porque in CASOS:
        got, total = rc.nivel(n)
        ok = got == esperado
        print("  [%s] %-56s %2d -> %s"
              % ("PASS " if ok else "FALHA", porque, total, got))
        if not ok:
            falhas.append("%s: esperava %s, veio %s" % (porque, esperado, got))

    print("\n== 2. entrada invalida REPROVA, nao vira veredito ==")
    ruins = [
        (notas(0, 1, 1, 1, 1), "nota 0 (abaixo da escala)"),
        (notas(6, 1, 1, 1, 1), "nota 6 (acima da escala)"),
        ({"escopo": 3}, "faltam 4 dimensoes"),
        (notas(True, 1, 1, 1, 1),
         "True: em Python passa por `int` e valeria 1 CALADO"),
        (notas(2.5, 1, 1, 1, 1), "nota fracionaria"),
    ]
    for n, porque in ruins:
        try:
            rc.nivel(n)
            print("  [FALHA] %-52s aceitou" % porque)
            falhas.append("aceitou entrada invalida: %s" % porque)
        except ValueError as e:
            print("  [PASS ] %-52s recusou: %s" % (porque, str(e)[:40]))

    print("\n== 3. o veredito MOSTRA as 5 notas ==")
    t = rc.veredito(notas(4, 3, 4, 3, 2), "tarefa X")
    faltam = [d for d in DIMS if d not in t]
    tem_fases = "FASES OBRIGATORIAS" in t
    tem_total = "16 de 25" in t
    ok = not faltam and tem_fases and tem_total
    print("  [%s] notas ausentes=%s · fases=%s · total visivel=%s"
          % ("PASS " if ok else "FALHA", faltam or "nenhuma", tem_fases,
             tem_total))
    if not ok:
        falhas.append("veredito incompleto: faltam=%s fases=%s total=%s"
                      % (faltam, tem_fases, tem_total))

    print("\n== 4. COMPLEX manda considerar QUEBRAR a tarefa ==")
    # A linha que mais muda o trabalho real: 16+ costuma ser duas tarefas, e um
    # nivel que so exige mais processo sem sugerir dividir empurra a pessoa a
    # fazer a tarefa grande com mais burocracia — o pior dos dois mundos.
    ok = "QUEBRAR" in rc.veredito(notas(5, 5, 5, 5, 5))
    print("  [%s] a sugestao de dividir aparece no COMPLEX"
          % ("PASS " if ok else "FALHA"))
    if not ok:
        falhas.append("COMPLEX nao sugere quebrar a tarefa")

    if falhas:
        print("\nREPROVADO — %d falha(s)" % len(falhas))
        for f in falhas:
            print("   %s" % f)
        print("\n   mutacao NAO AVALIADA: o baseline esta morto, e desarmar um "
              "detector que ja pega zero continua pegando zero.")
        return 1

    print("\n== 5. MUTACAO (quebrar o alvo e exigir que o teste ACUSE) ==")
    fonte = io.open(ALVO, encoding="utf-8").read()
    sobreviveram = []
    for nome, porque, de, para, devem in MUTACOES:
        if fonte.count(de) != 1:
            print("  [PULADA   ] %s — trecho aparece %d vez(es), nao 1"
                  % (nome, fonte.count(de)))
            sobreviveram.append(nome + " (ambigua)")
            continue
        ns = {}
        exec(compile(fonte.replace(de, para), "<mutante>", "exec"), ns)  # noqa: S102
        # CONJUNTO, nao contagem, e exige que NADA fora do alvo mude — a licao
        # que custou quatro reprovacoes: mutacao grosseira se passa por
        # deteccao fina do detector que ela deveria isolar.
        alvo_esperado = {tuple(v) for v in devem}
        mudou, fora = set(), set()
        for n, esperado, _porque in CASOS:
            chave = tuple(n[d] for d in DIMS)
            if ns["nivel"](n)[0] == esperado:
                continue
            (mudou if chave in alvo_esperado else fora).add(chave)
        if mudou == alvo_esperado and not fora:
            print("  [DETECTADA] %s" % nome)
            print("              %s" % porque)
            print("              %d de %d alvo(s) mudaram, 0 fora do alvo"
                  % (len(mudou), len(alvo_esperado)))
        else:
            print("  [SOBREVIVEU] %s" % nome)
            print("              alvos %s de %s; fora do alvo: %s"
                  % (sorted(mudou), sorted(alvo_esperado),
                     sorted(fora) or "nenhum"))
            sobreviveram.append(nome)

    if sobreviveram:
        print("\nREPROVADO — %d mutacao(oes) sobreviveram:" % len(sobreviveram))
        for s in sobreviveram:
            print("   %s" % s)
        return 1

    print("\nAPROVADO — %d casos, 0 falha, 0 mutacao sobrevivente: o nivel sai "
          "da conta,\nas bordas 8->9 e 15->16 estao no lugar, entrada invalida "
          "REPROVA (inclusive `True`),\no veredito mostra as notas, e as %d "
          "mutacoes sao acusadas." % (len(CASOS), len(MUTACOES)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
