# -*- coding: utf-8 -*-
r"""Prova de `regua_de_trava.py` — os dois grupos, mais mutacao.

O RITO DA CASA, e por que cada grupo existe:

  1. DEVE dar trava dura   — contrato cujo push vira efeito irreversivel
  2. NAO pode dar trava    — contrato de brinquedo; recomendar aqui e o modo de
                             falha por RUIDO, que ensina a pular o lembrete
  3. as 3 partes sempre    — recomendado · custo · saida daqui. Ele exigiu a
                             terceira, e lembrete sem ela deixa o projeto sem
                             nada enquanto a conta nao muda
  4. le o disco de verdade — um `projeto.yml` escrito e lido de volta
  5. MUTACAO               — quebrar cada detector e exigir que o teste ACUSE

Chamador: declarado no `inventario.py` (lista `PECAS`), que o verificador
diario de saude roda todo dia. Peca cujo teste nao entra na lista no mesmo
commit fica invisivel, e invisivel le igual a inexistente.

Rodar: python -B maquina/testar_regua_de_trava.py
"""
from __future__ import annotations

import io
import os
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                           # noqa: BLE001
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

import regua_de_trava as rt                                 # noqa: E402

ALVO = os.path.join(AQUI, "regua_de_trava.py")

# (efeito, dado_de_cliente, lifecycle, nivel_esperado, porque)
CASOS = [
    # ── grupo 1: tem de dar DURA ────────────────────────────────────────────
    ("deploy", "nao", "experimental", rt.DURA,
     "deploy: o push republica sozinho, sem ninguem no meio"),
    ("cobranca", "nao", "experimental", rt.DURA,
     "cobranca: dinheiro nao volta por git revert"),
    ("nenhum", "sim", "experimental", rt.DURA,
     "dado de cliente: LGPD, e o estrago nao volta atras"),
    ("deploy", "sim", "producao", rt.DURA,
     "tudo ligado ao mesmo tempo continua DURA, nao escala para alem"),
    # ── grupo 2: NAO pode dar dura ──────────────────────────────────────────
    ("nenhum", "nao", "experimental", rt.NENHUMA,
     "o projeto de brinquedo: recomendar aqui e ruido"),
    ("nenhum", "nao", "pausado", rt.NENHUMA,
     "pausado sem efeito tambem nao exige nada"),
    ("publica", "nao", "experimental", rt.MEDIA,
     "publica: tem leitor, mas nao ha deploy automatico"),
    ("mensagem", "nao", "experimental", rt.MEDIA,
     "mensagem: alguem recebe, e isso nao se desfaz"),
    ("nenhum", "nao", "producao", rt.MEDIA,
     "producao sem efeito declarado: ja tem gente dependendo"),
    # ── grupo 3: entrada suja nao pode virar veredito errado ────────────────
    ("  DEPLOY  ", "NAO", "  Experimental ", rt.DURA,
     "caixa e espaco nao mudam o veredito"),
    ("", "", "", rt.NENHUMA,
     "contrato VAZIO nao inventa trava — quem cobra e o fundacao_na_porta"),
]

# Cada mutacao: (nome, porque, de, para, casos_que_devem_mudar)
MUTACOES = [
    # O caso concreto que originou a regua: um site institucional cujo push
    # na `main` republica o dominio inteiro no ar. O caso fica AQUI, no
    # comentario, e nao dentro da string: a string e codigo, e codigo com
    # dado do dono obriga a versao publicada a divergir da interna — que e a
    # unica coisa proibida. Comentario se destila; codigo e identico.
    ("o verbo `deploy` sai da lista de efeito duro",
     "e o caso que originou a regua: um site cujo push republica o dominio no "
     "ar a cada commit. Sem este verbo, ele nasceria sem trava nenhuma",
     'EFEITO_DURO = {"deploy", "cobranca"}',
     'EFEITO_DURO = {"cobranca"}',
     ["deploy/nao/experimental"]),
    ("dado de cliente deixa de puxar trava",
     "LGPD vira opcional: projeto que toca dado de cliente cai para o nivel "
     "do efeito, que pode ser nenhum",
     # DESLIGA o detector, nao o inverte. `== "nao"` faria todo contrato sem
     # dado de cliente virar DURA — mutacao que muda o mundo inteiro nao prova
     # nada sobre o detector que ela deveria isolar, e foi o proprio criterio
     # "nada fora do alvo" desta suite que acusou isso.
     '    if cliente == "sim":\n        return DURA',
     '    if cliente == "jamais":\n        return DURA',
     ["nenhum/sim/experimental"]),
    ("producao para de contar",
     "projeto com gente dependendo passa a nao exigir nada, porque o efeito "
     "declarado e `nenhum`",
     '    if ciclo == "producao":\n        return MEDIA',
     '    if ciclo == "jamais":\n        return MEDIA',
     ["nenhum/nao/producao"]),
    ("o nivel mais forte deixa de vencer (ordem invertida)",
     "a regua passa a se dimensionar pela media e nao pelo pior estrago: "
     "`publica` seria avaliado antes de `deploy`",
     "    if efeito in EFEITO_DURO:\n        return DURA",
     "    if efeito in EFEITO_MEDIO:\n        return MEDIA",
     ["deploy/nao/experimental", "cobranca/nao/experimental"]),
]


def chave(efeito, cliente, ciclo):
    return "%s/%s/%s" % (efeito.strip().lower(), cliente.strip().lower(),
                         ciclo.strip().lower())


def main() -> int:
    falhas = []

    print("== 1. o nivel sai do contrato (os dois grupos) ==")
    for efeito, cliente, ciclo, esperado, porque in CASOS:
        got = rt.nivel(efeito, cliente, ciclo)
        ok = got == esperado
        print("  [%s] %-56s -> %s" % ("PASS " if ok else "FALHA", porque, got))
        if not ok:
            falhas.append("%s: esperava %s, veio %s" % (porque, esperado, got))

    print("\n== 2. as 3 partes aparecem SEMPRE, em todo nivel ==")
    for efeito, cliente, ciclo, esperado, _ in CASOS:
        txt = rt.lembrete(efeito, cliente, ciclo, "X")
        faltam = [p for p in ("RECOMENDADO", "CUSTO", "A SAIDA AQUI")
                  if p not in txt]
        # A terceira parte tem de ter CONTEUDO, nao so o rotulo: rotulo vazio
        # passaria no `in` e entregaria exatamente o lembrete sem saida que ele
        # mandou nao existir.
        corpo = txt.split("A SAIDA AQUI:")[-1].strip().strip("-").strip()
        ok = not faltam and len(corpo) > 40
        print("  [%s] nivel %-8s ausentes=%-8s saida com %d chars"
              % ("PASS " if ok else "FALHA", esperado,
                 ",".join(faltam) or "nenhuma", len(corpo)))
        if not ok:
            falhas.append("nivel %s: faltam %s / saida=%d chars"
                          % (esperado, faltam, len(corpo)))

    print("\n== 3. o lembrete diz QUAL resposta dele puxou o nivel ==")
    t = rt.lembrete("deploy", "nao", "experimental", "X")
    ok = "efeito_no_mundo: deploy" in t
    print("  [%s] cita o campo que decidiu" % ("PASS " if ok else "FALHA"))
    if not ok:
        falhas.append("o lembrete nao cita o campo que decidiu o nivel")

    print("\n== 4. le um projeto.yml de verdade, do disco ==")
    tmp = tempfile.mkdtemp(prefix="regua_")
    with io.open(os.path.join(tmp, "projeto.yml"), "w", encoding="utf-8") as f:
        f.write("# comentario que nao pode virar campo\n"
                "nome: teste\n"
                "lifecycle: producao   # comentario na MESMA linha\n"
                "efeito_no_mundo: deploy\n"
                "dado_de_cliente: nao\n")
    c = rt.campos(tmp)
    ok = (c["efeito_no_mundo"] == "deploy" and c["lifecycle"] == "producao"
          and c["dado_de_cliente"] == "nao")
    print("  [%s] leu do disco: %s" % ("PASS " if ok else "FALHA", c))
    if not ok:
        falhas.append("leitura do projeto.yml: %s" % c)
    vazio = rt.campos(os.path.join(tmp, "nao-existe"))
    ok2 = vazio == {"efeito_no_mundo": "", "dado_de_cliente": "",
                    "lifecycle": ""}
    print("  [%s] sem projeto.yml devolve vazio, nao explode"
          % ("PASS " if ok2 else "FALHA"))
    if not ok2:
        falhas.append("pasta sem projeto.yml: %s" % vazio)

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
    for nome, porque, de, para, devem_mudar in MUTACOES:
        if fonte.count(de) != 1:
            print("  [PULADA   ] %s — trecho aparece %d vez(es), nao 1"
                  % (nome, fonte.count(de)))
            sobreviveram.append(nome + " (ambigua)")
            continue
        # `__file__` entra no namespace de proposito: a peca deriva o proprio
        # caminho dele, e um modulo executado sem `__file__` e uma execucao que
        # nao existe na vida real. Sem esta linha a mutacao morria de
        # `NameError` e o teste leria isso como "detectada" — mutacao que nem
        # roda nao prova detector nenhum.
        ns = {"__file__": ALVO}
        exec(compile(fonte.replace(de, para), "<mutante>", "exec"), ns)  # noqa: S102
        # CONJUNTO, nao contagem. Dois CASOS diferentes podem ter a MESMA chave
        # — `deploy/nao/experimental` e `  DEPLOY  /NAO/  Experimental ` sao o
        # mesmo contrato escrito sujo, e e de proposito que os dois estejam na
        # lista. Contar deu "2 de 1 mudaram" e leu como mutacao sobrevivente
        # quando a regua estava certa: metrica errada acusando saude errada,
        # que e o mesmo defeito do gate que mede a si mesmo.
        mudou, mudou_fora = set(), set()
        for efeito, cliente, ciclo, esperado, _ in CASOS:
            k = chave(efeito, cliente, ciclo)
            if ns["nivel"](efeito, cliente, ciclo) == esperado:
                continue
            (mudou if k in devem_mudar else mudou_fora).add(k)
        # As duas condicoes: mudou TUDO o que devia, e NADA alem. A segunda
        # impede que uma mutacao grosseira (quebrar a regua inteira) se passe
        # por deteccao fina do detector que ela deveria isolar.
        if mudou == set(devem_mudar) and not mudou_fora:
            print("  [DETECTADA] %s" % nome)
            print("              %s" % porque)
            print("              %d de %d alvo(s) mudaram, 0 fora do alvo"
                  % (len(mudou), len(set(devem_mudar))))
        else:
            print("  [SOBREVIVEU] %s — alvos mudados %s de %s; fora do alvo: %s"
                  % (nome, sorted(mudou), sorted(set(devem_mudar)),
                     sorted(mudou_fora) or "nenhum"))
            sobreviveram.append(nome)

    if sobreviveram:
        print("\nREPROVADO — %d mutacao(oes) sobreviveram:" % len(sobreviveram))
        for s in sobreviveram:
            print("   %s" % s)
        return 1

    print("\nAPROVADO — %d casos, 0 falha, 0 mutacao sobrevivente: o nivel sai "
          "do contrato,\nas 3 partes sempre aparecem, o disco e lido de "
          "verdade, e as %d mutacoes sao acusadas."
          % (len(CASOS), len(MUTACOES)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
