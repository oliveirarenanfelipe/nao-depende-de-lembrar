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
except Exception:
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import o_basico as ob                                       # noqa: E402


def ler(p):
    try:
        return io.open(p, encoding="utf-8", errors="replace").read()
    except Exception:                                       # noqa: BLE001
        return ""


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
        except Exception:                                   # noqa: BLE001
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
        if proprios:
            return ("script proprio da casa (%d)" % len(proprios),
                    " && ".join("python -B %s" % t for t in proprios),
                    "python")
    if usa_pytest:
        ignora = "".join(" --ignore=%s" % w for w in wts)
        return ("pytest" + (" (worktree fora: %s)" % ", ".join(wts)
                            if wts else ""),
                "python -m pytest -q" + ignora, "python")
    if script_test and "test" in script_test.lower():
        return ("npm test", "npm test", "node")
    if js:
        return ("node --test", "node --test", "node")
    return (None, None, None)


def provar(base, cmd):
    """Roda o comando NO REPO. Devolve (ok, codigo, ultimas linhas)."""
    try:
        r = subprocess.run(cmd, cwd=base, shell=True, capture_output=True,
                           timeout=600)
        saida = (r.stdout + r.stderr).decode("utf-8", "replace")
        linhas = [l.strip() for l in saida.rstrip().split("\n") if l.strip()]
        return (r.returncode == 0, r.returncode, linhas[-4:])
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
        print("  %s: nao existe" % nome)
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
    for l in ult:
        print("  %-26s     %s" % ("", l[:84]))
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
