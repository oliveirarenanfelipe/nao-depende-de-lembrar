# -*- coding: utf-8 -*-
"""Prova do `antes_de_publicar.py` — com mutação em cada superfície.

    python -B maquina/testar_antes_de_publicar.py

Este gate é o último antes de um `push`, que não desfaz. Um gate assim só vale
pelo que ele ACUSA — se ele aprovar por não ter olhado, o estrago já saiu.

Por isso a prova monta um repositório git de verdade num diretório temporário
e planta, em cada uma das três superfícies, exatamente o defeito que já
aconteceu nesta casa:

    1. arquivo versionado com conteúdo privado    (4 linhas, num arquivo)
    2. arquivo solto esperando um `git add .`     (4 arquivos, gerados)
    3. mensagem de commit com conteúdo privado    (superfície que nenhum
                                                   gate de repositório olha)

E a mutação desarma a medição de cada uma, para provar que o verde vem de
medir, e não de não olhar.

CHAMADOR: `maquina/mapa.json`, lido pelo `inventario.py` — que o
`~/.claude/hooks/mente_health.py`, bloco `[6u]`, roda todo dia.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001,S110 - sem stdout nao ha para onde avisar
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import antes_de_publicar as ap  # noqa: E402

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


def escreve(p, t):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, "w", encoding="utf-8", newline=N).write(t)


def g(base, *args):
    return subprocess.run(("git",) + args, cwd=base, capture_output=True)


print("== PROVA DO GATE DO PUSH ==" + N)

# A linha suja e MONTADA, nunca escrita: um arquivo de teste que contem o
# texto privado literal seria acusado pelo proprio detector que ele prova.
# (O mesmo cuidado do `amostra_positiva()` do destilar.)
CAMINHO_SUJO = ("C" + ":" + chr(92) + "Users" + chr(92) + "fulano"
                + chr(92) + "Projeto")

banca = tempfile.mkdtemp(prefix="pub-")
try:
    print("== 1. UM REPOSITORIO DE VERDADE, LIMPO ==")
    g(banca, "init", "-q")
    g(banca, "config", "user.email", "prova" + chr(64) + "exemplo.invalid")
    g(banca, "config", "user.name", "Prova")
    escreve(os.path.join(banca, "limpo.py"), "print('ok')" + N)
    escreve(os.path.join(banca, ".gitignore"), "*.pyc" + N)
    g(banca, "add", "-A")
    g(banca, "commit", "-q", "-m", "feat: a primeira peca")

    r = ap.auditar(banca, isentos={})
    diz("mede um repositorio de verdade", r is not None)
    diz("repositorio limpo tem veredito 0", ap.veredito(r) == 0, str(r))
    diz("conta os arquivos versionados", r["versionados"] == 2,
        str(r["versionados"]))

    print(N + "== 2. ACUSA A SUPERFICIE 1: o que esta VERSIONADO ==")
    escreve(os.path.join(banca, "sujo.py"),
            "SAIDA = %r" % (CAMINHO_SUJO + chr(92) + "x.md") + N)
    g(banca, "add", "-A")
    g(banca, "commit", "-q", "-m", "feat: mais uma peca")
    r = ap.auditar(banca, isentos={})
    quais = [x[0] for x in r["sujos"]]
    diz("acusa o arquivo versionado com caminho de uma maquina",
        "sujo.py" in quais, str(quais))
    diz("e o veredito e 1 (privado no que sobe)", ap.veredito(r) == 1)

    print("  -- e a ISENCAO por NOME tira exatamente ele --")
    r2 = ap.auditar(banca, isentos={"sujo.py": "prova"})
    diz("isento por nome sai da conta", not r2["sujos"], str(r2["sujos"]))
    diz("e nada mais e isentado junto", ap.veredito(r2) == 0)

    print(N + "== 3. ACUSA A SUPERFICIE 2: o que espera um `git add .` ==")
    # O caso ja medido: o teste roda, escreve estado, e o arquivo fica
    # solto fora do .gitignore com o nome do dono do disco dentro.
    escreve(os.path.join(banca, "porta.estado.json"),
            '{"%s": 1.0}' % (CAMINHO_SUJO + chr(92) + "y.md") + N)
    escreve(os.path.join(banca, "rascunho.txt"), "nada demais" + N)
    r = ap.auditar(banca, isentos={"sujo.py": "prova"})
    diz("acusa o arquivo GERADO que ficou solto",
        "porta.estado.json" in r["soltos"], str(r["soltos"]))
    diz("acusa tambem o solto que nao e gerado",
        "rascunho.txt" in r["soltos"], str(r["soltos"]))
    # O veredito e `1` — a mesma reprovacao do privado, e de proposito. O `2`
    # da taxonomia da maquina e "nao deu para USAR", e esta peca mediu muito
    # bem. A razao da reprovacao vai no texto, que e onde ela serve.
    diz("e o veredito e 1 (mediu, e reprovou)", ap.veredito(r) == 1)

    print("  -- e o .gitignore RESOLVE, que e o conserto esperado --")
    escreve(os.path.join(banca, ".gitignore"),
            "*.pyc" + N + "*.estado.json" + N + "rascunho.txt" + N)
    g(banca, "add", "-A")
    g(banca, "commit", "-q", "-m", "chore: o gitignore aprende")
    r = ap.auditar(banca, isentos={"sujo.py": "prova"})
    diz("com o .gitignore em dia, nada sobra solto",
        not (r["soltos"] or r["soltos_sujos"]),
        str(r["soltos"] + [x[0] for x in r["soltos_sujos"]]))

    print(N + "== 4. ACUSA A SUPERFICIE 3: a MENSAGEM de commit ==")
    escreve(os.path.join(banca, "outro.py"), "print('ok')" + N)
    g(banca, "add", "-A")
    g(banca, "commit", "-q", "-m",
      "fix: conserta o que quebrou em " + CAMINHO_SUJO)
    r = ap.auditar(banca, isentos={"sujo.py": "prova"})
    diz("acusa a linha privada na MENSAGEM de commit",
        r["mensagens_sujas"] >= 1, str(r["mensagens_sujas"]))
    diz("e a mensagem suja tambem da veredito 1", ap.veredito(r) == 1)

    print(N + "== 5. MUTACAO — desarmar cada superficie tem de cegar o gate ==")

    # 5a. o detector para de achar qualquer coisa: e o verde que nao verifica.
    medir_orig = ap.mp.medir
    texto_orig = ap.mp.medir_texto
    try:
        ap.mp.medir = lambda c: dict(total=1, sujas=0, marcas={})
        ap.mp.medir_texto = lambda t: (1, set(), {})
        cego = ap.auditar(banca, isentos={"sujo.py": "prova"})
        det_a = ap.veredito(cego) == 0
    finally:
        ap.mp.medir = medir_orig
        ap.mp.medir_texto = texto_orig
    print("  [%s] detector mudo faz o gate aprovar o repositorio SUJO"
          % ("DETECTADA" if det_a else "SOBREVIVEU"))
    if not det_a:
        FALHA += 1

    # 5b. o gate deixa de perguntar o que esta solto, e o buraco volta.
    escreve(os.path.join(banca, ".gitignore"), "*.pyc" + N)
    # ⚠️ `add .gitignore`, nunca `add -A`: o `-A` commitaria o proprio arquivo
    # que precisa ficar SOLTO, e o controle abaixo mediria outra coisa. Errei
    # assim na primeira rodada, e o controle acusou.
    g(banca, "add", ".gitignore")
    g(banca, "commit", "-q", "-m", "chore: o gitignore esquece")
    escreve(os.path.join(banca, "volta.estado.json"), "{}" + N)
    git_orig = ap.git

    def git_sem_others(base, *args):
        if "--others" in args:
            return []
        return git_orig(base, *args)

    try:
        ap.git = git_sem_others
        cego = ap.auditar(banca, isentos={"sujo.py": "prova"})
        det_b = not (cego["soltos"] or cego["soltos_sujos"])
    finally:
        ap.git = git_orig
    print("  [%s] sem perguntar o que esta solto, o gate nao ve o `git add .`"
          % ("DETECTADA" if det_b else "SOBREVIVEU"))
    if not det_b:
        FALHA += 1

    print("  -- controle --")
    volta = ap.auditar(banca, isentos={"sujo.py": "prova"})
    diz("com tudo armado, o gate volta a acusar",
        ap.veredito(volta) != 0 and bool(volta["soltos"]))

    print(N + "== 6. NAO MEDIDO NAO E VERDE ==")
    fora = tempfile.mkdtemp(prefix="pub-fora-")
    try:
        r = ap.auditar(fora, isentos={})
        diz("pasta que nao e repositorio devolve None, nunca vazio",
            r is None, str(r))
        diz("e o codigo de saida e 3 (nao medido), nunca 0",
            ap.veredito(None) == 3)
    finally:
        shutil.rmtree(fora, ignore_errors=True)

    print(N + "== 7. A ISENCAO E POR NOME EXATO, NUNCA POR PREFIXO ==")
    # 🔴 Este e um defeito ja pago, virado prova: `EXEMPLO-` isentava o arquivo
    # que mais precisava ser conferido, e a lista crescia sozinha.
    escreve(os.path.join(banca, "EXEMPLO-nao-isento.py"),
            "SAIDA = %r" % CAMINHO_SUJO + N)
    g(banca, "add", "-A")
    g(banca, "commit", "-q", "-m", "test: o que parece isento")
    r = ap.auditar(banca, isentos={"EXEMPLO-outro.py": "prova"})
    diz("nome PARECIDO com o isento continua sendo medido",
        "EXEMPLO-nao-isento.py" in [x[0] for x in r["sujos"]],
        str([x[0] for x in r["sujos"]]))

    print(N + "== 8. O DADO DOS ISENTOS ==")
    vazio = os.path.join(banca, "isentos_vazio.json")
    escreve(vazio, '{"isentos": {}}' + N)
    diz("arquivo sem isentos da dicionario vazio",
        ap.carregar_isentos(vazio) == {})
    diz("arquivo AUSENTE cai para zero isentos (reprova mais, nao menos)",
        ap.carregar_isentos(os.path.join(banca, "nao_existe.json")) == {})
    bom = os.path.join(banca, "isentos_bom.json")
    escreve(bom, '{"_leia": ["x"], "isentos": {"LICENSE": "o titular"}}' + N)
    lidos = ap.carregar_isentos(bom)
    diz("le o isento com o motivo junto",
        lidos == {"LICENSE": "o titular"}, str(lidos))

    print(N + "== 9. O HOOK BARRA UM COMMIT DE VERDADE ==")
    # 🔑 Um hook que existe no disco nao e um hook que barra. A unica prova
    # que vale e a mesma de sempre nesta casa: quebrar o alvo e exigir que o
    # `git commit` FALHE. Sem isto, `.githooks/pre-commit` seria mais um
    # arquivo bonito que ninguem sabe se roda.
    # ⚠️ O HOOK MORA EM DOIS LUGARES, e procurar num so foi defeito medido
    # rodando com o `HOME` vazio. Nesta casa ele e `publicado/githooks-...`,
    # a forma que ainda vai ser renomeada; no repositorio publicado ele ja e
    # `.githooks/pre-commit`. Um teste que so conhece o primeiro reprova em
    # todo clone, e a mensagem faz parecer que o hook sumiu.
    ONDE_O_HOOK_MORA = [
        os.path.join(os.path.dirname(AQUI), ".githooks", "pre-commit"),
        os.path.join(AQUI, "publicado", "githooks-pre-commit"),
    ]
    hook_fonte = ([c for c in ONDE_O_HOOK_MORA if os.path.isfile(c)] or [""])[0]
    if not hook_fonte:
        diz("o hook existe num dos dois arranjos", False,
            str(ONDE_O_HOOK_MORA))
    else:
        casa = tempfile.mkdtemp(prefix="pub-hook-")
        try:
            g(casa, "init", "-q")
            g(casa, "config", "user.email", "prova" + chr(64) + "exemplo.invalid")
            g(casa, "config", "user.name", "Prova")
            # ⚠️ A BANCA ESPELHA O REPOSITORIO PUBLICADO, e as duas coisas
            # que isso exige foram erro meu na primeira rodada:
            #
            #   1. as pecas vem de `publicado/`, nunca daqui. As internas
            #      carregam a prosa da casa, e o gate as reprova — com razao,
            #      que e por isso que elas se destilam antes de sair.
            #   2. o `privacidade.json` NAO e versionado. Ele e a lista dos
            #      padroes do que e privado, e portanto contem a FORMA do que
            #      se procura. No repo real ele fica no `.gitignore` e nasce
            #      do `.exemplo` — o mesmo caminho que o CI faz.
            os.makedirs(os.path.join(casa, "maquina"))

            def de_onde(nome):
                """O arquivo no arranjo desta casa OU no do repositorio.

                Nesta casa a versao publicavel vive em `publicado/`; no
                repositorio ela JA e o arquivo de `maquina/`. Procurar so num
                dos dois quebra o teste no outro, e foi o que aconteceu.
                """
                em_pub = os.path.join(AQUI, "publicado", nome)
                return em_pub if os.path.isfile(em_pub) \
                    else os.path.join(AQUI, nome)

            for nome in ("antes_de_publicar.py", "medir_privacidade.py",
                         "inventario.py"):
                shutil.copy2(de_onde(nome),
                             os.path.join(casa, "maquina", nome))
            for nome in ("privacidade.json", "mapa.json"):
                shutil.copy2(de_onde(nome + ".exemplo"),
                             os.path.join(casa, "maquina", nome))
            escreve(os.path.join(casa, ".githooks", "pre-commit"),
                    io.open(hook_fonte, encoding="utf-8").read())
            os.chmod(os.path.join(casa, ".githooks", "pre-commit"), 0o755)
            g(casa, "config", "core.hooksPath", ".githooks")

            # 1o commit: limpo. Ele TEM de passar, senao o gate so diz `nao`.
            escreve(os.path.join(casa, ".gitignore"),
                    "*.pyc" + N + "__pycache__/" + N
                    + "maquina/privacidade.json" + N
                    + "maquina/mapa.json" + N)
            g(casa, "add", ".gitignore", ".githooks/pre-commit")
            g(casa, "add", "maquina")
            r1 = g(casa, "commit", "-q", "-m", "feat: o primeiro")
            diz("commit LIMPO passa pelo hook", r1.returncode == 0,
                r1.stderr.decode("utf-8", "replace")[-200:])

            # 2o commit: um arquivo com caminho de uma maquina dentro.
            escreve(os.path.join(casa, "vaza.py"),
                    "SAIDA = %r" % (CAMINHO_SUJO + chr(92) + "z.md") + N)
            g(casa, "add", "vaza.py")
            r2 = g(casa, "commit", "-q", "-m", "feat: o que nao pode subir")
            diz("commit SUJO e BARRADO pelo hook", r2.returncode != 0,
                "returncode=%d" % r2.returncode)

            # E a prova que separa barrar de reclamar: o commit nao existe.
            log = subprocess.run(("git", "log", "--oneline"), cwd=casa,
                                 capture_output=True)
            n_commits = len([x for x in log.stdout.decode(
                "utf-8", "replace").split(N) if x.strip()])
            diz("   e o commit NAO entrou na historia", n_commits == 1,
                "commits=%d" % n_commits)

            # ⚠️ O outro lado: `--no-verify` e a valvula documentada. Se ela
            # nao funcionar, o gate vira armadilha em vez de guarda.
            r3 = g(casa, "commit", "-q", "--no-verify", "-m",
                   "feat: com motivo declarado")
            diz("e `--no-verify` continua sendo a valvula",
                r3.returncode == 0,
                r3.stderr.decode("utf-8", "replace")[-200:])
        finally:
            shutil.rmtree(casa, ignore_errors=True)

    print(N + "== 10. O QUE NASCE DE RODAR NAO E CONTEUDO ==")
    diz("`.estado.json` e gerado", ap.e_gerado("porta.estado.json"))
    diz("`__pycache__/` e gerado", ap.e_gerado("portas/__pycache__/x.pyc"))
    diz("`.ruff_cache/` e gerado", ap.e_gerado(".ruff_cache/0.1/abc"))
    diz("e o codigo de verdade NAO e gerado",
        not ap.e_gerado("maquina/inventario.py"))
finally:
    shutil.rmtree(banca, ignore_errors=True)

print(N + "=== RESULTADO: %d PASS / %d FALHA ===" % (PASS, FALHA))
sys.exit(1 if FALHA else 0)
