# -*- coding: utf-8 -*-
r"""O RIGOR DO /sdd SAI DE UMA CONTA, NAO DO MEU OLHO.

Nasceu quando o dono perguntou se a extracao de um framework antigo tinha
sido 100%: *"tudo que a gente podia aprender e pegar de essencia deles ja foi
feito? os agentes? a arquitetura, coisas de seguranca, tudo? 100%?"*. A
conferencia item a item no disco disse **nao**: 4 de 6 extraidos, e faltavam os
dois gates do `/sdd`. `grep` em `commands/sdd.md` dava **0** para `SIMPLE`,
`STANDARD`, `COMPLEX` e `phantom` `[medido]`.

O QUE ERA, no `.aiox-core/development/tasks/spec-assess-complexity.md` (461
linhas, das quais a maior parte e boilerplate de pipeline que esta casa nao
usa): cinco dimensoes pontuadas de 1 a 5, somadas, com limiares que decidem
QUAIS fases do trabalho sao obrigatorias. Trouxe a conta, a escala e os limiares
verbatim; deixei o pipeline deles la, porque as fases desta casa sao outras.

POR QUE E PECA EXECUTAVEL, e nao um paragrafo no `/sdd`. Hoje **eu** decido no
olho se uma tarefa merece SPEC inteira — e "esta tarefa e complexa?" cada sessao
responde diferente, exatamente como "este projeto e profissional?" respondia
antes da `regua_de_trava`. Conta com entrada declarada da o mesmo resultado em
toda sessao, e pode ser conferida depois.

NAO E A `regua_de_trava`, e considerei junta-las: aquela le o `projeto.yml` e
decide TRAVA DE PUBLICACAO de um projeto; esta recebe 5 notas de uma TAREFA e
decide RIGOR DE PROCESSO. Entrada, saida e momento diferentes — juntar faria uma
peca que responde duas perguntas. O que reuso dela e a FORMA: campos -> nivel ->
consequencia, com as notas visiveis ao lado do veredito.

⚠️ O QUE ESTA PECA NAO E. Ela nao BARRA nada — quem pontua sou eu, e eu poderia
pontuar baixo para fugir do rigor. Declarado em vez de mascarado: a casa prefere
bloqueio a aviso, e isto e aviso. O que ela garante e que a decisao fique
ESCRITA, com as 5 notas ao lado, onde ele pode discordar de UMA nota em vez de
discordar de um palpite meu. [[concept-decisao-exige-antes-e-depois]]

Chamador: o comando de desenvolvimento guiado por spec, Fase 0, no mesmo
commit. Prova: `maquina/testar_regua_de_complexidade.py`, com mutacao.
"""
from __future__ import annotations

import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                           # noqa: BLE001
    pass

SIMPLE, STANDARD, COMPLEX = "SIMPLE", "STANDARD", "COMPLEX"

# As 5 dimensoes, verbatim do AIOX. A escala 1-5 de cada uma esta aqui porque
# pontuar sem a regua ao lado e adivinhar com numero.
DIMENSOES = [
    ("escopo", "Quantos arquivos/componentes serao afetados?", [
        "1-2 arquivos, mudanca localizada",
        "3-5 arquivos, um modulo",
        "6-10 arquivos, multiplos modulos",
        "11-20 arquivos, cross-cutting",
        "20+ arquivos, arquitetura inteira"]),
    ("integracao", "Quantas integracoes externas sao necessarias?", [
        "nenhuma integracao externa",
        "1 API interna existente",
        "1-2 APIs externas ou nova API interna",
        "3+ APIs ou integracao complexa (webhook, evento)",
        "orquestracao de multiplos sistemas"]),
    ("infra", "Mudancas de infraestrutura necessarias?", [
        "nenhuma mudanca de infra",
        "configuracao simples (env vars)",
        "nova dependencia ou servico",
        "mudanca de banco de dados / schema",
        "nova infraestrutura (servidor, container)"]),
    ("conhecimento", "Conhecimento necessario para implementar", [
        "padroes que ja existem no codebase",
        "tecnologia conhecida, padrao novo",
        "biblioteca nova, documentacao clara",
        "tecnologia nova para a casa",
        "dominio desconhecido, pesquisa necessaria"]),
    ("risco", "Risco de impacto negativo", [
        "baixo, peca isolada",
        "moderado, afeta poucos",
        "medio, peca importante",
        "alto, afeta muitos",
        "critico, core do sistema"]),
]

# Limiares verbatim do AIOX. As FASES foram traduzidas para as desta casa: la
# eram [gather, assess, research, spec, critique, plan]; aqui sao as 3 fases do
# `/sdd` mais os gates que ja existem no soberano (R4).
NIVEIS = {
    SIMPLE: (5, 8, "tarefa direta, padroes existentes", "< 1 dia", [
        "SPEC curta (o problema, o aceite, o fora-de-escopo)",
        "implementar",
        "1 check rodavel"]),
    STANDARD: (9, 15, "complexidade moderada, alguma pesquisa", "1-3 dias", [
        "PRD",
        "SPEC com aceite Given/When/Then",
        "CRITICA da spec antes de implementar",
        "implementar em etapas, >=1 teste de integracao por etapa"]),
    COMPLEX: (16, 25, "alta complexidade, multiplas iteracoes", "3+ dias", [
        "PRD",
        "pesquisa declarada (o que NAO sei ainda)",
        "SPEC com aceite Given/When/Then",
        "CRITICA, revisao, SEGUNDA critica",
        "premortem + tripwire + red team (R4)",
        "implementar em etapas, sem avancar sem a anterior comprovada",
        "considerar QUEBRAR em tarefas menores — 16+ costuma ser duas"]),
}


def nivel(notas: dict) -> tuple:
    """(nivel, total). `notas` = {dimensao: 1..5} para as 5 dimensoes.

    ponytail: SOMA PURA, verbatim do AIOX, e ela DILUI um 5 solitario. Medido
    ao escrever o teste: `risco=5` com todo o resto em 1 soma 9 e sai STANDARD,
    nao COMPLEX — ou seja, uma tarefa de um arquivo so que mexe no core do
    sistema nao recebe a segunda critica nem o premortem. Fica assim porque a
    conta veio inteira de fora e mudar a formula sem caso real e inventar
    politica; o caminho de upgrade, se doer na pratica, e um piso por dimensao
    (`risco>=4` forca no minimo STANDARD, `risco=5` forca COMPLEX) — e ai com
    um caso medido ao lado, nao por intuicao.
    """
    faltam = [d for d, _, _ in DIMENSOES if d not in notas]
    if faltam:
        raise ValueError("faltam notas: %s" % ", ".join(faltam))
    total = 0
    for d, _, _ in DIMENSOES:
        n = notas[d]
        if not isinstance(n, int) or isinstance(n, bool) or not 1 <= n <= 5:
            raise ValueError("%s: nota %r fora de 1..5" % (d, n))
        total += n
    # Ordem: do mais forte para o mais fraco, como na `regua_de_trava` — a
    # exigencia se dimensiona pelo pior caso, nunca pela media.
    if total >= NIVEIS[COMPLEX][0]:
        return COMPLEX, total
    if total >= NIVEIS[STANDARD][0]:
        return STANDARD, total
    return SIMPLE, total


def veredito(notas: dict, tarefa: str = "") -> str:
    n, total = nivel(notas)
    _, _, desc, tempo, fases = NIVEIS[n]
    L = ["", "  " + "-" * 68,
         "  RIGOR DO /sdd — %s  (total %d de 25)%s"
         % (n, total, ("  ·  " + tarefa) if tarefa else ""),
         "  " + "-" * 68,
         "  %s. Tempo tipico: %s." % (desc.capitalize(), tempo),
         "", "  As notas que produziram isto:"]
    for d, _pergunta, escala in DIMENSOES:
        L.append("    %-13s %d/5  %s" % (d, notas[d], escala[notas[d] - 1]))
    L += ["", "  FASES OBRIGATORIAS:"]
    L += ["    %d. %s" % (i, f) for i, f in enumerate(fases, 1)]
    L += ["  " + "-" * 68, ""]
    return "\n".join(L)


def main(argv) -> int:
    if len(argv) == 6:
        try:
            notas = {d: int(argv[i + 1])
                     for i, (d, _, _) in enumerate(DIMENSOES)}
            print(veredito(notas))
        except ValueError as e:
            print("erro: %s" % e)
            return 2
        return 0
    print("O rigor do /sdd sai de uma conta, nao do olho.\n")
    print("uso: python regua_de_complexidade.py <escopo> <integracao> <infra> "
          "<conhecimento> <risco>")
    print("     cada uma de 1 a 5. Ex.: 2 1 1 2 3\n")
    for d, pergunta, escala in DIMENSOES:
        print("  %s — %s" % (d.upper(), pergunta))
        for i, t in enumerate(escala, 1):
            print("     %d  %s" % (i, t))
    print("\n  total 5-8 = SIMPLE   ·   9-15 = STANDARD   ·   16-25 = COMPLEX")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
