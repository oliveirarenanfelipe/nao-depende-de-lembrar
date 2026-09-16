# -*- coding: utf-8 -*-
"""O BÁSICO DE ENGENHARIA, medido em TODOS os projetos da casa.

    python _shared/o_basico.py            # tabela, com a evidência ao lado
    python _shared/o_basico.py --json     # para máquina (o bloco do health)

POR QUE ESTA PEÇA EXISTE
------------------------
A pergunta que abriu isto: *"eu tenho certeza que existe um básico. nós temos
cuidado com esse básico em todos os projetos?"* É a mesma pergunta que abriu o
projeto inteiro, dita de outro jeito:

    "não mais ficar com essa desconfiança de se tá rodando ou não, se tá
     validando ou não (...) uma estrutura forte, robusta, que aplique em todos
     os projetos, rodando ou ainda a rodar"
    "às vezes faz e às vezes esquece, depende de eu lembrar de ficar pedindo"

O gate `padroes_na_porta` protege o que eu VOU escrever. Nada olhava o estado
do que JÁ existe. Esta peça olha — e olha todo dia, que é a diferença entre
resposta e medição avulsa: um inventário feito à mão mediu esta mesma casa,
não virou peça, e a pergunta ficou três dias sem resposta.

O CHECKLIST NÃO É INVENÇÃO MINHA
--------------------------------
Cada linha vem do `projeto.yml` (o contrato de fundação da casa, cobrado pelo
`fundacao_na_porta`) ou de algo que já virou gate. Acrescentar item aqui exige
o mesmo: a pergunta já tem de ser da casa.

🔴 A LIÇÃO QUE ESTA PEÇA CARREGA NO CORPO
-----------------------------------------
A 1ª versão disto respondeu que **o SaaS da casa não roda teste no CI**.
Falso: o `ci.yml` dele roda `pnpm exec turbo test` e ainda tem um job separado
de testes de servidor com banco. O detector conhecia `npm test`, `pytest` e
`jest`, e não conhecia `turbo test` — e respondeu "não" sobre o SaaS com
cliente real. Detector que não conhece a FORMA da casa mede a si mesmo, não a
casa. Dois consertos ficaram no corpo:

  1. `CMD_TESTE` é largo de propósito, e é lista de FORMAS, não de ferramentas.
  2. **Todo `ok` sai com a evidência ao lado** — o comando que foi encontrado.
     Número sem a evidência do lado foi o que quase virou alarme falso sobre o
     projeto com cliente real.

CHAMADOR: o verificador diário de saúde da casa.
PROVA:    `testar_o_basico.py`, com mutação.
"""
import io
import json
import os
import re
import sys

RAIZ = os.path.join(os.path.expanduser("~"), "Projeto")

PULAR = {"_shared", "_arquivo", "obra", "repos"}
PODA = ("node_modules", ".venv", "venv", "dist", "build", "__pycache__",
        ".next", "out", "site-packages", "repos", ".aiox-core")

# NAO e lista de ferramentas: e lista de FORMAS de rodar teste. Faltou uma e o
# numero saiu errado sobre o projeto com cliente real.
CMD_TESTE = re.compile(
    r"\b("
    r"turbo\s+(run\s+)?test|pnpm\s+(exec\s+\S+\s+)?test|npm\s+(run\s+)?test|"
    r"yarn\s+test|vitest|jest|playwright\s+test|cypress|"
    # `node --test` e o runner nativo do Node, e e o que o
    # `ligar_ci.py` EMITE para projeto sem script de teste. Sem esta
    # linha o medidor nao enxergava o CI que o proprio gerador da casa
    # tinha acabado de escrever.
    r"node\s+--test|node:test|"
    r"pytest|unittest|tox\b|nox\b|"
    r"python3?\s+-?m?\s*[^\n]*test[a-z_]*\.py|"
    r"bash\s+[^\n]*test[a-z_]*\.sh|"
    r"go\s+test|cargo\s+test|mvn\s+test|gradle\s+test"
    r")", re.I)

# Arquivo de teste e arquivo de CODIGO cujo NOME diz teste - as duas coisas.
# \U0001f534 A versao anterior pedia so o nome e casou `_pollen_test.jpg`, uma
# FOTO, colocando um projeto inteiro na fila de ataque por causa dela.
EXT_CODIGO = r"\.(py|js|ts|tsx|jsx|mjs|cjs|sh|ps1|rb|go|rs|java|php)$"
ARQ_TESTE = re.compile(
    r"(^|/)(test_[^/]*|testar_[^/]*|[^/]*_test|[^/]*\.test|[^/]*\.spec)"
    + EXT_CODIGO + r"|(^|/)tests?/[^/]*" + EXT_CODIGO, re.I)

ITENS = ["id", "git", "ign", "tst", "cit", "sec", "dec"]
ROTULO = {
    "id": "projeto.yml (identidade)",
    "git": "e repositorio git",
    "ign": ".gitignore",
    "tst": "tem teste escrito",
    "cit": "o CI RODA o teste",
    "sec": "varredura de segredo",
    "dec": "decisoes registradas",
}


def ler(caminho):
    try:
        with io.open(caminho, encoding="utf-8", errors="replace",
                     newline="") as fh:
            return fh.read()
    except Exception:                                       # noqa: BLE001
        return ""


def arquivos(base):
    """Anda o projeto pulando pasta de terceiro e WORKTREE.

    Worktree e o mesmo projeto num segundo lugar: contar de novo inflaria
    tudo, como ja aconteceu antes com outra peca desta maquina.
    """
    for dp, dns, fns in os.walk(base):
        dns[:] = [x for x in dns
                  if x not in PODA
                  and not (x.startswith(".") and x != ".github")
                  and not os.path.isfile(os.path.join(dp, x, ".git"))]
        for fn in fns:
            yield os.path.join(dp, fn)


def medir_projeto(base):
    todos = list(arquivos(base))
    rel = [a[len(base) + 1:].replace("\\", "/") for a in todos]

    wf = [a for a, r in zip(todos, rel)
          if r.startswith(".github/workflows/")
          and r.endswith((".yml", ".yaml"))]
    prova_ci = None
    for a in wf:
        m = CMD_TESTE.search(ler(a))
        if m:
            prova_ci = re.sub(r"\s+", " ", m.group(0)).strip()[:30]
            break

    v = {
        "id": os.path.isfile(os.path.join(base, "projeto.yml")),
        "git": os.path.isdir(os.path.join(base, ".git")),
        "ign": os.path.isfile(os.path.join(base, ".gitignore")),
        "tst": any(ARQ_TESTE.search(r) for r in rel),
        "cit": prova_ci is not None,
        "sec": (os.path.isfile(os.path.join(base, ".git", "hooks",
                                            "pre-commit"))
                or os.path.isfile(os.path.join(base, ".gitleaks.toml"))
                or any("gitleaks" in r.lower() for r in rel)),
        "dec": any(r in ("DECISIONS.md", "PROJETO.md", "REGRAS.md")
                   for r in rel),
    }
    v["_prova_ci"] = prova_ci or ""
    v["_workflows"] = len(wf)
    return v


# As contas da casa. Quem nao e de uma delas e repo de TERCEIRO: nao se
# conserta, e contar a divida dele envenena o numero que decide onde atacar -
# o mesmo raciocinio que ja tirou arquivo minificado e clone de estudo da conta.
# Medido: 5 repositorios de terceiro viviam dentro da arvore — clones de
# estudo e projetos capturados numa pasta de entrada — e entravam na conta
# como projeto nosso.
def carregar_contas(fonte=None):
    """As contas da casa vem de DADO, nao de constante no codigo.

    🔴 Saiu do codigo na terceira ocorrencia do mesmo defeito no
    mesmo dia: os nomes do medidor de privacidade, os caminhos do destilador e
    estas contas. Todos eram dado privado morando em constante, e todos so
    apareceram quando a peca foi destilada para publicacao — porque ate ali
    ninguem tinha motivo para olhar o codigo com essa pergunta.

    ⚠️ Lista vazia aqui seria pior que erro: TODO repositorio viraria "de
    terceiro", a casa inteira sumiria da conta, e o placar sairia lindo sobre
    zero projeto. Entao, sem o arquivo, a peca para.
    """
    caminho = fonte or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "privacidade.json")
    with io.open(caminho, encoding="utf-8") as fh:
        contas = json.load(fh).get("contas_da_casa") or []
    if not contas:
        raise ValueError(
            "privacidade.json sem `contas_da_casa`. Sem elas todo repo vira "
            "de terceiro e o placar mede zero projeto com cara de sucesso.")
    return tuple(contas)


NOSSOS = carregar_contas()


def dono_do_repo(base):
    """'nosso', 'terceiro' ou 'sem-remote' (nosso, ainda nao publicado)."""
    cfg = os.path.join(base, ".git", "config")
    texto = ler(cfg)
    m = re.search(r"\[remote \"origin\"\][^\[]*?url\s*=\s*(\S+)",
                  texto, re.S)
    if not m:
        return "sem-remote"
    url = m.group(1)
    return "nosso" if any(c in url for c in NOSSOS) else "terceiro"


def repositorios(raiz):
    """Todo diretorio com `.git` DIRETORIO e um projeto, mesmo aninhado.

    \U0001f534 A versao anterior varria so a pasta de 1o nivel e chamava de
    projeto. Uma pasta guarda-chuva nao e repositorio: as tres etapas
    dentro dela sao, cada uma com CI proprio. O pai aparecia como "sem CI"
    enquanto os filhos tinham, o teste do filho contava como do pai, e os
    projetos de verdade nunca eram medidos.

    `.git` como ARQUIVO e worktree: fica de fora, e o mesmo projeto num
    segundo lugar.
    """
    achados = []
    for dp, dns, _fns in os.walk(raiz):
        dns[:] = [x for x in dns
                  if x not in PODA and x not in PULAR
                  and not (x.startswith(".") and x != ".github")]
        if os.path.isdir(os.path.join(dp, ".git")):
            achados.append(dp)
            # NAO poda aqui: repositorio dentro de repositorio e
            # projeto proprio e precisa ser medido tambem.
    return sorted(achados)


def medir(raiz=None):
    raiz = raiz or RAIZ
    # 🔴 RAIZ QUE NAO EXISTE E ERRO DE CONFIGURACAO, e tem de dizer isso. Ate
    # aqui vinha um `FileNotFoundError` cru la de dentro, tres frames abaixo,
    # e quem o lesse nao saberia que o problema era a RAIZ e nao o projeto que
    # estava sendo medido. Achado ao rodar a maquina destilada fora da casa de
    # origem — la `~/Projeto` sempre existiu, e por isso o caminho nunca foi
    # exercitado.
    #
    # ⚠️ E levanta, nao devolve vazio: casa inexistente respondendo `0
    # projetos, nada quebrado` e o verde sobre o nada, que e o unico erro que
    # esta peca inteira existe para impedir.
    if not os.path.isdir(raiz):
        raise ValueError(
            "a raiz `%s` nao existe. Ela e onde seus projetos moram — ajuste "
            "`RAIZ` no topo desta peca, ou passe o caminho: "
            "`medir(\"/caminho/dos/projetos\")`. Devolver vazio aqui diria "
            "`nada quebrado` sobre nenhum projeto." % raiz)
    fora, dados = [], {}

    repos, terceiros = [], []
    for base in repositorios(raiz):
        (terceiros if dono_do_repo(base) == "terceiro" else repos).append(base)
    for base in repos:
        nome = base[len(raiz) + 1:].replace("\\", "/") or os.path.basename(base)
        dados[nome] = medir_projeto(base)
    for base in terceiros:
        fora.append(base[len(raiz) + 1:].replace("\\", "/") + " (de terceiro)")

    # pasta de 1o nivel que NAO e repo e nao contem repo: so registra que
    # existe, para o numero nao mentir por omissao.
    for nome in sorted(os.listdir(raiz)):
        base = os.path.join(raiz, nome)
        if not os.path.isdir(base) or nome in PULAR or nome.startswith("."):
            continue
        if not any(r == base or r.startswith(base + os.sep) for r in repos):
            fora.append(nome)
    return dados, fora


def resumo(dados):
    n = len(dados)
    placar = {k: sum(1 for v in dados.values() if v[k]) for k in ITENS}
    # o buraco que importa: teste escrito que NENHUM ci roda
    orfaos = sorted(p for p, v in dados.items() if v["tst"] and not v["cit"])
    return n, placar, orfaos


def main():
    dados, fora = medir()
    n, placar, orfaos = resumo(dados)

    if "--json" in sys.argv:
        print(json.dumps({"projetos": n, "placar": placar,
                          "teste_sem_ci": orfaos, "fora": fora},
                         ensure_ascii=False))
        return 0

    print("%-40s %-4s %-4s %-4s %-4s %-5s %-4s %-4s %s"
          % ("projeto", "id", "git", "ign", "tst", "ci-t", "sec", "dec",
             "o comando de teste encontrado"))
    print("-" * 112)
    for p in sorted(dados):
        v = dados[p]
        print("%-40s%s%s%s%s%s %s%s  %s"
              % (p[:40],
                 " ok " if v["id"] else " -- ",
                 " ok " if v["git"] else " -- ",
                 " ok " if v["ign"] else " -- ",
                 " ok " if v["tst"] else " -- ",
                 " ok " if v["cit"] else " -- ",
                 " ok " if v["sec"] else " -- ",
                 " ok " if v["dec"] else " -- ",
                 v["_prova_ci"]))
    print("-" * 112)
    print("%-40s%4d%5d%5d%5d%6d%5d%5d   de %d projetos"
          % ("TOTAL", placar["id"], placar["git"], placar["ign"],
             placar["tst"], placar["cit"], placar["sec"], placar["dec"], n))
    print()
    print("O BURACO: %d projeto(s) tem teste escrito que NENHUM CI roda."
          % len(orfaos))
    print("  %s" % ", ".join(orfaos))
    print()
    print("fora da conta (pasta, nao projeto): %s" % ", ".join(fora))
    print()
    for k in ITENS:
        print("  %-5s %s" % (k, ROTULO[k]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
