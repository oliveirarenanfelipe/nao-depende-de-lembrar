#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bash_na_porta.py — PreToolUse: BLOQUEIA comando Bash que pode destruir a mente.

Por que existe — e o estrago é medido
--------------------------------------
Eu estava ESCREVENDO um `uninstall.sh` (conteúdo = dado, texto a gravar em
disco). Passei o gerador por heredoc de bash, e dentro do texto havia outro
heredoc com o MESMO delimitador. O de dentro fechou o de fora, e o bash passou a
executar como COMANDO o que eu redigia como CONTEÚDO — apontando para o
`~/.claude` real.

  · 5 hooks apagados (memory_lib, session_context, prompt_memory, auto_brief,
    reindex_memory)
  · 5 registros removidos do settings.json
  · memory_cache.json, memory_index.pkl e recall.log deletados
  · recuperado de um backup de dias antes; o recall.log (186 KB) não voltou

No mesmo dia, os gates da casa me barraram 7 vezes — TODAS em `Write` de arquivo
novo, inofensivo — e ZERO vezes no `Bash` que apagou a mente. A estrutura vigiava
a ferramenta segura e deixava a perigosa passar. É esse buraco que este arquivo
fecha.

A regra já existia e não segurou. Uma nota escrita três semanas antes dizia
literalmente *"num arquivo .py que eu escreva com a ferramenta de escrita
(nunca por heredoc do shell)"*, e outra registrava a MESMA ferramenta
corrompendo acento pela 4ª vez. Nota escrita não é conserto — bloqueio é.

O que bloqueia
--------------
1. Comando destrutivo que toca `~/.claude` (apagar, mover, sobrescrever, resetar).
2. Heredoc aninhado com delimitador repetido — o vazamento exato de hoje.

Escape deliberado
-----------------
Incluir `# GATE-OK: <motivo>` no comando. Escolhido de propósito: o modo de falha
aqui é EXECUÇÃO ACIDENTAL, e texto vazado nunca carrega esse marcador. Ao
contrário do `soberano_na_porta.py`, **repetir o comando NÃO passa** — gate de
coisa irreversível que cede na segunda tentativa é decoração.

Chamador: settings.json, PreToolUse (matcher Bash).
Teste: testar_bash_na_porta.py — inclui mutação (desarma o detector e exige que
os casos deixem de ser pegos).
"""
import datetime
import json
import os
import re
import sys

# 🔴 SEM ISTO O GATE MORRE NA HORA DE BLOQUEAR — pego pelo próprio teste.
# O console do Windows é cp1252 e a mensagem de bloqueio tem `·` e `→`: o `print`
# estourava UnicodeEncodeError, o hook saía com código 1 e SEM saída, e o Claude
# Code seguia como se nada tivesse sido negado. Um gate que morre ao reprovar é
# pior que gate nenhum, porque parece que existe. Foi assim que o
# outro gate desta casa ficou inerte desde que nasceu, por semanas.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

MARCADOR_OK = "# GATE-OK:"
GATES_LOG = os.path.join(os.path.expanduser("~"), ".claude", "hooks", "gates.log")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _fl():
    """`fronteira_lib` importada tarde: o mesmo reconhecedor de dono que o
    `fronteira_de_projeto.py` usa. Import no topo faria um erro de sintaxe la
    matar ESTE gate tambem, e gate que morre parece gate que aprovou."""
    import fronteira_lib
    return fronteira_lib

# Verbos que apagam, movem ou sobrescrevem. `cp` entra porque sobrescrever um
# hook é tão destrutivo quanto apagá-lo — foi `cp` que usei para restaurar, e
# restaurar TAMBÉM deve ser deliberado.
VERBOS_DESTRUTIVOS = [
    (r"\brm\b", "rm"),
    (r"\bmv\b", "mv"),
    (r"\bcp\b", "cp"),
    (r"\bdd\b", "dd"),
    (r"\bshred\b", "shred"),
    (r"\btruncate\b", "truncate"),
    (r"\brmdir\b", "rmdir"),
    (r"\bunlink\s*\(", "unlink()"),
    (r"\bos\.remove\b", "os.remove"),
    (r"\bos\.replace\b", "os.replace"),
    (r"\bshutil\.rmtree\b", "shutil.rmtree"),
    (r"\bshutil\.move\b", "shutil.move"),
    # `[^\n;|&]*` porque o comando real traz opções no meio:
    # `git -C ~/.claude reset --hard`. Com as palavras coladas, não casava —
    # pego pelo próprio teste, não por leitura.
    (r"\bgit\b[^\n;|&]*\breset\s+--hard\b", "git reset --hard"),
    (r"\bgit\b[^\n;|&]*\bclean\b\s+-", "git clean"),
    (r"\bgit\b[^\n;|&]*\bcheckout\s+--\s", "git checkout --"),
    # `git restore` sobrescreve o arquivo do disco com a versão guardada, então
    # descarta trabalho ainda não salvo. Faltava na lista — furo achado ao usar
    # o próprio gate para provar a reversão, não por leitura do código.
    (r"\bgit\b[^\n;|&]*\brestore\b", "git restore"),
    (r">\s*[\"']?[^\s|&;<>]*\.claude", "redirecionamento > para dentro de .claude"),
    (r"\bwrite_text\s*\(", "write_text()"),
    (r"open\s*\([^)]*[\"']w[\"']", "open(...,'w')"),
]

# Só olha comandos que mencionam a mente. Sem isto o gate barraria o mundo.
ALVO = re.compile(r"\.claude\b", re.I)

# Abertura de heredoc: <<EOF, <<'EOF', <<"EOF", <<-EOF
RE_HEREDOC = re.compile(r"<<-?\s*([\"']?)([A-Za-z_][A-Za-z0-9_]*)\1")

# O trecho de um comando que PROCURA por um termo literal. Pega o padrao de
# busca logo depois do verbo (grep/rg/...) e o `in` de comparacao do Python,
# que e como um `python -c` verifica se um texto existe num arquivo.
RE_BUSCA = re.compile(
    r"(?:\b(?:grep|egrep|fgrep|rg|ripgrep|ag|findstr|Select-String|sls)\b"
    r"(?:\s+-{1,2}[A-Za-z-]+)*\s+(?P<t1>\"[^\"]*\"|'[^']*'|\S+))"
    r"|(?:(?P<t2>\"[^\"]*\"|'[^']*')\s+in\s+[A-Za-z_])")


# ── O SEGUNDO EIXO: apagar coisa de OUTRO DONO ───────────────────────────────
#
# Numa sessão de um projeto eu apaguei uma pasta em `/tmp` numa VPS. Aquela
# cópia era de OUTRO projeto (o `git remote` dizia) — outro
# projeto, outro responsável. Eu tinha o OK dele para "apagar as duas cópias",
# mas o OK foi dado quando **eu as descrevi como equivalentes**; que uma era de
# outro dono só descobri DEPOIS, lendo o `git remote`, e segui assim mesmo.
#
# Ele, verbatim: *"vc tá apagando coisa do seu projeto né [...] não está metendo
# a mão em outro projeto e quebrando nada de outro responsável, certo?"* e
# *"eu toco 10 projetos ao mesmo tempo, e não posso confiar no que vc tá fazendo,
# tem que ficar igual babá vendo o que tá fazendo [...] e aí eu libero para vc
# ter autonomia e faz isso"*.
#
# O dano em dado foi **zero** (os blobs sujos já estavam commitados na origem, e
# aquele projeto seguiu commitando 4× depois do `rm`). O que quebrou foi a
# **premissa da autonomia**: quem trabalha assim não valida diff,
# então o MECANISMO é a rede de segurança — não a revisão.
#
# 🔴 O BURACO, MEDIDO: havia gate para tudo, menos para isto.
#   · `fronteira_de_projeto.py` já pergunta "de quem é este arquivo?" — mas só
#     em PreToolUse|**Edit|Write**. O `rm` foi por **Bash**.
#   · este arquivo já bloqueia destrutivo por Bash — mas só quando o alvo casa
#     `ALVO` (linha 99), que é `\.claude\b`. `/tmp/eval380` não casa.
#   · nenhum dos dois enxerga caminho **remoto**: o comando roda por `ssh` e o
#     alvo mora na VPS, onde convivem os 10 projetos dele.
# Os dois eixos daquele comando — ferramenta Bash **e** alvo remoto — eram
# exatamente os dois que ninguém cobria.
#
# 🔑 O QUE ESTE GATE NÃO TENTA FAZER: adivinhar o dono de um caminho remoto.
# `/tmp/eval380` não diz a quem pertence; descobrir exige `git remote`, e hook
# não roda comando. Quem sabe o dono sou eu, no instante em que escrevo o `rm`.
# Então a regra não é "adivinhe o dono" — é **"declare que você checou"**.

# Verbos de ALTO dano: recursivos, ou que descartam trabalho não salvo.
# ⚠️ `rm -f arquivo.mjs` (não recursivo, arquivo único) ficou FORA de propósito:
# é o padrão de limpeza dos meus próprios scripts na VPS, o dano é limitado ao
# que eu mesmo criei, e barrar isso viraria atrito diário — gate que estorva no
# caso inofensivo ensina a procurar o escape.
VERBOS_ALTO_DANO = [
    (r"\brm\b[^\n;|&]*\s-[a-zA-Z]*r", "rm recursivo (-r/-rf)"),
    (r"\brm\b[^\n;|&]*\*", "rm com glob (*)"),
    (r"\bgit\b[^\n;|&]*\breset\b[^\n;|&]*--hard", "git reset --hard"),
    (r"\bgit\b[^\n;|&]*\bclean\b[^\n;|&]*-[a-zA-Z]*[fd]", "git clean -fd"),
    (r"\bshred\b", "shred"),
    (r"\bdd\b[^\n;|&]*\bof=", "dd of="),
    (r"\btruncate\b", "truncate"),
    (r"\bfind\b[^\n;|&]*-delete\b", "find -delete"),
    (r"\bfind\b[^\n;|&]*-exec\s+rm\b", "find -exec rm"),
    (r"\bmv\b\s+[^\n;|&]*\s/(?:opt|srv|var|etc|root|home)\b", "mv para área de sistema"),
]

# Comando que atravessa para outra máquina.
RE_REMOTO = re.compile(r"\b(ssh|scp|rsync)\b", re.I)

# Caminho absoluto estilo POSIX — o que aparece em comando de VPS.
RE_ABS_POSIX = re.compile(r"(?<![\w/])(/(?:tmp|opt|srv|var|etc|root|home|mnt|data)[\w./-]*)")


# ── O TERCEIRO EIXO: ESCREVER em projeto alheio pelo Bash ───────────────────
#
# este arquivo nasceu porque os gates vigiavam a ferramenta segura (Write)
# e deixavam passar a perigosa (Bash). Fechou a fatia DESTRUICAO. Hoje a mesma
# classe apareceu na fatia ESCRITA, e foi uma pessoa quem pegou, nao o gate:
# numa sessao do Central-Comando-360, um script Python rodado por Bash gravou em
# um script gravou dentro de `<PROJETOS>/<outro-projeto>/scripts/` — projeto
# alheio, o caso exato que o `fronteira_de_projeto.py` existe para impedir — e
# houve ZERO bloqueios, porque aquele hook so escuta `Edit|Write`.
#
# Medido com o gate original: das 6 formas de gravar arquivo pelo
# Bash em projeto alheio (open(w), `>`, `sed -i`, heredoc, `tee`, prosa .md),
# **as 6 passaram**. E o controle mostrou um furo que ninguem tinha reportado:
# apagar recursivo em projeto alheio com caminho WINDOWS tambem passava, porque
# `RE_ABS_POSIX` so casa `/tmp|/opt|/srv|...` e os 33 projetos dele moram em
# `<PROJETOS>\`. O eixo do dono estava cego para a maquina local.
#
# 🔑 A REGRA E A MESMA DOS OUTROS EIXOS: nao e "adivinhe a intencao" — e
# "declare que voce checou". Ler projeto alheio continua livre (VER e
# deliberado, a Ronda do Diretor injeta isso de proposito). O que interrompe e
# ESCREVER.
VERBOS_DE_ESCRITA = [
    (r">>?\s*[\"']?(?=[~./A-Za-z])", "redirecionamento (> ou >>)"),
    (r"\btee\b", "tee"),
    (r"\bsed\b[^\n;|&]*\s-[a-zA-Z]*i", "sed -i (edicao no lugar)"),
    (r"\bperl\b[^\n;|&]*\s-[a-zA-Z]*i", "perl -i"),
    (r"\bcp\b", "cp"),
    (r"\bmv\b", "mv"),
    (r"\btouch\b", "touch"),
    (r"\binstall\b\s+-", "install"),
    (r"\bdd\b[^\n;|&]*\bof=", "dd of="),
    (r"\bcurl\b[^\n;|&]*\s-[a-zA-Z]*[oO]\b", "curl -o"),
    (r"\bwget\b[^\n;|&]*\s-[a-zA-Z]*O\b", "wget -O"),
    (r"open\s*\([^)]*[\"'][waxr]\+?[bt]?[\"']", "open(..., 'w'/'a')"),
    (r"\bwrite_text\s*\(", "write_text()"),
    (r"\bjson\.dump\s*\(", "json.dump()"),
    (r"\bshutil\.copy\w*\s*\(", "shutil.copy()"),
    (r"\bos\.rename\b", "os.rename"),
    (r"\bgit\b[^\n;|&]*\b(?:commit|checkout|apply|stash)\b", "git que altera o disco"),
]


def verbos_de_escrita(cmd):
    return [nome for padrao, nome in VERBOS_DE_ESCRITA if re.search(padrao, cmd)]


# 🔴 SEGMENTAR É OBRIGATÓRIO, e descobri por uso, não por leitura.
# Minutos depois de instalar, este comando legítimo foi negado:
#     echo x > ./SONDA.txt && head -c 60 .../<outro-projeto>/CLAUDE.md
# Ele ESCREVE no próprio projeto e apenas LÊ o alheio. O detector perguntava
# "há verbo de escrita?" e "há caminho alheio?" sobre o comando INTEIRO, sem
# ligar um ao outro — e num `&&` as duas respostas são sim por motivos
# diferentes. Avaliar cada segmento isolado é o que amarra verbo ao alvo.
# Ler projeto alheio tinha de continuar livre, e essa era a promessa que o
# próprio gate quebrou na primeira hora.
RE_SEPARADOR = re.compile(r"&&|\|\||;|\|")


def segmentos(cmd):
    """Pedaços executáveis do comando. O conteúdo de heredoc não é comando."""
    partes, aberto = [], None
    for linha in cmd.split("\n"):
        if aberto is not None:
            if linha.strip() == aberto:
                aberto = None
            continue
        m = RE_HEREDOC.search(linha)
        if m:
            aberto = m.group(2)          # a linha que ABRE ainda é comando
        partes += [p for p in RE_SEPARADOR.split(linha) if p.strip()]
    return partes or [cmd]


def por_segmento(funcao, cmd, cwd):
    """Roda `funcao` em cada segmento e junta, sem repetir o mesmo motivo."""
    achados, vistos = [], set()
    for seg in segmentos(cmd):
        for motivo in funcao(seg, cwd):
            if motivo[0] not in vistos:
                vistos.add(motivo[0])
                achados.append(motivo)
    return achados


# 🔴 O ALVO DA ESCRITA, não qualquer caminho do segmento. Segunda correção da
# mesma hora, e de novo achada por USO: `head -c 40 .../<outro>/CLAUDE.md
# > /dev/null` tem redirecionamento E caminho alheio no mesmo segmento, mas o
# alvo da gravação é `/dev/null` e o caminho alheio é ENTRADA. Segmentar por
# `&&` resolveu o comando composto e não resolveu este. A pergunta certa não é
# "há escrita e há caminho alheio?", é "o que exatamente vai ser gravado?".
RE_REDIRECIONA = re.compile(r">>?\s*([\"']?)([^\s\"'|&;<>]+)\1")
RE_DOIS_ARGS = re.compile(
    r"\b(?:cp|mv|rsync|install)\b|\bshutil\.(?:copy\w*|move)\s*\(|\bos\.rename\b")


def alvos_de_escrita(seg):
    """Os caminhos que este segmento realmente GRAVA."""
    alvos = [m.group(2) for m in RE_REDIRECIONA.finditer(seg)]
    outros = [n for p, n in VERBOS_DE_ESCRITA
              if not n.startswith("redirecionamento") and re.search(p, seg)]
    if not outros:
        return alvos
    # 🔴 DUAS CLASSES, e confundi-las me custou duas rodadas hoje.
    # (1) Verbo de DOIS ARGUMENTOS (cp, mv, rsync): origem e destino ocupam
    #     posições, e só o destino conta. `cp alheio/x ./meu` é leitura do
    #     alheio e passa. Tentei "último caminho de projeto" e devolvia a
    #     ORIGEM; o certo é o último token.
    # (2) Todo o resto (tee, sed -i, open(w), touch...): não há origem em
    #     caminho, então qualquer caminho citado no segmento é destino.
    #     Aqui usar "último token" foi REGRESSÃO medida: em
    #     `python -c "open(r'...alheio...','w').write('x')"` o `split()` por
    #     espaço parte a string entre aspas e o último token vira `3')"`,
    #     que não contém caminho nenhum — e a escrita alheia PASSOU ao vivo.
    if RE_DOIS_ARGS.search(seg):
        tokens = [t for t in seg.split() if not t.startswith("-")]
        if tokens:
            alvos.append(tokens[-1])
        return alvos
    alvos.append(seg)
    return alvos


def escrita_fora_do_projeto(cmd, cwd):
    """[(titulo, detalhe, conserto)] — escrever em projeto que nao e o da sessao."""
    raiz_sessao = _fl().raiz_de_projeto(cwd)
    if not raiz_sessao:
        return []                       # sessao fora de `Projeto\`: nada a dizer
    verbos = verbos_de_escrita(cmd)
    if not verbos:
        return []                       # so leitura: VER projeto alheio e livre
    alheias = sorted({r for alvo in alvos_de_escrita(cmd)
                      for r in _fl().raizes_citadas(alvo)
                      if not _fl().mesmo_projeto(r, raiz_sessao)})
    if not alheias:
        return []
    return [(
        "ESCRITA em projeto alheio pelo Bash: %s." % ", ".join(verbos),
        ("A sessao esta no projeto **%s** e o comando toca **%s**.\n    "
         "O `fronteira_de_projeto.py` faria esta pergunta — mas ele so escuta "
         "`Edit|Write`, e por aqui a escrita entra pela porta que ele nao vigia. "
         "Ler projeto alheio e livre e deliberado (a Ronda do Diretor mostra "
         "pendencia dos outros de proposito); ESCREVER exige abrir o projeto "
         "dono, que carrega o pre-voo dele — DECISIONS.md, CLAUDE.md, stories. "
         "Daqui, esse contexto nao esta na mesa."
         % (raiz_sessao, ", ".join(alheias))),
        ("Se a escrita AQUI for mesmo a certa — ordem dele, ou peca transversal — "
         "diga numa frase por que, e repita com `%s escrevo em <PROJETO> porque "
         "<motivo>`." % MARCADOR_OK))]


def verbos_alto_dano(cmd):
    return [nome for padrao, nome in VERBOS_ALTO_DANO if re.search(padrao, cmd)]


def _sob(caminho, raiz):
    """`caminho` está dentro de `raiz`? Comparação normalizada, sem tocar o disco."""
    if not raiz:
        return False
    try:
        a = os.path.normcase(os.path.abspath(caminho))
        b = os.path.normcase(os.path.abspath(raiz))
        return a == b or a.startswith(b + os.sep)
    except (ValueError, TypeError):
        return False


def fronteira_de_dono(cmd, cwd):
    """[(titulo, detalhe, conserto)] — o segundo eixo do gate."""
    verbos = verbos_alto_dano(cmd)
    if not verbos:
        return []
    lista = ", ".join(verbos)

    # 1. Destrutivo atravessando para outra máquina.
    if RE_REMOTO.search(cmd):
        alvos = sorted(set(RE_ABS_POSIX.findall(cmd)))[:6]
        onde = ("\n    alvo(s): " + ", ".join(alvos)) if alvos else ""
        return [(
            "Comando de ALTO DANO indo para OUTRA MÁQUINA: %s." % lista,
            ("Numa máquina remota convivem projetos de donos diferentes, e o "
             "caminho não diz de quem é: uma pasta em `/tmp` parecia lixo e era "
             "o clone de outro projeto. Este gate não descobre o dono daqui; "
             "você descobre, com `git -C <alvo> remote -v`." + onde),
            ("Antes de repetir: `git -C <alvo> remote -v` + `git status`, e prove que "
             "o conteúdo existe na origem (`git hash-object` + `git cat-file -e`). "
             "Depois repita com `%s este alvo é do projeto <NOME>, conferido`. "
             "🔴 Se o dono NÃO for o projeto desta sessão, isso é decisão DELE — "
             "pergunte, não conclua que a prova técnica basta." % MARCADOR_OK))]

    # 2. Destrutivo local fora do projeto da sessão.
    # 🔴 Este ramo era CEGO na máquina local. `RE_ABS_POSIX` só casa
    # `/tmp|/opt|/srv|/var|/etc|/root|/home|/mnt|/data`, e os 33 projetos moram em
    # `<PROJETOS>\`: apagar recursivo em projeto alheio com caminho
    # Windows PASSAVA `[medido: sonda de 8 casos]`. O eixo do dono nasceu
    # de um `rm` na VPS e só enxergava a VPS.
    scratch = os.environ.get("CLAUDE_SCRATCHPAD_DIR") or ""
    fora = sorted({a for a in RE_ABS_POSIX.findall(cmd)
                   if not _sob(a, cwd) and not _sob(a, scratch)})
    raiz_sessao = _fl().raiz_de_projeto(cwd)
    if raiz_sessao:
        fora += sorted(r for r in _fl().raizes_citadas(cmd)
                       if not _fl().mesmo_projeto(r, raiz_sessao))
    if fora:
        return [(
            "Comando de ALTO DANO fora do projeto desta sessão: %s." % lista,
            ("A sessão está em `%s`, e o alvo está fora dela:\n    %s\n    "
             "Você vê pendência de outro projeto de propósito (a Ronda do Diretor), "
             "mas VER não é AGIR — e apagar é a forma de agir que não tem desfazer."
             % (cwd or "(cwd desconhecido)", ", ".join(fora[:6]))),
            ("Se for mesmo o certo, repita com `%s este alvo é do projeto <NOME>, "
             "conferido`." % MARCADOR_OK))]

    return []


def heredoc_aninhado_mesmo_delimitador(cmd):
    """Devolve o delimitador culpado, ou None.

    Percorre linha a linha como o bash faz. Quando um heredoc D está aberto, as
    linhas seguintes são CONTEÚDO até uma linha igual a D. Se dentro desse
    conteúdo aparecer uma abertura do PRÓPRIO D, é a armadilha: eu quis aninhar,
    o bash fechou cedo, e o resto do meu texto virou comando.

    Heredocs em SEQUÊNCIA com o mesmo nome não são pegos — aquilo funciona, e eu
    mesmo usei hoje sem problema. O que se proíbe é o aninhamento.
    """
    aberto = None
    for linha in cmd.split("\n"):
        if aberto is None:
            m = RE_HEREDOC.search(linha)
            if m:
                aberto = m.group(2)
            continue
        if linha.strip() == aberto:
            aberto = None
            continue
        m = RE_HEREDOC.search(linha)
        if m and m.group(2) == aberto:
            return aberto
    return None


def heredoc_com_acento(cmd):
    """Devolve (delimitador, amostra) se o CONTEUDO de um heredoc tem acento.

    O QUARTO EIXO, e o unico que nao trata de destruir nem de
    invadir projeto alheio: trata de ENTREGAR TEXTO ERRADO em silencio.

    O estrago medido: escrevi 53 caracteres U+FFFD numa nota de memoria - os
    acentos de "irmao", "relogio", "tres vezes" viraram o losango de
    substituicao. O arquivo continua sendo UTF-8 valido, o comando sai com
    exit 0, e nada avisa. Varri a mente depois: **31 arquivos** ja carregam
    esse estrago, o `PADROES.md` com 180 caracteres
    `[medido: varredura de 2.329 arquivos]`.

    E o pior: a regra JA ESTAVA ESCRITA, em quatro memorias diferentes desde
    antes - uma delas, a propria nota sobre o assunto, corrompida pelo
    proprio defeito que descreve. Texto nao me alcancou quatro vezes. Por isso
    virou porta: e a escada de forca da casa (texto < recall < varredura <
    gate na porta) aplicada a um caso em que os tres primeiros degraus ja
    falharam, com data.

    Nao e determinístico qual comando corrompe - um `cat` heredoc sozinho
    gravou bytes corretos no mesmo dia em que a combinacao com `python - <<`
    corrompeu 5 de 5 acentos. Causa nao reproduzida nao vira regra; a defesa,
    sim: texto acentuado para a mente vai pela ferramenta de escrita.
    """
    aberto = None
    conteudo = []
    for linha in cmd.split("\n"):
        if aberto is None:
            m = RE_HEREDOC.search(linha)
            if m:
                aberto = m.group(2)
                conteudo = []
            continue
        if linha.strip() == aberto:
            texto = "\n".join(conteudo)
            fora = [c for c in texto if ord(c) > 127]
            if fora:
                amostra = "".join(sorted(set(fora))[:8])
                return aberto, amostra
            aberto = None
            continue
        conteudo.append(linha)
    if aberto is not None:                  # heredoc sem fechamento no comando
        texto = "\n".join(conteudo)
        fora = [c for c in texto if ord(c) > 127]
        if fora:
            return aberto, "".join(sorted(set(fora))[:8])
    return None


def busca_com_acento(cmd):
    """Devolve o termo culpado se o comando PROCURA por texto acentuado.

    O irmao pior de `heredoc_com_acento`, medido meia hora depois.
    La o acento se perde na ESCRITA e o estrago fica no arquivo, visivel a
    quem reler. Aqui ele se perde na COMPARACAO, e o que sai e um VEREDITO:

        grep -c "correcoes" arquivo.md   -> 0      (pelo Bash)
        ferramenta Grep do harness       -> 1      (o certo)

    Os dois numeros acima sao do MESMO arquivo, no mesmo instante
    `[medido]`. A palavra chega ao grep com o acento ja trocado por
    U+FFFD, entao ele procura uma coisa que ninguem escreveu e responde
    honestamente que nao achou. Exit 1, nenhum erro, nenhum aviso.

    Por que isso e mais grave que gravar errado: a REGRA #0 desta casa manda
    VERIFICAR antes de afirmar, e verificar aqui e quase sempre grep. Um
    instrumento de verificacao que responde "nao existe" para coisa que existe
    nao produz um bug - produz uma afirmacao falsa com cara de medida. E da
    familia de [[concept-a-cegueira-que-responde-200]]: entrada nao-vazia,
    saida vazia, e nada distingue "nao ha" de "nao consegui ver".

    So pega comando de BUSCA (grep/rg/findstr/select-string, ou `in` de
    Python), porque e ai que o silencio vira veredito. Acento em `echo` ou em
    mensagem de commit e outra conversa - erra, mas erra visivel.
    """
    if not any(ord(c) > 127 for c in cmd):
        return None
    for m in RE_BUSCA.finditer(cmd):
        termo = m.group(0)
        fora = [c for c in termo if ord(c) > 127]
        if fora:
            return " ".join(termo.split())[:70]
    return None


def verbos_encontrados(cmd):
    achados = []
    for padrao, nome in VERBOS_DESTRUTIVOS:
        if re.search(padrao, cmd):
            achados.append(nome)
    return achados


def analisar(cmd, cwd=""):
    """[(titulo, detalhe, conserto)] — vazio = pode passar."""
    if MARCADOR_OK in cmd:
        return []
    motivos = []

    delim = heredoc_aninhado_mesmo_delimitador(cmd)
    if delim:
        motivos.append((
            "HEREDOC ANINHADO com o delimitador `%s` repetido." % delim,
            "O `%s` de dentro FECHA o de fora. Tudo o que vem depois deixa de ser "
            "conteúdo e vira comando executado pelo bash. Foi assim que 5 hooks "
            "e 5 registros do settings.json foram apagados aqui." % delim,
            "Conteúdo que contém shell ou python vai pela ferramenta de ESCRITA "
            "(Write), nunca por heredoc. Se for mesmo heredoc, use delimitadores "
            "diferentes e nunca aninhe."))

    # 🔴 O QUARTO EIXO: heredoc carregando texto ACENTUADO.
    # Fora do `if ALVO` porque o estrago não depende de o alvo ser `.claude`:
    # o que se perde é o conteúdo, em qualquer arquivo. Recusa antes de rodar,
    # porque depois de rodar o arquivo está gravado, válido e errado.
    acento = heredoc_com_acento(cmd)
    if acento:
        delim_ac, amostra = acento
        motivos.append((
            "HEREDOC (`%s`) carregando texto com ACENTO: %s" % (delim_ac,
                                                                amostra),
            "Neste ambiente isso às vezes grava U+FFFD no lugar da letra — o "
            "arquivo sai UTF-8 válido, o comando sai com exit 0, e nada "
            "avisa. Aqui foram 53 caracteres perdidos numa nota; a varredura "
            "seguinte achou 31 arquivos já estragados assim, um deles com "
            "180. A regra estava escrita em 4 lugares e não me alcançou "
            "nenhuma das vezes — foi por isso que ela virou bloqueio.",
            "Texto com acento vai pela ferramenta de ESCRITA (Write), que "
            "chega em UTF-8 exato; o shell carrega só CAMINHOS. Se for mesmo "
            "necessário aqui, repita com `%s <motivo>` e depois confira em "
            "bytes: `texto.count(chr(0xFFFD))` tem de dar 0." % MARCADOR_OK))

    termo = busca_com_acento(cmd)
    if termo:
        motivos.append((
            "BUSCA por texto ACENTUADO pelo Bash: %s" % termo,
            "O termo chega ao grep com o acento já trocado, então ele procura "
            "o que ninguém escreveu e responde honestamente que não achou: "
            "exit 1, zero ocorrências, nenhum aviso. Medido no mesmo "
            "arquivo e no mesmo instante: `grep -c` pelo Bash deu 0, a "
            "ferramenta Grep deu 1. A REGRA #0 manda verificar antes de "
            "afirmar, e verificar aqui é quase sempre grep — um instrumento "
            "que diz \"não existe\" para o que existe não gera um bug, gera "
            "uma afirmação falsa com cara de medida.",
            "Use a ferramenta **Grep** do harness, que recebe o padrão em "
            "UTF-8 exato. Se precisar ser aqui: `grep -f termo.txt` (o termo "
            "por ARQUIVO, medido funcionando), ou procure um trecho sem "
            "acento da mesma linha. Em `python -c`, escape unicode "
            "(`corre\\u00e7\\u00f5es`) passa, porque o comando fica ASCII — "
            "mas NÃO serve para grep, que trata `\\u00e7` como literal e "
            "devolve 0 `[medido]`. Deliberado: `%s <motivo>`."
            % MARCADOR_OK))

    if ALVO.search(cmd):
        verbos = verbos_encontrados(cmd)
        if verbos:
            motivos.append((
                "Comando DESTRUTIVO tocando `~/.claude`: %s." % ", ".join(verbos),
                "`~/.claude` é a mente inteira — os hooks, as memórias dos "
                "projetos, os briefs e o settings.json. Um erro aqui não tem "
                "desfazer, e o backup mais recente pode ter dias.",
                "Se é intencional, repita o comando com `%s <motivo>` no fim. "
                "Repetir sem o marcador NÃO passa." % MARCADOR_OK))

    # 🔴 O SEGUNDO EIXO: apagar coisa de outro DONO. Roda fora do
    # `if ALVO` de propósito — foi justamente por o alvo NÃO ser `.claude` que o
    # um `rm -rf` numa pasta de `/tmp` (clone de outro projeto) passou liso.
    # 🔴 FAIL-SAFE, e a escolha é deliberada. Os dois eixos abaixo dependem do
    # `fronteira_lib`. Se ele sumir ou quebrar, um `raise` aqui derrubaria o hook
    # inteiro e o Claude Code seguiria SEM gate nenhum — o modo de falha que este
    # arquivo mais teme ("gate que morre parece gate que aprovou"). Então o erro
    # NEGA, em vez de passar. A válvula continua aberta: `# GATE-OK:` é checado
    # na primeira linha de `analisar()`, antes de qualquer import.
    try:
        motivos += por_segmento(fronteira_de_dono, cmd, cwd)
        # O TERCEIRO EIXO: ESCREVER em projeto alheio pelo Bash.
        # Separado do eixo de destruição de propósito — gravar não é apagar, e a
        # mensagem precisa dizer a coisa certa para eu ler o aviso certo.
        motivos += por_segmento(escrita_fora_do_projeto, cmd, cwd)
    except Exception as erro:                        # noqa: BLE001
        motivos.append((
            "GATE DE FRONTEIRA QUEBRADO: %s: %s" % (type(erro).__name__, erro),
            ("`bash_na_porta.py` nao conseguiu decidir de quem e o alvo deste "
             "comando, entao nao pode afirmar que ele e seguro. Isto NEGA em vez "
             "de passar de proposito: gate que morre em silencio parece gate que "
             "aprovou."),
            ("Conferir `~/.claude/hooks/fronteira_lib.py` (existe? importa?) e "
             "rodar `python ~/.claude/hooks/testar_fronteira_bash.py`. Para "
             "seguir enquanto conserta, use `%s <motivo>`." % MARCADOR_OK)))

    return motivos


def registrar(motivos):
    try:
        with open(GATES_LOG, "a", encoding="utf-8") as fh:
            fh.write("\t".join([
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "bash", "deny", "", motivos[0][0][:150]]) + "\n")
    except Exception:
        pass


def negar(motivos):
    # O título segue o motivo: os dois eixos deste gate têm donos diferentes de
    # estrago (a mente num caso; projeto de terceiro no outro), e um título que
    # fala da mente num `rm` de VPS faria eu ler o aviso errado.
    de_dono = any("OUTRA MÁQUINA" in t or "fora do projeto" in t for t, _, _ in motivos)
    de_escrita = any("ESCRITA em projeto alheio" in t for t, _, _ in motivos)
    if de_dono:
        cabeca = "PARE — isto pode apagar coisa de OUTRO DONO."
    elif de_escrita:
        cabeca = "PARE — isto GRAVA em projeto que nao e o desta sessao."
    else:
        cabeca = "PARE — este comando Bash pode destruir a mente."
    linhas = [cabeca, ""]
    for titulo, detalhe, conserto in motivos:
        linhas += ["  · " + titulo, "    " + detalhe, "    → " + conserto, ""]
    linhas += [
        ("Origem, verbatim: *\"vc tá apagando coisa do seu projeto né, "
         "vc tá seguro [...] não está metendo a mão em outro projeto e quebrando "
         "nada de outro responsável, certo?\"* — a resposta honesta era NÃO.\n"
         "Quem trabalha com 10 projetos e NÃO valida diff depende do mecanismo "
         "como rede de segurança, não da revisão.") if de_dono else
        ("Origem: numa sessão de um projeto, um script Python rodado por Bash "
         "gravou dentro de OUTRO projeto, e os 4 gates de escrita da casa não "
         "viram nada, porque todos escutam só `Edit|Write`. Quem pegou foi uma "
         "pessoa.\n"
         "Este eixo NÃO cede na repetição de propósito: o gate que cede na 2ª "
         "tentativa foi o que ensinou o hábito de repetir até passar.")
        if de_escrita else
        "Este gate nasceu de um estrago real e NÃO cede na segunda "
        "tentativa — ao contrário dos outros gates da casa.",
    ]
    registrar(motivos)
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "\n".join(linhas)}}, ensure_ascii=False))


def main():
    # stdin em utf-8 explícito: no cp1252 do Windows o payload volta mojibake e o
    # gate fica INERTE em silêncio — foi o que aconteceu com o soberano_na_porta
    # desde que nasceu, por semanas.
    try:
        ent = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
    except (ValueError, AttributeError):
        return
    if ent.get("tool_name") != "Bash":
        return
    cmd = (ent.get("tool_input") or {}).get("command") or ""
    if not cmd:
        return
    motivos = analisar(cmd, ent.get("cwd") or "")
    if motivos:
        negar(motivos)


if __name__ == "__main__":
    main()
