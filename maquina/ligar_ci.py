# -*- coding: utf-8 -*-
"""Liga o CI de um repositório aos testes que ele JÁ TEM.

    python ligar_ci.py <repo>            # diagnostica e PROVA, nao escreve
    python ligar_ci.py <repo> --escrever # emite o workflow
    python ligar_ci.py --todos           # todos os repositorios de uma vez

POR QUE ESTA PEÇA EXISTE
------------------------
Numa casa com 30 repositórios, a medição foi: 16 tinham teste escrito e apenas
5 tinham CI rodando esse teste. Onze projetos fizeram o trabalho e não colhiam
nada — o teste só roda se alguém lembrar de rodar na mão.

Isto não é lista para caçar um a um: é a capacidade que faltava. O criador de
projeto novo passa a chamá-la, para que nenhum projeto nasça sem CI.

🔴 A REGRA DURA DESTA PEÇA
--------------------------
**Ela NÃO escreve workflow cujo comando ela não viu passar.** CI que roda o
comando errado fica **verde sem testar nada** — e verde falso é pior que
vermelho, porque ninguém volta a olhar. Então:

  1. descobre o comando pela FORMA do repositório, não por palpite;
  2. **RODA o comando ali mesmo** e lê o código de saída;
  3. só emite o workflow se o comando rodou;
  4. se não rodou, diz o que faltou e **não escreve nada**.

O passo 2 é o que separa esta peça de um gerador de template.

CHAMADORES: `new-project.sh` (projeto novo) e `--todos` (os existentes).
COBRANÇA:   bloco `[6u]` do `mente_health`, que conta o buraco todo dia.
PROVA:      `_shared/testar_ligar_ci.py`, com mutação.
"""
import io
import json
import os
import re
import subprocess
import sys

# O console do Windows e cp1252 e explode em qualquer caractere fora do
# latim-1. Esta peca IMPRIME a saida de teste de outros projetos, que vem
# com acento, emoji e ate U+FFFD de encoding quebrado - sem isto ela morre
# no print DEPOIS de ja ter feito o trabalho. E a regra
# `modulo-reconfigura-stdout` da casa - e esta peca nasceu com o defeito
# que a propria regra descreve, o que diz algo sobre confiar na memoria.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001,S110 - sem stdout nao ha para onde avisar
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import o_basico as ob  # noqa: E402


def erro(msg):
    """Diagnostico vai para stderr; stdout fica so com resultado.

    Quem chama esta peca num `|` ou num `>` precisa poder separar as duas
    coisas. Misturadas, quem consome tem de adivinhar qual linha e resultado e
    qual e reclamacao.
    """
    sys.stderr.write(msg + chr(10))


def ler(p):
    try:
        return io.open(p, encoding="utf-8", errors="replace").read()
    except Exception:                                       # noqa: BLE001
        return ""


# 🔴 O NOME DO ARQUIVO VEM DO DISCO DE OUTRA PESSOA, e ja foi
# interpolado direto num comando que rodava com `shell=True`. Um arquivo
# chamado
#
#     testar_x.py && <um comando qualquer>
#
# virava, depois do `" && ".join(...)`:
#
#     python -B ok.py && python -B testar_x.py && curl ...s.sh | sh
#
# e esta peca varre 30 projetos. Pior: o mesmo texto ia para o `run:` do
# workflow gerado, entao a injecao viajaria para o CI do projeto alvo.
#
# 🔑 A ironia que fecha o caso: a `seguranca_na_porta` desta mesma casa tem a
# familia `execucao-perigosa`, e ela ACUSA a linha do `shell=True` — conferido
# rodando o detector contra ela. O gate nao pegou porque so olha codigo NOVO
# sendo escrito, e esta peca e mais velha que o gate. **Gate que so olha o
# futuro nao audita o passado.**
#
# A defesa tem duas camadas, e as duas sao necessarias:
#   1. AQUI: nome que nao casa `NOME_SEGURO` nao entra na receita, e o fato e
#      dito em voz alta — silenciar seria esconder um arquivo do CI;
#   2. no `provar()`: a execucao passa a ser por LISTA DE ARGUMENTOS, sem
#      shell. Sem metacaractere interpretado, nao ha o que injetar.
#
# Uma camada so bastaria para o caso conhecido. Duas bastam para o caso que
# ainda nao vi: se um dia o filtro deixar passar algo, a execucao sem shell
# continua tratando o nome como nome.
NOME_SEGURO = re.compile(r"^[\w./\\-]+$")


def _seguros(relativos):
    """(aceitos, recusados) — nome de arquivo que pode virar comando."""
    ok = [t for t in relativos if NOME_SEGURO.match(t)]
    return ok, [t for t in relativos if not NOME_SEGURO.match(t)]


def receita(base):
    """COMO rodar os testes deste repo. Devolve (nome, comando, ambiente).

    A ordem importa: o script proprio da casa (`testar_*.py`) vem antes do
    pytest, porque varios deles nao sao coletaveis pelo pytest - rodam
    sozinhos e reportam por `sys.exit(1)`.
    """
    arqs = list(ob.arquivos(base))
    rel = [a[len(base) + 1:].replace("\\", "/") for a in arqs]
    testes = [r for r in rel if ob.ARQ_TESTE.search(r)]
    py = [t for t in testes if t.endswith(".py")]
    js = [t for t in testes if t.endswith((".js", ".ts", ".tsx", ".mjs",
                                           ".cjs"))]

    pkg = os.path.join(base, "package.json")
    script_test = ""
    if os.path.isfile(pkg):
        try:
            script_test = ((json.loads(ler(pkg) or "{}").get("scripts")
                            or {}).get("test") or "")
        except Exception:  # noqa: BLE001,S110 - json alheio quebrado
            # nao e problema nosso: seguimos para as outras formas de teste
            pass

    proprios = sorted(t for t in py
                      if os.path.basename(t).startswith("testar_"))
    usa_pytest = any("import pytest" in ler(os.path.join(base, t))
                     or re.search(r"^def test_", ler(os.path.join(base, t)),
                                  re.M)
                     for t in py[:10])

    # \U0001f534 Worktree faz um projeto ENGOLIR o outro. Medido: num
    # repositorio com 71 testes proprios e um worktree de outro projeto
    # dentro, o pytest somava 6.500 testes, levava 544 s e acusava 2 falhas —
    # que eram do OUTRO dono. Sem o worktree: 1.391 testes, 39 s, zero falhas.
    # CI vermelho por defeito alheio nao ensina nada.
    wts = sorted(set(
        d for d in os.listdir(base)
        if os.path.isdir(os.path.join(base, d))
        and os.path.isfile(os.path.join(base, d, ".git"))))

    if proprios:
        proprios = [t for t in proprios
                    if not any(t.startswith(w + "/") for w in wts)]
        proprios, recusados = _seguros(proprios)
        # Dito em voz alta, nunca engolido: um arquivo fora do CI por causa do
        # NOME e um teste que deixa de rodar, e teste que some calado e pior
        # que teste que falha.
        for t in recusados:
            print("       ⚠ FORA do CI: `%s` tem caractere que virava comando"
                  % t[:70])
        if proprios:
            return ("script proprio da casa (%d)" % len(proprios),
                    " && ".join("python -B %s" % t for t in proprios),
                    "python")
    if usa_pytest:
        wts_ok, wts_ruins = _seguros(wts)
        for w in wts_ruins:
            print("       ⚠ worktree `%s` NAO entra no --ignore (nome)" % w[:60])
        ignora = "".join(" --ignore=%s" % w for w in wts_ok)
        return ("pytest" + (" (worktree fora: %s)" % ", ".join(wts_ok)
                            if wts_ok else ""),
                "python -m pytest -q" + ignora, "python")
    if script_test and "test" in script_test.lower():
        return ("npm test", "npm test", "node")
    if js:
        return ("node --test", "node --test", "node")
    return (None, None, None)


def argumentos(cmd):
    """O comando como LISTA de listas de argumentos, para rodar sem shell.

    O `cmd` e uma string porque e ela que vai para o `run:` do workflow — la
    o shell e do GitHub e nao ha como fugir dele. Aqui a mesma string vira
    argumentos separados, e cada `&&` vira um passo da sequencia.

    Devolve [] quando a string tem metacaractere que so o shell entende. Isso
    NAO e conservadorismo: se a peca nao consegue reproduzir o comando sem
    shell, ela nao pode provar que ele funciona — e ela so escreve o CI do que
    provou.
    """
    if re.search(r"[|;><`$(){}\[\]*?~\n]", cmd):
        return []
    return [p.split() for p in cmd.split("&&") if p.strip()]


def provar(base, cmd):
    """Roda o comando NO REPO, SEM shell. Devolve (ok, codigo, ultimas linhas).

    🔴 Rodava com `shell=True`, e o `cmd` carrega nome de arquivo
    lido do disco de outra pessoa. Agora cada passo vai como LISTA DE
    ARGUMENTOS: o sistema operacional trata cada item como um argumento, e
    `&&`, `|` ou `;` dentro de um nome deixam de ser operadores para virar o
    que sempre foram — caracteres de um nome de arquivo.

    Quando a string tem metacaractere que so o shell entende, a peca RECUSA em
    vez de cair para o shell. Cair de volta seria manter a porta aberta com um
    nome mais bonito.
    """
    passos = argumentos(cmd)
    if not passos:
        return (False, -1,
                ["comando exige shell (metacaractere) — NAO provado, e sem "
                 "prova este CI nao e escrito"])
    try:
        ultimas = []
        for argv in passos:
            r = subprocess.run(argv, cwd=base, capture_output=True,
                               timeout=600)
            saida = (r.stdout + r.stderr).decode("utf-8", "replace")
            ultimas = [l_.strip() for l_ in saida.rstrip().split("\n")
                       if l_.strip()]
            if r.returncode != 0:
                return (False, r.returncode, ultimas[-4:])
        return (True, 0, ultimas[-4:])
    except Exception as e:                                  # noqa: BLE001
        return (False, -1, ["%s: %s" % (type(e).__name__, e)])


def workflow(nome_receita, cmd, ambiente):
    setup = ("""      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
""" if ambiente == "python" else """      - uses: actions/setup-node@v4
        with:
          node-version: '22'
      - run: npm ci || npm install
""")
    hoje = __import__("datetime").date.today().isoformat()
    return """# Roda os testes que este repositorio JA TEM.
# Gerado por `_shared/ligar_ci.py` em %s, e o comando abaixo foi PROVADO
# rodando neste repo antes de este arquivo existir - receita: %s.
#
# Se este CI ficar vermelho, o teste quebrou. Nao afrouxe o comando: conserte
# o teste, ou apague-o se ele nao vale mais. CI verde que nao roda nada e a
# unica coisa pior que CI nenhum.
name: testes

on:
  push:
  pull_request:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  testes:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
%s      - name: Testes
        run: %s
""" % (hoje, nome_receita, setup, cmd)


def um(nome, escrever=False):
    base = os.path.join(ob.RAIZ, nome.replace("/", os.sep))
    if not os.path.isdir(base):
        erro("  %s: nao existe" % nome)
        return False
    r_nome, cmd, amb = receita(base)
    if not cmd:
        print("  %-26s SEM RECEITA - tem teste e nao da para saber como "
              "rodar. Nao escrevo nada." % nome[:26])
        return False
    print("  %-26s receita: %s" % (nome[:26], r_nome))
    print("  %-26s   comando: %s" % ("", cmd[:88]))
    ok, cod, ult = provar(base, cmd)
    print("  %-26s   PROVA LOCAL: %s (exit %d)"
          % ("", "PASSOU" if ok else "FALHOU", cod))
    for l_ in ult:
        print("  %-26s     %s" % ("", l_[:84]))
    if not ok:
        print("  %-26s   -> NAO escrevo workflow de comando que nao passa."
              % "")
        return False
    if not escrever:
        print("  %-26s   (diagnostico; --escrever para emitir)" % "")
        return True
    destino = os.path.join(base, ".github", "workflows", "testes.yml")
    if os.path.isfile(destino):
        print("  %-26s   ja existe - nao sobrescrevo." % "")
        return False
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    io.open(destino, "w", encoding="utf-8", newline="\n").write(
        workflow(r_nome, cmd, amb))
    print("  %-26s   ESCRITO: .github/workflows/testes.yml" % "")
    return True


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    escrever = "--escrever" in sys.argv
    if "--todos" in sys.argv:
        dados, _ = ob.medir()
        alvos = sorted(p for p, v in dados.items()
                       if v["tst"] and not v["cit"])
        print("PROJETOS COM TESTE QUE NENHUM CI RODA: %d" % len(alvos))
        print()
        for a in alvos:
            um(a, escrever)
            print()
        return 0
    if not args:
        print(__doc__)
        return 1
    return 0 if um(args[0], escrever) else 1


if __name__ == "__main__":
    sys.exit(main())
