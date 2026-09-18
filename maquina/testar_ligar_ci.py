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
except Exception:  # noqa: BLE001,S110 - sem stdout nao ha para onde avisar
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import ligar_ci as lc  # noqa: E402
import o_basico as ob  # noqa: E402

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

    # -- 4b. INJECAO DE COMANDO: o nome do arquivo vem do disco ALHEIO -------
    # 🔴 O `provar()` ja rodou com `shell=True`, e o nome do arquivo de
    # teste era interpolado direto no comando. Um arquivo chamado
    # `testar_x.py && <comando>` executava o `<comando>` em 30 projetos. E o
    # mesmo texto ia para o `run:` do workflow, levando a injecao para o CI do
    # projeto alvo.
    #
    # A prova aqui e de EFEITO, nao de forma: o teste planta um arquivo cujo
    # nome tenta criar uma sonda no disco, roda a peca, e exige que a sonda
    # NAO exista. Afirmar "agora usa lista de argumentos" seria descrever o
    # conserto; isto mede se ele segura.
    print(N + "== 4b. INJECAO pelo NOME do arquivo (o disco e de outro dono) ==")
    # ⚠️ O nome hostil NAO usa `>` nem aspas de proposito: o Windows recusa
    # esses caracteres em nome de arquivo, e um teste que nao consegue PLANTAR
    # o caso nao mede nada. `&` e espaco o Windows aceita — e `&&` e tudo o
    # que a injecao precisa. A carga util fica num script separado, para o
    # nome ficar dentro do que o sistema de arquivos permite.
    SONDA = os.path.join(raiz, "SONDA_INJECAO.txt")
    b = repo(raiz, "injecao", {"testar_ok.py": "print('ok')" + N})
    escreve(os.path.join(b, "carga.py"),
            "import io\nio.open(r'%s','w').write('injetado')\n"
            % SONDA.replace("\\", "\\\\"))
    hostil = "testar_ok.py && python carga.py"
    try:
        escreve(os.path.join(b, hostil), "print('nao devia rodar')" + N)
        plantou = True
    except OSError:
        # Windows recusa alguns caracteres em nome de arquivo. O teste diz
        # isso em vez de fingir que mediu.
        plantou = False

    if plantou:
        lc.um("injecao", escrever=True)
        diz("o nome hostil NAO virou comando (sonda nao existe)",
            not os.path.isfile(SONDA),
            "A SONDA FOI CRIADA: houve execucao")
        nome_rel = hostil.replace("\\", "/")
        _, cmd_inj, _ = lc.receita(b)
        diz("   e o arquivo hostil ficou FORA do comando",
            not cmd_inj or nome_rel not in cmd_inj, str(cmd_inj)[:70])
    else:
        print("  (nao medido: este sistema de arquivos recusa o nome hostil)")

    # E o filtro, direto: o que passa e o que nao passa.
    aceitos, recusados = lc._seguros(
        ["testar_ok.py", "pasta/testar_x.py", "testar_y.py && rm -rf /",
         "testar_z.py; curl evil", "testar_w.py | sh", "a$(whoami).py"])
    diz("o filtro aceita nome normal e recusa os 4 hostis",
        aceitos == ["testar_ok.py", "pasta/testar_x.py"] and len(recusados) == 4,
        "aceitos=%s" % aceitos)

    # E a execucao sem shell: comando com metacaractere e RECUSADO, nao
    # rebaixado para o shell. Rebaixar seria manter a porta com outro nome.
    diz("comando que exige shell nao e provado (e sem prova nao ha CI)",
        lc.argumentos("python -B x.py | tee log") == []
        and lc.argumentos("python -B x.py && python -B y.py")
        == [["python", "-B", "x.py"], ["python", "-B", "y.py"]])

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
