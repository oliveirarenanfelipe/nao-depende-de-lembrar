# -*- coding: utf-8 -*-
r"""Teste de mutação do `humanizar_na_porta.py`.

A regra da casa (REGRA #0, tabela "o que conta como prova"): *"o gate reprova de
verdade"* exige **mutação** — quebrar o alvo e ver o gate falhar. Gate que passou
não provou nada; ele pode estar passando por acaso.

Roda o hook como o harness roda: processo separado, payload JSON no stdin.

CHAMADOR: `mente_health.py`, bloco [6f] — o mesmo lugar de onde saem
`testar_fronteira` [6e] e `golden_recall` [6c]. Sem isso este arquivo seria
órfão, e o gate voltaria a ser decoração na primeira refatoração.
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(AQUI, "humanizar_na_porta.py")

# Texto com cara de IA: negrito em tudo, travessao como conector, triade.
RUIM = (
    "## O panorama da entrega\n\n"
    "A **arquitetura** proposta — que nasce da **necessidade real** do cliente — "
    "cobre tres frentes: **coleta**, **tratamento** e **entrega**. Nao e apenas "
    "uma melhoria incremental, mas uma mudanca de patamar. **Cada modulo** foi "
    "pensado para ser **robusto**, **escalavel** e **observavel**.\n\n"
    "O **ponto crucial** aqui — e vale ressaltar isso — e que a **solucao** "
    "elimina o retrabalho. Alem disso, o **ganho de tempo** e **imediato**, o "
    "**custo** e **previsivel** e a **manutencao** fica **simples**.\n\n"
    "Em suma: a **entrega** muda tudo. Descubra como o **fluxo** se torna "
    "**poderoso** quando cada etapa — da **captura** ao **relatorio** — passa a "
    "ser **rastreavel**. Portanto, o **proximo passo** e **fundamental**: "
    "aprofundar o **mapeamento**, alavancar o **conhecimento** existente e "
    "**consolidar** o **processo**.\n\n"
    "Nao se engane: o **resultado** nao e so tecnico, e estrategico. "
    "**Cada decisao** foi **validada** — e **cada numero** foi **conferido**. "
    "O **impacto** e **surpreendente**, o **retorno** e **incrivel** e a "
    "**operacao** fica **impressionante**. A verdade e que o **time** ganha "
    "**autonomia**, **velocidade** e **confianca** — tudo ao mesmo tempo.\n"
) * 2

# Mesmo conteudo, escrito como gente: sem negrito decorativo nem travessao.
BOM = (
    "## O panorama da entrega\n\n"
    "A arquitetura proposta nasce da necessidade real do cliente e cobre tres "
    "frentes: coleta, tratamento e entrega. Cada modulo foi pensado para "
    "aguentar carga, crescer e deixar rastro do que aconteceu.\n\n"
    "O que decide aqui e o fim do retrabalho. O ganho de tempo aparece na "
    "primeira semana, o custo fica previsivel e a manutencao cabe numa pessoa.\n\n"
    "O fluxo inteiro passa a ser rastreavel, da captura ao relatorio. O proximo "
    "passo e mapear o que ja existe, reusar o que funciona e consolidar o "
    "processo num lugar so.\n\n"
    "O resultado tem efeito tecnico e comercial. Cada decisao foi validada e "
    "cada numero conferido na fonte. O time ganha autonomia e velocidade sem "
    "depender de quem escreveu o codigo.\n"
) * 2

CODIGO = "def f():\n    return 1\n" * 60


def roda(payload, hook=HOOK):
    p = subprocess.run([sys.executable, "-B", hook],
                       input=json.dumps(payload).encode("utf-8"),
                       capture_output=True)
    saida = p.stdout.decode("utf-8", "replace").strip()
    if not saida:
        return None
    try:
        return json.loads(saida)
    except ValueError:
        return None


def negou(res):
    return bool(res) and (res.get("hookSpecificOutput", {})
                          .get("permissionDecision") == "deny")


def caso(nome, payload, espera_deny, hook=HOOK):
    res = roda(payload, hook)
    ok = negou(res) == espera_deny
    print("  [%s] %-50s (esperado: %s)"
          % ("OK " if ok else "FALHA", nome, "NEGAR" if espera_deny else "passar"))
    return ok


def main():
    # Cada caso usa sessao propria: o hook so interrompe UMA vez por arquivo.
    # ⚠️ E o prefixo muda A CADA EXECUCAO. Sem isso o estado de 24 h da rodada
    # ANTERIOR marcava "ja avisei" e o gate deixava passar texto de indice 441,7
    # — o teste reprovava o gate por culpa do proprio teste `[medido]`.
    marca = "t%d" % int(time.time() * 1000)

    def pl(texto, alvo, sess):
        return {"session_id": marca + sess, "tool_name": "Write",
                "tool_input": {"file_path": alvo, "content": texto}}

    tmp = tempfile.gettempdir()
    md = os.path.join(tmp, "proposta_cliente.md")
    mem = os.path.join(tmp, "memory", "concept_x.md")
    py = os.path.join(tmp, "script.py")

    print("1. O gate REPROVA o que tem de reprovar")
    r = [caso("prosa com cara de IA -> NEGA", pl(RUIM, md, "s1"), True)]

    print("2. O gate DEIXA PASSAR o que nao e o alvo")
    r += [
        caso("mesmo conteudo escrito como gente", pl(BOM, md, "s2"), False),
        caso("arquivo .py (nao e prosa)", pl(CODIGO, py, "s3"), False),
        caso("dentro de memory/ (negrito e estrutura)", pl(RUIM, mem, "s4"), False),
        caso("texto curto (< 150 palavras)", pl(RUIM[:400], md, "s5"), False),
    ]

    print("3. Interrompe UMA vez por arquivo (a 2a passa)")
    p = pl(RUIM, md, "s6")
    primeira = negou(roda(p))
    segunda = negou(roda(p))
    ok = primeira and not segunda
    print("  [%s] 1a NEGA=%s, 2a NEGA=%s" % ("OK " if ok else "FALHA",
                                             primeira, segunda))
    r.append(ok)

    print("4. MUTACAO - quebrar o alvo e ver o gate falhar")
    # Se eu subir o teto para 9999, o caso 1 TEM de deixar de negar. Se continuar
    # negando, a decisao nao vem da regua medida: vem de outra coisa, e o verde
    # do caso 1 nao provava nada.
    mut = os.path.join(tmp, "mut_humanizar.py")
    io.open(mut, "w", encoding="utf-8").write(
        io.open(HOOK, encoding="utf-8").read().replace("TETO = 35.0",
                                                       "TETO = 9999.0"))
    r.append(caso("teto 9999 -> o MESMO texto ruim deixa de negar",
                  pl(RUIM, md, "s7"), False, hook=mut))
    # mutacao inversa: teto 0 faz ate o texto BOM ser barrado
    mut2 = os.path.join(tmp, "mut2_humanizar.py")
    io.open(mut2, "w", encoding="utf-8").write(
        io.open(HOOK, encoding="utf-8").read().replace("TETO = 35.0", "TETO = 0.0"))
    r.append(caso("teto 0 -> ate o texto bom e barrado",
                  pl(BOM, md, "s8"), True, hook=mut2))
    for f in (mut, mut2):
        try:
            os.remove(f)
        except OSError:
            pass

    print("%d de %d passaram." % (sum(r), len(r)))
    return 0 if all(r) else 1


if __name__ == "__main__":
    sys.exit(main())
