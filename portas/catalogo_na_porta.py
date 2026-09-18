# -*- coding: utf-8 -*-
r"""O CATÁLOGO INTERROMPE NA PORTA — hook PreToolUse de criação de arquivo.

Nasceu de uma correção do dono da casa, verbatim:

    *"testei é bom, mas não tem uso agora: precisamos que TODOS os projetos
    tenham esse mapeamento, pq se eu pedir algo em algum momento relacionado
    àquela solução, nós temos aquilo já mapeado (…) se eu abrir outro projeto,
    novo ou existente, ele tem que saber que aquilo existe"*

A CAUSA, VERIFICADA. O recall é **BM25 — busca por palavra**
`[medido em prompt_memory.py: bm25_search, top_k=5]`. Ele devolve o que casa com
as palavras que ELE escreve. Quando ele diz *"roda os blocos"*, as palavras são
"blocos" e "vídeo" — **"graphify" nunca aparece**, porque não está na frase. É um
sistema que RESPONDE PERGUNTA, não que OFERECE o que eu não sei procurar. Foi
assim que uma ferramenta aprovada no catálogo sumiu por um mês: para eu
lembrar dele, eu já teria que estar lembrando.

E o pré-voo do `CLAUDE.md` não salva, porque manda consultar o catálogo em
*"escolha de stack/ferramenta"* — o que depende de EU classificar a situação
assim. Eu não classifiquei.

A SOLUÇÃO: **o gatilho é a AÇÃO, não a palavra.** O catálogo chega no segundo em
que eu vou criar a peça 29 — que é exatamente o instante em que eu erro. Não
depende de ele mencionar nada nem de eu classificar nada.

🔴 INTERROMPE, NÃO AVISA (T9, OK dele). Na primeira tentativa de criar um arquivo
de código novo, a criação é NEGADA e a resposta traz (a) as ferramentas aprovadas
e sem uso e (b) o que no próprio projeto já faz coisa parecida. Se depois disso a
criação ainda fizer sentido, basta repetir — a segunda passa. Aviso que não
interrompe é decoração; e uma negação por arquivo não trava trabalho nenhum.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import tempfile


# ── log do gate ─────────────────────────────────────────────────────────────
# Só REGISTRA; nunca decide nada. Existe porque o gate barrava em silêncio: o
# bloqueio acontecia, ninguém via, e o painel da mente não tinha como mostrar a
# mente se autocontrolando. Qualquer erro aqui é engolido — um log que falha
# jamais pode derrubar um guard.
def _log_gate(nome, linhas):
    try:
        import datetime
        motivo = ""
        for _l in (linhas or []):
            _l = (_l or "").strip()
            if _l and not _l.startswith(("·", "-", "`")):
                motivo = _l[:150]
                break
        alvo = ""
        try:
            alvo = str(globals().get("file_path", "") or globals().get("caminho", ""))[:120]
        except Exception:
            pass
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "gates.log"),
                  "a", encoding="utf-8") as _f:
            _f.write("\t".join([
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                nome, "deny", alvo, motivo]) + "\n")
    except Exception:
        pass


CODIGO = (".py", ".js", ".ts", ".tsx", ".mjs", ".sh", ".sql", ".ps1")


def catalogo_do_disco(fonte=None):
    """O caminho do catalogo de ferramentas, lido do `casa.json`.

    🔴 ELE ESTAVA ESCRITO AQUI, com o nome do usuario do disco no meio. Isso e
    dado da casa dentro do codigo pela quinta vez nesta maquina, e o sintoma
    seria o de sempre: noutra maquina o caminho nao existe, a funcao devolve
    lista vazia, e o gate deixa de lembrar de qualquer ferramenta — sem
    quebrar, sem avisar.

    ⚠️ AUSENCIA AQUI NAO LEVANTA, e e a unica diferenca em relacao aos outros
    campos do `casa.json`. Quem nao mantem um catalogo assim deixa vazio e o
    gate segue barrando o resto: ele so para de lembrar. Levantar aqui tornaria
    a peca inutil para quem nao tem o habito, e gate que exige um habito que a
    pessoa nao tem e desinstalado no primeiro dia.
    """
    caminho = fonte or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "casa.json")
    try:
        with io.open(caminho, encoding="utf-8") as fh:
            rel = (json.load(fh).get("catalogo_de_ferramentas") or "").strip()
    except Exception:                                       # noqa: BLE001
        return ""
    if not rel:
        return ""
    return os.path.join(os.path.expanduser("~"), rel.replace("/", os.sep))


MOC = catalogo_do_disco()
# 🔴 AS PASTAS QUE O GATE NAO OLHA — por SEGMENTO, nunca por pedaco de string
# com barra dentro.
#
# A lista dizia `"\\temp\\"` e `"/temp/"`, que sao as duas formas do Windows e
# de um caminho POSIX chamado `temp`. Ela nao conhecia `/tmp`, que e o nome
# real no Linux e no Mac, nem `.git/` com barra para frente. Quem rodasse isto
# fora do Windows tinha o gate analisando arquivo temporario e o interior do
# `.git` — em silencio, porque um gate que analisa demais so parece chato.
#
# 🔑 Escrever o separador de caminho dentro do termo e o defeito: ele amarra a
# regra a um sistema operacional e obriga a lembrar de TODAS as grafias. Aqui
# o caminho e quebrado em segmentos e o que se compara e o NOME da pasta.
IGNORAR = ("scratchpad", "temp", "tmp", "node_modules", "graphify-out",
           "__pycache__", "tasks", ".git", "_vsl_tmp")


def em_pasta_ignorada(caminho, ignorar=None):
    """O caminho passa por alguma pasta que o gate nao olha?

    ⚠️ Compara SEGMENTO, nao substring: `temperatura.py` nao mora numa pasta
    chamada `temp`, e um detector que casa substring diria que sim.
    """
    partes = [p for p in caminho.replace("\\", "/").lower().split("/") if p]
    alvo = set(IGNORAR if ignorar is None else ignorar)
    return any(p in alvo for p in partes)


def _ja_perguntei(sessao, alvo):
    """Um arquivo só é interrompido UMA vez por sessão."""
    marca = os.path.join(tempfile.gettempdir(),
                         f"catalogo_porta_{sessao or 'x'}.json")
    vistos = []
    if os.path.exists(marca):
        try:
            vistos = json.load(io.open(marca, encoding="utf-8"))
        except ValueError:
            vistos = []
    if alvo in vistos:
        return True
    vistos.append(alvo)
    json.dump(vistos, io.open(marca, "w", encoding="utf-8"))
    return False


def aprovadas_sem_uso(limite=6):
    """Linhas do catálogo com veredito de ADOÇÃO e sem `arquivo:linha` de uso.

    A régua do T8/regra 5: *não existe "aprovado, a adotar"* — ou está EM USO com
    o `arquivo:linha` de quem chama, ou está DESCARTADO com motivo. Aqui a leitura
    é textual de propósito: o catálogo é markdown escrito à mão, e um parser
    esperto erraria calado. Se a linha diz "adotar/testado/validado" e não mostra
    um caminho de arquivo, ela entra na lista.
    """
    if not os.path.exists(MOC):
        return []
    fora = []
    with io.open(MOC, encoding="utf-8", errors="replace") as fh:
        for ln in fh:
            if not ln.startswith("|") or len(ln) < 40:
                continue
            baixo = ln.lower()
            if not any(k in baixo for k in ("adotar", "✅ testado", "validado",
                                            "em produção", "piloto ok")):
                continue
            if re.search(r"[\w/\\-]+\.(py|js|ts|sh|md|json):\d+", ln):
                continue                       # tem chamador declarado
            if "em uso" in baixo or "descartad" in baixo:
                continue                       # já respondida, num sentido ou no outro
            nome = ln.split("|")[1].strip()
            if nome and len(nome) < 160:
                fora.append(re.sub(r"[\[\]]", "", nome))
    return fora[:limite]


def parecidos(alvo, limite=6):
    """Arquivos do mesmo projeto cujo nome divide um pedaço com o novo."""
    base = os.path.splitext(os.path.basename(alvo))[0].lower()
    toks = {t for t in re.split(r"[_\-.]", base) if len(t) >= 4}
    if not toks:
        return []
    dono = raiz = os.path.dirname(os.path.abspath(alvo))
    # sobe até a raiz do projeto (onde houver .git), no máximo 4 níveis
    achou = False
    for _ in range(4):
        if os.path.isdir(os.path.join(raiz, ".git")):
            achou = True
            break
        pai = os.path.dirname(raiz)
        if pai == raiz:
            break
        raiz = pai
    # Sem .git em 4 níveis, `raiz` acabava na raiz do usuário e o os.walk varria
    # a pasta inteira dele: 45,3 s contra o timeout de 15 s do hook `[medido
    # medido]`. O gate NEGAVA certo e morria antes de responder — inerte e
    # calado justamente fora de repo (`~/.claude/hooks`, scripts soltos). Sem
    # âncora de projeto, o alcance é a pasta do próprio arquivo.
    if not achou:
        raiz = dono
    achados = []
    for r, dirs, arqs in os.walk(raiz):
        dirs[:] = [d for d in dirs if not d.startswith(".")
                   and d not in ("node_modules", "__pycache__", "graphify-out")]
        for f in arqs:
            if not f.endswith(CODIGO) or f == os.path.basename(alvo):
                continue
            n = os.path.splitext(f)[0].lower()
            if any(t in n for t in toks):
                achados.append(os.path.relpath(os.path.join(r, f), raiz))
                if len(achados) >= limite:
                    return achados
    return achados


def main():
    # o catálogo tem ★, · e emoji; sem isto o hook morre com UnicodeEncodeError
    # no cp1252 do Windows e some sem dizer nada — hook que falha calado é o
    # mesmo defeito que ele está me cobrando, um nível abaixo.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                       # noqa: BLE001
        pass
    # o mesmo cp1252 do comentário acima também morde na ENTRADA: `json.load(
    # sys.stdin)` decodificava o payload no locale e todo caminho com acento
    # (`instalação/`, `Documentação/`) chegava mojibake. A extensão sobrevive
    # (ASCII no fim), mas o `os.path.exists(alvo)` da linha abaixo passa a olhar
    # um caminho que não existe `[medido: correto True / mojibake False]`
    # — então a EDIÇÃO de um .py já existente era tratada como criação e
    # interrompida. Falso positivo, não falso negativo: o gate travaria trabalho
    # legítimo. Caminho ASCII sobrevivia por sorte; o do soberano não.
    try:
        ent = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
    except (ValueError, AttributeError):
        return
    ti = ent.get("tool_input") or {}
    alvo = ti.get("file_path") or ""
    if not alvo or not alvo.endswith(CODIGO):
        return
    if os.path.exists(alvo):
        return                                  # editar não é criar
    if em_pasta_ignorada(alvo):
        return
    if _ja_perguntei(ent.get("session_id"), os.path.abspath(alvo)):
        return

    sem_uso, iguais = aprovadas_sem_uso(), parecidos(alvo)
    linhas = [
        f"PARE ANTES DE CRIAR `{os.path.basename(alvo)}`.",
        "",
        "Este é o instante em que mais uma peça nasce sem ninguém para "
        "chamá-la — o padrão nomeado aqui como *\"toda vez você somente cria, "
        "não usa\"*. Responda as três, na resposta ao usuário, antes de "
        "repetir a criação (a 2ª tentativa passa):",
        "",
        "1. **Já existe algo que faz isto?** Se existe, use ou estenda.",
        "2. **Quem vai CHAMAR esta peça?** Diga o `arquivo:linha`. Sem chamador "
        "no mesmo commit, não é entrega — é órfã.",
        "3. **Alguma ferramenta já aprovada resolve?**",
    ]
    if iguais:
        linhas += ["", "No projeto já existem, com nome parecido:"]
        linhas += [f"  · {x}" for x in iguais]
    if sem_uso:
        linhas += ["", "Aprovadas no catálogo e SEM uso declarado "
                       "(`_MOC_ferramentas.md`):"]
        linhas += [f"  · {x}" for x in sem_uso]
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "\n".join(linhas)}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
