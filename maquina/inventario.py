# -*- coding: utf-8 -*-
"""O MAPA DA MÁQUINA — gerado e verificado, nunca escrito à mão.

    python maquina/inventario.py            # a tabela
    python maquina/inventario.py --json     # para o bloco do mente_health
    python maquina/inventario.py --rapido   # sem rodar os testes

POR QUE ESTA PEÇA EXISTE
------------------------
Uma pergunta simples — *"esse projeto está salvo em qual pasta?"* — e a
medição respondeu o pior possível: a pasta tinha **6 documentos e ZERO
código**. A máquina existia, funcionava, e **não tinha endereço**. Sem um
lugar onde ela mora, toda sessão vira "vou onde tem defeito" — e defeito tem
nos projetos antigos. A deriva não era só falta de disciplina: o trabalho não
tinha para onde ir.

🔴 POR QUE GERADO, E NÃO UM README
----------------------------------
Um README de inventário **apodrece na primeira peça nova** e ninguém percebe,
porque documento errado se parece com documento certo. Este mapa pergunta ao
DISCO, e para cada peça responde três coisas que só a execução sabe:

    existe?  ·  tem quem a chame?  ·  o teste dela PASSA agora?

A terceira é a que separa mapa de enfeite. Peça que existe, tem chamador e
cujo teste reprova não está "no ar" — está quebrada, e o mapa diz isso.

⚠️ O QUE ELE NÃO SABE, dito na frente: ele lista o que está NESTA lista. Peça
nova que ninguém acrescentar aqui fica invisível — por isso o `[6u]` cobra o
NÚMERO de peças, não só o verde.

CHAMADOR: o verificador diário de saúde da casa.
PROVA:    `maquina/testar_inventario.py`, com mutação.
"""
import io
import json
import os
import re
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001,S110 - sem stdout nao ha para onde avisar
    pass

CASA = os.path.expanduser("~")
HOOKS = os.path.join(CASA, ".claude", "hooks")
FUND = os.path.dirname(os.path.abspath(__file__))
SHARED = os.path.join(CASA, "Projeto", "_shared")

# 🔴 O MAPA SAIU DO CODIGO, e foi a publicação que revelou
# por quê. Esta lista foi copiada para o repositório candidato dentro do
# `inventario.py`, e lá ele respondeu **`sem arquivo no disco: 0`** — porque
# continuava lendo os hooks DESTA casa, num diretório temporário que nada
# tinha a ver com ele. Na máquina de outra pessoa o mesmo código acusaria 11
# peças sumidas que nunca existiram, e ainda imprimiria o caminho da casa
# alheia. Era o inventário particular de alguém publicado como se fosse
# código — e código publicado que responde bonito sobre o nada é pior que
# código não publicado, porque ninguém desconfia de uma peça que roda.
#
# É o mesmo conserto de `privacidade.json` e da lista de contas, pela quinta
# vez seguida: **o que identifica a casa é DADO, nunca constante de
# código** (catálogo > hardcode).
#
# ⚠️ Sem o arquivo isto NÃO cai para lista vazia. Mapa vazio responde
# "nenhuma peça quebrada" sobre nenhuma peça, que é o verde que não verifica
# nada — o modo de falha que esta máquina inteira existe para impedir.
FONTE = os.path.join(FUND, "mapa.json")

# Os três lugares que a máquina conhece. O mapa cita o rótulo; quem resolve
# para caminho é o código, que é o único que sabe onde ele mesmo está.
LUGARES = {"HOOKS": HOOKS, "FUND": FUND, "SHARED": SHARED}


def carregar_mapa(fonte=None):
    """As peças, lidas do disco. Sem o arquivo, ERRO — nunca lista vazia."""
    caminho = fonte or FONTE
    with io.open(caminho, encoding="utf-8") as fh:
        dados = json.load(fh)
    pecas = []
    for p in (dados.get("pecas") or []):
        onde = p.get("onde", "")
        if onde not in LUGARES:
            raise ValueError(
                "mapa.json: a peca `%s` diz morar em `%s`, que nao e um dos "
                "lugares conhecidos (%s). Lugar errado faz a peca ser "
                "procurada onde ela nao esta, e o mapa acusa uma falta que "
                "nao existe." % (p.get("nome", "?"), onde,
                                 ", ".join(sorted(LUGARES))))
        pecas.append((p["camada"], p["nome"], LUGARES[onde],
                      p.get("teste", ""), p["chamador"]))
    if not pecas:
        raise ValueError(
            "mapa.json sem `pecas`. Sem elas o inventario responde `nenhuma "
            "peca quebrada` sobre NENHUMA peca — verde que nao verifica nada, "
            "que e exatamente o que esta peca existe para impedir.")
    return pecas


# (camada, nome, pasta, teste, chamador)
# O chamador e o arquivo que a INVOCA - sem ele a peca e orfa, que e defeito
# e nao pendencia: peca sem quem a chame e defeito, nao item de lista.
PECAS = carregar_mapa()


def caminho(pasta, nome):
    p = os.path.join(pasta, nome)
    return p if os.path.isfile(p) else p + ".py"


def roda(p):
    try:
        r = subprocess.run([sys.executable, "-B", p], capture_output=True,
                           timeout=600, cwd=os.path.dirname(p))
        return r.returncode == 0
    except Exception:                                       # noqa: BLE001
        return None


def levantar(rodar_testes=True):
    linhas = []
    for cat, nome, pasta, teste, chamador in PECAS:
        arq = caminho(pasta, nome)
        existe = os.path.isfile(arq)
        t_arq = os.path.join(pasta, teste) if teste else ""
        t_existe = bool(teste) and os.path.isfile(t_arq)
        passa = roda(t_arq) if (rodar_testes and t_existe) else None
        linhas.append(dict(cat=cat, nome=nome, onde=pasta, existe=existe,
                           teste=teste, teste_existe=t_existe, passa=passa,
                           chamador=chamador))
    return linhas


def curto(p):
    return p.replace(CASA, "~").replace("\\", "/")


# Caminho de escrita que so existe NESTA casa. Cada padrao e um caso medido,
# nao uma suspeita.
PRESOS = [
    # o log de auditoria apontando para a pasta do agente: a peca escreve
    # onde ELA mora, nunca num endereco decorado.
    re.compile(r'expanduser\("~"\)[^)]{0,40}"\.claude"[^)]{0,60}'
               r'(log|estado|cache)', re.I),
    # qualquer caminho absoluto de uma maquina especifica
    re.compile(r'["\'][A-Za-z]:[\\/]{1,2}Users[\\/]'),
]


def caminho_preso(dados):
    """Pecas que ESCREVEM num caminho so desta casa. [] quando nenhuma.

    🔴 POR QUE ESTA CHECAGEM EXISTE, e o preco foi pago no mesmo dia. O
    `gates.log` estava escrito com caminho fixo em TRES portas. Eu consertei
    UMA de manha, e as outras duas seguiram apontando para uma pasta que so
    existe aqui — com o erro de escrita engolido por um `except: pass`.

    🔑 Consertar uma de tres e pior que nao consertar nenhuma: o resultado
    parece resolvido, e nada acusa as que sobraram. Entao o conserto nao podia
    ser a mao — tinha de virar pergunta que o mapa faz TODO DIA, senao a
    proxima peca nasce com o mesmo endereco decorado.

    ⚠️ So olha ESCRITA (log, estado, cache) e caminho absoluto. Ler de
    `~/.claude` e legitimo: e onde o agente mora, e varias pecas precisam
    disso.
    """
    presas = []
    for d in dados:
        arq = caminho(d["onde"], d["nome"])
        if not os.path.isfile(arq):
            continue
        try:
            texto = io.open(arq, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        if any(rx.search(texto) for rx in PRESOS):
            presas.append(d["nome"])
    return presas


# A TAXONOMIA DE ERRO DA MAQUINA — quatro codigos, e nenhum quinto.
#
# 🔴 ELA JA EXISTIA, E JA TINHA DIVERGIDO. O `2` significava "uso errado" em
# duas pecas e "achou arquivo solto" numa terceira. Duas pecas dizendo coisas
# diferentes com o MESMO numero e pior que nao ter numero: quem le o codigo de
# saida num script decide errado, e nada acusa — o script simplesmente segue.
#
# 🔑 Por isso a lista nao e um documento. Documento de convencao apodrece na
# primeira peca nova, porque nada le documento. Isto e uma pergunta que o mapa
# faz todo dia, e que REPROVA.
SAIDAS = {
    0: "nada a acusar",
    1: "ACUSOU — mediu, e o alvo reprovou",
    2: "nao deu para USAR — argumento faltando, pasta que nao existe",
    3: "nao deu para MEDIR — a fonte nao respondeu. NAO e um verde",
}

# `return <n>` no fim de uma funcao de linha de comando, e `sys.exit(<n>)`.
_RETORNO = re.compile(r"^\s*(?:return|sys\.exit\()\s*(\d+)\s*\)?\s*$", re.M)


def codigos_de_saida(dados):
    """Pecas que devolvem um codigo fora da taxonomia. [] quando nenhuma.

    ⚠️ So olha o retorno LITERAL — `return 4`, `sys.exit(7)`. Retorno
    calculado (`sys.exit(1 if FALHA else 0)`) passa direto, e isso e o certo:
    inventar uma analise de fluxo aqui daria um detector que erra nos dois
    sentidos. O que se quer pegar e o numero novo escrito a mao, que e como a
    divergencia entrou da primeira vez.
    """
    fora = []
    for d in dados:
        arq = caminho(d["onde"], d["nome"])
        if not os.path.isfile(arq) or not arq.endswith(".py"):
            continue
        try:
            texto = io.open(arq, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        achados = sorted({int(m) for m in _RETORNO.findall(texto)}
                         - set(SAIDAS))
        if achados:
            fora.append((d["nome"], achados))
    return fora


def main():
    dados = levantar("--rapido" not in sys.argv)

    if "--json" in sys.argv:
        print(json.dumps({
            "pecas": len(dados),
            "sem_arquivo": [d["nome"] for d in dados if not d["existe"]],
            "sem_teste": [d["nome"] for d in dados if not d["teste_existe"]],
            "reprovando": [d["nome"] for d in dados if d["passa"] is False],
        }, ensure_ascii=False))
        return 0

    print("A MAQUINA - %d pecas" % len(dados))
    print()
    print("%-11s %-26s %-7s %-12s %s"
          % ("camada", "peca", "existe", "teste", "quem chama"))
    print("-" * 92)
    for d in dados:
        if d["passa"] is True:
            t = "PASSA"
        elif d["passa"] is False:
            t = "REPROVA"
        elif d["teste_existe"]:
            t = "(nao rodado)"
        else:
            t = "SEM TESTE"
        print("%-11s %-26s %-7s %-12s %s"
              % (d["cat"], d["nome"][:26], "ok" if d["existe"] else "NAO",
                 t, d["chamador"][:34]))
    print("-" * 92)
    sem_arq = [d["nome"] for d in dados if not d["existe"]]
    sem_t = [d["nome"] for d in dados if not d["teste_existe"]]
    ruim = [d["nome"] for d in dados if d["passa"] is False]
    print("  sem arquivo no disco ..... %d %s" % (len(sem_arq), sem_arq or ""))
    print("  SEM TESTE ................ %d %s" % (len(sem_t), sem_t or ""))
    print("  com teste REPROVANDO ..... %d %s" % (len(ruim), ruim or ""))
    presas = caminho_preso(dados)
    print("  com CAMINHO PRESO ........ %d %s" % (len(presas), presas or ""))
    fora = codigos_de_saida(dados)
    print("  com CODIGO DE SAIDA fora . %d %s"
          % (len(fora), ["%s:%s" % (n, c) for n, c in fora] or ""))
    print()
    print("  onde cada camada mora:")
    print("    porta/regua  -> %s   (o Claude Code LE de la)" % curto(HOOKS))
    print("    medida/cons. -> %s" % curto(FUND))
    print("    biblioteca   -> %s   (importada por projeto)" % curto(SHARED))
    return 1 if (sem_arq or ruim or fora) else 0


if __name__ == "__main__":
    sys.exit(main())
