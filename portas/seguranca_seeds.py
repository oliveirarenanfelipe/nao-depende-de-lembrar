# -*- coding: utf-8 -*-
r"""A FONTE ÚNICA do que é "default inseguro" nesta casa.

Por que este módulo existe em vez de o código estar repetido: o gate da porta
(`seguranca_na_porta.py`) e a varredura diária (`mente_health.py`, bloco `[6j]`)
precisam da MESMA definição. Duas cópias divergiriam em silêncio na primeira
calibração, e aí um aprovaria o que o outro reprova
([[concept_a_identidade_do_registro_tem_de_ser_uma]]).

Os seeds vivem em `seeds_inseguros.json`: 6 famílias do `trailofbits/insecure-defaults`
(CC-BY-SA-4.0) mais a família `casa-aprendeu`, que são os padrões que ESTA casa
pagou para descobrir e que os seeds de fora NÃO pegam.

🔴 O caso que provou a necessidade da família própria: o teste de
mutação mostrou que `verify_mode = ssl.CERT_NONE` — o defeito exato dos 88
arquivos achados, com uma senha real trafegando — **passava** pelos seeds
de fora, porque eles exigem MAIÚSCULA ou `= False`.

Os 7 filtros de ruído também moram aqui, e cada um nasceu de um falso positivo
medido na primeira execução `[medido: 19 achados, e os que conferi eram
todos falso positivo — `owner: "owner"` é mapa de papéis, `md5()` de arquivo é
checksum, e um deles pegou "ECB" no nome de um PDF da Intelbras]`.
Gate ruidoso é gate ignorado.

CHAMADORES: `seguranca_na_porta.py` (PreToolUse Edit|Write) e `mente_health.py`
bloco `[6j]` (varredura diária).
"""
import io
import json
import os
import re

AQUI = os.path.dirname(os.path.abspath(__file__))
SEEDS = os.path.join(AQUI, "seeds_inseguros.json")

# famílias de alto sinal. `fallback-secrets` e `debug-features` ficam de fora da
# contagem grave: o primeiro sozinho deu 1.266 achados e quase nenhum
# prestava.
GRAVES = ("default-credentials", "fail-open-security", "permissive-access",
          "weak-crypto", "casa-aprendeu", "casa-portugues", "execucao-perigosa",
          # As duas de POR_ARQUIVO (vetores 23 e 24 do checklist).
          # Não vivem no JSON porque não são perguntas de linha; entram aqui
          # porque é esta tupla que o `[6j]` usa para decidir o que reportar.
          "llm-sem-teto", "vetorial-sem-isolamento")

# `casa-portugues` e `execucao-perigosa` entraram depois, e cada uma so
# foi promovida DEPOIS de medir sinal e ruido em codigo real - a regra que o
# `fallback-secrets` ensinou quando deu 1.266 achados quase todos falsos.
#
#   casa-portugues  - nasceu do buraco de VOCABULARIO: o gitleaks e os 42 seeds
#     pegam `password = "..."` e nao pegam `SENHA = "..."` [medido: 2 de 4 linhas
#     identicas em conteudo]. Tres defesas cegas pelo mesmo motivo. Achou 7
#     segredos reais, concentrados em dois projetos. Com as isencoes:
#     19 achados em 16 arquivos.
#   execucao-perigosa - eval/exec/pickle/yaml.load/shell=True/SQL concatenado.
#     Calibrada de 175 achados brutos para 5 que o gate ve, com ZERO falso
#     positivo entre eles. Pega 2 classes que nem o semgrep p/python pegou
#     (yaml.load sem SafeLoader, assert como controle de autorizacao).

_DEFESA = re.compile(
    r"auth|verify|ssl|tls|cert|csrf|token|secret|senha|password|cred"
    r"|login|permiss|rate.?limit|guard|sign|hmac|encrypt|cripto|admin"
    r"|debug|allow|origin|cors", re.I)


# ---------------------------------------------------------------------------
# ISENÇÕES — quem NÃO se audita, e o motivo de cada um
#
# Estavam só dentro do `seguranca_na_porta.py`, e a varredura diária tinha as
# dela, menores. Resultado medido: dos 13 alertas graves do relatorio,
# **11 eram fixture de teste** e um estava numa worktree — 85% de ruído num
# vigia, que é a definição de vigia que se ignora. O módulo existe para não
# haver duas verdades, e a segunda verdade estava nas isenções.
ISENTOS = (
    # aqui MORAM os padrões: o arquivo que descreve o defeito casa com ele mesmo
    "\\.claude\\hooks\\", "/.claude/hooks/", "seeds_inseguros",
    # teste precisa poder escrever o caso ruim, senão não prova nada
    "\\test", "/test", "_test.", ".test.", ".spec.", "fixture", "conftest",
    "testar_", "__tests__",
    # não é código nosso, ou não é fonte
    "node_modules", "\\.git\\", "/.git/", "\\dist\\", "/dist/",
    "\\build\\", "/build/", ".venv", "site-packages", "__pycache__",
    "graphify-out", "\\backup", "/backup", ".bak",
    # worktree: é a mesma árvore de outro repo, e o achado seria contado 2x.
    # ⚠️ O sufixo `-wt` é a convenção desta casa para worktree; quem usar outra
    # acrescenta a sua aqui. Já houve um nome de projeto escrito nesta
    # linha, o que resolvia UM worktree e nenhum outro.
    "-wt", "worktrees",
)


def e_isento(caminho):
    """True quando este caminho está fora do alcance da auditoria."""
    b = caminho.lower().replace("/", os.sep).replace("\\", os.sep)
    return any(x.replace("/", os.sep).replace("\\", os.sep) in b for x in ISENTOS)


def _posix2py(p):
    return (p.replace("[[:space:]]", r"\s").replace("[[:alpha:]]", "[A-Za-z]")
             .replace("[[:alnum:]]", r"\w").replace("[[:digit:]]", r"\d"))


class SeedsAusentes(RuntimeError):
    """Os seeds não carregaram. Quem chama TEM de tratar, e negando."""


def carregar(so_graves=True, fonte=None):
    """[(familia, regex_compilado)] — os seeds prontos para uso.

    🔴 ISTO DEVOLVIA `[]` EM SILÊNCIO, e era o pior modo de falha possível
    para um detector: sem o JSON, o gate não quebrava — ele passava a APROVAR
    tudo, e nada no mundo avisava. Medido ao rodar a peça destilada
    numa pasta sem o dado: três famílias que barram (`TLS desligado`, `segredo
    em portugues`, `shell=True com entrada`) responderam `passou`, e o veredito
    lido de fora era "o código está limpo".

    Detector vazio é indistinguível de detector que não achou nada. Agora ele
    levanta, e quem chama decide — o gate da porta NEGA com a explicação, em
    vez de deixar passar. É a mesma escolha do `privacidade.json` e do
    `mapa.json`: **falhar alto, nunca cair para vazio.**
    """
    caminho = fonte or SEEDS
    try:
        with io.open(caminho, encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception as e:                                  # noqa: BLE001
        # `from e` preserva a causa ORIGINAL na cadeia. Sem ele, quem le o
        # traceback ve so "os seeds nao carregaram" e perde a informacao que
        # resolve: se foi arquivo ausente, permissao negada ou JSON quebrado.
        raise SeedsAusentes(
            "nao consegui ler os seeds em `%s` (%s). Sem eles este detector "
            "aprova TODO codigo em silencio, que e o unico erro aqui que nao "
            "se descobre depois." % (caminho, type(e).__name__)) from e
    if not d:
        raise SeedsAusentes(
            "o arquivo de seeds `%s` esta vazio. Detector sem padrao nao acha "
            "nada, e 'nada achado' le igual a 'codigo limpo'." % caminho)
    saida = []
    for fam, bloco in d.items():
        if so_graves and fam not in GRAVES:
            continue
        for s in bloco.get("seeds", []):
            try:
                saida.append((fam, re.compile(_posix2py(s))))
            except re.error:
                pass                       # seed quebrado não derruba o gate
    return saida


def e_ruido(ln):
    """True quando a linha casa um seed por acidente. Cada caso foi medido."""
    # 1) variável de ambiente sem cara de defesa: `getenv("NEXEN_SMOKE","0")`
    m = re.search(r"(?:getenv|environ\.get|process\.env)\s*[\(\.]\s*"
                  r"[\"']?([A-Za-z_][A-Za-z0-9_]*)", ln)
    if m and not _DEFESA.search(m.group(1)):
        return True
    # 2) comentário: `# [medido: ... 0,0000]` casava permissive-access
    if re.match(r"\s*(#|//|/\*|\*)", ln):
        return True
    # 3) mapa de papéis, não credencial: `admin: "admin", operador: "operador"`
    if re.search(r"(\w+)\s*:\s*[\"']\1[\"']", ln):
        return True
    # 4) md5/sha1 como CHECKSUM de arquivo, não como cripto de segredo
    if re.search(r"(?:md5|sha1)\s*\(", ln, re.I) and not re.search(
            r"senha|password|token|secret|assinat|sign|hmac|auth|cred", ln, re.I):
        return True
    # 5) sigla de cripto dentro de URL ou nome de arquivo
    if re.search(r"https?://|\.(?:pdf|png|jpe?g|zip|docx?|xlsx?)\b", ln, re.I) \
            and not re.search(r"(?:cipher|crypt|algorithm|mode)\s*[:=]", ln, re.I):
        return True
    # 6) sigla de cifra exige contexto de cifra: "ECB Wi-Fi" é produto Intelbras
    if re.search(r"\b(?:DESede|DES|RC2|RC4|Blowfish|ECB|PKCS1v15)\b", ln) \
            and not re.search(r"cipher|crypt|encrypt|decrypt|algorithm|"
                              r"\bkey\b|hash|padding", ln, re.I):
        return True
    # 7) marca de evidência da casa dentro de docstring
    if re.search(r"\[(?:medido|n[ãa]o.?verificado|alvo|estimado)\b", ln, re.I):
        return True
    # 🔴 NÃO EXISTE UM FILTRO 8, e o motivo fica escrito:
    # escrevi um, para pular linha que mostra segredo já tapado (`[REDIGIDO]`,
    # `****`). Justifiquei com o último alerta do [6j], onde eu tinha LIDO
    # `?secret=[REDIGIDO]` na docstring do `secret_sanitizer.py`. Aquele
    # `[REDIGIDO]` não estava no arquivo: era o hook `redigir_segredos` da casa
    # tapando o texto NA MINHA TELA. Nos bytes está `?secret=/JWT`.
    # Filtro promovido por observação fantasma é pior que alerta conhecido, e a
    # regra desta casa é medir sinal e ruído em código real antes de promover
    # (foi o que o `fallback-secrets` ensinou com 1.266 achados).
    # O alerta que sobra é conhecido e benigno: docstring do sanitizador
    # descrevendo o que ele protege. Um alerta conhecido não afoga ninguém.
    return False


# ---------------------------------------------------------------------------
# SEGUNDO MODO: perguntas que são sobre o ARQUIVO, não sobre a linha
#
# `varrer` compara linha a linha, e isso basta para "esta linha desliga o TLS".
# Não basta para "este arquivo chama LLM pago e em lugar nenhum põe teto de
# token": a chamada ocupa 5 linhas e a defesa pode estar na 1ª ou na 40ª.
# Tentei escrever isso como regex multilinha e o gate passou 4 de 7 no teste —
# o varredor de linha não tinha como casar. O instrumento é que estava errado.
#
# Formato: gatilho presente E defesa ausente no texto inteiro = achado.
# Escrito assim, e não como um regex só, porque a pergunta é essa mesma.
POR_ARQUIVO = [
    {
        "familia": "llm-sem-teto",
        "titulo": ("Chamada de LLM pago sem teto de saída (OWASP LLM10, vetor 24 "
                   "do security-audit). O rate limit conta REQUISIÇÃO; isto conta "
                   "TOKEN e DINHEIRO."),
        "gatilho": r"(?:messages|completions)\.create\s*\(|"
                   r"api\.(?:anthropic|openai|groq)\.com/v\d",
        "defesa": r"max_tokens|max_output_tokens|maxTokens|maxOutputTokens",
        "conserto": "passe max_tokens na chamada, e limite o tamanho da entrada "
                    "ANTES de ela virar prompt",
    },
    {
        "familia": "vetorial-sem-isolamento",
        "titulo": ("Busca por similaridade sem filtro de dono (OWASP LLM08, vetor 23). "
                   "Índice de embeddings responde por similaridade e quase nunca tem "
                   "controle de acesso por linha: a mesma busca alcança documento de "
                   "outro cliente e a resposta parece certa."),
        "gatilho": r"\.(?:similarity_search\w*|max_marginal_relevance_search)\s*\(|"
                   r"query_embeddings\s*=|\.query\s*\(\s*(?:vector|queryVector)",
        "defesa": r"filter|where|tenant|namespace|metadata|\bowner\b|usuario_id|cliente_id",
        "conserto": "filtre por dono DENTRO da consulta, não só na tela",
    },
]
_POR_ARQUIVO = [(d, re.compile(d["gatilho"], re.I), re.compile(d["defesa"], re.I))
                for d in POR_ARQUIVO]


def varrer_arquivo(texto):
    """[(familia, n_linha, trecho)] — o que só se vê olhando o arquivo inteiro.

    ⚠️ Exige o texto COMPLETO do arquivo. Rodar isto sobre o `new_string` de um
    Edit produz falso positivo (a defesa está no resto do arquivo, fora do
    pedaço) — [[concept-a-condicao-de-arquivo-julgada-sobre-o-pedaco]]. Quem
    chama é responsável por montar o conteúdo final.
    """
    achados = []
    linhas = texto.split("\n")
    for d, rx_g, rx_d in _POR_ARQUIVO:
        if rx_d.search(texto):
            continue
        for n, ln in enumerate(linhas, 1):
            if len(ln) > 400 or e_ruido(ln):
                continue
            if rx_g.search(ln):
                achados.append((d["familia"], n, ln.strip()[:110]))
                break
    return achados


def conserto_de(familia):
    for d in POR_ARQUIVO:
        if d["familia"] == familia:
            return d["conserto"]
    return ""


def varrer(texto, regras=None, limite=None):
    """[(familia, n_linha, trecho)] — o que este texto tem de default inseguro."""
    regras = regras if regras is not None else carregar()
    achados = []
    for n, ln in enumerate(texto.split("\n"), 1):
        if len(ln) > 400 or e_ruido(ln):
            continue
        for fam, rx in regras:
            m = rx.search(ln)
            if m:
                achados.append((fam, n, ln.strip()[:110]))
                break
        if limite and len(achados) >= limite:
            break
    return achados
