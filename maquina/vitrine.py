# -*- coding: utf-8 -*-
"""A VITRINE — a casa inteira numa tela, para ele olhar sem perguntar.

    python maquina/vitrine.py            # gera vitrine.html na raiz
    python maquina/vitrine.py --abrir    # gera e abre no navegador
    python maquina/vitrine.py --json     # o caminho e o resumo, para o [6u]

POR QUE ESTA PECA EXISTE
------------------------
A frase que abriu o projeto, e que ainda nao tinha resposta:

    *"nao mais ficar com essa DESCONFIANCA de se ta rodando ou nao, se ta
    validando ou nao, depender de vc olhar o memory, ou o claude.md"*

Repare no que ele pede: nao e que a maquina funcione. E que ele nao precise
DESCONFIAR. Sao coisas diferentes, e so a primeira estava resolvida.

O estado da casa existe e e medido todo dia. Mas ele mora no
`mente_health_report.txt`, que e um arquivo de texto de centenas de linhas que
ele nao le, e chega ate ele por uma Ronda que injeta so o URGENTE. Estado que
so aparece quando vira urgencia nao tira desconfianca nenhuma — ele continua
tendo de perguntar para saber.

🔑 E ISTO JA ESTAVA ESCRITO NO NOSSO PROPRIO REGISTRO DE DECISOES. A decisao
descartou o Backstage e registrou o motivo com uma ressalva que era uma divida
declarada: *"se a casa deixar de ser operada por uma pessoa no terminal, o
Backstage volta a mesa — sobretudo pela camada 5 (VITRINE), que e onde ele e
imbativel."* A camada que faltava tinha nome desde aquele dia. Esta peca e ela,
no tamanho da casa: uma pagina, sem Postgres e sem 3 engenheiros dedicados.

O QUE A PAGINA MOSTRA, e a ordem e a resposta a pergunta dele:
  1. o BASICO nos 30 projetos, em barra — da para ver de longe
  2. a MAQUINA: cada peca existe? o teste dela passa AGORA?
  3. o que DA para consertar, e o que NAO se conserta sozinho (com o porque)
  4. a tabela por projeto, para quando ele quiser o detalhe

🔴 PROVA ANTES DE GRAVAR (D-03). O modo de falha desta familia e o pior de
todos: um template quebrado gera uma pagina BONITA e VAZIA, e pagina vazia le
como casa saudavel. Entao antes de gravar, a peca procura no HTML gerado cada
numero que mediu. Se algum nao estiver la, ela NAO grava e diz qual sumiu.

ZERO CDN, por regra da casa (R4): a pagina e autocontida e abre sem rede.

CHAMADOR: o verificador diario de saude da casa.
PROVA:    `maquina/testar_vitrine.py`, com mutacao.
"""
import datetime
import io
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001,S110 - sem stdout nao ha para onde avisar
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import consertar as ct  # noqa: E402
import inventario as inv  # noqa: E402
import o_basico as ob  # noqa: E402

DESTINO = os.path.join(os.path.dirname(AQUI), "vitrine.html")

ROTULO = {
    "id": "contrato projeto.yml",
    "git": "e repositorio git",
    "ign": ".gitignore",
    "tst": "tem teste escrito",
    "cit": "o CI RODA o teste",
    "sec": "varredura de segredo",
    "dec": "decisoes registradas",
}

CSS = """
:root{color-scheme:light dark;
 --fundo:#f6f7f9;--carta:#fff;--linha:#e3e6ea;--texto:#14171a;--fraco:#5c6570;
 --bom:#1a7f4b;--meio:#b5761b;--ruim:#b3261e;--barra:#e9ecf0}
@media (prefers-color-scheme:dark){:root{
 --fundo:#0e1116;--carta:#171b22;--linha:#262c36;--texto:#e6e9ee;--fraco:#9aa4b2;
 --bom:#3fb950;--meio:#d29922;--ruim:#f85149;--barra:#232a34}}
*{box-sizing:border-box}
body{margin:0;padding:0;background:var(--fundo);color:var(--texto);
 font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:980px;margin:0 auto;padding:28px 18px 60px}
h1{font-size:26px;margin:0 0 4px;letter-spacing:-.4px}
.sub{color:var(--fraco);font-size:13px;margin:0 0 26px}
.carta{background:var(--carta);border:1px solid var(--linha);border-radius:12px;
 padding:20px;margin:0 0 18px}
h2{font-size:12px;letter-spacing:.9px;text-transform:uppercase;color:var(--fraco);
 margin:0 0 16px;font-weight:600}
.lin{display:grid;grid-template-columns:170px 1fr 58px;gap:12px;align-items:center;
 margin:0 0 9px;font-size:13px}
.trilho{background:var(--barra);border-radius:999px;height:9px;overflow:hidden}
.ench{height:100%;border-radius:999px}
.num{text-align:right;font-variant-numeric:tabular-nums;color:var(--fraco);font-size:12px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;font-weight:600;color:var(--fraco);font-size:11px;
 text-transform:uppercase;letter-spacing:.6px;padding:0 8px 8px;white-space:nowrap}
td{padding:7px 8px;border-top:1px solid var(--linha);vertical-align:top}
td.c{text-align:center;width:44px}
.ok{color:var(--bom);font-weight:600}.nao{color:var(--ruim);font-weight:600}
.pt{color:var(--fraco)}
ul{margin:0;padding-left:18px}li{margin:0 0 7px}
.nota{color:var(--fraco);font-size:12.5px;margin:14px 0 0;
 border-left:2px solid var(--linha);padding-left:12px}
code{background:var(--barra);padding:1px 5px;border-radius:4px;font-size:12px}
.rodape{color:var(--fraco);font-size:12px;text-align:center;margin-top:26px}
@media(max-width:560px){.lin{grid-template-columns:1fr;gap:4px}
 .num{text-align:left}.wrap{padding:18px 14px 40px}}
"""


def _cor(n, total):
    p = (n * 100.0 / total) if total else 0
    return "var(--bom)" if p >= 90 else (
        "var(--meio)" if p >= 50 else "var(--ruim)")


def _esc(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def montar():
    """Devolve (html, numeros) — `numeros` e o que a prova vai procurar nele."""
    dados, _fora = ob.medir()
    total = len(dados)
    placar = {k: sum(1 for v in dados.values() if v[k]) for k in ob.ITENS}
    pecas = inv.levantar(rodar_testes=True)
    acoes, recusas, _a, _d, _n = ct.levantar(aplicar=False)
    consertaveis = [a for a in acoes if a["ok"]]
    agora = datetime.datetime.now().strftime("%d/%m/%Y as %H:%M")

    p = ['<!doctype html><html lang="pt-BR"><meta charset="utf-8">',
         '<meta name="viewport" content="width=device-width,initial-scale=1,'
         'viewport-fit=cover"><title>A casa</title><style>', CSS,
         '</style><div class="wrap">',
         '<h1>A casa</h1>',
         '<p class="sub">Medido em %s &middot; %d projetos &middot; %d pecas '
         'na maquina</p>' % (agora, total, len(pecas))]

    # 1. o basico
    p.append('<div class="carta"><h2>O basico, nos %d projetos</h2>' % total)
    for k in ob.ITENS:
        n = placar[k]
        p.append('<div class="lin"><div>%s</div>'
                 '<div class="trilho"><div class="ench" style="width:%.1f%%;'
                 'background:%s"></div></div>'
                 '<div class="num" data-item="%s">%d/%d</div></div>'
                 % (_esc(ROTULO[k]), n * 100.0 / total if total else 0,
                    _cor(n, total), k, n, total))
    p.append('</div>')

    # 2. a maquina
    quebradas = [d for d in pecas if d["passa"] is False or not d["existe"]]
    p.append('<div class="carta"><h2>A maquina &mdash; ela ainda esta de pe?</h2>')
    p.append('<table><tr><th>peca</th><th>camada</th><th>existe</th>'
             '<th>teste</th><th>quem chama</th></tr>')
    for d in pecas:
        if d["passa"] is True:
            t = '<span class="ok">passa</span>'
        elif d["passa"] is False:
            t = '<span class="nao">REPROVA</span>'
        elif d["teste_existe"]:
            t = '<span class="pt">nao rodado</span>'
        else:
            t = '<span class="pt">sem teste</span>'
        p.append('<tr><td><code>%s</code></td><td class="pt">%s</td>'
                 '<td class="c">%s</td><td>%s</td><td class="pt">%s</td></tr>'
                 % (_esc(d["nome"]), _esc(d["cat"]),
                    '<span class="ok">sim</span>' if d["existe"]
                    else '<span class="nao">NAO</span>', t,
                    _esc(d["chamador"])))
    p.append('</table>')
    if quebradas:
        p.append('<p class="nota">%d peca(s) com problema. Peca que existe, '
                 'tem chamador e cujo teste reprova nao esta no ar: esta '
                 'quebrada.</p>' % len(quebradas))
    else:
        p.append('<p class="nota">As %d pecas existem e os testes delas passam '
                 'agora, nesta medicao. Nao e memoria de ontem.</p>'
                 % len(pecas))
    p.append('</div>')

    # 3. o que falta
    p.append('<div class="carta"><h2>O que falta</h2>')
    if consertaveis:
        p.append('<p><b>%d conserto(s) prontos.</b> A casa sabe fazer sozinha: '
                 '<code>python maquina/consertar.py --aplicar</code> '
                 '(escreve local, nao commita).</p>' % len(consertaveis))
    else:
        p.append('<p>Nada pendente nas 4 familias que a casa conserta sozinha.</p>')
    if recusas:
        p.append('<p>E estas <b>nao se consertam sozinhas, de proposito</b>:</p><ul>')
        vistos = set()
        for r in recusas:
            if r["item"] in vistos:
                continue
            vistos.add(r["item"])
            quais = sorted({x["projeto"] for x in recusas
                            if x["item"] == r["item"]})
            p.append('<li><b>%s</b> em %d projeto(s) &mdash; %s<br>'
                     '<span class="pt">%s</span></li>'
                     % (_esc(r["rotulo"]), len(quais), _esc(r["porque"]),
                        _esc(", ".join(quais))))
        p.append('</ul>')
    p.append('</div>')

    # 4. por projeto
    p.append('<div class="carta"><h2>Projeto a projeto</h2><table><tr>'
             '<th>projeto</th>')
    for k in ob.ITENS:
        p.append('<th class="c">%s</th>' % _esc(k))
    p.append('</tr>')
    for nome in sorted(dados):
        p.append('<tr><td>%s</td>' % _esc(nome))
        for k in ob.ITENS:
            p.append('<td class="c">%s</td>'
                     % ('<span class="ok">&#10003;</span>' if dados[nome][k]
                        else '<span class="nao">&#183;</span>'))
        p.append('</tr>')
    p.append('</table><p class="nota">%s</p></div>'
             % " &middot; ".join("<code>%s</code> %s" % (k, _esc(ROTULO[k]))
                                for k in ob.ITENS))

    p.append('<p class="rodape">Gerado por <code>maquina/vitrine.py</code>'
             ' &middot; nenhum dado sai desta maquina</p></div></html>')

    # o que a prova vai procurar: cada numero que esta pagina afirma
    numeros = {"projetos": total, "pecas": len(pecas),
               "consertaveis": len(consertaveis)}
    numeros.update({("placar_" + k): placar[k] for k in ob.ITENS})
    return "".join(p), numeros


def gravar(destino=DESTINO):
    html, numeros = montar()
    # PROVA ANTES DE GRAVAR: cada numero medido tem de aparecer no HTML. Um
    # template quebrado produz pagina bonita e VAZIA, e pagina vazia le como
    # casa saudavel — o modo de falha mais perigoso de uma vitrine.
    #
    # ⚠️ O NUMERO VAI ANCORADO NO ITEM, e isto foi achado pela mutacao, nao
    # por leitura. A 1a versao procurava a string solta no documento — e o
    # placar tem colunas que empatam: quatro delas valiam "30 de 30" ao mesmo
    # tempo. Apagar a linha de uma dessas quatro deixava a prova passar,
    # porque o mesmo texto continuava ali, vindo de outra coluna. Detector que
    # casa por valor solto num documento com valores repetidos mede a si
    # mesmo. Agora o alvo carrega o par item+numero, e nao o numero sozinho.
    faltando = []
    for chave, valor in numeros.items():
        if chave.startswith("placar_"):
            alvo = 'data-item="%s">%d/%d<' % (chave[7:], valor,
                                              numeros["projetos"])
        else:
            alvo = str(valor)
        if alvo not in html:
            faltando.append("%s=%s" % (chave, alvo))
    if faltando:
        return None, numeros, faltando
    io.open(destino, "w", encoding="utf-8", newline="\n").write(html)
    return destino, numeros, []


def main():
    destino, numeros, faltando = gravar()
    if faltando:
        print("NAO GRAVEI — a pagina nao carrega o que eu medi:")
        for f in faltando:
            print("   sumiu do HTML: %s" % f)
        print("Pagina bonita e vazia le como casa saudavel. Melhor nao ter.")
        return 1

    if "--json" in sys.argv:
        saida = {"caminho": destino, "ok": True}
        saida.update(numeros)
        print(json.dumps(saida, ensure_ascii=False))
        return 0

    print("VITRINE gravada: %s" % destino)
    print("  %d projetos | %d pecas na maquina | %d conserto(s) prontos"
          % (numeros["projetos"], numeros["pecas"], numeros["consertaveis"]))
    print("  os %d numeros da pagina foram conferidos dentro do HTML."
          % len(numeros))
    if "--abrir" in sys.argv:
        import webbrowser
        webbrowser.open("file:///" + destino.replace("\\", "/"))
        print("  aberto no navegador.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
