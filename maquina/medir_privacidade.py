# -*- coding: utf-8 -*-
"""Quanto CONTEXTO PRIVADO existe nas peças da máquina?

    python maquina/medir_privacidade.py

A decisão que isto serve: a casa é a fonte, o repo público é uma **destilação**.
Antes de construir o destilador, é preciso saber o tamanho do problema: se as
peças são 5% contexto privado, destilar é filtrar; se são 40%, destilar é
reescrever — e isso muda o desenho inteiro.

Nada é reescrito aqui. Isto só MEDE, para a decisão sair de número e não de
impressão. É o que o `calibrar_padroes` é para o gate: a régua que vem antes.

🔴 O QUE ESTA PEÇA COBRE E O QUE JÁ EXISTIA
--------------------------------------------
Uma casa madura costuma ter duas defesas de **credencial**: um redator que
tarja segredo, e um gate que barra segredo no código novo. Nenhuma das duas
sabe que o nome de uma empresa, de um cliente ou de um projeto é contexto
privado — credencial e IDENTIDADE são coisas diferentes, e publicar vaza a
segunda enquanto todo mundo olha a primeira.

O que conta como privado, e por quê:
  - nome de pessoa e de empresa  -> identifica o cliente
  - caminho da máquina           -> expõe a estrutura do disco
  - nome de projeto interno      -> revela a carteira de clientes
  - incidente com data           -> conta o que quebrou, quando e onde
  - contato/URL                  -> dado de contato

CHAMADOR: `maquina/destilar.py` e a mão, na decisão de publicar.
PROVA:    `maquina/testar_destilar.py`, com mutação.
"""
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                           # noqa: BLE001
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import inventario as inv                                    # noqa: E402

# 🔴 OS NOMES SAIRAM DO CODIGO, e o motivo e o melhor argumento que
# esta peca ja produziu: ao destilar a maquina para publicacao, ELA FOI
# REPROVADA PELO SEU PROPRIO DETECTOR — e com razao, porque as regex listavam
# os nomes reais de pessoas, empresas e projetos. A lista de nomes privados
# ERA o conteudo privado.
#
# As duas saidas obvias eram ruins: publicar com a lista vaza a carteira de
# clientes; publicar sem ela entrega um detector morto, que responde "nada
# encontrado" para tudo — [[concept-a-cegueira-que-responde-200]].
#
# O conserto nao e filtrar melhor: e separar DADO de CODIGO, que e a R7 da
# casa (*catalogo > hardcode, nunca no script*). O codigo abaixo vai para o
# repositorio publico e funciona; `privacidade.json` fica aqui. E a D-04
# continua valendo — UMA implementacao, nao duas: a peca interna le
# exatamente o mesmo arquivo que a publicada leria.
#
# ⚠️ Se o JSON sumir, isto NAO cai para uma lista vazia. Detector vazio aprova
# tudo em silencio, e este e o unico erro que nao se descobre depois: o que
# vazou ja vazou. Sem o arquivo, a peca levanta e para.
FONTE = os.path.join(AQUI, "privacidade.json")

# 🔴 A FAMILIA `ip publico` quase nao nasceu. Ao preparar a
# porta do Bash para publicacao, o teste dela tinha o IP REAL de um servidor ao
# lado do caminho de uma chave SSH. O detector ACUSOU aquela linha — mas por
# acidente, porque o `root@` na frente fez a regex de e-mail casar. IP sem
# usuario antes (num `ping`, num `curl`, num comentario) passaria limpo.
#
# 🔑 Gate que acerta por coincidencia acerta so enquanto a coincidencia durar,
# e ninguem fica sabendo quando ela acaba.
_ORDEM = [
    ("pessoa/empresa", "pessoa_empresa", True),
    ("caminho do disco", "caminho_do_disco", False),
    ("projeto interno", "projeto_interno", True),
    ("incidente com data", "incidente_com_data", False),
    ("ip publico", "ip_publico", False),
    ("contato/URL", "contato_url", False),
]


def carregar_marcas(fonte=None):
    """[(rotulo, regex)] a partir do JSON. Sem o arquivo, ERRO — nunca vazio."""
    caminho = fonte or FONTE
    with io.open(caminho, encoding="utf-8") as fh:
        dados = json.load(fh)
    marcas = []
    for rotulo, chave, com_borda in _ORDEM:
        termos = [t for t in (dados.get(chave) or []) if t]
        if not termos:
            raise ValueError(
                "privacidade.json sem termos em %r. Um grupo vazio faz o "
                "detector aprovar essa familia inteira em silencio." % chave)
        juntos = "|".join(termos)
        padrao = (r"\b(%s)\b" % juntos) if com_borda else juntos
        marcas.append((rotulo, re.compile(padrao, re.I)))
    return marcas


MARCAS = carregar_marcas()


def medir_texto(t):
    """Devolve (linhas, linhas_sujas, {marca: n}) para um texto."""
    linhas = t.split(chr(10))
    por_marca = {}
    sujas = set()
    for nome, rx in MARCAS:
        n = 0
        for i, l in enumerate(linhas):
            if rx.search(l):
                n += 1
                sujas.add(i)
        por_marca[nome] = n
    return len(linhas), sujas, por_marca


def medir(caminho):
    try:
        t = io.open(caminho, encoding="utf-8", errors="replace").read()
    except Exception:                                       # noqa: BLE001
        return None
    total, sujas, marcas = medir_texto(t)
    return dict(total=total, sujas=len(sujas), marcas=marcas)


def main():
    print("QUANTO CONTEXTO PRIVADO EXISTE NA MAQUINA")
    print()
    print("%-26s %7s %7s %6s  %s"
          % ("peca", "linhas", "sujas", "%", "o que aparece"))
    print("-" * 96)
    tot_l = tot_s = 0
    for cat, nome, pasta, teste, _ in inv.PECAS:
        m = medir(inv.caminho(pasta, nome))
        if not m:
            continue
        tot_l += m["total"]
        tot_s += m["sujas"]
        quais = ", ".join("%s:%d" % (k.split("/")[0], v)
                          for k, v in m["marcas"].items() if v)
        print("%-26s %7d %7d %5.0f%%  %s"
              % (nome[:26], m["total"], m["sujas"],
                 100.0 * m["sujas"] / max(1, m["total"]), quais[:44]))
    print("-" * 96)
    print("%-26s %7d %7d %5.0f%%"
          % ("TOTAL", tot_l, tot_s, 100.0 * tot_s / max(1, tot_l)))
    print()
    print("Leitura: %d de %d linhas carregam contexto privado."
          % (tot_s, tot_l))
    print("  ate ~10%  -> destilar e FILTRAR")
    print("  acima      -> destilar e REESCREVER, e o desenho muda")
    return 0


if __name__ == "__main__":
    sys.exit(main())
