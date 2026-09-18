#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
O CONTRATO DE PARTIDA INTERROMPE NA PORTA - PreToolUse de Edit|Write em
CODIGO.

Pergunta do dono da casa, que e a origem deste arquivo:

    "dentro da nossa metodologia tem algo que vai SEMPRE nos resguardar disso
     de forma que vire o basico nosso de trabalho, o basic engineering do nosso
     modo de trabalho, ou eu teria que ficar lembrando que temos que fazer x ou y."

A resposta medida naquele dia: NAO havia. Os 8 hooks de porta que ja existiam
cobriam seguranca e higiene de contexto - nenhum cobria ENGENHARIA DE PROJETO.
Este arquivo e o nono, e fecha esse buraco.

O QUE ELE IMPEDE
  Escrever codigo num projeto que nunca respondeu as perguntas do dia zero.
  Enquanto nao houver um `projeto.yml` valido na raiz, a primeira escrita de
  codigo daquele projeto e RECUSADA.

POR QUE ISSO E O DEGRAU CERTO
  texto no soberano ......... vale enquanto alguem lembra de ler
  recall / catalogo ......... vale quando a palavra encosta
  varredura diaria .......... descobre no dia seguinte
  gate na porta ............. IMPEDE de acontecer      <- aqui

  Medido: um framework inteiro que PROMETE bloquear
  ("Violacoes sao bloqueadas automaticamente via gates", constitution.md) e
  nunca bloqueou nada - das 411 validacoes "blocking" dele, 10 citam um comando
  de verdade, e ele nunca rodou uma vez em 5 meses nos 6 projetos. Promessa
  escrita e o PRIMEIRO degrau da escada. So o gate executavel e o quarto.

O QUE ELE NAO FAZ, E E LIMITE ASSUMIDO
  Nao julga se a resposta e BOA. Alguem escreve `ci: nao` e passa pela porta.
  Quem pega resposta que virou mentira e o vigia (bloco do mente_health):
  `lifecycle: producao` sem CI que roda teste e contradicao, e contradicao ele
  acha. Mentira COERENTE passa. Isso e teto, nao descuido.

  E nao vira gate de julgamento: "este codigo merece teste?" nao entra aqui.
  Gate que julga erra, e gate que erra vira ruido, e ruido treina a ignorar.
  Decisao tomada aqui: teste e CI sao gate no INICIO e vigia DEPOIS, nunca
  gate por arquivo.

COMO ELE SE COMPORTA
  Recusa na 1a tentativa daquele projeto, PASSA na 2a. E o padrao da casa
  (`fronteira_de_projeto`, `seguranca_na_porta`): nao trava o trabalho, obriga
  a olhar. O retrofit dos projetos antigos e preguicoso de proposito - o
  `projeto.yml` nasce quando o projeto for tocado, sem forca-tarefa nos 15,
  porque forca-tarefa de 15 e o padrao "crio e nao uso".

CHAMADOR: `~/.claude/settings.json`, bloco `PreToolUse`, matcher `Edit|Write`.
TESTE:    `~/.claude/hooks/testar_fundacao_na_porta.py` (com mutacao).
"""

import io
import json
import os
import sys
import time

CODIGO = (".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs", ".sh", ".sql",
          ".go", ".rb", ".php", ".java", ".tf")

RAIZ_PROJETOS = os.path.join(os.path.expanduser("~"), "Projeto")

ESTADO = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "fundacao_na_porta.estado.json")

# Os 10 campos que o projeto tem de ter respondido. Cada um existe porque muda
# uma decisao real - nenhum e enfeite:
#   nome/owner/lifecycle .. identidade (formato do catalog-info.yaml do Backstage,
#                           que e padrao conhecido e nao custa nada)
#   o_que_e ............... o papel do PO em UMA FRASE, nao num PRD de 463 linhas
#                           que congela em 6 meses (medido: o unico `prd.md`
#                           de verdade desta casa tem UM commit)
#   efeito_no_mundo ....... decide se a R2 (OK explicito) se aplica a este projeto
#   dado_de_cliente ....... decide LGPD, redacao de PII e raio de estrago
#   onde_roda ............. a pergunta dele: "vamos mexer com aws? sim nao pq?"
#   teste / ci ............ o piso; medido: 320 workflows e 9 rodam teste
#   trabalho_aberto ....... onde mora a fila; medido: 8 de 12 projetos sem backlog
OBRIGATORIOS = ("nome", "owner", "lifecycle", "o_que_e", "efeito_no_mundo",
                "dado_de_cliente", "onde_roda", "teste", "ci", "trabalho_aberto")

VALORES = {
    "lifecycle": ("experimental", "producao", "pausado", "aposentado"),
    "efeito_no_mundo": ("nenhum", "publica", "mensagem", "cobranca", "deploy"),
    "dado_de_cliente": ("nao", "sim"),
    "teste": ("nenhum", "manual", "automatizado"),
    "ci": ("nao", "sim"),
}

# Fora do alcance, cada um com motivo:
#  - .claude/hooks/: aqui moram os gates; barrar aqui me impede de consertar o
#    proprio gate quando ele estiver errado.
#  - .aiox-core/: framework de terceiro, aposentado (new-project.sh:48).
#  - test/spec/fixture: teste precisa poder escrever qualquer coisa.
#  - node_modules/.git/dist/build/.venv: nao e codigo nosso.
#  - scratchpad: rascunho de sessao, nao e projeto.
#
# NAO isentar "temp": o scratchpad ja esta coberto pelo proprio nome, e arquivo
# fora de ~/Projeto ja nao chega aqui (raiz_do_projeto devolve None). Isentar a
# substring "temp" pegaria de graca um `src/temp/` legitimo dentro de um projeto
# real - o defeito de substring que esta casa ja pagou.
ISENTOS = ("\\.claude\\hooks\\", "/.claude/hooks/", ".aiox-core",
           "node_modules", "\\.git\\", "/.git/", "\\dist\\", "/dist/",
           "\\build\\", "/build/", ".venv", "site-packages", "__pycache__",
           "\\test", "/test", "_test.", ".test.", ".spec.", "fixture",
           "conftest", ".bak", "scratchpad")


# 🔴 AS CONFIGURACOES DE LINTER E FORMATADOR, protegidas quando JA EXISTEM.
#
# Veio de um repositorio de referencia, medido em vez de resumido — a peca que
# esta casa tinha mapeado e nao adotou. A frase dele cabe inteira numa linha:
# **conserte o codigo, nao afrouxe a regra**.
#
# 🔑 POR QUE ISSO E UM GATE E NAO UM CONSELHO. Afrouxar o linter e a fuga mais
# barata que existe para quem esta com pressa: some com o aviso, o comando sai
# verde, e a regra que alguem escreveu por um motivo deixa de valer para todo
# mundo dali em diante — sem ninguem decidir isso. Um `# noqa` no lugar errado
# some numa revisao; uma regra desligada no arquivo de config nao volta.
#
# ⚠️ CRIAR CONFIG NOVO CONTINUA LIBERADO, e a distincao e o que torna a regra
# usavel. Projeto novo precisa do primeiro `ruff.toml`; o que se barra e mexer
# no que ja esta valendo.
CONFIGS_PROTEGIDAS = frozenset([
    ".eslintrc", ".eslintrc.js", ".eslintrc.cjs", ".eslintrc.json",
    ".eslintrc.yml", ".eslintrc.yaml", "eslint.config.js", "eslint.config.mjs",
    "eslint.config.cjs", "eslint.config.ts",
    ".prettierrc", ".prettierrc.js", ".prettierrc.cjs", ".prettierrc.json",
    ".prettierrc.yml", ".prettierrc.yaml", "prettier.config.js",
    "prettier.config.cjs", "prettier.config.mjs",
    "biome.json", "biome.jsonc",
    "ruff.toml", ".ruff.toml", ".flake8", ".pylintrc", "setup.cfg",
    ".stylelintrc", ".stylelintrc.json", ".stylelintrc.yml",
    ".stylelintrc.yaml",
    ".editorconfig", "sonar-project.properties",
    "checkstyle.xml", ".checkstyle", "mypy.ini", ".mypy.ini",
])


def afrouxa_config(alvo):
    """True quando o alvo e uma config de linter que JA existe no disco.

    ⚠️ O `os.path.isfile` e a regra inteira, nao um detalhe: e ele que separa
    *criar a primeira config do projeto* de *mexer na que ja esta valendo*.
    Em caso de duvida ao ler o disco, responde False — um gate que trava por
    nao conseguir olhar e um gate que alguem desliga.
    """
    if os.path.basename(alvo).lower() not in CONFIGS_PROTEGIDAS:
        return False
    try:
        return os.path.isfile(alvo)
    except OSError:
        return False


def ja_avisei(sessao, projeto):
    """True se este projeto ja foi recusado nesta sessao (entao a 2a passa)."""
    chave = "%s|%s" % (sessao or "?", projeto)
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


def raiz_do_projeto(alvo):
    """Sobe do arquivo ate a raiz do projeto.

    Ordem: o primeiro diretorio com `.git` vence (repo == projeto). Se nenhum
    tiver, cai para o filho direto de ~/Projeto - que cobre projeto ainda sem
    git. Devolve None se o arquivo estiver fora de ~/Projeto.
    """
    try:
        alvo = os.path.abspath(alvo)
    except Exception:                                       # noqa: BLE001
        return None
    raiz = os.path.abspath(RAIZ_PROJETOS)
    if not os.path.normcase(alvo).startswith(os.path.normcase(raiz) + os.sep):
        return None
    d = os.path.dirname(alvo)
    candidato = None
    while d and os.path.normcase(d).startswith(os.path.normcase(raiz)):
        if os.path.normcase(d) == os.path.normcase(raiz):
            break
        if os.path.exists(os.path.join(d, ".git")):
            return d
        candidato = d
        pai = os.path.dirname(d)
        if pai == d:
            break
        d = pai
    return candidato


def ler_projeto_yml(pasta):
    """Le o projeto.yml SEM depender de PyYAML - so `chave: valor` de 1 nivel.

    Deliberado: o hook roda em toda escrita de codigo do dia. Depender de
    biblioteca externa faria o gate morrer calado numa maquina sem ela, e
    "gate que falha aberto sem avisar" e o defeito que o proprio shunt do
    Spotify nomeia: "a silent pass looks like a working plugin".

    Devolve None se o arquivo nao existe; dict (possivelmente vazio) se existe.
    """
    caminho = os.path.join(pasta, "projeto.yml")
    if not os.path.exists(caminho):
        return None
    campos = {}
    try:
        with io.open(caminho, encoding="utf-8", errors="replace") as fh:
            linhas = fh.read().splitlines()
    except Exception:                                       # noqa: BLE001
        return {}
    i = 0
    while i < len(linhas):
        linha = linhas[i]
        i += 1
        if not linha.strip() or linha.lstrip().startswith("#"):
            continue
        if linha[:1] in (" ", "\t"):        # valor continuado de bloco `>`
            continue
        if ":" not in linha:
            continue
        chave, _, valor = linha.partition(":")
        chave = chave.strip()
        valor = valor.split("#")[0].strip().strip("\"'")
        if valor in (">", "|", ">-", "|-"):  # bloco: o texto vem indentado
            corpo = []
            while i < len(linhas) and (not linhas[i].strip()
                                       or linhas[i][:1] in (" ", "\t")):
                corpo.append(linhas[i].strip())
                i += 1
            valor = " ".join([c for c in corpo if c]).strip()
        campos[chave] = valor
    return campos


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                       # noqa: BLE001
        pass
    try:
        ent = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
    except (ValueError, AttributeError):
        return                                  # fail-open: nao trava o dia
    ti = ent.get("tool_input") or {}
    alvo = ti.get("file_path") or ""
    if not alvo:
        return

    # ⚠️ ESTA CHECAGEM VEM ANTES DO FILTRO DE EXTENSAO, e tem de vir: config
    # de linter nao e `.py` nem `.js`, entao ela morreria no `endswith(CODIGO)`
    # logo abaixo sem nunca ter sido feita.
    if afrouxa_config(alvo):
        if ja_avisei(ent.get("session_id"), alvo):
            return                              # 2a tentativa passa
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "\n".join([
                "PARE - isto e a config de um linter que JA existe.",
                "",
                "  arquivo: %s" % alvo,
                "",
                "CONSERTE O CODIGO, NAO AFROUXE A REGRA. Desligar a regra faz",
                "o aviso sumir e a falha ficar - e ela deixa de valer para",
                "todo o projeto dali em diante, sem ninguem ter decidido isso.",
                "Um `# noqa` no lugar errado morre na proxima revisao; uma",
                "regra apagada do arquivo de config nao volta.",
                "",
                "CRIAR uma config nova continua liberado. O que se barra aqui",
                "e mexer na que ja esta valendo.",
                "",
                "Se a regra estiver MESMO errada, diga numa frase por que -",
                "a 2a tentativa neste arquivo passa, e a frase fica no registro.",
            ])}}, ensure_ascii=False))
        return

    if not alvo.lower().endswith(CODIGO):
        return
    baixo = alvo.replace("/", "\\").lower()
    if any(p.replace("/", "\\").lower() in baixo for p in ISENTOS):
        return

    pasta = raiz_do_projeto(alvo)
    if not pasta:
        return                                  # fora de ~/Projeto: nao e nosso

    campos = ler_projeto_yml(pasta)
    nome = os.path.relpath(pasta, os.path.abspath(RAIZ_PROJETOS))

    if campos is None:
        motivo = "nao existe `projeto.yml` na raiz deste projeto"
        faltando = list(OBRIGATORIOS)
        invalidos = []
    else:
        faltando = [c for c in OBRIGATORIOS if not campos.get(c)]
        invalidos = ["%s: `%s` (aceita: %s)" % (c, campos.get(c),
                                                ", ".join(VALORES[c]))
                     for c in VALORES
                     if campos.get(c) and campos[c] not in VALORES[c]]
        if not faltando and not invalidos:
            return                              # projeto em ordem: passa
        motivo = "o `projeto.yml` existe mas esta incompleto"

    if ja_avisei(ent.get("session_id"), pasta):
        return                                  # 2a tentativa passa

    linhas = [
        "PARE - este projeto nunca respondeu as perguntas do dia zero.",
        "",
        "  projeto: %s" % nome,
        "  motivo:  %s" % motivo,
    ]
    if faltando:
        linhas.append("  faltam:  %s" % ", ".join(faltando))
    if invalidos:
        linhas.append("  valor invalido: %s" % " | ".join(invalidos))
    linhas += [
        "",
        "Escrever codigo aqui e construir em cima de decisao que ninguem tomou.",
        "Origem, verbatim: \"tem algo que vai SEMPRE nos resguardar disso (...)",
        "ou eu teria que ficar lembrando que temos que fazer x ou y\".",
        "",
        "O QUE FAZER: criar/completar `%s`" % os.path.join(pasta, "projeto.yml"),
        "com os 10 campos. Modelo pronto: `projeto.yml.modelo`, na pasta",
        "compartilhada da casa.",
        "Leva 2 minutos e nao e burocracia - cada campo muda uma decisao real:",
        "efeito_no_mundo decide se a R2 se aplica; dado_de_cliente decide LGPD;",
        "teste/ci sao o piso; trabalho_aberto diz onde mora a fila.",
        "",
        "Se a escrita AQUI for mesmo a certa antes disso - conserto urgente, ou",
        "arquivo que nao pertence a projeto nenhum - diga numa frase por que, e",
        "repita: a 2a tentativa neste projeto passa.",
    ]
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "\n".join(linhas)}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
