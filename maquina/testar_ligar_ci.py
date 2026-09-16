# -*- coding: utf-8 -*-
"""Prova do `ligar_ci.py` — com mutação na garantia que importa.

    python _shared/testar_ligar_ci.py

A garantia central desta peça é UMA: **ela não escreve workflow de comando
que ela não viu passar**. Um CI que roda o comando errado fica verde sem
testar nada, e verde falso é pior que vermelho — ninguém volta a olhar.

Por isso metade das checagens é sobre a RECUSA, não sobre o acerto. E a
mutação desarma justamente o "provar antes", para ver se a recusa é real ou
decorativa.

Tudo roda em repositórios de mentira numa pasta temporária.

CHAMADOR: o verificador diário de saúde da casa.
"""
import io
import os
import shutil
import sys
import tempfile

# Este teste imprime saida de teste de outros projetos, que vem com
# acento e ate U+FFFD. O console do Windows e cp1252 e morre neles.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import ligar_ci as lc                                       # noqa: E402
import o_basico as ob                                       # noqa: E402

PASS = 0
FALHA = 0
N = chr(10)


def diz(rotulo, ok, extra=""):
    global PASS, FALHA
    if ok:
        PASS += 1
        print("  PASS  %s" % rotulo)
    else:
        FALHA += 1
        print("  FALHA %s%s" % (rotulo, ("   -> " + extra) if extra else ""))


def escreve(caminho, texto):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with io.open(caminho, "w", encoding="utf-8", newline="") as fh:
        fh.write(texto)


def repo(raiz, nome, arquivos):
    base = os.path.join(raiz, nome)
    os.makedirs(os.path.join(base, ".git"), exist_ok=True)
    for rel, conteudo in arquivos.items():
        escreve(os.path.join(base, rel.replace("/", os.sep)), conteudo)
    return base


print("== PROVA DO LIGAR_CI ==" + N)
raiz = tempfile.mkdtemp(prefix="ligarci-")
raiz_orig = ob.RAIZ
try:
    ob.RAIZ = raiz
    lc.ob.RAIZ = raiz

    print("== 1. DESCOBRE A RECEITA PELA FORMA DO REPO ==")
    b = repo(raiz, "com_proprio", {"testar_x.py": "print('ok')" + N})
    n, cmd, amb = lc.receita(b)
    diz("script proprio da casa",
        bool(n) and "proprio" in n and "testar_x.py" in (cmd or ""),
        str((n, cmd)))

    b = repo(raiz, "com_pytest",
             {"tests/test_x.py": "def test_x():" + N + "    assert 1" + N})
    n, cmd, amb = lc.receita(b)
    diz("pytest", n == "pytest" and "pytest" in (cmd or ""), str((n, cmd)))

    b = repo(raiz, "com_npm",
             {"package.json": '{"scripts":{"test":"vitest run"}}',
              "src/a.test.js": "test('x',()=>{})" + N})
    n, cmd, amb = lc.receita(b)
    diz("npm test", n == "npm test" and amb == "node", str((n, cmd)))

    b = repo(raiz, "sem_pista", {"leia.md": "sem teste aqui" + N})
    n, cmd, amb = lc.receita(b)
    diz("repo sem teste nao ganha receita", cmd is None, str((n, cmd)))

    print(N + "== 2. A GARANTIA: nao escreve comando que nao passou ==")
    b = repo(raiz, "teste_quebrado",
             {"testar_quebra.py": "import sys" + N + "sys.exit(1)" + N})
    ok = lc.um("teste_quebrado", escrever=True)
    wf = os.path.join(b, ".github", "workflows", "testes.yml")
    diz("recusa quando o teste FALHA", not ok)
    diz("  ...e NAO deixa workflow no disco", not os.path.isfile(wf))

    b = repo(raiz, "teste_bom", {"testar_bom.py": "print('tudo certo')" + N})
    ok = lc.um("teste_bom", escrever=True)
    wf = os.path.join(b, ".github", "workflows", "testes.yml")
    diz("escreve quando o teste PASSA", ok and os.path.isfile(wf))
    if os.path.isfile(wf):
        t = io.open(wf, encoding="utf-8").read()
        diz("  ...com o comando PROVADO dentro", "testar_bom.py" in t)
        diz("  ...e o aviso de nao afrouxar", "Nao afrouxe o comando" in t)

        print(N + "== 3. NAO SOBRESCREVE O QUE JA EXISTE ==")
        antes = t
        ok2 = lc.um("teste_bom", escrever=True)
        depois = io.open(wf, encoding="utf-8").read()
        diz("nao sobrescreve workflow existente",
            (not ok2) and antes == depois)

    print(N + "== 4. DIAGNOSTICO NAO ESCREVE ==")
    b = repo(raiz, "so_diagnostico", {"testar_ok.py": "print('ok')" + N})
    ok3 = lc.um("so_diagnostico", escrever=False)
    wf3 = os.path.join(b, ".github", "workflows", "testes.yml")
    diz("sem --escrever, nada vai para o disco",
        ok3 and not os.path.isfile(wf3))

    print(N + "== 5. MUTACAO (desarmar a recusa tem de virar dano) ==")
    b = repo(raiz, "mutacao",
             {"testar_quebra.py": "import sys" + N + "sys.exit(1)" + N})
    provar_orig = lc.provar
    try:
        lc.provar = lambda base, cmd: (True, 0, ["(prova desarmada)"])
        lc.um("mutacao", escrever=True)
        escreveu = os.path.isfile(os.path.join(b, ".github", "workflows",
                                               "testes.yml"))
    finally:
        lc.provar = provar_orig
    print("  [%s] sem a prova, ele escreve CI de teste quebrado"
          % ("DETECTADA" if escreveu else "SOBREVIVEU"))
    if not escreveu:
        FALHA += 1

    print("  -- controle --")
    b = repo(raiz, "controle",
             {"testar_quebra.py": "import sys" + N + "sys.exit(1)" + N})
    lc.um("controle", escrever=True)
    diz("com a prova armada, volta a recusar",
        not os.path.isfile(os.path.join(b, ".github", "workflows",
                                        "testes.yml")))
finally:
    ob.RAIZ = raiz_orig
    lc.ob.RAIZ = raiz_orig
    shutil.rmtree(raiz, ignore_errors=True)

print(N + "=== RESULTADO: %d PASS / %d FALHA ===" % (PASS, FALHA))
sys.exit(1 if FALHA else 0)
