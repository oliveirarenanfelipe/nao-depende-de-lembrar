# -*- coding: utf-8 -*-
"""Destila uma peça da máquina para publicação — e RECUSA o que não limpou.

    python maquina/destilar.py <peca>             # mostra o que falta limpar
    python maquina/destilar.py <peca> --escrever  # grava em publicado/
    python maquina/destilar.py --todas

O CICLO COMPLETO, quando a peca tem linha que exige decisao humana:

    python maquina/destilar.py <peca> --rascunho  # 1. marca o que decidir
    (gente reescreve, e o par entra em reescritas.json)
    python maquina/destilar.py --reescrever       # 2. aplica o dado
    python maquina/destilar.py --conferir         # 3. mede e aprova

A DECISÃO QUE DESENHA ISTO: **a casa é a fonte, o repo público é uma
destilação.** Não duas implementações paralelas — foi assim que o
`estado_atomico` virou 29 cópias, e a casa e o repo público já estavam
divergindo do mesmo jeito: 7 gates lá, 14 peças aqui, **zero em comum**.

🔴 A GARANTIA, E ELA É O OPOSTO DE UM SANITIZADOR
--------------------------------------------------
Sanitizador silencioso **dá falsa confiança**: troca o que conhece, publica o
resto, e o que ele não conhecia vaza sem aviso. Aqui é ao contrário:

  1. troca só o que é MECÂNICO e sem julgamento (caminho de disco);
  2. **mede a própria saída** com o `medir_privacidade`;
  3. se sobrou UMA linha com contexto privado, **não escreve nada** e mostra
     a linha, o número e a marca;
  4. publicar exige saída limpa MEDIDA, não confiança no filtro.

O passo 2 é o que separa isto de um `sed`. Mesma forma do `ligar_ci`, que
roda o comando antes de escrever o CI.

⚠️ O QUE ELE NÃO FAZ: não reescreve prosa. Linha que cita cliente, projeto ou
incidente é DECISÃO — quem escreve a versão pública é gente, com a linha na
frente. O destilador diz quais são e para de trabalhar.

CHAMADOR: `maquina/testar_destilar.py` e a mão, antes de publicar.
PROVA:    `maquina/testar_destilar.py`, com mutação.
"""
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001,S110 - sem stdout nao ha para onde avisar
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import inventario as inv  # noqa: E402
import medir_privacidade as mp  # noqa: E402

SAIDA = os.path.join(AQUI, "publicado")

# Trocas MECANICAS: caminho de disco vira marcador. Sem julgamento nenhum —
# o caminho de uma maquina nao carrega ideia, so localizacao.
#
# 🔴 OS PADROES SAIRAM DO CODIGO, e o sintoma aqui foi pior que no
# `medir_privacidade`. La os nomes no codigo apenas REPROVAVAM a peca. Aqui os
# caminhos dentro das regex faziam o destilador CORROMPER a si mesmo: ao
# destilar este arquivo, ele trocava o conteudo das proprias regex por
# marcadores, e a versao publicada saia sem saber detectar caminho POSIX.
# Codigo publicado e quebrado e pior que codigo nao publicado — ninguem
# desconfia de uma peca que roda e nao acha nada.
#
# A mesma R7 de sempre: catalogo > hardcode. E o mesmo arquivo dos nomes, para
# nao existirem dois lugares onde "o que e privado" se define.
def carregar_mecanicas(fonte=None):
    with io.open(fonte or mp.FONTE, encoding="utf-8") as fh:
        pares = (json.load(fh).get("trocas_mecanicas") or [])
    if not pares:
        raise ValueError(
            "privacidade.json sem `trocas_mecanicas`. Sem elas o destilador "
            "para de limpar caminho de disco e passa a REPROVAR toda peca, "
            "que e o modo de falha barulhento — mas ainda assim e erro.")
    return [(re.compile(p), novo) for p, novo in pares]


MECANICAS = carregar_mecanicas()


def carregar_trocas_de_data(fonte=None):
    """As trocas que tiram a DATA do incidente. Lista vazia e valida.

    🔴 POR QUE ELAS SAO MECANICAS E NAO REESCRITA HUMANA. Ao destilar o
    catalogo de regras da casa, 71 de 158 linhas marcadas tinham como UNICA
    marca a data de um incidente. Sao todas a mesma transformacao, feita 71
    vezes a mao — e que se repetiria a cada regra nova.

    🔑 A regua da casa e `o numero sobrevive, o dono sai`. A data de um
    incidente interno e dono: ela diz QUANDO esta casa quebrou. O numero que
    importa fica intacto, porque nenhuma destas trocas toca em numero solto.

    ⚠️ Lista vazia e valida, ao contrario das `trocas_mecanicas`: sem ela o
    destilador apenas deixa de tirar datas, e a linha com data continua sendo
    REPROVADA pelo detector. O modo de falha e barulhento, nao silencioso.
    """
    with io.open(fonte or mp.FONTE, encoding="utf-8") as fh:
        pares = (json.load(fh).get("trocas_de_data") or [])
    return [(re.compile(p), novo) for p, novo in pares]


DE_DATA = carregar_trocas_de_data()


def erro(msg):
    """Diagnostico vai para stderr; stdout fica so com resultado.

    Quem chama esta peca num `|` ou num `>` precisa poder separar as duas
    coisas. Misturadas, quem consome tem de adivinhar qual linha e resultado e
    qual e reclamacao.
    """
    sys.stderr.write(msg + chr(10))


def destilar_texto(t):
    """So as trocas mecanicas. Devolve (texto, quantas trocas).

    ⚠️ A ORDEM DAS DUAS FAMILIAS IMPORTA e nao e arbitraria. Primeiro os
    caminhos de disco, que viram marcador; depois as datas, que somem. Se a
    data saisse antes, um caminho como `logs/13-09/saida` perderia o pedaco no
    meio e deixaria de casar a troca de caminho — a peca sairia com meio
    caminho da casa dentro.
    """
    n = 0
    for rx, novo in MECANICAS:
        t, k = rx.subn(novo, t)
        n += k
    for rx, novo in DE_DATA:
        t, k = rx.subn(novo, t)
        n += k
    return t, n


def sujeira(t):
    """Linhas que AINDA carregam contexto privado: [(n, marca, linha)]."""
    achados = []
    for i, l_ in enumerate(t.split(chr(10)), 1):
        # ⚠️ A REGUA NAO MORA MAIS AQUI. Esta funcao ja limpou o que
        # ja e publico por conta propria, e o `medir_privacidade` nao limpava
        # — duas reguas do que e privado, respondendo numeros diferentes sobre
        # os mesmos arquivos. Agora as duas perguntam ao MESMO lugar.
        quais = mp.marcas_da_linha(l_)
        if quais:
            achados.append((i, quais[0], l_.strip()[:88]))
    return achados


def caminho_do_alvo(nome):
    """Caminho da peca OU do teste dela, pelo nome. '' quando nao e da maquina.

    🔴 O TESTE TAMBEM SE DESTILA, e por muito tempo ele nao se destilava.
    Achado na hora de publicar de verdade: `publicado/` tinha as 7 pecas e
    NENHUM teste. Publicar peca sem a prova contradiz a casa inteira, onde
    "verde que nao verifica e pior que vermelho" — e quem baixasse receberia
    justamente a metade que pede confianca, sem a metade que a dispensa.

    O defeito era de ALCANCE, nao de logica: tres lugares varriam `inv.PECAS`
    procurando so a coluna do NOME, e a coluna do TESTE estava ali ao lado,
    sabida pelo mapa desde sempre. Resolver os dois no mesmo lugar e o que
    impede a proxima peca de nascer com o mesmo buraco.

    Medido antes de mexer: os 8 testes somam 1.707 linhas com **29** privadas
    (1%) — filtro, nao reescrita, pela propria leitura do `medir_privacidade`.
    """
    for _cat, n, pasta, teste, _ in inv.PECAS:
        if n == nome:
            return inv.caminho(pasta, n)
        if teste and os.path.splitext(teste)[0] == nome:
            return inv.caminho(pasta, teste)
    return ""


def uma(nome, escrever=False):
    alvo = caminho_do_alvo(nome)
    if not alvo or not os.path.isfile(alvo):
        erro("  %s: nao e peca nem teste da maquina (veja o inventario)"
             % nome)
        return False

    t = io.open(alvo, encoding="utf-8", errors="replace").read()
    limpo, trocas = destilar_texto(t)
    resta = sujeira(limpo)

    print("  %-24s %3d troca(s) mecanica(s) | sobraram %d linha(s) privadas"
          % (nome[:24], trocas, len(resta)))
    if resta:
        for n_l, marca, texto in resta[:6]:
            print("       L%-5d [%s] %s" % (n_l, marca, texto[:70]))
        if len(resta) > 6:
            print("       ... e mais %d" % (len(resta) - 6))
        print("       -> NAO publico. Estas linhas sao DECISAO, nao filtro.")
        return False

    if not escrever:
        print("       LIMPA. (--escrever para gravar em publicado/)")
        return True

    os.makedirs(SAIDA, exist_ok=True)
    destino = os.path.join(SAIDA, os.path.basename(alvo))
    io.open(destino, "w", encoding="utf-8", newline=chr(10)).write(limpo)
    print("       PUBLICAVEL: publicado/%s" % os.path.basename(alvo))
    return True


RASCUNHO = os.path.join(SAIDA, "_rascunho")
MARCA = "# >>> PRIVADO["


def rascunho(nome, silencioso=False):
    """Grava a peça com CADA linha privada marcada, para a reescrita humana.

    🔴 O QUE FALTAVA, achado ao tentar usar isto de verdade: o
    destilador só sabia dizer NÃO. Ele media, listava as linhas sujas e parava
    — e não havia caminho nenhum para eu entregar a versão reescrita e ele
    conferir. Um gate que só reprova, sem porta de saída, não é fluxo: é um
    muro. E muro sem porta é o que ensina a contornar por fora, que aqui
    significaria alguém copiando o arquivo na mão para o repo público, sem
    medição nenhuma — exatamente o que o destilador existe para impedir.

    Agora são três passos, e o do meio é humano de propósito:
      1. `--rascunho` marca cada linha que precisa de decisão
      2. gente reescreve, com a régua da amostra: **o número sobrevive, o dono
         sai** (`maquina/EXEMPLO-reescrita-do-cabecalho.py`)
      3. `--conferir` mede o que a gente escreveu e aprova ou reprova

    🔴 E ESTE ERA O QUARTO LUGAR do mesmo defeito de alcance. O
    commit anterior consertou tres varreduras de `inv.PECAS` que liam so a
    coluna do NOME e ignoravam a do TESTE — e deixou esta de fora, porque as
    tres estavam juntas e esta nao. O sintoma apareceu na primeira tentativa
    de usar o fluxo para valer: `--todas` ja listava os 8 testes como alvo, o
    `--conferir` ja os mediria, e `--rascunho testar_inventario` respondia
    *"nao e peca da maquina"*. Ou seja, o fluxo tinha comeco e fim, e nenhum
    meio — exatamente o muro que esta funcao nasceu para derrubar.

    🔑 A licao e sobre consertar por BUSCA, nao por vizinhanca: quando um
    defeito e "varrer a lista lendo so uma coluna", o conserto so termina
    depois de um `grep` por quem mais varre a lista. Agora ha uma porta unica
    — `caminho_do_alvo` — e o proximo lugar que precisar do caminho a chama.
    """
    alvo = caminho_do_alvo(nome)
    if not alvo or not os.path.isfile(alvo):
        if not silencioso:
            print("  %s: nao e peca nem teste da maquina (veja o inventario)"
                  % nome)
        return False
    t = io.open(alvo, encoding="utf-8", errors="replace").read()
    limpo, _trocas = destilar_texto(t)
    marcadas, n_marcas = [], 0
    for l_ in limpo.split(chr(10)):
        achou = ""
        for marca, rx in mp.MARCAS:
            if rx.search(l_):
                achou = marca
                break
        if achou:
            n_marcas += 1
            marcadas.append("%s%s] — reescreva: o numero sobrevive, "
                            "o dono sai" % (MARCA, achou))
        marcadas.append(l_)
    os.makedirs(RASCUNHO, exist_ok=True)
    destino = os.path.join(RASCUNHO, os.path.basename(alvo))
    io.open(destino, "w", encoding="utf-8",
            newline=chr(10)).write(chr(10).join(marcadas))
    if not silencioso:
        print("  %-24s %d linha(s) marcadas -> publicado/_rascunho/%s"
              % (nome[:24], n_marcas, os.path.basename(alvo)))
        print("       regua: maquina/EXEMPLO-reescrita-do-cabecalho.py")
        print("       depois: destilar.py --conferir")
    return True


REESCRITAS = os.path.join(AQUI, "reescritas.json")


def carregar_reescritas(fonte=None):
    """{arquivo: [[de, para], ...]} do disco. Sem o arquivo, ERRO."""
    with io.open(fonte or REESCRITAS, encoding="utf-8") as fh:
        dados = (json.load(fh).get("reescritas") or {})
    if not dados:
        raise ValueError(
            "reescritas.json sem `reescritas`. Sem elas o `--reescrever` "
            "copiaria o rascunho cru para publicado/ e o `--conferir` "
            "reprovaria tudo — barulhento, mas ainda assim errado.")
    return dados


def reescrever(fonte=None):
    """Aplica a reescrita humana (dado) sobre os rascunhos. O passo do meio.

    🔴 POR QUE ISTO EXISTE, e o preco foi pago duas vezes no mesmo dia. A
    reescrita e a unica parte da destilacao que custa julgamento, e era a
    unica que nao tinha onde morar: ela existia so DENTRO do arquivo
    publicado. Regenerar o rascunho — coisa que se faz toda vez que a peca
    interna muda — apagava o trabalho inteiro, em silencio, com cara de
    operacao rotineira. Na segunda vez o conserto veio de um `git show`, e so
    funcionou porque o arquivo ja estava commitado. Sorte nao e mecanismo.

    Agora o fluxo fecha o ciclo e e repetivel:
      1. `--rascunho <peca>`  marca cada linha que precisa de decisao
      2. gente reescreve, com a regua: o numero sobrevive, o dono sai
      3. `--reescrever`       aplica `reescritas.json` sobre os rascunhos
      4. `--conferir`         mede o resultado e aprova ou reprova

    ⚠️ Par que nao casa nem no texto velho nem no novo e AVISADO e conta como
    falha: significa que a peca interna mudou por baixo daquela reescrita.
    Aplicar o resto calado publicaria uma reescrita PARCIAL com cara de
    completa — e a parcial passa no `--conferir` se o pedaco que sobrou nao
    tiver marca de privacidade, que e o pior dos mundos.

    🔴 E O RASCUNHO E REGERADO AQUI, sempre. Sem isto o passo REGREDIA a peca
    publicada: bastava um `_rascunho/` velho para a versao de ontem sobrepor a
    de hoje, em silencio, com cara de operacao rotineira. Aconteceu tres vezes
    num unico dia, e nas tres o `--conferir` pegou depois — o que significa
    que a rede existia e o buraco tambem.

    🔑 Regenerar e seguro justamente porque a reescrita mora no DADO. Era o
    contrario antes: quando ela vivia dentro do arquivo publicado, regenerar
    apagava o trabalho. O conserto de la e o que torna este possivel aqui.
    """
    mapa = carregar_reescritas(fonte)
    for nome in sorted(mapa):
        rascunho(os.path.splitext(nome)[0], silencioso=True)
    if not os.path.isdir(RASCUNHO):
        erro("  _rascunho/ nao existe e nao deu para gerar.")
        return 1
    print("REESCRITA DE %d ARQUIVO(S), a partir do dado" % len(mapa))
    print()
    ruins = 0
    for nome in sorted(mapa):
        rasc = os.path.join(RASCUNHO, nome)
        if not os.path.isfile(rasc):
            print("  %-30s SEM RASCUNHO — pule ou gere" % nome[:30])
            ruins += 1
            continue
        t = chr(10).join(
            l_ for l_ in io.open(rasc, encoding="utf-8").read().split(chr(10))
            if not l_.strip().startswith(MARCA))
        perdidos, n = [], 0
        for de, para in mapa[nome]:
            if de in t:
                t = t.replace(de, para, 1)
                n += 1
            elif para not in t:
                perdidos.append(de.strip().split(chr(10))[0][:58])
        if perdidos:
            ruins += 1
            print("  %-30s %d de %d — %d par(es) PERDIDO(S)"
                  % (nome[:30], n, len(mapa[nome]), len(perdidos)))
            for p in perdidos[:4]:
                print("       nao achei: %s" % p)
            print("       -> a peca interna mudou. Refaca a reescrita destes.")
            continue
        io.open(os.path.join(SAIDA, nome), "w", encoding="utf-8",
                newline=chr(10)).write(t)
        print("  %-30s %d de %d aplicada(s)" % (nome[:30], n, len(mapa[nome])))
    print()
    print("  reescritos: %d de %d" % (len(mapa) - ruins, len(mapa)))
    return 1 if ruins else 0


def defasagem(nome_arquivo):
    """Linhas de CODIGO que a peca interna tem e a publicada nao. [] = em dia.

    🔴 O FURO QUE ISTO FECHA, achado na primeira destilacao real. Eu
    consertei um defeito na peca interna e a versao publicada ficou com o
    defeito, porque ela e uma COPIA tirada num instante — e nada no mundo
    avisava. A D-04 diz *"nunca duas implementacoes"*, e uma copia que apodrece
    em silencio e exatamente duas implementacoes, so que com uma delas
    fingindo ser a mesma.

    ⚠️ A COMPARACAO E SO DO CODIGO, e a primeira versao errou isto. Ela
    comparava toda linha que nao casasse com uma marca de privacidade — e
    acusou 10 linhas de defasagem no `ligar_ci` que eram a MINHA reescrita.
    O motivo e obvio depois de ver: a reescrita e por BLOCO. A marca cai numa
    linha, e o paragrafo inteiro muda junto, inclusive linhas que sozinhas nao
    tinham nada de privado. Detector que compara linha a linha uma coisa que
    se edita por paragrafo acusa trabalho legitimo, e detector que acusa
    trabalho legitimo e desligado na segunda semana.

    A regua certa e mais dura e mais simples: **o CODIGO tem de ser identico;
    a PROSA e o que se destila.** Se o codigo divergir, sao duas
    implementacoes — que e exatamente o que a D-04 proibe. Docstring e
    comentario ficam livres, porque e neles que mora o contexto privado.
    """
    alvo = caminho_do_alvo(os.path.splitext(nome_arquivo)[0])
    if not alvo or not os.path.isfile(alvo):
        return []
    interno, _ = destilar_texto(
        io.open(alvo, encoding="utf-8", errors="replace").read())
    publicado = io.open(os.path.join(SAIDA, nome_arquivo),
                        encoding="utf-8", errors="replace").read()
    fora = []
    for i, l_ in enumerate(so_codigo(interno), 1):
        if l_ not in publicado:
            fora.append((i, l_.strip()[:70]))
    return fora


def so_codigo(texto):
    """As linhas de CODIGO: fora de docstring, sem ser comentario nem vazias.

    O rastreio de docstring e por contagem de aspas triplas, que e simples e
    erra para um lado seguro: na duvida, trata como docstring e NAO compara.
    Comparar de menos deixa passar uma divergencia; comparar de mais reprova
    a destilacao legitima e mata o fluxo. Entre os dois, o segundo e o que faz
    a peca ser desligada.
    """
    linhas, dentro = [], False
    for l_ in texto.split(chr(10)):
        n_aspas = l_.count('"""') + l_.count("'''")
        se_abria = dentro
        if n_aspas % 2:
            dentro = not dentro
        if se_abria or n_aspas:
            continue                      # linha de docstring, ou que a delimita
        nu = l_.strip()
        if not nu or nu.startswith("#") or len(nu) < 8:
            continue
        linhas.append(l_)
    return linhas


# 🔴 A CONFERENCIA SO OLHAVA `.py`, e o buraco apareceu na hora de montar o
# repositorio de verdade: o README, o CI e os arquivos de exemplo foram para
# `publicado/` e NENHUM passou pelo medidor. Um README com nome de cliente
# sairia daqui com o gate verde. E o README e justamente o arquivo que mais
# fala de gente, porque e o unico escrito para gente.
#
# A licao e a de sempre com detector: ele mede o que a lista manda medir, e a
# lista sempre parece completa ate alguem acrescentar um tipo de arquivo.
CONFERIVEIS = {".py", ".md", ".json", ".yml", ".yaml", ".txt", ".toml",
               ".cfg", ".ini", ".sh", ".exemplo", ""}

# ⚠️ ISENTO NAO E PERDAO, e a lista tem de caber numa linha de justificativa
# cada. Isento demais e como o gate morre: um dia alguem acrescenta o arquivo
# que incomoda, e o medidor vira enfeite.
#
# 🔴 UMA ISENCAO JA COBROU O PRECO. Havia aqui um `not f.startswith("EXEMPLO-")`
# — regra por PREFIXO, sem nome e sem motivo escrito. Ela isentava a amostra de
# reescrita, que por natureza mostra o texto ANTES e DEPOIS e portanto cita
# projeto real. Na varredura final sobre o que ia mesmo subir, aquele arquivo
# apareceu com 4 linhas privadas, e o `--conferir` tinha dito 24 de 24. A
# isencao por padrao de nome e pior que a isencao por nome: ela cresce sozinha,
# porque basta batizar o proximo arquivo com o mesmo prefixo. O exemplo mudou
# de endereco para fora de `publicado/`, que era o lugar certo dele desde
# sempre, e a regra por prefixo morreu junto.
ISENTOS = {
    # A licenca MIT EXIGE o nome do titular. Tirar o nome nao e destilar, e
    # invalidar a licenca — e o nome ja e publico por definicao, porque uma
    # licenca sem titular nao licencia nada.
    "LICENSE": "a licenca exige o titular; sem o nome ela nao vale",
    # O formato Keep a Changelog EXIGE a data de cada versao. Changelog sem
    # data nao e changelog: a pergunta que ele responde e "quando isto mudou".
    "CHANGELOG.md": "a data da versao e o formato, nao um incidente",
}


def conferir():
    """Mede o que JA esta em publicado/ — a reescrita humana passa por aqui.

    Ninguem publica por ter reescrito: publica por ter reescrito E medido. A
    conferencia e a mesma do caminho automatico, contra o mesmo medidor, para
    nao existirem duas reguas do que e privado.
    """
    if not os.path.isdir(SAIDA):
        erro("  publicado/ nao existe. Rode `--rascunho <peca>` primeiro.")
        return 1
    alvos = [f for f in sorted(os.listdir(SAIDA))
             if os.path.isfile(os.path.join(SAIDA, f))
             and os.path.splitext(f)[1].lower() in CONFERIVEIS
             and f not in ISENTOS]
    if not alvos:
        print("  publicado/ nao tem peca destilada ainda.")
        return 1
    print("CONFERENCIA DE %d ARQUIVO(S) JA REESCRITOS" % len(alvos))
    print()
    ruins = 0
    for f in alvos:
        t = io.open(os.path.join(SAIDA, f), encoding="utf-8",
                    errors="replace").read()
        resta = sujeira(t)
        # ⚠️ A marca conta so quando e a LINHA INTEIRA, nao a string solta.
        # Achado na primeira conferencia de verdade: o `destilar.py`
        # foi reprovado por si mesmo, porque e ELE quem gera a marca e a
        # string aparece no codigo dele, dentro de aspas. E a mesma familia do
        # arquivo que descreve o defeito e casa com ele proprio — o que os
        # ISENTOS do gate de seguranca resolvem la. Aqui nao precisa de lista
        # de excecao: precisa perguntar a coisa certa, que e se a linha E a
        # marca, e nao se ela CITA a marca.
        sobradas = [i for i, l_ in enumerate(t.split(chr(10)), 1)
                    if l_.strip().startswith(MARCA)]
        for i in sobradas:
            resta.append((i, "marca de rascunho",
                          "sobrou a marca de reescrita — nao terminou"))
        velhas = defasagem(f)
        if resta:
            ruins += 1
            print("  %-26s REPROVA — %d linha(s)" % (f[:26], len(resta)))
            for n_l, marca, texto in resta[:5]:
                print("       L%-5d [%s] %s" % (n_l, marca, texto[:66]))
        elif velhas:
            ruins += 1
            print("  %-26s DEFASADA — %d linha(s) do interno nao estao aqui"
                  % (f[:26], len(velhas)))
            for n_l, texto in velhas[:5]:
                print("       L%-5d %s" % (n_l, texto))
            print("       -> a peca interna mudou depois desta destilacao. "
                  "Refaca: --rascunho e reescreva o que estiver marcado.")
        else:
            print("  %-26s LIMPO — pode ir para o repo publico" % f[:26])
    print()
    print("  aprovados: %d de %d" % (len(alvos) - ruins, len(alvos)))
    return 1 if ruins else 0


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    escrever = "--escrever" in sys.argv
    if "--conferir" in sys.argv:
        return conferir()
    if "--reescrever" in sys.argv:
        return reescrever()
    if "--rascunho" in sys.argv:
        if not args:
            print("  diga qual peca: destilar.py <peca> --rascunho")
            return 1
        return 0 if rascunho(args[0]) else 1
    if "--todas" in sys.argv:
        # Peca E teste. Por muito tempo so a peca entrava aqui, e o resultado era
        # `publicado/` com 7 pecas e zero provas — a metade que pede confianca,
        # sem a metade que a dispensa. A coluna do teste sempre esteve no mapa.
        # Sem repetir: uma suite pode provar DUAS pecas, e isso e legitimo —
        # `testar_destilar` prova o `destilar` e o `medir_privacidade`, e o
        # mapa declara os dois de proposito. Destilar duas vezes o mesmo
        # arquivo so gastaria trabalho e faria o total mentir.
        alvos, vistos = [], set()
        for _cat, n, _pasta, teste, _ in inv.PECAS:
            for a in (n, os.path.splitext(teste)[0] if teste else ""):
                if a and a not in vistos:
                    vistos.add(a)
                    alvos.append(a)
        print("DESTILACAO DE %d ALVOS (%d pecas + os testes delas)"
              % (len(alvos), len(inv.PECAS)))
        print()
        limpas = 0
        for n in alvos:
            if uma(n, escrever):
                limpas += 1
        print()
        print("  prontas para publicar: %d de %d" % (limpas, len(alvos)))
        print("  as demais tem linha que precisa de DECISAO humana.")
        return 0
    if not args:
        print(__doc__)
        return 1
    return 0 if uma(args[0], escrever) else 1


if __name__ == "__main__":
    sys.exit(main())
