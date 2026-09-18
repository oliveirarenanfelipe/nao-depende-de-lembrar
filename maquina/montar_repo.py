# -*- coding: utf-8 -*-
"""MONTA o repositório publicável, e prova o ARRANJO — não só o conteúdo.

    python maquina/montar_repo.py --montar <pasta>
    python maquina/montar_repo.py --conferir <pasta>
    python maquina/montar_repo.py --fatos <pasta>

🔴 POR QUE ESTA PEÇA EXISTE
---------------------------
O `destilar.py --conferir` prova o CONTEÚDO de cada arquivo: nenhuma linha
privada, nada defasado. Nada provava o ARRANJO — quais arquivos sobem, com que
nome, em que pasta.

E arranjo errado não parece erro. Um arquivo esquecido não aparece como falha:
aparece como um repositório que monta, roda e passa nos testes, faltando uma
peça que ninguém procurou. Até aqui o arranjo morava num script escrito na hora
de montar e jogado fora depois, o que é a mesma coisa que não existir.

🔑 A IDEIA VEIO DE FORA, e a fonte importa: o `basic-engineering` tem um
`scripts/validate.js` que roda no CI e confere a estrutura do repositório —
manifesto apontando para script que não existe, versão divergindo entre
arquivos, arquivo gerado que ficou obsoleto. Nós tínhamos metade do conteúdo
e nenhuma da estrutura.

AS TRÊS PERGUNTAS QUE ELA FAZ
-----------------------------
1. **todo arquivo de `publicado/` tem destino declarado?** O que não tem não
   sobe por acidente: a montagem reprova dizendo o nome.
2. **todo destino declarado tem fonte?** Declarar o `.githooks/pre-commit` e
   não ter o arquivo produz um repositório com um gate que não existe.
3. **o painel de fatos do README ainda é verdade?** Ele carrega números
   medidos, e número escrito à mão envelhece calado. O do nosso README dizia
   *9 suítes* quando o repositório já tinha 15.

⚠️ A LISTA É FECHADA, NUNCA UMA VARREDURA. Varrer a pasta e publicar o que
aparecer significa que um rascunho largado ali sobe junto — e rascunho largado
numa pasta de saída é o caso comum, não o raro.

CÓDIGOS DE SAÍDA (a taxonomia da máquina)
    0  nada a acusar
    1  ACUSOU — arquivo sem destino, destino sem fonte, ou painel obsoleto
    2  não deu para USAR — falta o argumento da pasta
    3  não deu para MEDIR — sem `arranjo.json`. NÃO é um verde.

CHAMADOR: `.github/workflows/testes.yml` do repositório publicado, job
`o-que-sobe` — e a mão, ao montar antes de publicar.
PROVA:    `maquina/testar_montar_repo.py`, com mutação.
"""
import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001,S110 - sem stdout nao ha para onde avisar
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(AQUI, "publicado")
ARRANJO = os.path.join(AQUI, "arranjo.json")


def carregar_arranjo(fonte=None):
    """O arranjo, lido do disco. Sem o arquivo, ERRO — nunca dicionario vazio.

    ⚠️ Aqui a ausencia tem de gritar, e e o oposto do `publicar_isentos.json`.
    La a lista vazia reprova mais; aqui ela faria a montagem achar que NADA
    tem destino declarado — ou, pior, montar um repositorio vazio e responder
    que esta tudo certo.
    """
    caminho = fonte or ARRANJO
    with io.open(caminho, encoding="utf-8") as fh:
        d = json.load(fh)
    if not d.get("renomeados") and not d.get("na_raiz"):
        raise ValueError(
            "arranjo.json sem `renomeados` nem `na_raiz`. Sem eles a montagem "
            "produz um repositorio vazio e responde que esta tudo certo.")
    return d


def fica(nome, arr):
    """O arquivo foi DECLARADO como algo que nao sobe?

    ⚠️ Nao subir por decisao e nao subir por esquecimento sao a mesma coisa
    para quem le a pasta. So o que esta escrito aqui separa as duas.
    """
    return nome in (arr.get("ficam") or {})


def destino(nome, arr):
    """O caminho do arquivo DENTRO do repositorio. '' quando nao sobe."""
    if fica(nome, arr):
        return ""
    for rel, fonte in (arr.get("renomeados") or {}).items():
        if fonte == nome:
            return rel
    if nome in (arr.get("na_raiz") or []):
        return nome
    ps = arr.get("por_sufixo") or {}
    if not any(nome.endswith(s) for s in (ps.get("sufixos") or [])):
        return ""
    base = nome.replace("testar_", "")
    if nome.endswith(".py"):
        base = base[:-3]
    onde = "portas" if base in (ps.get("portas") or []) \
        else ps.get("padrao", "maquina")
    return "%s/%s" % (onde, nome)


def planejar(arr, saida=None):
    """[(destino, caminho_de_origem)] e os nomes SEM destino declarado."""
    pasta = saida or SAIDA
    plano, orfaos = [], []
    for nome in sorted(os.listdir(pasta)):
        caminho = os.path.join(pasta, nome)
        if os.path.isdir(caminho):
            if nome in (arr.get("pastas") or {}):
                sob = (arr["pastas"])[nome]
                for raiz, _d, arquivos in os.walk(caminho):
                    for f in sorted(arquivos):
                        completo = os.path.join(raiz, f)
                        rel = os.path.relpath(completo, caminho)
                        plano.append(("%s/%s" % (sob, rel.replace(os.sep, "/")),
                                      completo))
            elif not nome.startswith("_"):
                orfaos.append(nome + "/")
            continue
        if fica(nome, arr):
            continue
        alvo = destino(nome, arr)
        if alvo:
            plano.append((alvo, caminho))
        else:
            orfaos.append(nome)
    return plano, orfaos


def sem_fonte(arr, saida=None):
    """Destinos declarados cuja origem nao existe no disco."""
    pasta = saida or SAIDA
    faltam = []
    for rel, fonte in (arr.get("renomeados") or {}).items():
        if not os.path.isfile(os.path.join(pasta, fonte)):
            faltam.append("%s (esperava `%s`)" % (rel, fonte))
    for nome in (arr.get("na_raiz") or []):
        if not os.path.isfile(os.path.join(pasta, nome)):
            faltam.append(nome)
    return faltam


def montar(base, arr=None, saida=None):
    """Escreve o repositorio em `base`. Devolve (escritos, orfaos)."""
    arr = carregar_arranjo() if arr is None else arr
    plano, orfaos = planejar(arr, saida)
    if orfaos:
        return [], orfaos
    escritos = []
    for rel, origem in plano:
        alvo = os.path.join(base, rel.replace("/", os.sep))
        pai = os.path.dirname(alvo)
        if pai:
            os.makedirs(pai, exist_ok=True)
        shutil.copy2(origem, alvo)
        escritos.append(rel)
    return escritos, []


# -- O painel de fatos -------------------------------------------------------
# 🔑 *Um painel de fatos que ninguem re-roda vira um painel de fatos que
# mente.* A frase e do `basic-engineering`, e o nosso README ja era a prova
# dela: dizia `9 suites` com o repositorio em 15.
_PASS = re.compile(r"(\d+)\s+PASS")
_OK = re.compile(r"(\d+)\s+de\s+\1\s+passaram")


def medir_suites(base):
    """(suites, checagens, mutacoes, sobreviventes) rodando tudo de verdade.

    ⚠️ Conta pelo que as suites IMPRIMEM, porque elas nao compartilham um
    formato de saida. Tres formas convivem hoje, e inventar um formato unico
    agora sairia mais caro que ler as tres.
    """
    testes = sorted(glob.glob(os.path.join(base, "maquina", "testar_*.py")))
    testes += sorted(glob.glob(os.path.join(base, "portas", "testar_*.py")))
    suites = checagens = mutacoes = vivas = falharam = 0
    for t in testes:
        r = subprocess.run([sys.executable, "-B", t], cwd=base,
                           capture_output=True, timeout=900)
        texto = r.stdout.decode("utf-8", "replace")
        suites += 1
        falharam += 1 if r.returncode else 0
        achados = [int(m) for m in _PASS.findall(texto)]
        checagens += max(achados) if achados else len(_OK.findall(texto))
        mutacoes += texto.count("[DETECTADA]") + texto.count("[SOBREVIVEU]")
        vivas += texto.count("[SOBREVIVEU]")
    return suites, checagens, mutacoes, vivas, falharam


def medida_vale(numeros):
    """A medicao pode virar painel? Falso quando alguma suite reprovou.

    🔴 SEM ISTO O PAINEL MENTE DE OUTRO JEITO. Medindo uma pasta em que os
    dados ainda nao foram preparados, as suites falham e os numeros caem — e
    o painel escreve esse numero menor como se fosse o estado do projeto.
    Aconteceu aqui: `129 checagens, 7 sobreviventes` foi gravado por engano
    sobre `314 checagens, 0`.

    🔑 Painel so vale quando sai de uma rodada inteira verde. Numero de
    rodada quebrada nao e um numero pior: e outro assunto.
    """
    return len(numeros) > 4 and numeros[4] == 0


def linha_de_fatos(numeros):
    """A linha do painel, com os números que NÃO dependem do ambiente.

    🔴 A CONTAGEM DE CHECAGENS SAIU DAQUI, e o motivo é bom. Várias suítes
    pulam, de propósito, grupos que não se aplicam onde estão rodando: a prova
    cruzada do `projeto.yml` exige um gate que não viaja com a máquina; o
    grupo do arranjo exige a pasta que só existe na casa que monta; a
    comparação entre catálogos exige dois catálogos diferentes. Cada uma
    anuncia que pulou, e pular dizendo é o comportamento certo delas.

    O efeito é que o total de checagens varia com o ambiente — medido: 401
    nesta casa e 396 no runner do CI, sem nenhum defeito existir. Comparar
    isso por igualdade transforma um painel de fatos numa fonte de alarme
    falso, e alarme falso é o caminho mais curto para alguém desligar a
    checagem inteira.

    ⚠️ Suítes, mutações e sobreviventes NÃO variam assim, e por isso ficam:
    eles contam o que a máquina prova, não quanto do ambiente ela encontrou.
    """
    s, _c, m, v = numeros[:4]
    return ("Medido: %d suítes, %d mutações, %d sobrevivente%s."
            % (s, m, v, "" if v == 1 else "s"))


def painel_atual(base, arr):
    """A linha de fatos que esta ESCRITA no repositorio. '' quando nao ha."""
    cfg = arr.get("painel_de_fatos") or {}
    caminho = os.path.join(base, cfg.get("arquivo", "README.md"))
    prefixo = cfg.get("prefixo", "Medido: ")
    try:
        texto = io.open(caminho, encoding="utf-8").read()
    except OSError:
        return ""
    for linha in texto.split(chr(10)):
        if linha.strip().startswith(prefixo):
            return linha.strip()
    return ""


def escrever_painel(base, arr, nova):
    """Troca a linha de fatos no arquivo. True quando trocou."""
    cfg = arr.get("painel_de_fatos") or {}
    caminho = os.path.join(base, cfg.get("arquivo", "README.md"))
    prefixo = cfg.get("prefixo", "Medido: ")
    texto = io.open(caminho, encoding="utf-8").read()
    linhas = texto.split(chr(10))
    for i, linha in enumerate(linhas):
        if linha.strip().startswith(prefixo):
            linhas[i] = nova
            io.open(caminho, "w", encoding="utf-8",
                    newline=chr(10)).write(chr(10).join(linhas))
            return True
    return False


def main():
    argv = sys.argv[1:]
    modo = ([a for a in argv if a.startswith("--")] or [""])[0]
    alvo = [a for a in argv if not a.startswith("-")]
    if modo not in ("--montar", "--conferir", "--fatos") or not alvo:
        print("uso: montar_repo.py --montar|--conferir|--fatos <pasta>")
        return 2
    base = os.path.abspath(alvo[0])

    try:
        arr = carregar_arranjo()
    except Exception as e:                                  # noqa: BLE001
        print("  NAO MEDIDO: %s: %s" % (type(e).__name__, e))
        print("  Sem o arranjo nao ha o que conferir — e isto NAO e um verde.")
        return 3

    if modo == "--montar":
        escritos, orfaos = montar(base, arr)
        if orfaos:
            print("REPROVA — %d arquivo(s) em publicado/ sem destino "
                  "declarado:" % len(orfaos))
            for o in orfaos:
                print("    %s" % o)
            print()
            print("  Nada e montado enquanto houver um. Ou ele entra no")
            print("  `arranjo.json` com o destino, ou sai de `publicado/`.")
            return 1
        print("  %d arquivo(s) escritos em %s" % (len(escritos), base))
        return 0

    if modo == "--fatos":
        numeros = medir_suites(base)
        nova = linha_de_fatos(numeros)
        print("  %s" % nova)
        if not medida_vale(numeros):
            print()
            print("  NAO ESCRITO: %d suite(s) REPROVARAM nesta pasta."
                  % numeros[4])
            print("  Painel so vale saindo de uma rodada inteira verde —")
            print("  numero de rodada quebrada nao e um numero pior, e outro")
            print("  assunto. Prepare o dado (os `.exemplo`) e rode de novo.")
            return 1
        if "--escrever" in argv:
            # ⚠️ Escreve na FONTE (`publicado/`), nunca no repositorio montado.
            # O montado e descartavel: gravar nele daria um painel certo que
            # some na proxima montagem, e o README fonte continuaria mentindo.
            print("  escrito em publicado/: %s"
                  % escrever_painel(SAIDA, arr, nova))
        return 0

    # --conferir
    print("O ARRANJO DO REPOSITORIO - %s" % base)
    print()

    # ⚠️ AS DUAS PRIMEIRAS PERGUNTAS EXIGEM A PASTA DE ORIGEM, e ela existe só
    # na casa que monta. Rodando DENTRO do repositório publicado — que é onde
    # o CI roda — `publicado/` não existe, e isso não é defeito: é o arranjo
    # já resolvido. O que não pode acontecer é a ausência passar como verde
    # sem ninguém ler, então ela é dita com todas as letras.
    tem_origem = os.path.isdir(SAIDA)
    orfaos, faltam = [], []
    if tem_origem:
        _plano, orfaos = planejar(arr)
        faltam = sem_fonte(arr)
        print("== 1. todo arquivo de publicado/ tem destino ==")
        for o in orfaos:
            print("  SEM DESTINO  %s" % o)
        if not orfaos:
            print("  ok — nenhum arquivo sobe por acidente")

        print()
        print("== 2. todo destino declarado tem fonte ==")
        for f in faltam:
            print("  SEM FONTE    %s" % f)
        if not faltam:
            print("  ok — nenhum destino aponta para o vazio")
    else:
        print("== 1 e 2. NAO SE APLICAM AQUI ==")
        print("  Nao ha `publicado/` nesta pasta, entao este NAO e o lado que")
        print("  monta: e o repositorio ja montado. As duas perguntas sobre a")
        print("  origem sao feitas na casa, antes de publicar. Aqui sobra a 3.")

    print()
    print("== 3. o painel de fatos ainda e verdade ==")
    escrito = painel_atual(base, arr)
    numeros = medir_suites(base)
    medido = linha_de_fatos(numeros)
    igual = escrito == medido
    print("  escrito: %s" % (escrito or "(nenhuma linha de fatos no README)"))
    print("  medido : %s" % medido)
    if not medida_vale(numeros):
        print()
        print("  %d suite(s) REPROVARAM: o painel nao pode ser comparado com"
              % numeros[4])
        print("  uma rodada quebrada, e isto conta como reprovacao.")
        igual = False
    if not igual:
        print()
        print("  O painel diverge do que as suites respondem agora.")
        print("  Regenere com: montar_repo.py --fatos <pasta> --escrever")

    print()
    if orfaos or faltam or not igual:
        print("  REPROVA (1) — o arranjo nao confere.")
        return 1
    print("  LIMPO (0) — arranjo e painel conferidos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
