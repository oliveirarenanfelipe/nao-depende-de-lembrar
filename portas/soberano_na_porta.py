# -*- coding: utf-8 -*-
r"""A FILA-MESTRA INTERROMPE NA PORTA — hook PreToolUse sobre o CLAUDE.md.

Nasceu quando o harness avisou que o arquivo soberano passou dos 150 mil
caracteres. A causa foi medida na hora, e são três, todas de mecanismo:

  1. A skill `/salvar` (Passo 4) mandava editar `## Pendências Críticas` — seção
     que NÃO EXISTE desde uma reestruturação `[medido: 2 menções na skill,
     0 no CLAUDE.md]`. Sem alvo válido, cada sessão improvisava onde escrever, e
     improvisar é colar o texto fresco da sessão: narrativa longa.
  2. A mesma skill só sabia ADICIONAR — *"resolvida → marcar com ✅"*. Não existia,
     em lugar nenhum, regra de REMOÇÃO `[medido: grep = 0]`. Resultado: 112 itens
     já fechados ocupando 41.239 chars numa seção cujo cabeçalho promete "só itens
     abertos".
  3. Nada media o tamanho. `mente_health.py` vigiava órfãs, links e o vault, e não
     citava o CLAUDE.md.

Fila só com operação de entrada, alimentada por um procedimento que aponta para um
alvo morto, e sem medidor: cresce até estourar. Chegou a 148.861 chars de fila num
arquivo de 189.855 — 78% do que carrega em TODA sessão.

O QUE ESTE HOOK FAZ. O gatilho é a AÇÃO — o instante em que a linha gorda nasce,
não a auditoria seis semanas depois. Ele só olha edições que caem DENTRO da seção
da fila (o intervalo é calculado no arquivo real, não adivinhado), e nega três
coisas:

  · item de pendência acima de FILA_ITEM_MAX chars  → o detalhe é da micro mente
  · item entrando com status FECHADO (✅ ❌ ⛔)      → fechado SAI, não entra
  · bloco narrativo `>` longo dentro da fila         → resumo de sessão é do brief

🔴 INTERROMPE, NÃO AVISA. Mesma disciplina do `catalogo_na_porta.py` aprovada por
aqui: a primeira tentativa é NEGADA com a régua na mensagem; repetir
a mesma edição passa. A marca é por CONTEÚDO, não por arquivo — negar uma vez não
pode liberar o resto da sessão. Assim nunca trava trabalho e a violação deixa de
ser silenciosa. O que escapar aqui, o check [6] do `mente_health.py` acha depois.

Chamador: `~/.claude/settings.json` → PreToolUse, matcher `Edit|Write`.
"""
from __future__ import annotations

import hashlib
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


# 🔴 O CAMINHO ERA ABSOLUTO E FIXO, com o nome do usuario do disco dentro.
# Achado pela checagem `caminho preso` do inventario, na primeira vez
# que ela rodou. Noutra maquina o arquivo nao existe naquele endereco, a
# leitura falha, e o gate fica INERTE — exatamente o defeito que a docstring
# deste arquivo diz que ele ja sofreu uma vez, por outro motivo.
#
# 🔑 E gate inerte e indistinguivel de gate que aprovou: ele simplesmente para
# de reclamar, e silencio le igual a "esta tudo certo".
#
# Agora sai do `casa.json`, o mesmo dado que a fronteira ja usa, para nao
# existirem duas verdades sobre onde os projetos moram.
def _soberano_do_disco():
    """O caminho do arquivo soberano, derivado do `casa.json`."""
    aqui = os.path.dirname(os.path.abspath(__file__))
    pasta = "Projeto"
    try:
        with io.open(os.path.join(aqui, "casa.json"), encoding="utf-8") as fh:
            pasta = (json.load(fh).get("pasta_dos_projetos") or "").strip() \
                or pasta
    except Exception:  # noqa: BLE001,S110 - o default cobre, e e o da casa
        pass
    return os.path.normcase(
        os.path.join(os.path.expanduser("~"), pasta, "CLAUDE.md"))


SOBERANO = _soberano_do_disco()
SECAO = "## Pendências — fila-mestra"
FILA_ITEM_MAX = 180        # calibrado na distribuição real: p50 = 186 chars
NARRATIVA_MAX = 180        # linha `>` dentro da fila; o mesmo teto do item
ARQUIVO_MAX = 150_000      # o limite do harness do Claude Code

# `- ✅ **#id** — ...` / `- 🔴 **#247d** — ...`
ITEM = re.compile(r"^\s*[-*]\s+(\S+)\s+\*\*#([^*]+)\*\*")
FECHADO = ("✅", "❌", "⛔")


def _ja_negou(sessao, texto):
    """Nega a MESMA violação uma vez por sessão; repetir a edição passa."""
    marca = os.path.join(tempfile.gettempdir(),
                         f"soberano_porta_{sessao or 'x'}.json")
    chave = hashlib.sha256(texto.encode("utf-8", "replace")).hexdigest()[:16]
    vistos = []
    if os.path.exists(marca):
        try:
            vistos = json.load(io.open(marca, encoding="utf-8"))
        except ValueError:
            vistos = []
    if chave in vistos:
        return True
    vistos.append(chave)
    json.dump(vistos, io.open(marca, "w", encoding="utf-8"))
    return False


def _limites_da_fila(txt):
    """(inicio, fim) da seção da fila no arquivo REAL. (-1, -1) se não achar."""
    i = txt.find(SECAO)
    if i < 0:
        return -1, -1
    j = txt.find("\n## ", i + len(SECAO))
    return i, (j if j > 0 else len(txt))


def _itens_de_pendencia(linhas):
    """Linhas `- <status> **#id** — ...` — o formato da fila que foi EXTINTA.

    A fila-mestra saiu do soberano (decisão medida: 20.921
    tokens em toda requisição de todo projeto, 70% do arquivo). Sem esta função
    o gate ficaria INERTE justamente agora: `_limites_da_fila` devolve (-1,-1),
    o caminho do Edit retornava cedo, e a próxima sessão recriaria a fila sem
    nada reclamar. O propósito do guard não mudou — o soberano não engorda com
    pendência; o que mudou é que agora o teto é ZERO, não 180 chars.
    """
    return [ITEM.match(l_.rstrip("\r")).group(2)
            for l_ in linhas if ITEM.match(l_.rstrip("\r"))]


def _violacoes(linhas):
    """As três formas de furar a regra escrita no cabeçalho da própria seção."""
    fora = []
    for ln in linhas:
        bruto = ln.rstrip("\r")
        m = ITEM.match(bruto)
        if m:
            status, cid = m.group(1), m.group(2)
            if any(f in status for f in FECHADO):
                fora.append((f"#{cid}", "FECHADO entrando no soberano",
                             "o ✅ vai na micro mente do dono; a linha SAI daqui"))
            elif len(bruto) > FILA_ITEM_MAX:
                fora.append((f"#{cid}", f"{len(bruto)} chars (teto {FILA_ITEM_MAX})",
                             "o detalhe é da micro mente; aqui fica o gancho"))
        elif bruto.lstrip().startswith(">") and len(bruto) > NARRATIVA_MAX:
            fora.append(("(bloco >)", f"{len(bruto)} chars (teto {NARRATIVA_MAX})",
                         "resumo de sessão é do brief/micro mente, não do soberano"))
    return fora


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                            # noqa: BLE001
        pass
    # 🔴 stdin em BYTES, decodificado à força em utf-8. `json.load(sys.stdin)`
    # abre o stdin no locale do Windows (cp1252) e o payload chega em utf-8: o
    # `old_string` volta mojibake (79 → 87 chars), `atual.find(velho)` dá -1 e o
    # hook retorna em silêncio como se a edição fosse fora da fila. Foi assim que
    # este gate ficou INERTE desde que nasceu `[medido: mesmo payload, sem
    # PYTHONIOENCODING passa / com utf-8 nega]`. Os hooks antigos da casa já liam
    # assim; os dois novos não seguiram.
    try:
        ent = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
    except (ValueError, AttributeError):
        return
    ti = ent.get("tool_input") or {}
    alvo = ti.get("file_path") or ""
    if os.path.normcase(os.path.abspath(alvo)) != SOBERANO:
        return

    novo = ti.get("new_string")
    if novo is None:
        novo = ti.get("content")
    if not novo:
        return

    atual = ""
    if os.path.exists(alvo):
        with io.open(alvo, encoding="utf-8", errors="replace") as fh:
            atual = fh.read()

    motivos, extintos = [], []
    if ti.get("content") is not None:            # Write: o arquivo INTEIRO
        if len(novo) > ARQUIVO_MAX:
            motivos.append(("(arquivo)", f"{len(novo)} chars (teto {ARQUIVO_MAX})",
                            "o harness corta aqui; o soberano carrega em toda sessão"))
        ini, fim = _limites_da_fila(novo)
        alcance = novo[ini:fim].splitlines() if ini >= 0 else []
        if ini < 0:                              # fila extinta: teto ZERO
            extintos = _itens_de_pendencia(novo.splitlines())
    else:                                        # Edit
        velho = ti.get("old_string") or ""
        ini, fim = _limites_da_fila(atual)
        if ini < 0:
            # A fila nao existe mais. Qualquer pendencia
            # entrando aqui e tentativa de recria-la, em qualquer ponto do
            # arquivo — nao ha mais "dentro da fila" para delimitar.
            extintos = _itens_de_pendencia(novo.splitlines())
            if not extintos:
                return                           # edição comum no soberano: passa
            alcance = []
        else:
            pos = atual.find(velho) if velho else -1
            if pos < 0 or not (ini <= pos < fim):
                return                           # edição fora da fila: não é comigo
            alcance = novo.splitlines()

    motivos += _violacoes(alcance)
    motivos += [(f"#{cid}", "pendência entrando no soberano",
                 "a fila-mestra saiu daqui — escreva na "
                 "`pendencias_ativas.md` do dono") for cid in extintos]
    if not motivos or _ja_negou(ent.get("session_id"), novo):
        return

    if extintos:
        linhas = [
            "PARE — a fila-mestra saiu do CLAUDE.md, e não volta.",
            "",
            "Ela era 70% do soberano e entrava em TODA requisição de TODO "
            "projeto — 20.921 tokens por vez [medido] — carregando as pendências "
            "dos 15 projetos que não eram o ativo. Decisão tomada aqui.",
            "",
            "O que não passou:",
        ]
        linhas += [f"  · {a} — {b}\n    → {c}" for a, b, c in motivos]
        linhas += [
            "",
            "Onde a pendência vive agora:",
            "  · na `pendencias_ativas.md` da micro mente do DONO — o "
            "detalhe [medido] inteiro, sem teto",
            "  · carrega quando você abre AQUELE projeto (pré-voo, passo 2)",
            "  · a Ronda do Diretor continua chegando pelo hook "
            "`session_context.py` — nunca dependeu desta seção",
            "  · a cópia do que havia ficou arquivada na memória",
            "",
            "Escreva na micro mente do dono e siga.",
        ]
    else:
        linhas = [
            "PARE — esta edição engorda a fila-mestra do CLAUDE.md.",
            "",
            "O soberano carrega em TODA sessão. A seção se declara *índice enxuto: "
            "id + status + gancho, só itens abertos* — e foi assim que ela chegou a "
            "148 mil caracteres, com 112 itens já fechados dentro.",
            "",
            "O que não passou:",
        ]
        linhas += [f"  · {a} — {b}\n    → {c}" for a, b, c in motivos]
        linhas += [
            "",
            "A régua (skill `/salvar`, Passo 4):",
            f"  · o soberano leva UMA linha por pendência, até {FILA_ITEM_MAX} chars: "
            "`- <status> **#id** — gancho`",
            "  · o detalhe medido, o histórico e a narrativa vão para a "
            "`pendencias_ativas.md` da micro mente do dono",
            "  · fechou? o ✅ é escrito lá, e a linha **sai** daqui",
            "",
            "Corrija e repita — a mesma edição, na segunda vez, passa.",
        ]
    _log_gate("soberano", linhas)
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "\n".join(linhas)}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
