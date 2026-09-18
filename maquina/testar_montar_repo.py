# -*- coding: utf-8 -*-
"""Prova do `montar_repo.py` — o arranjo é provado, não conferido a olho.

    python -B maquina/testar_montar_repo.py

Esta peça decide o que sai da casa. Um defeito nela não quebra nada: produz um
repositório que monta, roda e passa nos testes, com uma peça faltando ou uma
peça a mais. Por isso a prova ataca as três perguntas que ela faz, e desarma
cada uma para exigir que a resposta mude.

A banca é uma pasta `publicado/` de mentira, montada aqui. A de verdade não é
tocada — e isso é provado no grupo 0, não prometido.

CHAMADOR: `maquina/mapa.json`, lido pelo `inventario.py` — que o
`~/.claude/hooks/mente_health.py`, bloco `[6u]`, roda todo dia.
"""
import io
import json
import os
import shutil
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001,S110 - sem stdout nao ha para onde avisar
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import montar_repo as mr  # noqa: E402

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
    pai = os.path.dirname(p)
    if pai:
        os.makedirs(pai, exist_ok=True)
    io.open(p, "w", encoding="utf-8", newline=N).write(t)


BANCA = tempfile.mkdtemp(prefix="arranjo-")
SAIDA_REAL = mr.SAIDA

print("== 0. SANDBOX (provado, nao prometido) ==")
diz("a banca fica fora da pasta publicado/ real",
    os.path.normcase(BANCA) != os.path.normcase(SAIDA_REAL))
ANTES_REAL = sorted(os.listdir(SAIDA_REAL)) if os.path.isdir(SAIDA_REAL) else []

# Uma `publicado/` de mentira, com um caso de cada forma do arranjo.
FALSA = os.path.join(BANCA, "publicado")
ARR = {
    "renomeados": {".gitignore": "gitignore-do-repo",
                   ".github/workflows/testes.yml": "ci-do-repo.yml"},
    "na_raiz": ["LICENSE", "README.md"],
    "pastas": {"github-templates": ".github"},
    "por_sufixo": {"sufixos": [".py", ".exemplo"],
                   "portas": ["porta_de_mentira", "casa.json.exemplo"],
                   "padrao": "maquina"},
    "ficam": {".gitignore-interno": "e o gitignore desta pasta"},
    "painel_de_fatos": {"arquivo": "README.md", "prefixo": "Medido: "},
}

try:
    escreve(os.path.join(FALSA, "gitignore-do-repo"), "*.pyc" + N)
    escreve(os.path.join(FALSA, "ci-do-repo.yml"), "name: testes" + N)
    escreve(os.path.join(FALSA, "LICENSE"), "MIT" + N)
    escreve(os.path.join(FALSA, "README.md"), "# titulo" + N)
    escreve(os.path.join(FALSA, "peca_de_mentira.py"), "print('ok')" + N)
    escreve(os.path.join(FALSA, "testar_peca_de_mentira.py"), "print('ok')" + N)
    escreve(os.path.join(FALSA, "porta_de_mentira.py"), "print('ok')" + N)
    escreve(os.path.join(FALSA, "testar_porta_de_mentira.py"), "print(1)" + N)
    escreve(os.path.join(FALSA, "casa.json.exemplo"), "{}" + N)
    escreve(os.path.join(FALSA, "mapa.json.exemplo"), "{}" + N)
    escreve(os.path.join(FALSA, ".gitignore-interno"), "_rascunho/" + N)
    escreve(os.path.join(FALSA, "github-templates",
                         "PULL_REQUEST_TEMPLATE.md"), "# pr" + N)
    escreve(os.path.join(FALSA, "github-templates", "ISSUE_TEMPLATE",
                         "1-defeito.yml"), "name: defeito" + N)
    # A pasta `_rascunho` comeca com `_`: e trabalho em curso, nao orfa.
    escreve(os.path.join(FALSA, "_rascunho", "meio_feito.py"), "x = 1" + N)

    print(N + "== 1. CADA FORMA DO ARRANJO LEVA AO LUGAR CERTO ==")
    esperado = {
        "gitignore-do-repo": ".gitignore",
        "ci-do-repo.yml": ".github/workflows/testes.yml",
        "LICENSE": "LICENSE",
        "peca_de_mentira.py": "maquina/peca_de_mentira.py",
        "testar_peca_de_mentira.py": "maquina/testar_peca_de_mentira.py",
        "porta_de_mentira.py": "portas/porta_de_mentira.py",
        "casa.json.exemplo": "portas/casa.json.exemplo",
        "mapa.json.exemplo": "maquina/mapa.json.exemplo",
    }
    for nome, onde in esperado.items():
        diz("`%s` vai para `%s`" % (nome, onde),
            mr.destino(nome, ARR) == onde, mr.destino(nome, ARR))

    # 🔑 O teste do TESTE: o `testar_` de uma PORTA tem de ir para `portas/`,
    # nao para `maquina/`. A regra tira o prefixo antes de decidir, e sem isso
    # a prova de uma porta publicada moraria longe da porta.
    diz("o teste de uma PORTA acompanha a porta",
        mr.destino("testar_porta_de_mentira.py", ARR)
        == "portas/testar_porta_de_mentira.py",
        mr.destino("testar_porta_de_mentira.py", ARR))

    diz("o que foi declarado como `fica` NAO sobe",
        mr.destino(".gitignore-interno", ARR) == "")

    print(N + "== 2. ACUSA O ARQUIVO SEM DESTINO ==")
    _plano, orfaos = mr.planejar(ARR, FALSA)
    diz("com tudo declarado, nao ha orfao", not orfaos, str(orfaos))

    escreve(os.path.join(FALSA, "largado.txt"), "rascunho" + N)
    _plano, orfaos = mr.planejar(ARR, FALSA)
    diz("acusa o arquivo largado na pasta de saida",
        "largado.txt" in orfaos, str(orfaos))

    # ⚠️ E NADA E MONTADO enquanto houver um. Montar o resto e deixar o orfao
    # para depois produz um repositorio que parece completo.
    destino_teste = os.path.join(BANCA, "repo1")
    escritos, orfaos = mr.montar(destino_teste, ARR, FALSA)
    diz("com um orfao, a montagem nao escreve NADA",
        not escritos and orfaos and not os.path.isdir(destino_teste),
        "escritos=%d" % len(escritos))
    os.remove(os.path.join(FALSA, "largado.txt"))

    # A pasta nova e igualmente orfa: uma subpasta inteira publicada por
    # engano e pior que um arquivo.
    escreve(os.path.join(FALSA, "pasta_nova", "x.md"), "oi" + N)
    _plano, orfaos = mr.planejar(ARR, FALSA)
    diz("acusa a PASTA sem destino declarado",
        "pasta_nova/" in orfaos, str(orfaos))
    shutil.rmtree(os.path.join(FALSA, "pasta_nova"))

    diz("e a pasta `_rascunho` NAO e orfa (trabalho em curso)",
        "_rascunho/" not in mr.planejar(ARR, FALSA)[1])

    print(N + "== 3. ACUSA O DESTINO SEM FONTE ==")
    diz("com tudo no disco, nenhum destino aponta para o vazio",
        not mr.sem_fonte(ARR, FALSA), str(mr.sem_fonte(ARR, FALSA)))

    ARR_FANTASMA = json.loads(json.dumps(ARR))
    ARR_FANTASMA["renomeados"][".githooks/pre-commit"] = "githooks-pre-commit"
    faltam = mr.sem_fonte(ARR_FANTASMA, FALSA)
    diz("acusa o destino declarado que nao tem arquivo",
        any("pre-commit" in f for f in faltam), str(faltam))

    ARR_FANTASMA2 = json.loads(json.dumps(ARR))
    ARR_FANTASMA2["na_raiz"].append("SECURITY.md")
    diz("acusa tambem o que foi declarado na raiz e nao existe",
        "SECURITY.md" in mr.sem_fonte(ARR_FANTASMA2, FALSA))

    print(N + "== 4. A MONTAGEM ESCREVE O QUE PLANEJOU ==")
    destino2 = os.path.join(BANCA, "repo2")
    escritos, orfaos = mr.montar(destino2, ARR, FALSA)
    diz("monta sem orfao", not orfaos, str(orfaos))
    no_disco = set()
    for raiz, _d, arquivos in os.walk(destino2):
        for f in arquivos:
            rel = os.path.relpath(os.path.join(raiz, f), destino2)
            no_disco.add(rel.replace(os.sep, "/"))
    diz("o que foi planejado e o que esta no disco, sem sobra nem falta",
        no_disco == set(escritos),
        "so no disco: %s | so no plano: %s"
        % (sorted(no_disco - set(escritos)), sorted(set(escritos) - no_disco)))
    diz("a arvore da pasta de templates vai inteira",
        ".github/ISSUE_TEMPLATE/1-defeito.yml" in no_disco,
        str(sorted(no_disco)))
    diz("e o `_rascunho` NAO e montado",
        not [x for x in no_disco if "meio_feito" in x], str(sorted(no_disco)))

    print(N + "== 5. O PAINEL DE FATOS ==")
    escreve(os.path.join(destino2, "README.md"),
            "# titulo" + N + N + "Medido: 1 suítes, 2 checagens, 3 mutações, "
            "0 sobreviventes." + N)
    diz("le a linha de fatos escrita",
        mr.painel_atual(destino2, ARR).startswith("Medido: 1 suítes"),
        mr.painel_atual(destino2, ARR))
    diz("monta a linha a partir dos numeros",
        mr.linha_de_fatos((15, 296, 40, 0))
        == "Medido: 15 suítes, 296 checagens, 40 mutações, 0 sobreviventes.",
        mr.linha_de_fatos((15, 296, 40, 0)))
    diz("e o singular de 1 sobrevivente e respeitado",
        mr.linha_de_fatos((1, 1, 1, 1)).endswith("1 sobrevivente."),
        mr.linha_de_fatos((1, 1, 1, 1)))
    diz("troca a linha no arquivo",
        mr.escrever_painel(destino2, ARR, "Medido: 9 suítes, 9 checagens, "
                           "9 mutações, 0 sobreviventes.")
        and mr.painel_atual(destino2, ARR).startswith("Medido: 9 suítes"))
    diz("README sem linha de fatos devolve vazio, e nao inventa",
        mr.painel_atual(BANCA, ARR) == "")

    # 🔴 A MEDICAO RODA AS SUITES DE VERDADE. Um painel que conta lendo o
    # codigo em vez de executa-lo conta o que foi ESCRITO, nunca o que passa.
    print(N + "== 6. A MEDICAO EXECUTA, NAO LE ==")
    falso = os.path.join(BANCA, "falso")
    escreve(os.path.join(falso, "maquina", "testar_um.py"),
            "print('  PASS  a')" + N + "print('=== RESULTADO: 7 PASS ===')" + N
            + "print('  [DETECTADA] x')" + N + "print('  [SOBREVIVEU] y')" + N)
    escreve(os.path.join(falso, "portas", "testar_dois.py"),
            "print('3 de 3 passaram.')" + N)
    medido = mr.medir_suites(falso)
    diz("conta as duas suites", medido[0] == 2, str(medido))
    diz("conta as checagens pelo MAIOR `N PASS` de cada uma",
        medido[1] == 7 + 1, str(medido))
    diz("conta as mutacoes, detectadas e sobreviventes",
        medido[2] == 2, str(medido))
    diz("e conta separado a que SOBREVIVEU", medido[3] == 1, str(medido))
    # 🔴 E CONTA QUANTAS SUITES REPROVARAM, que e o que impede o painel de
    # mentir de outro jeito: medindo uma pasta sem o dado preparado, os
    # numeros CAEM e o painel gravaria esse numero menor como se fosse o
    # estado do projeto. Aconteceu — 129 checagens e 7 sobreviventes foram
    # escritos por engano sobre 314 e 0.
    diz("conta as suites que REPROVARAM", medido[4] == 0, str(medido))
    mr.escreve_falso = True
    _quebrado = os.path.join(BANCA, "quebrado")
    escreve(os.path.join(_quebrado, "maquina", "testar_ruim.py"),
            "import sys" + N + "print('  PASS  a')" + N + "sys.exit(1)" + N)
    _n = mr.medir_suites(_quebrado)
    diz("acusa a suite que reprovou", _n[4] == 1, str(_n))
    diz("e a medida NAO vale para virar painel", not mr.medida_vale(_n))
    diz("   enquanto a medida de uma rodada verde vale",
        mr.medida_vale(medido))

    print(N + "== 7. MUTACAO — desarmar cada pergunta cega a peca ==")

    # 7a. o detector de orfao para de olhar: o arquivo largado sobe junto.
    escreve(os.path.join(FALSA, "largado2.txt"), "x" + N)
    destino_orig = mr.destino
    try:
        mr.destino = lambda nome, arr: "maquina/" + nome
        _p, orfaos_cegos = mr.planejar(ARR, FALSA)
        det_a = not orfaos_cegos
    finally:
        mr.destino = destino_orig
    print("  [%s] com todo nome virando destino, o largado deixa de ser orfao"
          % ("DETECTADA" if det_a else "SOBREVIVEU"))
    if not det_a:
        FALHA += 1
    os.remove(os.path.join(FALSA, "largado2.txt"))

    # 7b. a checagem de fonte para de olhar o disco.
    isfile_orig = mr.os.path.isfile
    try:
        mr.os.path.isfile = lambda p: True
        det_b = not mr.sem_fonte(ARR_FANTASMA, FALSA)
    finally:
        mr.os.path.isfile = isfile_orig
    print("  [%s] sem olhar o disco, o destino fantasma passa a ter fonte"
          % ("DETECTADA" if det_b else "SOBREVIVEU"))
    if not det_b:
        FALHA += 1

    # 7c. a medicao para de executar: o painel vira sempre zero, e um README
    # que diz zero passaria a ser "verdade".
    medir_orig = mr.medir_suites
    try:
        mr.medir_suites = lambda base: (0, 0, 0, 0)
        det_c = mr.linha_de_fatos(mr.medir_suites(falso)).startswith(
            "Medido: 0 suítes")
    finally:
        mr.medir_suites = medir_orig
    print("  [%s] medicao muda faz o painel dizer zero sobre tudo"
          % ("DETECTADA" if det_c else "SOBREVIVEU"))
    if not det_c:
        FALHA += 1

    print("  -- controle --")
    diz("com tudo armado, a peca volta a acusar",
        not mr.planejar(ARR, FALSA)[1]
        and bool(mr.sem_fonte(ARR_FANTASMA, FALSA))
        and mr.medir_suites(falso)[0] == 2)

    print(N + "== 8. O ARRANJO E DADO, e some-lo e ERRO ==")
    try:
        mr.carregar_arranjo(os.path.join(BANCA, "nao_existe.json"))
        levantou = False
    except Exception:                                       # noqa: BLE001
        levantou = True
    diz("SEM o arranjo, levanta erro em vez de dicionario vazio", levantou)

    vazio = os.path.join(BANCA, "arranjo_vazio.json")
    escreve(vazio, '{"na_raiz": [], "renomeados": {}}' + N)
    try:
        mr.carregar_arranjo(vazio)
        levantou2 = False
    except ValueError:
        levantou2 = True
    except Exception:                                       # noqa: BLE001
        levantou2 = False
    diz("arranjo sem destino nenhum levanta ValueError", levantou2)

    bom = os.path.join(BANCA, "arranjo_bom.json")
    escreve(bom, '{"na_raiz": ["LICENSE"], "renomeados": {}}' + N)
    diz("arranjo valido volta como dicionario",
        mr.carregar_arranjo(bom).get("na_raiz") == ["LICENSE"])

    print(N + "== 9. O ARRANJO REAL, quando ha um lado que MONTA ==")
    # 🔑 Os grupos acima medem a MECANICA contra uma banca. Este mede o dado
    # de verdade: se o `arranjo.json` desta casa tiver um arquivo sem destino,
    # a proxima montagem sai faltando uma peca e nada mais avisa.
    #
    # ⚠️ E ELE SO SE APLICA DE UM LADO. Rodando dentro do repositorio ja
    # publicado nao existe `publicado/`, e isso nao e defeito: e o arranjo ja
    # resolvido. Assumir que a pasta existe foi erro meu, pego rodando com o
    # `HOME` vazio — a mesma classe de defeito que peca viajante repete, a de
    # conhecer um endereco so.
    if os.path.isdir(SAIDA_REAL):
        real = mr.carregar_arranjo()
        _p, orfaos_reais = mr.planejar(real)
        diz("nenhum arquivo de publicado/ sem destino declarado",
            not orfaos_reais, str(orfaos_reais))
        diz("nenhum destino declarado sem fonte no disco",
            not mr.sem_fonte(real), str(mr.sem_fonte(real)))
    else:
        print("  (pulado: nao ha `publicado/` aqui, entao este nao e o lado")
        print("   que monta. As duas perguntas sao feitas na casa de origem.)")
finally:
    shutil.rmtree(BANCA, ignore_errors=True)

print(N + "== prova final: a pasta publicado/ real continua intocada ==")
diz("nada foi criado nem apagado em publicado/",
    (sorted(os.listdir(SAIDA_REAL)) == ANTES_REAL)
    if os.path.isdir(SAIDA_REAL) else ANTES_REAL == [])

print(N + "=== RESULTADO: %d PASS / %d FALHA ===" % (PASS, FALHA))
sys.exit(1 if FALHA else 0)
