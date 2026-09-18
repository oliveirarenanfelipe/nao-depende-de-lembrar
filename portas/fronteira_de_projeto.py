# -*- coding: utf-8 -*-
r"""A FRONTEIRA DO PROJETO INTERROMPE NA PORTA — hook PreToolUse sobre Edit|Write.

Nasceu de uma pergunta simples: por que uma sessao aberta num projeto estava
atacando a pendencia de OUTRO? A investigacao achou DUAS causas, e so a
segunda e defeito:

  1. VER pendencia de outro projeto e DELIBERADO. `session_context.py:115`
     (`ronda_urgente`) injeta a Ronda do Diretor em toda sessao, lendo o
     o relatorio de saude, que varre a pasta de memoria de todos. O arquivo soberano
     registra o porque quando a fila-mestra saiu do CLAUDE.md: *"eu deixei
     de enxergar pendencia de projeto alheio sem abrir o projeto. O cruzamento entre
     projetos passa a depender do mente_health"*. Isso e o objetivo, nao vazamento.

  2. AGIR e que nao tinha freio. Nada no sistema marcava a fronteira:
     - o texto injetado so diz de quem e o trabalho em UM dos tres blocos
       (`session_context.py:176`, "e trabalho MEU"); os outros dois listam projeto
       e id sem dizer se e para agir;
     - `grep` por "projeto alheio|outro projeto|escopo do projeto" no CLAUDE.md
       soberano e em `rules/` = **0 ocorrencias** `[medido]`;
     - dos 3 gates que negam (`soberano_na_porta`, `catalogo_na_porta`,
       `ler_com_pontaria`), nenhum olha a que projeto o arquivo pertence.
     Resultado medido no dia: numa sessao do **Personal** eu escrevi em **5
     projetos DIFERENTES**, incluindo a pasta dos hooks — e nada o deteve
     em nenhum.

O QUE ESTE HOOK FAZ. Ele nao proibe: ele torna VISIVEL. A escrita fora do projeto da
sessao e negada UMA vez, com o nome do projeto dono na mensagem; repetir passa. Assim
uma ordem legitima de mover pendencia entre projetos custa uma
frase minha dizendo por que estou saindo do projeto — e ele ve isso na conversa, em
vez de acontecer calado. Protecao que cobra pedagio de quem faz certo vira imposto:
[[concept-o-freio-mora-no-formato-da-saida]].

A resolucao de projeto REUSA o `fronteira_lib` — o mesmo reconhecedor que o
indexador e o recall usam. Reimplementar faria as duas divergirem em silencio,
que e o defeito de [[concept_a_identidade_do_registro_tem_de_ser_uma]].

⚠️ Ate agora ele chamava o `memory_lib` para isso, e o `memory_lib` apenas
repassava ao `fronteira_lib`. O intermediario custava caro num lugar so, e o
lugar que importa: a biblioteca de memoria nao viaja com esta porta, entao no
repositorio publicado o `import` falhava, o `except` devolvia vazio, e "nao ha
dono" LE COMO "pode escrever". Medido: 3 casos de recusa viraram aprovacao.

NAO barra (transversal por desenho):
  · `Projeto/_shared/`               — existe para ser usado por todos
  · `~/.claude/` fora de `projects/` — hooks, rules, commands, skills: a mente e global
  · pasta temporaria / scratchpad    — rascunho nao e entrega

⚠️ LIMITE CONHECIDO, declarado em vez de mascarado. A separacao vale ate onde o
`detect_project` separa. Uma etapa tem entrada propria no mapa e sai
com o apelido dela; as outras NAO tem, e caem no apelido do projeto PAI
`[medido]` — o proprio `memory_lib.detect_project` documenta isso como
coincidencia. Efeito: escrever numa etapa a partir da sessao de outra NAO e
barrado. Nao consertei aqui de proposito: mexer no `PROJECT_MAP` muda como o recall
pontua projeto, e um gate novo nao e hora de mexer no motor de busca. Fica como
limite ate alguem decidir a entrada do mapa.

Chamador: `~/.claude/settings.json` -> PreToolUse, matcher `Edit|Write`.
"""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile

HOME = os.path.expanduser("~")
RAIZ_PROJ = os.path.normcase(os.path.join(HOME, "Projeto"))
RAIZ_CLAUDE = os.path.normcase(os.path.join(HOME, ".claude"))
RAIZ_MENTE = os.path.normcase(os.path.join(HOME, ".claude", "projects"))
sys.path.insert(0, os.path.join(HOME, ".claude", "hooks"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fronteira_lib as fl  # noqa: E402  — o unico reconhecedor de dono

# nao barra: caminho transversal por desenho, ou rascunho
LIVRE = (
    os.path.normcase(os.path.join(HOME, "Projeto", "_shared")),
    os.path.normcase(tempfile.gettempdir()),
)


def _slug_do_caminho(caminho: str) -> str:
    """Slug do projeto DONO de um caminho, ou '' quando o caminho e transversal."""
    orig = os.path.abspath(caminho)
    p = os.path.normcase(orig)
    if any(p.startswith(x) for x in LIVRE):
        return ""
    if p.startswith(RAIZ_MENTE):
        # ~/.claude/projects/<prefixo-do-agente>-<Dono>/...
        #
        # a pasta sai de `orig`, NAO de `p`. `normcase` existe para
        # comparar prefixo no Windows e faz lowercase; mas quem recebe esta
        # string do outro lado e `memory_lib.project_dir_to_slug:141`, que tira
        # o prefixo com um `.replace()` LITERAL, sensivel a caixa. Em
        # minuscula o prefixo nao sai, a string inteira desce ao `_slug_de_base`
        # e so escapa quem tem fragmento no PROJECT_MAP — por substring, que e
        # acaso. Medido: 7 das 29 pastas divergiam e o gate negava a escrita na
        # PROPRIA memoria delas; o modo de falha e
        # pior que a lista, porque projeto novo fora do PROJECT_MAP nasce assim.
        # O conserto mora aqui, e nao no `memory_lib`, porque o outro chamador
        # (`memory_lib.py:187`) ja passa `d.name` na caixa do disco: mexer no
        # reconhecedor mudaria como o recall pontua projeto, sem necessidade.
        # `normcase` no Windows so troca caixa e separador, entao o corte por
        # `len(RAIZ_MENTE)` cai no mesmo indice nas duas strings.
        resto = orig[len(RAIZ_MENTE):].lstrip("\\/")
        pasta = resto.split(os.sep)[0] if resto else ""
        try:
            return fl.apelido_da_pasta_de_memoria(pasta) if pasta else ""
        except Exception:                            # noqa: BLE001
            return ""
    if p.startswith(RAIZ_CLAUDE):
        return ""                                    # hooks/rules/commands: mente global
    if p.startswith(RAIZ_PROJ):
        # antes daqui ia `os.path.dirname(p)`, o caminho INTEIRO, e o
        # `detect_project` junta tudo depois de `Projeto\` com hifen: uma subpasta
        # do proprio projeto virava outro projeto e a escrita legitima era negada.
        # Medido: 15 dos 33 diretorios de `Projeto\` (os que nao estao no
        # PROJECT_MAP). Agora so a PASTA-RAIZ vai ao resolvedor — que e a forma
        # para a qual ele nasceu, ja que ele recebia o cwd.
        # `dono_de_caminho` no lugar de `raiz_de_projeto`: o dono
        # sai do `projeto.yml` mais proximo, nao da primeira pasta sob
        # `Projeto\`. Ver o docstring da funcao em `fronteira_lib.py` para os 3
        # casos que a deducao errava e para o raio (o `bash_na_porta` NAO e
        # tocado, de proposito). Trocado nos DOIS lados, aqui e no cwd: uma
        # ponta so mudaria a gramatica de metade da comparacao.
        raiz = fl.dono_de_caminho(p)
        if not raiz:
            return ""
        try:
            return fl.apelido_do_diretorio(os.path.join(fl.RAIZ_PROJ, raiz))
        except Exception:                            # noqa: BLE001
            return ""
    return ""


def _ja_avisei(sessao: str, alvo: str) -> bool:
    """Um arquivo so interrompe UMA vez por sessao — repetir passa."""
    marca = os.path.join(tempfile.gettempdir(), f"fronteira_{sessao or 'x'}.json")
    vistos = []
    if os.path.exists(marca):
        try:
            vistos = json.load(io.open(marca, encoding="utf-8"))
        except ValueError:
            vistos = []
    if alvo in vistos:
        return True
    vistos.append(alvo)
    try:
        json.dump(vistos, io.open(marca, "w", encoding="utf-8"))
    except OSError:
        pass
    return False


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                # noqa: BLE001
        pass
    # stdin em BYTES: `json.load(sys.stdin)` abre no locale do Windows (cp1252) e o
    # payload chega em utf-8 — foi assim que o `soberano_na_porta` nasceu INERTE.
    try:
        ent = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
    except (ValueError, AttributeError):
        return

    alvo = (ent.get("tool_input") or {}).get("file_path") or ""
    if not alvo:
        return

    dono = _slug_do_caminho(alvo)
    if not dono:
        return                                       # transversal: passa

    cwd = ent.get("cwd") or os.getcwd()
    # As DUAS pontas passam pela mesma reducao a pasta-raiz. Normalizar so o alvo
    # deixaria a sessao aberta numa subpasta divergindo do proprio projeto — o
    # mesmo defeito, do outro lado da comparacao.
    raiz_cwd = fl.dono_de_caminho(cwd)
    try:
        sessao_proj = fl.apelido_do_diretorio(
            os.path.join(fl.RAIZ_PROJ, raiz_cwd) if raiz_cwd else cwd)
    except Exception:                                # noqa: BLE001
        return                                       # sem resolvedor, nao inventa veredito

    if not sessao_proj or sessao_proj == dono:
        return

    if _ja_avisei(ent.get("session_id"), os.path.normcase(os.path.abspath(alvo))):
        return

    linhas = [
        f"PARE — este arquivo e do projeto **{dono}**, e a sessao esta em "
        f"**{sessao_proj}**.",
        "",
        f"  arquivo: {alvo}",
        "",
        "Ver pendencia de outro projeto e de proposito: a Ronda do Diretor "
        "(`session_context.py`) injeta o cruzamento em toda sessao. Mas ela e "
        "AVISO, nao fila de trabalho — trabalhar num item exige abrir o projeto "
        "dono, que carrega o pre-voo dele (DECISIONS.md, CLAUDE.md do projeto, "
        "stories). Daqui, esse contexto nao esta na mesa.",
        "",
        "Origem, verbatim: *\"cara, isso nao e pendencia sua! pq esta vindo "
        "para ca? aqui e um projeto, pq vc esta atacando pendencia de "
        "outro?\"* — no mesmo dia o agente escreveu em 5 projetos a partir de "
        "uma sessao so, sem nada o deter.",
        "",
        "Se a escrita AQUI for mesmo a certa — ordem dele, ou peca transversal — "
        "diga numa frase por que, e repita: a 2a tentativa no mesmo arquivo passa.",
    ]
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "\n".join(linhas)}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
