#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OS PADROES DA CASA INTERROMPEM NA PORTA - PreToolUse de Edit|Write em CODIGO.

A ordem que originou esta peca, verbatim: *"existem muitas outras regras
(...) tanto de seguranca quanto regras de ARQUITETURA e etc. preciso que vc
trabalhasse nisso para a nossa engenharia basica nao depender de mim ou vc
lembrar"*.

O BURACO QUE ELE NOMEOU, medido no mesmo dia
--------------------------------------------
A casa tinha 9 gates de porta. Todos cobriam seguranca e higiene de contexto -
segredo, default inseguro, bash destrutivo, fronteira de projeto, prosa com cara
de IA, tamanho do arquivo soberano, leitura grande, saida grande, contrato de
dia zero.
**Nenhum cobria regra de CONSTRUCAO.** Elas existiam, 130 delas, escritas em
`_shared/PADROES.md` - o 1o degrau da escada de forca, o que vale enquanto
alguem lembra de ler.

E NAO FOI GARIMPO DE FORA. A mina mais rica era interna: o AIOX, varrido no
mesmo dia, deu 23 itens verificaveis em 933 (2%). O `PADROES.md` e o oposto -
cada regra la nasceu de um incidente REAL desta casa, com data, commit e o
conserto escrito.

O CRITERIO DE ENTRADA, e ele e duro
-----------------------------------
So entra a regra que uma MAQUINA decide sozinha. "Este codigo devia ter teste"
e julgamento e fica de fora: gate que julga erra, gate que erra vira ruido, e
ruido treina a ignorar o vermelho - a licao que um CI desta casa ja pagou.

COMO SE COMPORTA
----------------
Recusa na 1a vez por arquivo, PASSA na 2a - o padrao dos outros gates da casa.
Nao trava o trabalho, obriga a olhar. E a mensagem carrega o CONSERTO, nao so o
defeito: gate que aponta o erro sem dizer o que fazer custa uma ida ao
PADROES.md, e e nessa ida que se desiste.

CHAMADOR: `~/.claude/settings.json`, PreToolUse, matcher `Edit|Write`.
REGRAS:   `~/.claude/hooks/padroes_casa.json` (fonte unica, com `fonte:` de cada)
TESTE:    `~/.claude/hooks/testar_padroes_na_porta.py` (com mutacao)
"""

import io
import json
import os
import re
import sys
import time

# `.yml`/`.yaml` entraram depois dos primeiros, e nao por alcance: metade das
# regras que sobravam no `PADROES.md` fala de workflow do GitHub Actions, e a
# casa tem 320 deles. Medido ANTES de abrir, sobre 1.489 YAML: as regras que
# ja existiam nao criaram falso positivo - criaram ACHADO REAL, porque o YAML
# de workflow carrega shell e Python embutidos, que sao codigo de verdade
# rodando em producao sem nunca ter passado por gate nenhum.
CODIGO = (".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs", ".sh", ".ps1",
          ".yml", ".yaml",
          # `.php` entrou depois. Sao so 3 arquivos nesta casa, e os
          # tres estao NO AR numa area de cliente, fora de qualquer
          # gate ate entao.
          # Medido antes de abrir: 0 regra lenta, 0 falso positivo.
          ".php")

AQUI = os.path.dirname(os.path.abspath(__file__))
REGRAS = os.path.join(AQUI, "padroes_casa.json")
ESTADO = os.path.join(AQUI, "padroes_na_porta.estado.json")

# Fora do alcance, cada um com motivo:
#  - padroes_casa.json / este arquivo / o teste: aqui MORAM os padroes; o
#    arquivo que descreve o defeito casaria com ele mesmo.
#  - test/spec/fixture: teste precisa poder escrever o caso ruim.
#  - node_modules/.git/dist/build/.venv/.aiox-core: nao e codigo nosso.
#  - .min.js / .bundle. / vendor / .obsidian: biblioteca de TERCEIRO trazida
#    para dentro da arvore. Nao e nosso, nao se conserta, e custa caro: o
#    "maior arquivo nosso" era um `babel.min.js` de 2,8 MB (238 ms por
#    varredura) e o maior de todos, um plugin do Obsidian de 3,5 MB (865 ms).
#    Contar a divida de terceiro tambem envenena o numero que decide o degrau.
ISENTOS = ("padroes_casa", "padroes_na_porta", "node_modules", "\\.git\\",
           "/.git/", "\\dist\\", "/dist/", "\\build\\", "/build/", ".venv",
           "site-packages", "__pycache__", ".aiox-core", "\\test", "/test",
           "_test.", ".test.", ".spec.", "fixture", "conftest", ".bak",
           "scratchpad", ".min.js", ".min.ts", ".bundle.", "\\vendor\\",
           "/vendor/", ".obsidian",
           #  - claude-code-mastery: pacote de ESTUDO de terceiro, com
           #    templates de exemplo, replicado em varios projetos. Medido em
           #    ao abrir o gate para `.yml`: das 48 ocorrencias de
           #    `claude -p` sem allowlist, **45 eram dele** e 3 eram nossas.
           #    Exemplo de terceiro nao se conserta, e afogava o caso real -
           #    [[concept-ruido-que-afoga-o-caso-real]].
           "claude-code-mastery")


def carregar(onde="porta"):
    """[(id, titulo, fonte, porque, conserto, rx_escopo, rx_exige, [rx])]

    `onde` escolhe o degrau da escada: "porta" (o que este gate recusa),
    "vigia" (o que a varredura diaria so reporta) ou "todas".

    Por que a separacao existe, e foi medida: a regra do JSON de estado
    acha 235 arquivos em codigo real. O defeito e verdadeiro - foi assim que o
    MEMORY.md zerou duas vezes - mas e divida antiga espalhada, nao erro
    nascendo agora. Barrar 235 arquivos nao conserta nenhum e faz alguem
    desligar o gate na primeira semana. Divida velha e relatorio; erro novo e
    porta.
    """
    try:
        with io.open(REGRAS, encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception:                                       # noqa: BLE001
        return []
    saida = []
    for rid, b in d.items():
        if rid.startswith("_") or not isinstance(b, dict):
            continue
        if onde != "todas" and b.get("onde", "porta") != onde:
            continue
        try:
            rxs = [re.compile(s) for s in b.get("seeds", [])]
            # `seeds_bloco`: o defeito que NAO cabe numa linha. Nasceu de
            # `falha-nao-e-vazio`: o caso canonico do catalogo de regras e
            # `} catch (e) {` numa linha e `return [];` na seguinte - o motor
            # linha-a-linha nao ve nenhum dos dois como defeito, porque cada um
            # deles, sozinho, e codigo legitimo. O defeito e a VIZINHANCA.
            blocos = [re.compile(s, re.S) for s in b.get("seeds_bloco", [])]
            # `nao_tem`: o defeito de AUSENCIA. Nasceu de `ps1-crlf-bom`: um
            # `.ps1` sem CRLF nao tem linha errada nenhuma para apontar - o que
            # esta errado e o arquivo inteiro. Diferente de `exige`, que so
            # ISENTA quem tem a defesa: aqui a falta da defesa E o achado.
            nt = b.get("nao_tem")
            nt = re.compile(nt, re.S) if nt else None
            # `olha_comentario`: desliga o filtro que pula linha comentada.
            #
            # ⚠️ NENHUMA REGRA USA ISTO HOJE, e o campo continua aqui de
            # proposito, com o registro do porque. Nasceu para a
            # regra da crase solta, cujo alvo parecia ser o comentario. A
            # versao seguinte daquela regra ancorou no INICIO do template
            # (`= \`<!DOCTYPE[^\`]*`) em vez do comentario, ficou precisa - 4
            # falsos positivos viraram 0 - e dispensou o campo.
            # Fica como capacidade dormente e nao como codigo vivo: se a
            # proxima regra de comentario nao aparecer ate a proxima
            # mineracao, some daqui. Custa 1 linha e nao roda para ninguem.
            olha_com = bool(b.get("olha_comentario"))
        except re.error:
            continue                    # regra quebrada nao derruba o gate
        if not (rxs or blocos or nt):
            continue
        esc = b.get("escopo")
        exi = b.get("exige")
        sse = b.get("so_se")
        nse = b.get("nao_se")
        try:
            esc = re.compile(esc) if esc else None
            exi = re.compile(exi) if exi else None
            sse = re.compile(sse) if sse else None
            nse = re.compile(nse) if nse else None
        except re.error:
            esc = exi = sse = nse = None
        saida.append((rid, b.get("titulo", rid), b.get("fonte", ""),
                      b.get("porque", ""), b.get("conserto", ""),
                      esc, exi, sse, nse, rxs, blocos, nt, olha_com))
    return saida


def ja_avisei(sessao, alvo):
    chave = "%s|%s" % (sessao or "?", alvo)
    try:
        with io.open(ESTADO, encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception:                                       # noqa: BLE001
        d = {}
    agora = time.time()
    d = {k: v for k, v in d.items() if agora - v < 86400}
    visto = chave in d
    d[chave] = agora
    try:
        with io.open(ESTADO, "w", encoding="utf-8") as fh:
            json.dump(d, fh)
    except Exception:                                       # noqa: BLE001
        pass
    return visto


def _comentario(ln):
    return ln.lstrip().startswith(("#", "//", "*"))


def violacoes(alvo, texto, onde="porta", contexto=None):
    """[(id, titulo, fonte, porque, conserto, n_linha, trecho)]

    `texto`    o que esta ENTRANDO - e so nele que se procura o defeito.
    `contexto` o ARQUIVO como ele vai ficar. So difere de `texto` num `Edit`,
               em que a ferramenta manda o pedaco (`new_string`) e nao o todo.

    A separacao nasceu de um falso positivo neste proprio gate:
    editei tres linhas do `calibrar_padroes.py` que continham
    `print(json.dumps(...))`, e a regra `hook-stdout-utf8` recusou - porque o
    `exige` (`sys.stdout.reconfigure`) estava no arquivo, 150 linhas acima, e
    nao no pedaco. Com `so_se` o erro se INVERTE e fica pior: um `Edit` que
    introduz `main()` num script de disparo nao aciona a regra do guard,
    porque o sinal de envio mora no resto do arquivo. Era falso negativo com
    cara de gate funcionando - a familia de [[concept-o-gate-que-aprova-pelo-
    motivo-errado]].
    """
    achados = []
    dono = contexto if contexto is not None else texto
    for (rid, tit, fonte, pq, cons, esc, exi, sse, nse, rxs, blocos,
         nt, olha_com) in carregar(onde):
        if esc and not esc.search(alvo.replace("/", "\\")):
            continue
        # `exige`: o padrao so e defeito se a defesa NAO estiver no ARQUIVO
        if exi and exi.search(dono):
            continue
        # `so_se`: a regra so vale se o arquivo tiver ESTE sinal. Nasceu da regra
        # do guard `__main__`: ela vale para script que MANDA/PUBLICA/APAGA, nao
        # para todo script do mundo. Sem isso, a regra certa viraria ruido em
        # centenas de arquivos que nao correm risco nenhum.
        if sse and not sse.search(dono):
            continue

        # (a) AUSENCIA: a regra e satisfeita pela falta, nao pela presenca.
        # Olha o ARQUIVO: faltar num pedaco de `Edit` nao quer dizer nada.
        if nt and not nt.search(dono):
            achados.append((rid, tit, fonte, pq, cons, 0,
                            "(o arquivo inteiro - nao ha linha a apontar)"))
            continue

        # (b) VIZINHANCA: o defeito que so aparece em 2+ linhas juntas. A linha
        # reportada e a do INICIO do trecho, e um match que comece em
        # comentario nao conta - senao um exemplo comentado do proprio defeito
        # viraria achado (foi assim que 30 mencoes de `claude -p` em log
        # entraram como violacao na primeira rodada).
        achou_bloco = False
        for rx in blocos:
            m = rx.search(texto)
            if not m:
                continue
            n = texto.count("\n", 0, m.start()) + 1
            linha = texto.split("\n")[n - 1]
            if (_comentario(linha) and not olha_com) or \
                    (nse and nse.search(linha)):
                continue
            achados.append((rid, tit, fonte, pq, cons, n,
                            " ".join(m.group(0).split())[:100]))
            achou_bloco = True
            break
        if achou_bloco:
            continue

        # (c) LINHA: o caminho original.
        for n, ln in enumerate(texto.split("\n"), 1):
            if len(ln) > 400 or (_comentario(ln) and not olha_com):
                continue
            # `nao_se`: mata o falso positivo NA LINHA, nao no arquivo. Nasceu
            # de 30 achados de `claude -p` que eram `log(f"Calling claude -p")`
            # - a MENCAO em texto de log, nao a invocacao [medido].
            if nse and nse.search(ln):
                continue
            achou = False
            for rx in rxs:
                if rx.search(ln):
                    achou = True
                    break
            if achou:
                achados.append((rid, tit, fonte, pq, cons, n,
                                ln.strip()[:100]))
                break                   # uma ocorrencia por regra basta
    return achados


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                       # noqa: BLE001
        pass
    # stdin em BYTES - e a regra `hook-stdin-bytes` deste proprio gate
    try:
        ent = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
    except (ValueError, AttributeError):
        return                                  # fail-open: nao trava o dia
    ti = ent.get("tool_input") or {}
    alvo = ti.get("file_path") or ""
    if not alvo or not alvo.lower().endswith(CODIGO):
        return
    baixo = alvo.replace("/", "\\").lower()
    if any(p.replace("/", "\\").lower() in baixo for p in ISENTOS):
        return

    texto = ti.get("content") or ti.get("new_string") or ""
    if not texto.strip():
        return

    # Num `Write` o que entra JA e o arquivo todo. Num `Edit` e um pedaco, e as
    # condicoes de arquivo (`exige`, `so_se`, `nao_tem`) precisam ver o resto -
    # senao a defesa que existe 150 linhas acima conta como ausente. Aproximar
    # por "disco + pedaco novo" basta: nenhuma dessas condicoes pergunta ONDE o
    # sinal esta, so SE esta.
    contexto = texto
    if ti.get("content") is None:
        try:
            with io.open(alvo, encoding="utf-8", errors="replace") as fh:
                contexto = fh.read() + "\n" + texto
        except Exception:                                   # noqa: BLE001
            pass                        # arquivo novo: o pedaco e tudo que ha

    achados = violacoes(alvo, texto, "porta", contexto)
    if not achados:
        return
    if ja_avisei(ent.get("session_id"), os.path.abspath(alvo)):
        return

    linhas = [
        "PARE - este codigo repete um padrao que esta casa ja pagou para aprender.",
        "",
        "`%s` - %d regra(s):" % (os.path.basename(alvo), len(achados)),
    ]
    for rid, tit, fonte, pq, cons, n, trecho in achados[:3]:
        linhas += [
            "",
            "  [%s] linha %d" % (rid, n),
            "      %s" % trecho,
            "",
            "  %s" % tit,
            "  POR QUE: %s" % pq[:420],
            "  CONSERTO: %s" % cons,
            "  fonte: %s" % fonte,
        ]
    linhas += [
        "",
        "Se aqui for legitimo - script de uso unico, caso que a regra nao previu -",
        "diga numa frase por que, e repita: a 2a tentativa neste arquivo passa.",
    ]
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "\n".join(linhas)}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
