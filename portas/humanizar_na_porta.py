# -*- coding: utf-8 -*-
r"""O HUMANIZER INTERROMPE NA PORTA — hook PreToolUse de Write|Edit em prosa.

Ordem do dono da casa, verbatim:

    *"eu preciso que vc valide, rode, aprenda e ou incorpore no nosso modo de
    trabalho ou traga a skill de alguma maneira para gente passar a usar (...)
    não tem como inserir no modus operandi como vamos fazer para quando eu te
    pedir algo vc acionar saber que tem que acionar ele sem dar o /humanizer"*

O CHAMADOR DA SKILL `~/.claude/skills/humanizer/` (blader/humanizer, MIT,
46.891★ `[medido na API do GitHub]`). A skill sozinha é conhecimento
parado: ela diz COMO consertar e nunca diz QUANDO. Sem este arquivo ela seria
mais uma peça órfã — o padrão nomeado aqui como (*"toda vez você somente
cria, não usa"*).

O GATILHO É A AÇÃO, NÃO A PALAVRA. Mesma doutrina do `catalogo_na_porta.py`:
não depende de ele escrever "humaniza isso", nem de eu classificar o texto como
"prosa". Dispara no segundo em que eu vou GRAVAR o texto.

A RÉGUA É MEDIDA, NÃO OPINIÃO `[medido num corpus de controle]`:

    197 legendas humanas do vault (27.138 palavras) .... índice 23,73
    fala humana transcrita (1.745 palavras) ........... índice 18,34
    eu, no mesmo transcript (20.437 palavras) .......... índice 71,83
    eu, nota de hoje / candidaturas .................... índice 92,43 / 82,91

Escrevo 3,9x mais marcas de IA que ele, e quase tudo é NEGRITO DECORATIVO
(45-57 por mil palavras contra 0,00 dele) e TRAVESSÃO (21-31 contra 0,00).
Não é vocabulário: é formatação por regra.

TETO = 35, não 0. Reescrever um trecho real levou o índice a 2,84 — abaixo do
humano — e negrito zero atrapalha ELE, que lê varrendo a tela atrás da decisão.
35 é a faixa humana com folga para markdown técnico.

INTERROMPE UMA VEZ POR ARQUIVO. A segunda tentativa passa: às vezes o negrito é
estrutura legítima (índice, tabela de decisão). Aviso que nunca deixa passar
vira ruído, e ruído se ignora.

CHAMADOR DESTE ARQUIVO: `~/.claude/settings.json`, bloco PreToolUse `Edit|Write`.
TESTE DE MUTAÇÃO: `~/.claude/hooks/testar_humanizar_na_porta.py`.
"""
import io
import json
import os
import re
import sys
import time
import unicodedata

TETO = 35.0
MIN_PALAVRAS = 150
ESTADO = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "humanizar_na_porta.estado.json")

# prosa que um humano lê. `.txt` entra porque mensagem e roteiro nascem assim.
# `.html` entrou porque a peça que vai ao CLIENTE é HTML: proposta,
# apresentação, LP, e-mail. O gate nem chegava a medi-las: `main()` retornava na
# checagem de extensão, antes do medidor. Não era verde falso, era AUSÊNCIA de
# medição — e ausência de medição lê igual a aprovação.
EXT = (".md", ".txt", ".html", ".htm")

# Isentos, e o motivo de cada um:
#  - memory/ e MEMORY.md: o negrito ali é ESTRUTURA de índice (o gancho que eu
#    varro no recall), não decoração. Medi 29,34 nas minhas notas de conceito e
#    boa parte é isso.
#  - CLAUDE.md / _MOC_ / pendencias_ativas: mesma coisa, e são lidos por mim,
#    não por humano de fora.
#  - node_modules, .git, dist, build: nem prosa são.
ISENTOS = ("\\memory\\", "/memory/", "memory.md", "_moc_", "pendencias_ativas",
           "claude.md", "node_modules", "\\.git\\", "/.git/", "\\dist\\",
           "/dist/", "\\build\\", "/build/", "package-lock", "changelog")

TELLS = {
    "#1 nao-X-mas-Y":        r"\bn[ãa]o\s+(?:[éeh]|se trata de|apenas|s[óo])\b[^.!?\n]{2,60}?,?\s*(?:mas|e sim|[ée])\b",
    "#3 frase de efeito":    r"\b(no fim do dia|no fim das contas|a verdade [ée] que|deixa isso assentar|leia de novo|pense nisso)\b",
    "#5 discute com ninguem": r"\b(n[ãa]o se engane|ao contr[áa]rio do que (?:muitos|voc[êe]) pensa|esque[çc]a (?:tudo )?o que)\b",
    "#8 TRAVESSAO":          r"[—–]",
    "#9 qualificador empilhado": r"\b(pode(?:ria)? (?:ser que )?talvez|talvez possa|geralmente costuma|normalmente tende)\b",
    # ⚠️ `\w+(ada)` casava **'e cada'** — "cada" termina em -ada. Falso positivo
    # que barrava texto bom `[medido: o texto de controle BOM deu 24,4 de
    # passiva, e 2 das 6 ocorrencias eram "e cada"]`. Agora exige 4+ letras e
    # exclui os substantivos comuns que terminam igual.
    "#11 voz passiva":       r"\b(?:foi|foram|ser[áa]|ser[ãa]o|sido|[ée]|s[ãa]o)\s+(?!cada\b|nada\b|toda\b|vida\b|medida\b|entrada\b|sa[íi]da\b|d[úu]vida\b|comida\b|jornada\b)\w{4,}(?:ado|ada|ados|adas|ido|ida|idos|idas)\b",
    "#12 palavra generica de IA": r"\b(crucial|fundamental|robusto|robusta|aprofundar|alavancar|primordial|essencial|no entanto|al[ée]m disso|em suma|vale ressaltar|[ée] importante (?:notar|ressaltar|destacar)|em resumo|por fim|dessa forma|portanto)\b",
    "#13 significancia inflada": r"\b(revolucion[áa]?\w*|muda tudo|game[- ]chang\w+|divisor de [áa]guas|nunca mais ser[áa]|transform\w+ completamente)\b",
    "#16 linguagem de venda": r"\b(descubra|desbloqueie|potencialize|turbine|poderos[ao]|incr[íi]vel|impression\w+|surpreendente)\b",
    "#18 evita ser/ter":     r"\b(consiste em|configura-se como|apresenta-se como|caracteriza-se por)\b",
    "#19 NEGRITO decorativo": r"\*\*[^*\n]{1,80}\*\*",
    "#22 residuo de chat":   r"^\s*(claro!|[óo]tima pergunta|com certeza!|aqui est[áa]|espero que (?:isso )?ajude)",
    "#23 disclaimer de modelo": r"\b(como (?:um )?modelo de linguagem|at[ée] minha [úu]ltima atualiza[çc][ãa]o|n[ãa]o tenho acesso a)\b",
}

# Ficaram FORA por calibração contra controle humano, não por esquecimento:
# CAPS (pega sigla), aspas curvas (convenção tipográfica),
# par hifenizado (pega termo técnico), closer de uma linha (INVERSO em PT
# falado: a fala humana usa 18,34 e a do LLM, 0,73). Contar errado é pior.
#
# E o **#6 tríade forçada** saiu depois de o teste reprovar texto bom:
# `\w+, \w+ e \w+` não distingue a tríade por RITMO (o tell) de uma enumeração
# legítima de três coisas. No texto de controle ele contou
# "coleta, tratamento e entrega" — que é a lista real do que o sistema faz.
# Um regex não alcança essa diferença; quem alcança é a leitura, e para isso
# existe a skill. O tell continua descrito em `skills/humanizer/SKILL.md` §6.


# ── HTML ───────────────────────────────────────────────────────────────────
#
# A ARMADILHA, e ela é real: acrescentar `<strong>` à lista de tells SEM limpar
# as tags piora o diagnóstico em vez de melhorar. As tags são contadas como
# palavras (`<b>\w+\b>` casa "strong"), então o denominador infla e o índice
# cai. Medido num texto de controle: 1.040 palavras contadas no HTML
# contra 960 no markdown idêntico, +8,3% de denominador. Duas falhas na MESMA
# direção — não ver o tell e inflar o total.
#
# 🔑 O CONSERTO NÃO É UM SEGUNDO CONJUNTO DE TELLS. É traduzir o HTML para a
# gramática que os 13 tells já falam: `<strong>x</strong>` vira `**x**`, a
# entidade `&mdash;` vira `—`, e só depois as tags somem. Assim existe UM
# reconhecedor de negrito, não dois que divergem em silêncio
# ([[concept_a_identidade_do_registro_tem_de_ser_uma]]).
#
# ⚠️ LIMITE DECLARADO: negrito por CLASSE de CSS (`class="destaque"` com
# `font-weight:700` na folha) NÃO é alcançado — exigiria interpretar o CSS.
# Fica dito em vez de mascarado; o que se alcança é tag e style inline.
RE_HTML_SUJO = re.compile(r"<(script|style)\b.*?</\1>|<!--.*?-->", re.S | re.I)
RE_HTML_FORTE = re.compile(
    r"<(strong|b)\b[^>]*>(.*?)</\1>", re.S | re.I)
RE_HTML_FORTE_STYLE = re.compile(
    r"<(\w+)\b[^>]*style\s*=\s*[\"'][^\"']*font-weight\s*:\s*"
    r"(?:bold|bolder|[6-9]00)[^\"']*[\"'][^>]*>(.*?)</\1>", re.S | re.I)
RE_HTML_TAG = re.compile(r"<[^>]+>")
ENTIDADES = [("&mdash;", "—"), ("&ndash;", "–"), ("&nbsp;", " "),
             ("&quot;", '"'), ("&#39;", "'"), ("&lt;", "<"), ("&gt;", ">"),
             ("&amp;", "&")]


def html_para_prosa(txt):
    """HTML -> a mesma prosa em markdown, para os tells existentes medirem."""
    txt = RE_HTML_SUJO.sub(" ", txt)
    for _ in range(3):                      # aninhamento raso: <b><span>x</span></b>
        txt = RE_HTML_FORTE_STYLE.sub(lambda m: "**%s**" % m.group(2), txt)
        txt = RE_HTML_FORTE.sub(lambda m: "**%s**" % m.group(2), txt)
    txt = RE_HTML_TAG.sub(" ", txt)         # o resto some: não é prosa nem tell
    for ent, char in ENTIDADES:
        txt = txt.replace(ent, char)
    return txt


def so_prosa(txt):
    if "<" in txt and re.search(r"<[a-zA-Z!/]", txt):
        txt = html_para_prosa(txt)
    txt = re.sub(r"^---\n.*?\n---\n", "", txt, flags=re.S)
    txt = re.sub(r"```.*?```", " ", txt, flags=re.S)
    txt = re.sub(r"`[^`]+`", " ", txt)
    txt = re.sub(r"^\|.*$", " ", txt, flags=re.M)
    txt = re.sub(r"https?://\S+", " ", txt)
    return txt


def medir(txt):
    t = so_prosa(unicodedata.normalize("NFC", txt))
    palavras = len(re.findall(r"\b[\wÀ-ÿ]+\b", t))
    if palavras < MIN_PALAVRAS:
        return None, palavras, []
    por_tell = []
    total = 0
    for nome, pat in TELLS.items():
        flags = re.I | (re.M if nome.startswith("#22") else 0)
        n = len(re.findall(pat, t, flags))
        if n:
            por_tell.append((round(n * 1000.0 / palavras, 1), nome, n))
        total += n
    por_tell.sort(reverse=True)
    return round(total * 1000.0 / palavras, 1), palavras, por_tell


def ja_avisei(sessao, alvo):
    """Uma interrupção por arquivo. A segunda gravação passa."""
    chave = "%s|%s" % (sessao or "?", alvo)
    try:
        with io.open(ESTADO, encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception:                                   # noqa: BLE001
        d = {}
    agora = time.time()
    d = {k: v for k, v in d.items() if agora - v < 86400}   # 24 h
    visto = chave in d
    d[chave] = agora
    try:
        with io.open(ESTADO, "w", encoding="utf-8") as fh:
            json.dump(d, fh)
    except Exception:                                   # noqa: BLE001
        pass
    return visto


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                   # noqa: BLE001
        pass
    try:
        ent = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
    except (ValueError, AttributeError):
        return
    ti = ent.get("tool_input") or {}
    alvo = ti.get("file_path") or ""
    if not alvo.lower().endswith(EXT):
        return
    baixo = alvo.lower().replace("/", os.sep).replace("\\", os.sep)
    if any(x.replace("/", os.sep).replace("\\", os.sep) in baixo for x in ISENTOS):
        return

    texto = ti.get("content") or ti.get("new_string") or ""
    if not texto:
        return
    indice, palavras, por_tell = medir(texto)
    if indice is None or indice <= TETO:
        return
    if ja_avisei(ent.get("session_id"), os.path.abspath(alvo)):
        return

    piores = por_tell[:3]
    linhas = [
        "PARE — este texto tem cara de IA, e ele vai ser lido por gente.",
        "",
        "`%s` — indice %.1f por 1000 palavras, teto %.0f (%d palavras de prosa)."
        % (os.path.basename(alvo), indice, TETO, palavras),
        "Regua medida num corpus de controle: legenda humana 23,7 · "
        "fala humana transcrita 18,3 · texto de LLM 71,8 a 92,4.",
        "",
        "Os que mais pesam aqui:",
    ]
    for taxa, nome, n in piores:
        linhas.append("  · %-28s %5.1f /1000  (%d vezes)" % (nome, taxa, n))
    linhas += [
        "",
        "Leia `~/.claude/skills/humanizer/SKILL.md` (os 25 tells e o conserto de "
        "cada um) e reescreva ANTES de gravar. O alvo nao e zero: e <= %.0f."
        % TETO,
        "Os dois que quase sempre explicam o estouro: negrito decorativo (so "
        "onde carrega decisao) e travessao (vira ponto ou virgula).",
        "",
        "Nada se perde no conserto: no teste medido o indice caiu 75,1 -> 2,8 "
        "com +5,7% de palavras e ZERO fato perdido (63 numeros conferidos).",
        "",
        "Se o negrito aqui for estrutura de verdade (indice, tabela de decisao), "
        "repita a gravacao — a 2a passa.",
    ]
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "\n".join(linhas)}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
