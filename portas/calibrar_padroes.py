#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""CALIBRAR UMA REGRA ANTES DE ELA VIRAR PORTA - e contar a divida das que sao vigia.

POR QUE ESTA PECA EXISTE
------------------------
Ordem dele, *"Calibre ANTES de promover. Nenhuma regra entra sem
medir o ruido em codigo real - a licao do fallback-secrets (1.266 achados
falsos) e a regua."*

Ate agora a calibragem era feita a mao, com um `python -c` descartavel por
regra, e a varredura de divida vivia COPIADA dentro do bloco [6n] do
`mente_health.py`. Duas consequencias medidas:
  - a calibragem nao deixava rastro: o numero que decidiu `porta` vs `vigia`
    morria no terminal, e ninguem conseguia repetir a medicao amanha;
  - a varredura existia em dois lugares, e so um deles seria consertado.

Aqui ela vira UMA peca, com chamador, e o numero fica gravado.

O QUE ELA RESPONDE, e e a unica pergunta que importa na promocao
----------------------------------------------------------------
"Se esta regra fosse porta HOJE, quantos arquivos do codigo REAL desta casa ela
recusaria?" Poucos (ate DEZ_ARQUIVOS) = erro nascendo, vira `porta`. Muitos =
divida antiga espalhada, vira `vigia`: barrar 235 arquivos nao conserta nenhum
e faz alguem desligar o gate na primeira semana.

MODOS
-----
  calibrar_padroes.py                    todas as regras do JSON, por degrau
  calibrar_padroes.py --onde vigia       so as de vigia (o que o [6n] conta)
  calibrar_padroes.py --regra <id>       uma regra, com AMOSTRA das linhas
  calibrar_padroes.py --seed "<regex>"   uma CANDIDATA que ainda nao existe no
                                         JSON - e este e o uso principal, o que
                                         acontece antes de escrever a regra
        [--escopo RX] [--exige RX] [--so-se RX] [--nao-se RX] [--ext .py,.sh]
  --amostra N    quantas linhas mostrar por regra (padrao 8)
  --json         saida para maquina

CHAMADOR: `mente_health.py` bloco [6n] (varredura diaria de divida, 9h) e a mao
          na promocao de cada regra nova.
PROVA:    `testar_calibrar_padroes.py`, com mutacao.
"""

import argparse
import io
import json
import os
import re
import sys
import time as _relogio

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import padroes_na_porta as gate                             # noqa: E402

# O teto que separa `porta` de `vigia`. Nao e numero redondo por gosto: e a
# fronteira entre "da para consertar os casos hoje" e "isto e arqueologia".
DEZ_ARQUIVOS = 10


def quantificador_aninhado(padrao):
    """O padrao tem um grupo que REPETE dentro e e repetido fora?

    Devolve o trecho culpado, ou "" se estiver limpo.

    Por que a checagem e ESTATICA, e nao um cronometro: cronometro so acusa
    depois que a tentativa termina, e o caso que ele existe para pegar e
    exatamente o que NAO termina. Um `re` do CPython roda em C e nao se
    interrompe por thread nem por sinal no Windows. Medido: pus um
    relogio em volta de `violacoes()` e a calibragem travou do mesmo jeito,
    porque a linha do relogio nunca foi alcancada. E a
    [[concept_a_saida_por_tempo_vai_antes_da_tentativa]] aplicada a regex - a
    saida tem de estar ANTES, e aqui "antes" significa ler o padrao em vez de
    executa-lo.

    O alvo e o formato que explodiu: `(?:[ \\t]+(?!try\\b)[^\\n]*\\n){0,6}` -
    um grupo que ja repete (`+`, `*`) sob um quantificador externo (`{0,6}`).
    Cada caractere a mais dobra o numero de caminhos que o motor tenta antes
    de desistir.
    """
    i = 0
    n = len(padrao)
    while i < n:
        c = padrao[i]
        if c == "\\":
            i += 2
            continue
        if c != "(":
            i += 1
            continue
        # acha o ")" que fecha este grupo, respeitando aninhamento e escape
        prof = 0
        j = i
        while j < n:
            if padrao[j] == "\\":
                j += 2
                continue
            if padrao[j] == "(":
                prof += 1
            elif padrao[j] == ")":
                prof -= 1
                if prof == 0:
                    break
            j += 1
        if j >= n:
            return ""                       # padrao malformado; o re reclama
        dentro = padrao[i + 1:j]
        depois = padrao[j + 1:j + 2]
        # `?` sozinho nao explode: ele NAO multiplica caminhos, so torna o
        # grupo opcional uma vez.
        if depois in ("*", "+", "{") and re.search(r"(?<!\\)[*+]|\{\d", dentro):
            return padrao[i:j + 2]
        i += 1
    return ""


class EscopoVazio(Exception):
    """O escopo nao casou com arquivo nenhum - nao ha veredito a dar."""


class RegraLenta(Exception):
    """O seed candidato custa caro demais para virar porta.

    Levantada em vez de devolver um numero porque aqui nao ha veredito a dar:
    uma regra que congela o `Edit` nao e "porta ou vigia", e regra que nao
    pode existir em nenhum dos dois degraus.
    """

RAIZES = (os.path.join(os.path.expanduser("~"), "Projeto"), AQUI)

# A mesma poda do [6n]. Pasta de terceiro nao e codigo nosso e nao se conserta.
PODA = ("node_modules", ".aiox-core", ".git", "__pycache__", ".venv", "venv",
        "repos", "site-packages", "dist", "build", ".next", "out", "Lib")


def e_worktree(caminho):
    """Um worktree ligado tem `.git` como ARQUIVO ponteiro, nao diretorio.

    Detectar pelo que a coisa E, e nao pelo nome da pasta (`*-wt`): a
    heuristica de nome erra no dia em que o worktree se chamar outra coisa, e
    erra calado, que e o pior jeito.
    """
    return os.path.isfile(os.path.join(caminho, ".git"))


def arquivos(exts=None, contar=True):
    """Todo arquivo de codigo NOSSO, ja passado pelo filtro ISENTOS do gate.

    `contar=True` (o padrao, e o uso da calibragem) PULA worktrees: o mesmo
    arquivo aparece uma vez por worktree, e e o numero de arquivos que decide
    `porta` x `vigia`. Medido: 866 de 4.235 (20,4%) eram copia de
    worktree, TODAS com o original tambem na varredura - um dos projetos vive
    em mais dois lugares. Contado assim, uma regra de 9 arquivos virava 13 e
    era rebaixada para vigia por artefato de contagem, nao por divida real.
    E o mesmo raciocinio do `.min.js` ja anotado no ISENTOS: contar o que nao
    se conserta envenena o numero que decide o degrau. So que aqui e pior -
    e o NOSSO arquivo, contado de novo.

    `contar=False` varre tudo, inclusive worktree, para quem quiser o alcance
    bruto.
    """
    exts = tuple(exts or gate.CODIGO)
    for base in RAIZES:
        for dp, dns, fns in os.walk(base):
            if contar:
                dns[:] = [x for x in dns
                          if not e_worktree(os.path.join(dp, x))]
            # `.github` na lista de exceções, junto com `.claude`: a poda de
            # diretórios ocultos é certa para `.venv` e `.next`, e estava
            # cortando os **320 workflows** da casa. Medido, no dia
            # em que o gate passou a olhar `.yml`: a regra do `wrangler`
            # achava o defeito quando chamada direto e o calibrador reportava
            # ZERO, porque nunca chegava no arquivo. Instrumento que não visita
            # onde a regra atua mede o próprio alcance, não a casa.
            dns[:] = [x for x in dns
                      if x not in PODA
                      and (not x.startswith(".")
                           or x in (".claude", ".github"))]
            for fn in fns:
                if not fn.lower().endswith(exts):
                    continue
                cam = os.path.join(dp, fn)
                lo = cam.replace("/", "\\").lower()
                if any(p.replace("/", "\\").lower() in lo for p in gate.ISENTOS):
                    continue
                yield cam


def ler(cam):
    """`newline=""` NAO e detalhe: sem ele o Python traduz `\\r\\n` em `\\n` na
    leitura, e uma regra que pergunta por CRLF mede zero em 100% dos arquivos -
    inclusive nos corretos. Foi o que aconteceu na 1a calibragem de
    `ps1-crlf-bom`: acusou o `triagem_alertas.ps1`, que tem BOM e 331 CRLF e e
    o arquivo de onde a regra nasceu. O gate nao tem esse problema porque
    recebe o `content` como a ferramenta vai grava-lo; o calibrador le do
    disco, e o disco so responde a verdade em bytes.
    """
    try:
        with io.open(cam, encoding="utf-8", errors="replace",
                     newline="") as fh:
            return fh.read()
    except Exception:                                       # noqa: BLE001
        return ""


def _linhas_uteis(texto):
    for n, ln in enumerate(texto.split("\n"), 1):
        if len(ln) > 400 or ln.lstrip().startswith(("#", "//", "*")):
            continue
        yield n, ln


def calibrar_seed(seeds=None, escopo=None, exige=None, so_se=None, nao_se=None,
                  exts=None, seeds_bloco=None, nao_tem=None,
                  olha_comentario=False):
    """Roda uma CANDIDATA que ainda nao esta no JSON.

    NAO reimplementa a deteccao: monta a regra no formato do JSON e entrega ao
    proprio `padroes_na_porta.violacoes`. Esta peca ja nasceu com a deteccao
    duplicada a mao, e a duplicata envelheceu no mesmo dia - o motor ganhou
    `seeds_bloco` e `nao_tem` e a copia daqui continuou vendo so linha. Numero
    medido por um detector que nao e o que vai para a porta nao calibra nada.
    """
    # O id NAO pode comecar com "_": `carregar()` trata isso como chave de
    # metadado e pula a regra inteira. Foi o que aconteceu no 1o uso desta
    # peca - `_cand` fazia toda calibragem devolver `0 achados -> PORTA`, um
    # veredito produzido por lista vazia. Quem pegou foi o `--prova`.
    for p in list(seeds or []) + list(seeds_bloco or []) + (
            [nao_tem] if nao_tem else []):
        culpado = quantificador_aninhado(p)
        if culpado:
            raise RegraLenta(
                "quantificador ANINHADO no padrao - recusado antes de rodar:\n"
                "  padrao : %s\n"
                "  culpado: %s\n"
                "Um grupo que ja repete por dentro, repetido por fora, dobra "
                "os caminhos\na cada caractere. O gate roda em todo "
                "Edit/Write: isto congela a escrita.\nReescreva sem o "
                "aninhamento (ex.: `[\\s\\S]{0,200}?` no lugar do grupo)."
                % (p, culpado))

    regra = {"cand": {"titulo": "candidata", "onde": "porta",
                      "seeds": list(seeds or []),
                      "seeds_bloco": list(seeds_bloco or []),
                      "olha_comentario": bool(olha_comentario)}}
    for chave, valor in (("escopo", escopo), ("exige", exige),
                         ("so_se", so_se), ("nao_se", nao_se),
                         ("nao_tem", nao_tem)):
        if valor:
            regra["cand"][chave] = valor
    carregar_orig = gate.carregar
    compiladas = _compilar(regra)
    gate.carregar = lambda onde="porta": compiladas
    try:
        achados = []
        # `alcance`: quantos arquivos o ESCOPO deixou passar. Sem este numero,
        # `0 achados` de uma casa limpa e `0 achados` de um escopo que nao
        # casa com nada sao a mesma frase - e a segunda vem embrulhada em "a
        # casa esta limpa", que e a mentira mais confortavel que este
        # instrumento sabe contar.
        alcance = 0
        rx_escopo = re.compile(escopo) if escopo else None
        for cam in arquivos(exts):
            if rx_escopo and not rx_escopo.search(cam.replace("/", chr(92))):
                continue
            alcance += 1
            texto = ler(cam)
            if not texto:
                continue
            # O relogio aqui e a defesa real contra regex explosivo, e nao a
            # amostra dos maiores arquivos: o pior caso de backtracking NAO e
            # o arquivo maior, e o de estrutura que faz o regex retroceder.
            # Medido: um seed com quantificador aninhado passava
            # folgado nos 6 maiores e nao terminava em 60 s sobre 40 KB do
            # `monitor_fysol.py`, que nem estava na amostra. A calibragem
            # varre os 2.912 arquivos de qualquer jeito - entao e ELA que
            # encontra o caso ruim; so faltava parar e dizer o nome.
            i = _relogio.time()
            pares = gate.violacoes(cam, texto)
            ms = (_relogio.time() - i) * 1000
            if ms > TETO_MS:
                raise RegraLenta(
                    "esta regra levou %.0f ms em UM arquivo (teto %d ms):\n"
                    "  %s\n"
                    "O gate roda em todo Edit/Write: com este seed, editar "
                    "esse arquivo congela.\nQuase sempre e quantificador "
                    "aninhado - um `{0,N}` em volta de um grupo que ja repete "
                    "(`[^\\n]*`, `.*`, `\\s*`). Reescreva sem o aninhamento."
                    % (ms, TETO_MS, curto(cam)))
            for _rid, _t, _f, _p, _c, n, trecho in pares:
                achados.append((cam, n, trecho))
        if rx_escopo and alcance == 0:
            raise EscopoVazio(
                "o escopo nao alcancou NENHUM arquivo:\n  %s\n"
                "Sem alcance, `0 achados` nao quer dizer que a casa esta "
                "limpa - quer dizer que o detector nao olhou nada. Quase "
                "sempre e escape perdido ao passar o regex pela linha de "
                "comando: rode a calibragem de um arquivo .py em vez de "
                "`--escopo`." % escopo)
        calibrar_seed.alcance = alcance
        return achados
    finally:
        gate.carregar = carregar_orig


def _compilar(dicionario):
    """Usa o compilador do proprio gate, sem passar pelo arquivo de regras."""
    regras_orig = gate.REGRAS
    tmp = os.path.join(os.environ.get("TEMP", AQUI), "_cand_padroes.json")
    try:
        with io.open(tmp, "w", encoding="utf-8") as fh:
            json.dump(dicionario, fh, ensure_ascii=False)
        gate.REGRAS = tmp
        return gate.carregar("porta")
    finally:
        gate.REGRAS = regras_orig
        try:
            os.remove(tmp)
        except OSError:
            pass


def calibrar_regras(onde="todas"):
    """{id: [(arquivo, linha, trecho)]} para as regras JA no JSON."""
    saida = dict((r[0], []) for r in gate.carregar(onde))
    for cam in arquivos():
        texto = ler(cam)
        if not texto:
            continue
        for rid, tit, fonte, pq, cons, n, trecho in gate.violacoes(
                cam, texto, onde):
            saida.setdefault(rid, []).append((cam, n, trecho))
    return saida


def provar_vivo(prova, seeds=None, seeds_bloco=None, nao_tem=None,
                nao_se=None, olha_comentario=False):
    """O seed PEGA o defeito canonico? Sem isto, `0 achados` nao diz nada.

    Escrito depois de a primeira calibragem seria desta peca dar
    `0 arquivo(s) -> PORTA` para um conjunto de tres seeds em que UM estava
    morto: `[^)]{0,40}` nao atravessa o `()` de um arrow function, entao
    `.on('error', () => resolve([]))` - o exemplo LITERAL do `PADROES.md` -
    nunca casaria. O veredito estava certo por acaso, que e a pior forma de
    estar certo. Mesma familia de [[concept-mutacao-sobre-baseline-morto]]:
    um detector que ja pega zero continua pegando zero quando voce o desarma.

    `prova` e o trecho do defeito (o do proprio PADROES.md, de preferencia).
    Devolve (pegou, quais_seeds_pegaram).
    """
    achados = []
    regra = {"prova": {"titulo": "prova", "onde": "porta",
                       "seeds": list(seeds or []),
                       "seeds_bloco": list(seeds_bloco or []),
                       "olha_comentario": bool(olha_comentario)}}
    if nao_tem:
        regra["prova"]["nao_tem"] = nao_tem
    if nao_se:
        regra["prova"]["nao_se"] = nao_se
    carregar_orig = gate.carregar
    compiladas = _compilar(regra)
    gate.carregar = lambda onde="porta": compiladas
    try:
        achados = gate.violacoes("prova.py", prova)
    finally:
        gate.carregar = carregar_orig
    vivos = []
    for i, s in enumerate(list(seeds or []) + list(seeds_bloco or [])):
        um = {"um": {"titulo": "um", "onde": "porta",
                     "seeds": [s] if i < len(seeds or []) else [],
                     "seeds_bloco": [] if i < len(seeds or []) else [s],
                     "olha_comentario": bool(olha_comentario)}}
        c = _compilar(um)
        gate.carregar = lambda onde="porta", _c=c: _c
        try:
            if gate.violacoes("prova.py", prova):
                vivos.append(s)
        finally:
            gate.carregar = carregar_orig
    return bool(achados), vivos


#  O teto de custo por regra. O gate roda em TODO Edit/Write: uma regra lenta
#  nao "deixa o dia mais lento", ela congela a escrita de arquivo.
TETO_MS = 150


def custo(seeds=None, seeds_bloco=None, nao_tem=None, amostras=None):
    """Quanto esta regra custa no PIOR arquivo real da casa, em ms.

    Existe porque um seed meu com quantificador aninhado
    (`(?:[ \\t]+(?!try\\b)[^\\n]*\\n){0,6}`) nao terminou em 60 segundos sobre
    40 KB do `monitor_fysol.py` - backtracking exponencial. Se aquela regra
    tivesse entrado no JSON, o proximo `Edit` de qualquer arquivo .py teria
    congelado, e o sintoma seria "o Claude travou", nao "a regra X e ruim".

    `re` do Python nao tem timeout e um regex em C nao se interrompe por
    thread. Entao a defesa nao pode ser no relogio: **e impedir a regra ruim
    de entrar**. Esta funcao e o instrumento, e o teste do gate e a porta.

    A medicao e feita numa AMOSTRA dos maiores arquivos: e neles que o custo
    aparece, e varrer os 2.912 para medir tempo custaria mais que o gate.
    """
    import time as _t
    if amostras is None:
        tudo = [(os.path.getsize(c), c) for c in arquivos()]
        tudo.sort(reverse=True)
        amostras = [ler(c) for _s, c in tudo[:25]]
    regra = {"custo": {"titulo": "custo", "onde": "porta",
                       "seeds": list(seeds or []),
                       "seeds_bloco": list(seeds_bloco or [])}}
    if nao_tem:
        regra["custo"]["nao_tem"] = nao_tem
    compiladas = _compilar(regra)
    carregar_orig = gate.carregar
    gate.carregar = lambda onde="porta": compiladas
    try:
        pior = 0.0
        for txt in amostras:
            # TRES medicoes, e vale a MENOR. Uma medicao so, numa maquina
            # disputada, mede a interferencia e nao o custo: a MESMA
            # regra (`replace-silencioso`) deu 58, 76, 89, 132 e 259 ms em
            # medicoes do mesmo dia, conforme a RAM apertava - e o 259 reprovou
            # o teste por um motivo que nao tinha nada a ver com a regra.
            # A menor das tres e a que mais se aproxima do custo real: o ruido
            # de uma maquina ocupada so ADICIONA tempo, nunca subtrai.
            i = _t.time()
            gate.violacoes("x.py", txt)
            menor = (_t.time() - i) * 1000
            # Repete SO o que passou do teto. Medir tres vezes tudo triplicava
            # o custo do teste diario para consertar um caso em vinte; medir de
            # novo so o suspeito custa quase nada e mata o falso positivo onde
            # ele acontece.
            if menor > TETO_MS:
                for _ in range(2):
                    i = _t.time()
                    gate.violacoes("x.py", txt)
                    menor = min(menor, (_t.time() - i) * 1000)
            pior = max(pior, menor)
        return pior
    finally:
        gate.carregar = carregar_orig


def custo_das_regras(onde="todas"):
    """{id: ms} - o custo de CADA regra ja no JSON, no pior arquivo da casa."""
    tudo = [(os.path.getsize(c), c) for c in arquivos()]
    tudo.sort(reverse=True)
    amostras = [ler(c) for _s, c in tudo[:25]]
    saida = {}
    for r in gate.carregar(onde):
        # Por INDICE: a tupla do `carregar` cresce quando o motor ganha campo,
        # e um desempacotamento posicional quebra tudo por um motivo que nada
        # tem a ver com o que esta peca mede. Aconteceu no 13o campo.
        rid, rxs, blocos, nt = r[0], r[9], r[10], r[11]
        saida[rid] = custo([x.pattern for x in rxs],
                           [x.pattern for x in blocos],
                           nt.pattern if nt else None, amostras)
    return saida


def veredito(n, vivo=None):
    """`vivo=False` invalida qualquer numero: o detector nao estava armado."""
    if vivo is False:
        return "INVALIDO", ("o seed NAO pega o proprio defeito - o numero "
                            "abaixo mede o detector, nao a casa")
    if n == 0:
        if vivo:
            return "porta", ("0 achados, e o seed PROVADO vivo - a casa esta "
                             "limpa; a regra nasce preventiva")
        return "porta", "0 achados - ou o seed esta morto, ou a casa esta limpa"
    if n <= DEZ_ARQUIVOS:
        return "porta", "%d arquivo(s) - da para consertar hoje" % n
    return "vigia", "%d arquivo(s) - divida espalhada, barrar nao conserta" % n


def curto(cam):
    c = cam.replace("\\", "/")
    for marca in ("/Projeto/", "/.claude/"):
        if marca in c:
            return c.split(marca, 1)[1]
    return os.path.basename(c)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                       # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--onde", default="todas",
                    choices=("porta", "vigia", "todas"))
    ap.add_argument("--regra")
    ap.add_argument("--seed", action="append")
    ap.add_argument("--bloco", action="append", dest="seeds_bloco",
                    help="regex sobre o TEXTO INTEIRO (o defeito de 2+ linhas)")
    ap.add_argument("--nao-tem", dest="nao_tem",
                    help="defeito de AUSENCIA: acha o arquivo em que ESTE "
                         "regex NAO aparece")
    ap.add_argument("--olha-comentario", dest="olha_comentario",
                    action="store_true",
                    help="NAO pular linha comentada - para a regra cujo alvo "
                         "E o comentario (ex.: crase solta que fecha template)")
    ap.add_argument("--escopo")
    ap.add_argument("--exige")
    ap.add_argument("--so-se", dest="so_se")
    ap.add_argument("--nao-se", dest="nao_se")
    ap.add_argument("--ext")
    ap.add_argument("--amostra", type=int, default=8)
    ap.add_argument("--prova",
                    help="trecho (ou arquivo) com o DEFEITO canonico. Sem "
                         "ele, `0 achados` nao distingue casa limpa de seed "
                         "morto")
    ap.add_argument("--tempo", action="store_true",
                    help="mede o CUSTO de cada regra no pior arquivo da casa")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.tempo:
        c = custo_das_regras(a.onde)
        if a.json:
            print(json.dumps(dict((k, round(v, 1)) for k, v in c.items())))
            return
        print("CUSTO por regra no pior arquivo real (teto: %d ms)" % TETO_MS)
        for rid, ms in sorted(c.items(), key=lambda x: -x[1]):
            print("  %-34s %7.1f ms%s"
                  % (rid, ms, "   !! ACIMA DO TETO" if ms > TETO_MS else ""))
        return

    prova = a.prova
    if prova and os.path.isfile(prova):
        prova = ler(prova)

    exts = tuple(x.strip().lower() for x in a.ext.split(",")) if a.ext else None

    if a.seed or a.seeds_bloco or a.nao_tem:
        try:
            ach = calibrar_seed(a.seed, a.escopo, a.exige, a.so_se, a.nao_se,
                                exts, a.seeds_bloco, a.nao_tem,
                                a.olha_comentario)
        except RegraLenta as e:
            print("CANDIDATA RECUSADA POR CUSTO\n  %s" % e)
            sys.exit(2)
        vivo = mortos = None
        if prova:
            vivo, vivos = provar_vivo(prova, a.seed, a.seeds_bloco, a.nao_tem,
                                      a.nao_se, a.olha_comentario)
            mortos = [s for s in (a.seed or []) + (a.seeds_bloco or [])
                      if s not in vivos]
        grau, porque = veredito(len(ach), vivo)
        if a.json:
            print(json.dumps({"achados": len(ach), "onde": grau,
                              "seed_vivo": vivo, "seeds_mortos": mortos,
                              "amostra": [(curto(c), n, t)
                                          for c, n, t in ach[:a.amostra]]},
                             ensure_ascii=False))
            return
        print("CANDIDATA: %s" % " | ".join(
            (a.seed or []) + (a.seeds_bloco or []) +
            (["AUSENCIA DE " + a.nao_tem] if a.nao_tem else [])))
        print("  %d arquivo(s) do codigo real -> %s (%s)"
              % (len(ach), grau.upper(), porque))
        if prova:
            print("  PROVA: o seed %s o defeito canonico"
                  % ("PEGA" if vivo else "NAO PEGA"))
            for s in mortos:
                print("    MORTO (nao casa a prova): %s" % s)
        for c, n, t in ach[:a.amostra]:
            print("    %s:%d" % (curto(c), n))
            print("        %s" % t)
        if len(ach) > a.amostra:
            print("    ... e mais %d" % (len(ach) - a.amostra))
        return

    todos = calibrar_regras(a.onde)
    if a.regra:
        todos = {a.regra: todos.get(a.regra, [])}
    if a.json:
        print(json.dumps(dict((k, len(v)) for k, v in todos.items()),
                         ensure_ascii=False))
        return
    print("CALIBRAGEM das regras `%s` sobre o codigo real desta casa" % a.onde)
    for rid, ach in sorted(todos.items(), key=lambda x: -len(x[1])):
        grau, porque = veredito(len(ach))
        print("\n  %-30s %4d arquivo(s)   sugere: %s" % (rid, len(ach), grau))
        for c, n, t in ach[:a.amostra]:
            print("      %s:%d" % (curto(c), n))
            print("          %s" % t)
        if len(ach) > a.amostra:
            print("      ... e mais %d" % (len(ach) - a.amostra))


if __name__ == "__main__":
    main()
