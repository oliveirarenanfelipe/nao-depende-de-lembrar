# -*- coding: utf-8 -*-
"""O GATE DO `push` — mede a lista do GIT, não a lista do gate.

    python maquina/antes_de_publicar.py <pasta-do-repositorio>

🔴 POR QUE ESTA PEÇA EXISTE
---------------------------
Um gate de publicação responde **"o que eu olhei está limpo?"**. Quem dá o
`push` precisa de **"o que vai sair está limpo?"**. Parecem a mesma pergunta e
não são — a diferença entre elas é exatamente o tamanho da lista de isenções,
e isenção é a coisa que ninguém relê.

Ja aconteceu: o `destilar.py --conferir` respondeu `24 de 24 LIMPO`, e a
varredura sobre `git ls-files` achou **4 linhas privadas** num arquivo isento
por prefixo, com nome de projeto real dentro.

Aconteceu de novo, e por isso isto virou peça em vez de conserto: o
`.gitignore` do repositório candidato não cobria três arquivos que os próprios
testes geram ao rodar. Dois deles guardam caminho absoluto com o nome do dono
do disco. Nenhum estava commitado — estavam **a um `git add .` de distância**,
que é a mesma coisa com um dia a menos.

🔑 O CONSERTO NÃO PODIA SER O `.gitignore`. Acrescentar três linhas na mão é o
conserto pontual: resolve estes três e não sabe nada do quarto, que nasce no
próximo teste que escrever estado. O que fecha o buraco é uma pergunta feita
TODA VEZ, sobre a lista real.

AS TRÊS SUPERFÍCIES, e o `--conferir` não olha nenhuma
------------------------------------------------------
1. **o que está versionado** — `git ls-files`
2. **o que espera um `git add .`** — arquivo não rastreado e não ignorado
3. **o que a história guarda** — as mensagens de commit

SOBRE ISENÇÃO
-------------
Isento se declara **por nome, com o motivo numa linha**, em
`publicar_isentos.json`. Isenção por prefixo cresce sozinha: basta batizar o
próximo arquivo igual, e ninguém precisa decidir isentar nada.

⚠️ Sem o arquivo de isentos esta peça NÃO levanta erro — cai para zero isentos,
que reprova mais, nunca menos. É o oposto do `mapa.json`, onde a lista vazia
aprovava tudo em silêncio. A regra não é "falhar alto sempre": é que o dado
que some tem de puxar para o lado do NÃO.

CÓDIGOS DE SAÍDA — a taxonomia da máquina, não a desta peça
------------------------------------------------------------
    0  nada a acusar
    1  ACUSOU — mediu, e o alvo reprovou
    2  não deu para USAR — argumento faltando, pasta que não existe
    3  não deu para MEDIR — a fonte não respondeu. NÃO é um verde.

⚠️ O `2` aqui já significou *"achou arquivo solto"*, e isso era uma divergência
silenciosa: nas outras peças da máquina o `2` sempre foi *"uso errado"*. Duas
peças dizendo coisas diferentes com o mesmo número é pior que não ter número —
quem lê o código de saída num script decide errado, e nada acusa. O guardião
dessa lista é o `inventario.codigos_de_saida()`, que reprova qualquer peça
usando um código fora dela.

CHAMADOR: `.github/workflows/testes.yml` do repositório publicado, job
`o-que-sobe` — e a mão, antes de todo `push`.
PROVA:    `maquina/testar_antes_de_publicar.py`, com mutação.
"""
import io
import json
import os
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001,S110 - sem stdout nao ha para onde avisar
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import medir_privacidade as mp  # noqa: E402

ISENTOS = os.path.join(AQUI, "publicar_isentos.json")

# Arquivo que NASCE de rodar o codigo, e por isso nunca e conteudo. Cada forma
# aqui e um caso medido no repositorio candidato, nao uma suspeita.
GERADOS = (".estado.json", ".log", ".pyc", ".coverage")
PASTAS_GERADAS = ("__pycache__", ".ruff_cache", ".pytest_cache", ".venv")


def carregar_isentos(fonte=None):
    """{nome: motivo}. Sem o arquivo, ZERO isentos — que reprova mais."""
    caminho = fonte or ISENTOS
    try:
        with io.open(caminho, encoding="utf-8") as fh:
            dados = json.load(fh)
    except Exception:                                       # noqa: BLE001
        return {}
    return {k: v for k, v in (dados.get("isentos") or {}).items()
            if not k.startswith("_")}


def git(base, *args):
    """A saida do git em linhas. None quando o comando nao roda."""
    try:
        r = subprocess.run(("git",) + args, cwd=base, capture_output=True,
                           timeout=120)
    except Exception:                                       # noqa: BLE001
        return None
    if r.returncode != 0:
        return None
    t = r.stdout.decode("utf-8", "replace")
    return [l_ for l_ in t.split(chr(10)) if l_.strip()]


def e_gerado(rel):
    """O arquivo nasce de rodar o codigo?"""
    partes = rel.replace("\\", "/").split("/")
    if any(p in PASTAS_GERADAS for p in partes):
        return True
    return any(rel.endswith(s) for s in GERADOS)


def medir_arquivo(base, rel):
    """(linhas_sujas, {marca: n}) do arquivo. (0, {}) quando ilegivel."""
    caminho = os.path.join(base, rel.replace("/", os.sep))
    m = mp.medir(caminho)
    if not m:
        return 0, {}
    return m["sujas"], {k: v for k, v in m["marcas"].items() if v}


def auditar(base, isentos=None):
    """O veredito sobre o que o git vai mesmo empurrar.

    Devolve um dicionario com as tres superficies medidas, para que quem
    imprime e quem prova leiam do MESMO lugar. None quando nao deu para medir
    — e `None` nao e um verde: quem chama tem de tratar.
    """
    isentos = carregar_isentos() if isentos is None else isentos
    versionados = git(base, "ls-files")
    if versionados is None:
        return None
    esperando = git(base, "ls-files", "--others", "--exclude-standard") or []
    mensagens = git(base, "log", "--format=%B", "-n", "200") or []

    sujos = []
    for rel in versionados:
        if rel in isentos:
            continue
        n, marcas = medir_arquivo(base, rel)
        if n:
            sujos.append((rel, n, marcas))

    # ⚠️ O que espera um `git add .` e medido do mesmo jeito, mas contado
    # separado: arquivo gerado nao e "sujo", e um buraco no .gitignore.
    soltos, soltos_sujos = [], []
    for rel in esperando:
        if rel in isentos:
            continue
        if e_gerado(rel):
            soltos.append(rel)
            continue
        n, marcas = medir_arquivo(base, rel)
        if n:
            soltos_sujos.append((rel, n, marcas))
        else:
            soltos.append(rel)

    _, sujas_msg, marcas_msg = mp.medir_texto(chr(10).join(mensagens))

    return dict(versionados=len(versionados), sujos=sujos,
                soltos=soltos, soltos_sujos=soltos_sujos,
                mensagens=len(mensagens), mensagens_sujas=len(sujas_msg),
                mensagens_marcas={k: v for k, v in marcas_msg.items() if v},
                isentos=isentos)


def veredito(r):
    """O codigo de saida a partir do que foi medido. Sem imprimir nada.

    As duas reprovacoes dao o MESMO `1`, e de proposito: as duas sao a peca
    tendo medido e acusado. O que distingue uma da outra e o texto impresso,
    que e onde a distincao serve para alguma coisa. Numero de saida diferente
    por motivo diferente e o caminho para `2` significar uma coisa aqui e
    outra na peca ao lado.
    """
    if r is None:
        return 3
    if r["sujos"] or r["mensagens_sujas"]:
        return 1
    if r["soltos_sujos"] or r["soltos"]:
        return 1
    return 0


def _quais(marcas):
    return ", ".join("%s:%d" % (k.split("/")[0], v) for k, v in marcas.items())


def main():
    alvo = [a for a in sys.argv[1:] if not a.startswith("-")]
    base = os.path.abspath(alvo[0]) if alvo else os.getcwd()

    print("O QUE VAI SUBIR - %s" % base)
    print()
    r = auditar(base)
    if r is None:
        print("  NAO MEDIDO: `%s` nao respondeu como repositorio git." % base)
        print("  Gate que nao mede nao aprova — e isto NAO e um verde.")
        return 3

    print("  versionados .............. %d arquivo(s)" % r["versionados"])
    print("  isentos declarados ....... %d %s"
          % (len(r["isentos"]), sorted(r["isentos"]) or ""))
    print()

    print("== 1. o que esta versionado ==")
    for rel, n, marcas in r["sujos"]:
        print("  SUJO   %-44s %3d linha(s)  %s"
              % (rel[:44], n, _quais(marcas)))
    if not r["sujos"]:
        print("  limpo — nenhuma linha privada no que ja esta versionado")

    print()
    print("== 2. o que espera um `git add .` ==")
    for rel, n, marcas in r["soltos_sujos"]:
        print("  SUJO   %-44s %3d linha(s)  %s"
              % (rel[:44], n, _quais(marcas)))
    for rel in r["soltos"]:
        print("  SOLTO  %-44s %s"
              % (rel[:44], "(gerado ao rodar)" if e_gerado(rel) else ""))
    if not (r["soltos"] or r["soltos_sujos"]):
        print("  limpo — nada solto fora do .gitignore")
    else:
        print()
        print("  Cada um destes entra no repositorio com um `git add .`.")
        print("  Ou vai para o .gitignore, ou e isento com o motivo escrito.")

    print()
    print("== 3. as mensagens de commit ==")
    print("  %d mensagem(ns), %d linha(s) privada(s) %s"
          % (r["mensagens"], r["mensagens_sujas"],
             _quais(r["mensagens_marcas"]) if r["mensagens_marcas"] else ""))
    print()

    codigo = veredito(r)
    if codigo == 1:
        # O numero e o mesmo; a razao vai no texto, que e onde ela serve.
        if r["sujos"] or r["mensagens_sujas"]:
            print("  REPROVA (1) — ha conteudo privado no que sobe.")
        else:
            print("  REPROVA (1) — ha arquivo a um `git add .` de distancia.")
    else:
        print("  LIMPO (0) — as tres superficies medidas, nada a acusar.")
    return codigo


if __name__ == "__main__":
    sys.exit(main())
