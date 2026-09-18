# -*- coding: utf-8 -*-
"""Prova do `destilar.py` — ele publica limpo, ou nao publica.

🔴 POR QUE ESTE ARQUIVO NASCE UM DIA DEPOIS DO DESTILADOR. O `destilar.py`
declarava na propria docstring *"PROVA: maquina/testar_destilar.py, com
mutacao"* — e o arquivo nao existia. O `medir_privacidade.py` declarava a
mesma coisa, e tambem nao. E o mesmo defeito que ja pegamos noutra peca: o
rotulo da prova escrito no codigo, e a prova ausente do disco.

E aqui o erro custa mais caro que nos outros. As outras pecas da maquina, se
falharem, escrevem um arquivo errado no disco DELE. Esta escreve para FORA: o
que ela libera vai para um repositorio publico, e o que vaza nao volta.

O desenho do destilador e o contrario de um sanitizador, e o teste ataca as
duas metades:
  1. ele troca so o MECANICO (caminho de disco), sem julgamento;
  2. ele MEDE a propria saida e recusa publicar se sobrou contexto privado.

A metade 2 e a que importa. Um sanitizador troca o que conhece e publica o
resto — o que ele nao conhecia vaza calado. Entao a mutacao mais importante
aqui e cegar o medidor e exigir que o teste ACUSE: se cegar o medidor nao
muda nada, e porque ele ja nao media.

  0. SANDBOX   - pecas de mentira; as de verdade nao sao tocadas.
  1. DEVE RECUSAR - as familias de contexto privado.
  2. DEVE PUBLICAR - o que esta limpo, e o que a troca mecanica limpa.
  3. MUTACAO
  4. CONTROLE

CHAMADOR: `maquina/inventario.py` (PECAS), rodado pelo bloco [6u].

RODAR: python -B maquina/testar_destilar.py
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
import destilar as ds  # noqa: E402
import inventario as inv  # noqa: E402
import medir_privacidade as mp  # noqa: E402

PASS = 0
FALHA = 0


def marcar(nome, ok, extra=""):
    global PASS, FALHA
    if ok:
        PASS += 1
        print("  PASS  " + nome)
    else:
        FALHA += 1
        print("  FALHA " + nome + ("   " + extra if extra else ""))


# -- 0. SANDBOX --------------------------------------------------------------
SANDBOX = tempfile.mkdtemp(prefix="destilar_teste_")
PUBLICADO_REAL = ds.SAIDA
ANTES_REAL = sorted(os.listdir(PUBLICADO_REAL)) \
    if os.path.isdir(PUBLICADO_REAL) else []

print("== 0. SANDBOX (provado, nao prometido) ==")
marcar("sandbox fora da pasta publicado/ real",
       os.path.normcase(SANDBOX) != os.path.normcase(PUBLICADO_REAL))

PECAS_ORIG = list(inv.PECAS)
SAIDA_ORIG = ds.SAIDA
ds.SAIDA = os.path.join(SANDBOX, "publicado")

# 🔴 AS AMOSTRAS VIRARAM DADO DE MENTIRA, e o motivo e o
# unico que nao tinha saida por reescrita. Um teste de detector de privacidade
# precisa, por construcao, de amostras que o detector ACUSA. Enquanto os nomes
# reais estivessem escritos aqui, este arquivo seria eternamente reprovado por
# si mesmo — a mesma armadilha que tirou os nomes do `medir_privacidade.py`
# antes, so que agora do lado da prova.
#
# O conserto e o mesmo de sempre: o que identifica alguem e DADO,
# nunca constante de codigo. O teste escreve o proprio catalogo, com nomes
# inventados, e mede a MECANICA contra ele. Nada se perde: a secao 2c continua
# medindo o catalogo REAL, com a frase montada a partir do que ela leu do
# disco — e nao a partir do que alguem digitou aqui.
#
# 🔑 De quebra, o teste ficou mais duro. Antes ele dependia de o catalogo real
# ter certas familias e certos nomes; mexer no `privacidade.json` do dono
# quebraria a prova de uma peca que nao mudou. Agora o baseline e dele.
CATALOGO_FALSO = {
    "pessoa_empresa": ["Fulano de Tal", "Empresa Inventada"],
    "projeto_interno": ["Projeto-Alfa", "Projeto-Beta"],
    "caminho_do_disco": [r"C:\\+Users\\+olive", "<CASA>"],
    "incidente_com_data": [r"\b\d{2}/\d{2}(/\d{4})?\b"],
    # A familia do IP usa a regex REAL, copiada do catalogo de verdade, e nao
    # uma simplificacao: e a unica cujo valor esta todo nas EXCECOES (faixa
    # privada, loopback, documentacao). Uma versao simplificada aqui provaria
    # um detector que nao existe.
    "ip_publico": [
        r"\b(?!(?:0|10|127|169\.254|172\.(?:1[6-9]|2\d|3[01])|192\.168"
        r"|192\.0\.2|198\.51\.100|203\.0\.113)\.)(?:\d{1,3}\.){3}\d{1,3}\b"],
    "contato_url": [r"[\w.+-]+@[\w.-]+\.\w+", r"https?://[^\s`\"']+"],
    "trocas_mecanicas": [[r"C:\\+Users\\+olive\\+Projeto", "<PROJETOS>"],
                         [r"C:\\+Users\\+olive", "<CASA>"],
                         ["<PROJETOS>", "<PROJETOS>"],
                         ["<CASA>", "<CASA>"]],
}
FONTE_FALSA = os.path.join(SANDBOX, "privacidade_de_mentira.json")
io.open(FONTE_FALSA, "w", encoding="utf-8").write(
    json.dumps(CATALOGO_FALSO, ensure_ascii=False))

FONTE_REAL = mp.FONTE
mp.MARCAS = mp.carregar_marcas(FONTE_FALSA)
ds.MECANICAS = ds.carregar_mecanicas(FONTE_FALSA)
marcar("o teste roda contra um catalogo de MENTIRA, escrito por ele",
       len(mp.MARCAS) == len(mp._ORDEM) and os.path.isfile(FONTE_FALSA))

PESSOA = CATALOGO_FALSO["pessoa_empresa"][0]
PROJETO = CATALOGO_FALSO["projeto_interno"][0]
DATA = "%02d/%02d" % (6, 9)          # montada, nunca escrita: o detector le data
B = chr(92) * 2                      # a barra dupla do caminho Windows
CASA_FALSA = "C:" + B + "Users" + B + "olive" + B + "Projeto"


def amostra_positiva(*pedacos):
    """Junta uma frase que o detector TEM de acusar. Montada, nao escrita.

    Nao ha outra saida para esta, e vale dizer por que. Uma prova de detector
    precisa de amostra positiva, e amostra positiva e, por definicao, texto
    que o detector acusa. Escrita inteira aqui, ela faria ESTE arquivo ser
    reprovado para sempre — e teste que nao pode ser publicado junto com a
    peca deixa a peca publicada sem prova, que e o buraco que o fluxo de
    destilacao acabou de fechar.

    🔴 A FRONTEIRA, e ela nao se move: isto vale so para texto INVENTADO de
    sandbox. Montar por pedacos um dado REAL para escapar do medidor seria o
    oposto exato do que esta maquina faz, e nenhum gate pegaria — o gate le o
    texto pronto, nunca a intencao de quem o montou.
    """
    return "".join(pedacos)


EMAIL_FALSO = amostra_positiva("alguem", chr(64), "exemplo.com.br")

# O slug de projeto do agente, na forma que carrega um nome de usuario. Vale a
# mesma regra do e-mail: montado, nunca escrito.
SLUG_FALSO = amostra_positiva("C--", "Users-", "fulano", "-Projeto-Alfa")

# Um caminho absoluto Windows de um usuario que nao existe. Montado pela mesma
# razao de sempre: `[A-Z]:\\+Users` e estrutural e acusa qualquer caminho
# desses, inclusive o inventado — que e exatamente o que se quer provar.
_B1 = chr(92)
CAMINHO_FALSO = amostra_positiva(
    "C:", _B1, "Users", _B1, "fulano", _B1, ".claude", _B1, "hooks", _B1,
    "x.py")

# as pecas de mentira, uma por familia do medidor
AMOSTRAS = {
    "limpa": '"""Peca limpa.\n\nMede uma coisa e devolve um numero.\n"""\n'
             'def rodar():\n    return 1\n',
    "so_caminho": '"""Peca com caminho de disco, e SO isso.\n\n'
                  'Ela grava em %s e le de la.\n"""\n'
                  'def rodar():\n    return 2\n' % CASA_FALSA,
    "pessoa": '"""Peca que cita gente.\n\nNasceu de um pedido de %s.\n"""\n'
              'def rodar():\n    return 3\n' % PESSOA,
    "projeto": '"""Peca que cita projeto interno.\n\n'
               'Medido no %s, que tinha o defeito.\n"""\n'
               'def rodar():\n    return 4\n' % PROJETO,
    "data": '"""Peca que cita incidente com data.\n\n'
            'O estrago aconteceu em %s e custou caro.\n"""\n'
            'def rodar():\n    return 5\n' % DATA,
    "contato": '"""Peca com contato.\n\nDuvidas: %s\n"""\n'
               'def rodar():\n    return 6\n' % EMAIL_FALSO,
}

for nome, texto in AMOSTRAS.items():
    io.open(os.path.join(SANDBOX, nome + ".py"), "w",
            encoding="utf-8").write(texto)

# UMA das pecas de mentira declara TESTE, e nenhuma declarava.
# Sem isto o sandbox nao conseguia nem expressar o defeito de alcance: com a
# coluna do teste sempre vazia, ler so a coluna do nome da o mesmo resultado
# que ler as duas, e o teste passa nos dois mundos. Baseline que nao distingue
# o certo do errado nao e baseline.
PROVA_SUJA = "prova_da_limpa.py"
io.open(os.path.join(SANDBOX, PROVA_SUJA), "w", encoding="utf-8").write(
    '"""Prova da peca limpa.\n\nEscrita depois do estrago de %s.\n"""\n'
    'def testar():\n    return 7\n' % DATA)

inv.PECAS = [("teste", nome, SANDBOX,
              PROVA_SUJA if nome == "limpa" else "", "sandbox")
             for nome in AMOSTRAS]
marcar("inventario redirecionado para as %d pecas de mentira" % len(AMOSTRAS),
       len(inv.PECAS) == len(AMOSTRAS))
marcar("   e uma delas declara o teste dela (para medir o ALCANCE)",
       any(t for _c, _n, _p, t, _q in inv.PECAS))


def publica(nome):
    """True se o destilador liberou a peca."""
    return ds.uma(nome, escrever=True)


# -- 1. DEVE RECUSAR ---------------------------------------------------------
print("\n== 1. DEVE RECUSAR (o que vaza nao volta) ==")
for nome, rotulo in (("pessoa", "nome de pessoa"),
                     ("projeto", "nome de projeto interno"),
                     ("data", "incidente com data"),
                     ("contato", "email de contato")):
    liberou = publica(nome)
    marcar("recusa peca com %s" % rotulo, not liberou)
    marcar("   e NAO escreveu o arquivo",
           not os.path.isfile(os.path.join(ds.SAIDA, nome + ".py")))


# -- 2. DEVE PUBLICAR --------------------------------------------------------
print("\n== 2. DEVE PUBLICAR o que esta limpo ==")

marcar("libera a peca limpa", publica("limpa"))
marcar("   e o arquivo existe em publicado/",
       os.path.isfile(os.path.join(ds.SAIDA, "limpa.py")))

marcar("libera a peca cujo unico problema era caminho de disco",
       publica("so_caminho"))
saida = io.open(os.path.join(ds.SAIDA, "so_caminho.py"),
                encoding="utf-8").read() \
    if os.path.isfile(os.path.join(ds.SAIDA, "so_caminho.py")) else ""
marcar("   o caminho virou marcador", "<PROJETOS>" in saida)
marcar("   e o caminho original sumiu da saida",
       bool(saida) and "Users" not in saida and "olive" not in saida)


# -- 2b. O FLUXO DE SAIDA (rascunho -> reescrita -> conferir) ----------------
# Acrescentado no mesmo movimento em que o fluxo nasceu. Ate aqui o
# destilador so sabia dizer NAO: media, listava as linhas sujas e parava, sem
# caminho para entregar a versao reescrita. Gate que so reprova, sem porta de
# saida, e um muro — e muro sem porta ensina a contornar por fora, que aqui
# significaria copiar o arquivo na mao para o repo publico, sem medicao.
print("\n== 2b. O FLUXO DE SAIDA: rascunho -> reescrita -> conferir ==")

RASCUNHO_ORIG = ds.RASCUNHO
ds.RASCUNHO = os.path.join(ds.SAIDA, "_rascunho")

marcar("gera rascunho da peca suja", ds.rascunho("pessoa"))
rasc = os.path.join(ds.RASCUNHO, "pessoa.py")
marcar("   o rascunho existe", os.path.isfile(rasc))
texto_rasc = io.open(rasc, encoding="utf-8").read() if os.path.isfile(rasc) else ""
marcar("   e cada linha privada vem MARCADA para reescrita",
       "# >>> PRIVADO[pessoa/empresa]" in texto_rasc)
marcar("   sem perder o conteudo original",
       "def rodar():" in texto_rasc and "return 3" in texto_rasc)

# a conferencia tem de REPROVAR quem so copiou o rascunho sem reescrever:
# marca de rascunho sobrando e reescrita que nao terminou.
io.open(os.path.join(ds.SAIDA, "pessoa.py"), "w",
        encoding="utf-8").write(texto_rasc)
marcar("a conferencia REPROVA o rascunho copiado sem reescrever",
       ds.conferir() != 0)

# e tem de APROVAR a reescrita de verdade: o numero sobrevive, o dono sai.
io.open(os.path.join(ds.SAIDA, "pessoa.py"), "w", encoding="utf-8").write(
    '"""Peca que cita gente.\n\nNasceu de um pedido de quem opera a casa.\n"""\n'
    'def rodar():\n    return 3\n')
marcar("e APROVA a reescrita que tirou o dono e manteve o resto",
       ds.conferir() == 0)

for f in ("pessoa.py",):
    try:
        os.remove(os.path.join(ds.SAIDA, f))
    except OSError:
        pass
shutil.rmtree(ds.RASCUNHO, ignore_errors=True)


# -- 2d. O ALCANCE: o TESTE da peca tambem passa pelo fluxo ------------------
# O commit anterior consertou tres varreduras de `inv.PECAS`
# que liam so a coluna do NOME — `caminho_do_alvo`, o `--todas` e a defasagem —
# e o `--rascunho` ficou de fora, porque estava noutro ponto do arquivo. O
# resultado era um fluxo com comeco e fim e nenhum meio: `--todas` ja listava
# os 8 testes, `--conferir` ja os mediria, e `--rascunho testar_X` respondia
# "nao e peca da maquina". Publicar peca sem a prova e o que este alcance
# impede, entao ele e medido, nao prometido.
print("\n== 2d. o alcance: o TESTE da peca tambem entra no fluxo ==")

marcar("gera rascunho do TESTE de uma peca, nao so da peca",
       ds.rascunho(os.path.splitext(PROVA_SUJA)[0]))
rasc_t = os.path.join(ds.RASCUNHO, PROVA_SUJA)
marcar("   o rascunho do teste existe", os.path.isfile(rasc_t))
texto_t = io.open(rasc_t, encoding="utf-8").read() \
    if os.path.isfile(rasc_t) else ""
marcar("   com a linha privada marcada",
       "# >>> PRIVADO[incidente com data]" in texto_t)


# -- 2e. A REESCRITA HUMANA E DADO, e sobrevive a regenerar o rascunho -------
# O preco disto foi pago duas vezes antes de virar peca: a reescrita existia
# so DENTRO do arquivo publicado, e regenerar o rascunho — coisa que se faz
# toda vez que a peca interna muda — apagava o trabalho inteiro em silencio,
# com cara de operacao rotineira.
print("\n== 2e. a reescrita e DADO: o rascunho pode ser refeito a vontade ==")

ds.rascunho("pessoa")                       # rascunho limpo, do zero
fonte_re = os.path.join(SANDBOX, "reescritas_de_mentira.json")
io.open(fonte_re, "w", encoding="utf-8").write(json.dumps({"reescritas": {
    "pessoa.py": [["Nasceu de um pedido de %s." % PESSOA,
                   "Nasceu de um pedido de quem opera a casa."]]}},
    ensure_ascii=False))

marcar("aplica a reescrita do dado sobre o rascunho",
       ds.reescrever(fonte_re) == 0)
saida_re = os.path.join(ds.SAIDA, "pessoa.py")
texto_re = io.open(saida_re, encoding="utf-8").read() \
    if os.path.isfile(saida_re) else ""
marcar("   o dono saiu", bool(texto_re) and PESSOA not in texto_re)
marcar("   e o resto sobreviveu",
       "def rodar():" in texto_re and "return 3" in texto_re)
marcar("   sem sobrar marca de rascunho", ds.MARCA not in texto_re)

# o par que nao casa mais e a unica coisa que NAO pode passar calada: a peca
# interna mudou por baixo daquela reescrita, e publicar o resto entregaria uma
# reescrita PARCIAL com cara de completa.
perdido = os.path.join(SANDBOX, "reescritas_perdidas.json")
io.open(perdido, "w", encoding="utf-8").write(json.dumps({"reescritas": {
    "pessoa.py": [["uma frase que nunca existiu neste arquivo", "outra"]]}},
    ensure_ascii=False))
marcar("par que nao casa REPROVA, em vez de aplicar o resto calado",
       ds.reescrever(perdido) != 0)

# 🔴 E O RASCUNHO VELHO NAO PODE REGREDIR O PUBLICADO. Este era o defeito que
# aparecia tres vezes num unico dia: bastava um `_rascunho/` de ontem para o
# `--reescrever` sobrepor a versao de hoje, em silencio. O `--conferir` pegava
# depois, entao a rede existia — e o buraco tambem.
#
# 🔑 O conserto e o `--reescrever` REGENERAR o rascunho antes de aplicar, e
# isso so e seguro porque a reescrita mora no dado (grupo 2e acima). A prova
# e direta: enveneno o rascunho com um texto que a peca interna nao tem, e
# exijo que ele NAO chegue ao publicado.
_veneno = os.path.join(ds.RASCUNHO, "pessoa.py")
io.open(_veneno, "w", encoding="utf-8", newline=chr(10)).write(
    "# RASCUNHO VELHO QUE NAO PODE SUBIR\ndef rodar():\n    return 999\n")
ds.reescrever(fonte_re)
_depois = io.open(os.path.join(ds.SAIDA, "pessoa.py"),
                  encoding="utf-8").read()
marcar("rascunho VELHO nao regride o publicado",
       "RASCUNHO VELHO" not in _depois and "return 999" not in _depois,
       _depois.split(chr(10))[0][:50])
marcar("   e o conteudo certo continua la",
       "return 3" in _depois and PESSOA not in _depois)

vazio_re = os.path.join(SANDBOX, "reescritas_vazias.json")
io.open(vazio_re, "w", encoding="utf-8").write('{"reescritas": {}}')
try:
    ds.carregar_reescritas(vazio_re)
    levantou_re = False
except ValueError:
    levantou_re = True
except Exception:                                           # noqa: BLE001
    levantou_re = False
marcar("arquivo de reescrita vazio levanta erro", levantou_re)

try:
    os.remove(saida_re)
except OSError:
    pass
shutil.rmtree(ds.RASCUNHO, ignore_errors=True)


# -- 2f. A CONFERENCIA OLHA TODO ARQUIVO DE TEXTO, nao so `.py` -------------
# O buraco apareceu na hora de montar o repositorio de verdade: o README, o CI
# e os arquivos de exemplo foram para `publicado/` e NENHUM passou pelo
# medidor. E o README e justamente o arquivo que mais fala de gente, porque e
# o unico escrito para gente.
print("\n== 2f. a conferencia nao para nos `.py` ==")

io.open(os.path.join(ds.SAIDA, "LEIA.md"), "w", encoding="utf-8").write(
    "# Leia\n\nEste projeto nasceu de um pedido de %s.\n" % PESSOA)
marcar("README sujo REPROVA a conferencia", ds.conferir() != 0)

io.open(os.path.join(ds.SAIDA, "LEIA.md"), "w", encoding="utf-8").write(
    "# Leia\n\nEste projeto nasceu de um pedido de quem opera a casa.\n")
marcar("   e o mesmo README limpo passa", ds.conferir() == 0)

# O isento existe, e por isso mesmo tem de ser NOMEADO e estreito: a licenca
# MIT exige o titular, e tirar o nome dela nao e destilar, e invalidar a
# licenca. Qualquer outro arquivo com o mesmo conteudo continua reprovando.
io.open(os.path.join(ds.SAIDA, "LICENSE"), "w", encoding="utf-8").write(
    "MIT License\n\nCopyright (c) 2026 %s\n" % PESSOA)
marcar("o isento declarado (LICENSE) nao derruba a conferencia",
       ds.conferir() == 0)

io.open(os.path.join(ds.SAIDA, "LICENCA.md"), "w", encoding="utf-8").write(
    "MIT License\n\nCopyright (c) 2026 %s\n" % PESSOA)
marcar("   mas o MESMO texto com outro nome REPROVA (isento nao e perdao)",
       ds.conferir() != 0)

for f in ("LEIA.md", "LICENSE", "LICENCA.md"):
    try:
        os.remove(os.path.join(ds.SAIDA, f))
    except OSError:
        pass


# -- 2c. A FONTE DOS NOMES E DADO, E ELA FALHA ALTO --------------------------
# Os nomes sairam do codigo para o catalogo de privacidade, porque ao destilar
# esta propria peca ela foi REPROVADA pelo seu detector — a lista de nomes
# privados era o conteudo privado. O risco novo que isso cria e obvio e e o
# unico que nao se descobre depois: se o JSON sumir ou vier vazio e a peca cair
# para uma lista vazia, ela aprova TUDO em silencio, e o que vazou ja vazou.
# Entao a regra e falhar alto, e e isto que se prova aqui.
print("\n== 2c. a fonte dos nomes e DADO, e some-la e ERRO, nao lista vazia ==")

# O catalogo REAL entra aqui, e SO aqui. O resto do arquivo mede a mecanica
# contra o de mentira; esta secao mede que o de verdade carrega e morde. A
# frase suja e MONTADA com o que se leu do disco — escrever um nome real aqui
# so para provar que o detector o pega seria plantar no codigo exatamente o
# que o detector existe para impedir.
REAIS = mp.carregar_marcas(FONTE_REAL)
# ⚠️ O NUMERO SAI DA FONTE, e nao da minha memoria. Esta linha e a de cima
# diziam `== 5`, escrito a mao, e as duas envelheceram no dia em que nasceu a
# 6a familia. Contra `_ORDEM`, que e quem define as familias, elas nao
# envelhecem mais.
marcar("as %d familias carregam do JSON real" % len(REAIS),
       len(REAIS) == len(mp._ORDEM))

# E cada familia MORDE alguma coisa. Contar familia carregada nao prova
# deteccao: um grupo com regex que nao casa nada passaria na contagem e
# aprovaria a familia inteira em silencio.
# O IP e MONTADO, pelo mesmo motivo das outras amostras positivas: escrito
# inteiro, ele faria este arquivo ser reprovado pelo detector que ele prova.
# O valor e o resolvedor publico mais conhecido do mundo, um digito repetido
# quatro vezes, que nao identifica a maquina de ninguem.
#
# 🔑 E a primeira versao DESTE comentario escrevia o endereco por extenso para
# explicar a montagem — e foi reprovada. O detector nao le intencao: ele le o
# texto, e o texto tinha o IP. Explicar por que nao se escreve uma coisa nao e
# licenca para escreve-la.
IP_FALSO = amostra_positiva(*".".join("8888"))
AMOSTRAS_POR_FAMILIA = {
    "ip publico": "o servidor responde em %s desde ontem" % IP_FALSO,
    "incidente com data": "o estrago foi em %s" % ("%02d/%02d" % (6, 9)),
    "contato/URL": amostra_positiva("fulano", chr(64), "exemplo.com.br"),
}
for familia, amostra in sorted(AMOSTRAS_POR_FAMILIA.items()):
    pegou = [n for n, rx in REAIS if rx.search(amostra) and n == familia]
    marcar("   a familia `%s` morde de verdade" % familia, bool(pegou))

# 🔑 E o caso que originou a familia do IP: ele passava por ACIDENTE. O `root@`
# fazia a regex de e-mail casar, entao a linha era acusada — mas por outro
# motivo. Sem usuario na frente, o mesmo IP passava limpo. Gate que acerta por
# coincidencia acerta so enquanto a coincidencia durar.
so_ip = "ping %s -c 1" % IP_FALSO
por_ip = [n for n, rx in REAIS if rx.search(so_ip)]
marcar("   IP SEM usuario na frente e pego (era o furo)",
       "ip publico" in por_ip, str(por_ip))

# -- O detector de CAMINHO, nos dois sentidos -------------------------------
# 🔴 Duas mudancas, e as duas vieram de preparar uma porta para publicacao:
#   · saiu `~/.claude`, que nao identifica ninguem (e o diretorio do agente em
#     qualquer maquina) e e o ALVO do gate do Bash — os casos de teste dele
#     precisam cita-lo pelo nome, e um detector que reprova o alvo do proprio
#     gate torna a peca impublicavel por um motivo que nao e privacidade;
#   · entrou o slug de projeto do agente, que carrega o nome do usuario do
#     disco e passava limpo por TODOS os detectores. Nao chegou a vazar, mas
#     so porque as portas ainda nao tinham sido publicadas.
#
# 🔑 Os dois sentidos importam igualmente, e e por isso que a lista tem casos
# que DEVEM passar. Detector medido so pelo que ele pega vira pedra no
# caminho, e pedra no caminho e desligada.
# ⚠️ OS CAMINHOS USAM UM USUARIO FICTICIO, e nao o desta casa, por DOIS
# motivos que so aparecem juntos ao rodar isto fora daqui:
#   · com o nome real, a TROCA MECANICA os reescreve antes do detector ver: o
#     caminho vira um marcador, e marcador nao e caminho, entao o caso "deve
#     pegar" falha na versao publicada. E o mesmo defeito que ja fez o
#     `destilar.py` corromper as proprias regex;
#   · e o nome real dentro de um caso de teste e, ele proprio, o dado que o
#     detector procura.
#
# 🔑 E saiu daqui o caso do caminho POSIX (`/c/Users/<nome>`): aquele padrao
# depende de o NOME estar no catalogo, entao ele so passava nesta casa. Teste
# que so passa numa maquina nao mede o detector, mede a maquina.
CAMINHOS = [
    (CAMINHO_FALSO, True, "absoluto Windows"),
    # ⚠️ O slug e FICTICIO e ainda assim MONTADO, e as duas coisas por motivos
    # diferentes. Ficticio porque o que se prova e o PADRAO, nao o nome desta
    # casa. Montado porque amostra positiva, por definicao, casa o detector:
    # escrita inteira, ela reprovaria o arquivo que prova o detector.
    (SLUG_FALSO, True, "o slug (era o furo)"),
    ("~/.claude/projects/" + SLUG_FALSO, True, "slug dentro de ~"),
    ("~/.claude/hooks/", False, "generico: toda maquina tem"),
    ("git -C ~/.claude " + "reset --hard", False, "o alvo do gate do Bash"),
    ("~/Projeto/Alfa", False, "sem usuario no caminho"),
]
for txt, deve, porque in CAMINHOS:
    pego = bool([n for n, rx in REAIS
                 if rx.search(txt) and n == "caminho do disco"])
    marcar("   caminho %s: %s" % ("PEGO" if deve else "livre", porque),
           pego == deve, txt[:46])

# E as faixas que nao identificam ninguem NAO sao acusadas: rede privada,
# loopback e a faixa de documentacao da RFC 5737. Detector que reprova o
# exemplo correto e desligado na segunda semana.
for limpo in (amostra_positiva("http", "://", "192.168.0.10:8080"),
              "127.0.0.1", "203.0.113.7", "a versao 1.2.3 do pacote"):
    acusou = [n for n, rx in REAIS if rx.search(limpo) and n == "ip publico"]
    marcar("   nao acusa `%s`" % limpo[:24], not acusou)

catalogo_real = json.load(io.open(FONTE_REAL, encoding="utf-8"))


def termo_literal(grupo):
    """O 1o termo do grupo que seja texto puro, sem metacaractere de regex."""
    for p in catalogo_real.get(grupo) or []:
        if not [c for c in p if c in "\\[](){}?*+|^$."]:
            return p
    return ""


frase_suja = "Nasceu de um pedido de %s no %s em %s." % (
    termo_literal("pessoa_empresa"), termo_literal("projeto_interno"),
    "%02d/%02d" % (6, 9))
marcar("   e o que carregou de fato detecta",
       len([n for n, rx in REAIS if rx.search(frase_suja)]) >= 3)
marcar("   sem acusar frase limpa",
       not [n for n, rx in REAIS if rx.search("Mede e devolve um numero.")])

# 🔴 O `.exemplo` TEM DE CARREGAR, e este caso nasceu de ele nao carregar. Ao
# acrescentar a familia do IP ao catalogo real, esqueci o `.exemplo` publicado
# — e quem baixasse o repositorio receberia um arquivo que faz a peca levantar
# na importacao. Exemplo que nao roda e documentacao errada com cara de certa,
# e o pior tipo: quem baixa conclui que a peca esta quebrada.
#
# 🔑 O CI pegou. Mas depender do CI para isso e depender de alguem ler o CI:
# aqui a mesma pergunta e feita na suite, que roda antes.
#   · na casa ele mora em `publicado/`, porque so nasce na destilacao;
#   · no repositorio publicado ele mora ao lado da peca, porque la nao ha
#     `publicado/`. Procurar nos dois e o que faz esta checagem valer nos dois
#     mundos — e era no segundo que o defeito estava.
_NOME_EX = os.path.basename(mp.FONTE) + ".exemplo"
EXEMPLO = ""
for _cand in (os.path.join(SAIDA_ORIG, _NOME_EX),
              os.path.join(AQUI, _NOME_EX)):
    if os.path.isfile(_cand):
        EXEMPLO = _cand
        break
if EXEMPLO:
    try:
        do_exemplo = mp.carregar_marcas(EXEMPLO)
        erro_ex = ""
    except Exception as e:                                  # noqa: BLE001
        do_exemplo, erro_ex = [], "%s: %s" % (type(e).__name__, e)
    marcar("o `privacidade.json.exemplo` publicado CARREGA",
           len(do_exemplo) == len(mp._ORDEM), erro_ex or str(len(do_exemplo)))
else:
    # Dito na cara: o exemplo mora em `publicado/`, e ele so existe depois da
    # primeira destilacao. Silencio aqui esconderia a checagem mais util.
    print("  (nao medido: `%s` nao existe em publicado/ nem ao lado da peca)"
          % _NOME_EX)

# -- O QUE JA E PUBLICO POR DECISAO -----------------------------------------
# 🔴 Os arquivos de governanca do repositorio publico (README, CHANGELOG,
# SECURITY, CODE_OF_CONDUCT) foram TODOS reprovados pelo detector, e sempre
# pelo mesmo motivo: eles citam a URL do proprio repositorio, e ela carrega o
# nome da conta.
#
# A saida errada seria isentar os arquivos inteiros. O README e justamente o
# que mais fala de gente: isenta-lo deixaria passar um nome de cliente escrito
# ali, que e o caso que mais importa pegar. Entao o recorte e por STRING.
#
# 🔑 Este grupo mede os DOIS lados, e o segundo e o que impede a isencao de
# virar buraco: a linha publica deixa de acusar, E uma linha com nome novo
# continua acusando mesmo estando ao lado da URL publica.
print("\n== 2g. o publico declarado recorta por STRING, nao por arquivo ==")

# A URL de exemplo e MONTADA, pela mesma razao das outras amostras positivas:
# escrita inteira, ela reprovaria o arquivo que prova o filtro.
URL_FALSA = amostra_positiva("github", ".com/alguem/projeto-publico")
HTTPS = amostra_positiva("http", "s://")
PUB_FALSO = [URL_FALSA, "img.shields.io"]
_linha_pub = "[![ci](%s%s/x.yml)](%s%s)" % (HTTPS, URL_FALSA, HTTPS, URL_FALSA)
marcar("a URL declarada publica deixa de acusar",
       not [n for n, rx in REAIS
            if rx.search(mp.limpa_publicos(_linha_pub, PUB_FALSO))])

# ⚠️ O token INTEIRO sai, nao so a string. A 1a versao trocava o pedaco por
# vazio e sobrava um esqueleto de URL, que continua casando a regex. Meio
# conserto produzia o falso positivo que ele existia para tirar.
marcar("   e o que sobra nao e um esqueleto de URL",
       HTTPS not in mp.limpa_publicos(_linha_pub, PUB_FALSO),
       repr(mp.limpa_publicos(_linha_pub, PUB_FALSO)[:50]))

# O LADO QUE IMPEDE O BURACO: nome novo ao lado da URL publica continua pego.
_linha_mista = "veja em %s%s o caso de %s" % (
    HTTPS, URL_FALSA, termo_literal("pessoa_empresa"))
marcar("nome NOVO na mesma linha da URL publica CONTINUA acusando",
       bool([n for n, rx in REAIS
             if rx.search(mp.limpa_publicos(_linha_mista, PUB_FALSO))
             and n == "pessoa/empresa"]))

# E lista vazia e valida: quem nao declara nada publico nao perde deteccao.
marcar("sem nada declarado, o texto passa inteiro pelo detector",
       mp.limpa_publicos(_linha_pub, []) == _linha_pub)

# -- 2h. A FORMA publica isenta UMA LINHA, e nao pode virar um portao -------
# 🔴 Este grupo existe porque a isencao por FORMA e a mais perigosa das tres.
# Um padrao frouxo aqui nao isenta uma linha: DESLIGA o detector para todo
# mundo, e o sintoma e um relatorio verde — nunca um erro. Entao a prova mede
# os dois lados, e o segundo pesa mais que o primeiro.
print("\n== 2h. a forma publica isenta a LINHA, nunca o arquivo ==")

# As datas sao MONTADAS, pela mesma razao das outras amostras deste arquivo: a
# marca `incidente com data` acusa qualquer data escrita inteira, e este teste
# precisa justamente de datas para provar a forma. Escritas, elas reprovariam
# o arquivo que as usa.
ISO = amostra_positiva("20", "26", "-09-", "18")
DDMM = amostra_positiva("18", "/", "09")

marcar("o cabecalho de versao do Keep a Changelog e estrutura",
       mp.e_estrutura("## [0.1.0] - %s" % ISO))
marcar("   e o rodape de link da versao tambem",
       mp.e_estrutura("[0.1.0]: %s%s/releases/tag/v0.1.0" % (HTTPS, URL_FALSA)))
marcar("   e `[Unreleased]` tambem, que e o topo de todo changelog",
       mp.e_estrutura("## [Unreleased]"))

# ⚠️ OS QUATRO LADOS QUE IMPEDEM O BURACO. Cada um e uma forma de escrever a
# mesma data que a forma NAO pode aceitar, porque ai ela deixaria de ser
# estrutura e viraria uma licenca para contar incidente.
_prosa = "## [0.1.0] - %s %s quebrou no cliente" % (ISO, chr(0x2014))
marcar("cabecalho com PROSA depois da data NAO e estrutura",
       not mp.e_estrutura(_prosa))
marcar("   e continua acusando a data que ele carrega",
       bool(mp.marcas_da_linha(_prosa, marcas=REAIS)))
_solta = "achado em %s pela checagem do inventario" % DDMM
marcar("uma data solta em prosa NAO e estrutura",
       not mp.e_estrutura(_solta))
marcar("   e continua acusando",
       bool(mp.marcas_da_linha(_solta, marcas=REAIS)))
marcar("linha que so PARECE cabecalho (sem colchete) nao e estrutura",
       not mp.e_estrutura("## 0.1.0 - %s" % ISO))

# O lado que mais importa: nome de pessoa dentro de algo com cara de
# cabecalho continua sendo pego, porque a forma exige a linha INTEIRA.
_falso_cabecalho = "## [0.1.0] - %s %s" % (ISO,
                                           termo_literal("pessoa_empresa"))
marcar("nome de pessoa colado num cabecalho CONTINUA acusando",
       "pessoa/empresa" in mp.marcas_da_linha(_falso_cabecalho,
                                             marcas=REAIS),
       str(mp.marcas_da_linha(_falso_cabecalho, marcas=REAIS)))

# E o dado pode ser vazio: quem nao declara forma nenhuma nao perde deteccao.
marcar("sem forma declarada, tudo volta a ser conferido",
       not mp.e_estrutura("## [0.1.0] - %s" % ISO, formas=[]))

sem_arquivo = os.path.join(SANDBOX, "nao_existe.json")
try:
    mp.carregar_marcas(sem_arquivo)
    levantou = False
except Exception:                                           # noqa: BLE001
    levantou = True
marcar("SEM o arquivo, levanta erro (nao devolve lista vazia)", levantou)

# -- 2i. O `.exemplo` TEM DE ENSINAR A MESMA COISA QUE O REAL ---------------
# 🔴 ESTE GRUPO NASCEU DE DOIS DEFEITOS QUE SO APARECERAM FORA DE CASA. O
# `privacidade.json.exemplo` estava sem `publico_declarado` e sem
# `forma_publica`. Aqui tudo passava, porque aqui o arquivo real esta
# completo. Quem baixasse o repositorio teria o detector acusando toda URL de
# governanca e todo cabecalho de changelog — e leria isso como "o detector e
# barulhento", nunca como "faltou um pedaco do dado".
#
# 🔑 Exemplo incompleto e documentacao errada com cara de certa, e o custo
# cai inteiro em quem clonou. Entao a pergunta e feita aqui: as CHAVES do
# exemplo e do real tem de bater. Os VALORES podem e devem diferir — um e o
# dado desta casa, o outro e o ponto de partida de outra.
print("\n== 2i. o `.exemplo` ensina a mesma coisa que o real ==")

# ⚠️ E O PROPRIO GUARDIAO NASCEU COM O DEFEITO QUE ELE PEGA. A primeira versao
# procurava o `.exemplo` so em `publicado/`, que e o arranjo DESTA casa — e
# reprovava em todo clone, onde o exemplo ja mora ao lado do real. Esta lista
# de lugares e o conserto, e fica escrita porque a licao se repete: peca que
# viaja nao pode conhecer um endereco so.
PARES = ["privacidade.json", "mapa.json", "publicar_isentos.json"]
for _real in PARES:
    cr = os.path.join(AQUI, _real)
    ce = ([c for c in (os.path.join(AQUI, "publicado", _real + ".exemplo"),
                       os.path.join(AQUI, _real + ".exemplo"))
           if os.path.isfile(c)] or [""])[0]
    if not (os.path.isfile(cr) and ce):
        marcar("o par %s existe num dos arranjos" % _real, False,
               "real=%s exemplo=%s" % (os.path.isfile(cr), bool(ce)))
        continue
    kr = set(json.load(io.open(cr, encoding="utf-8")))
    ke = set(json.load(io.open(ce, encoding="utf-8")))
    marcar("`%s` ensina as mesmas chaves do real"
           % os.path.basename(ce),
           kr == ke,
           "falta no exemplo: %s | sobra: %s"
           % (sorted(kr - ke) or "-", sorted(ke - kr) or "-"))

# -- 2j. O CATALOGO DE EXEMPLO NAO PODE ACUSAR O QUE VAI PUBLICADO ----------
# 🔴 O DETECTOR ESTAVA MEDINDO A SI MESMO, e quem mostrou foi o CI. O
# `privacidade.json.exemplo` trazia `Fulano`, `Projeto-Alfa` e `Projeto-Beta`
# como termos de exemplo, e os testes usam exatamente esses nomes como
# amostras que o detector TEM de acusar.
#
# Rodando com o catalogo de exemplo — que e o que o CI faz e o que quem clona
# faz — o repositorio reprovava a si mesmo, em dois arquivos, com um motivo
# que parece vazamento e nao e.
#
# 🔑 Sao dois papeis, e eles nao podem compartilhar vocabulario:
#    · o `.exemplo` ensina a FORMA do dado a quem clona
#    · o teste precisa de texto que o detector acuse
# Onde os dois se encostam, o repositorio acusa a propria prova.
print("\n== 2j. o catalogo de exemplo nao acusa o que vai publicado ==")

_ex_priv = ([c for c in (os.path.join(AQUI, "publicado",
                                      "privacidade.json.exemplo"),
                         os.path.join(AQUI, "privacidade.json.exemplo"))
             if os.path.isfile(c)] or [""])[0]
if not _ex_priv:
    marcar("o catalogo de exemplo existe no disco", False)
else:
    # ⚠️ SO AS FAMILIAS DE IDENTIDADE, e o recorte e deliberado. A familia
    # `contato/URL` acusaria a URL do proprio repositorio, que os arquivos de
    # governanca citam por dever de oficio — e a URL nao pode entrar no
    # `.exemplo`, porque ali ela seria dado da casa. Quem cuida dela e o
    # `antes_de_publicar` com o catalogo real, e o CI, que acrescenta a URL do
    # repositorio ao dado antes de medir. O alvo AQUI e outro: colisao de
    # VOCABULARIO entre o exemplo e as amostras dos testes.
    IDENTIDADE = ("pessoa/empresa", "projeto interno", "caminho do disco")
    DO_EXEMPLO = [(n, rx) for n, rx in mp.carregar_marcas(_ex_priv)
                  if n in IDENTIDADE]
    PUB_EX = mp.carregar_publicos(_ex_priv)
    FORM_EX = mp.carregar_formas(_ex_priv)
    _pasta = os.path.dirname(_ex_priv)
    # O proprio catalogo se acusa, e nao ha como nao: ele E a lista do que
    # procura. Isento por NOME, com o motivo nesta linha.
    _isento = os.path.basename(_ex_priv)
    _sujos = []
    for _nome in sorted(os.listdir(_pasta)):
        if _nome == _isento or not _nome.endswith((".py", ".exemplo", ".md")):
            continue
        _cam = os.path.join(_pasta, _nome)
        if not os.path.isfile(_cam):
            continue
        _t = io.open(_cam, encoding="utf-8", errors="replace").read()
        _n, _sujas, _ = mp.medir_texto(_t, publicos=PUB_EX, marcas=DO_EXEMPLO,
                                       formas=FORM_EX)
        if _sujas:
            _sujos.append("%s(%d)" % (_nome, len(_sujas)))
    marcar("nenhum arquivo publicado e acusado pelo catalogo de EXEMPLO",
           not _sujos, str(_sujos))

    # E o outro lado, que impede a checagem de virar decoracao: se o catalogo
    # de exemplo nao acusa NADA em lugar nenhum, ele nao esta armado.
    _amostra = ("o %s trabalhou no %s"
                % (mp.carregar_marcas(_ex_priv) and
                   json.load(io.open(_ex_priv,
                                     encoding="utf-8"))["pessoa_empresa"][0],
                   json.load(io.open(_ex_priv,
                                     encoding="utf-8"))["projeto_interno"][0]))
    marcar("   e o catalogo de exemplo ACUSA quando ha o que acusar",
           len(mp.marcas_da_linha(_amostra, publicos=PUB_EX,
                                  marcas=DO_EXEMPLO, formas=FORM_EX)) == 2,
           str(mp.marcas_da_linha(_amostra, publicos=PUB_EX,
                                  marcas=DO_EXEMPLO, formas=FORM_EX)))

    # 🔴 O LADO QUE FECHA O BURACO DA ISENCAO. O `privacidade.json.exemplo`
    # e isento no gate do push, porque ele contem, por definicao, o
    # vocabulario que procura. Isento que ninguem mede e buraco — entao a
    # pergunta que sobra e a unica que importa: o exemplo nao pode carregar
    # nenhum termo do catalogo REAL desta casa.
    #
    # ⚠️ Se isso acontecer, o vazamento sai pela porta da frente: um arquivo
    # que o gate foi instruido a nao olhar, com o nome de um cliente dentro.
    #
    # ⚠️ E SO HA O QUE COMPARAR ONDE EXISTEM DOIS CATALOGOS. No repositorio
    # publicado o `privacidade.json` NASCE do `.exemplo`, entao os dois sao o
    # mesmo texto e a checagem se compararia consigo mesma — acusando sempre,
    # sem nenhum defeito existir. Foi erro meu, pego rodando o repositorio
    # montado: a quarta vez no dia em que uma peca assumiu o arranjo da casa.
    # A comparacao e das FAMILIAS DE IDENTIDADE, e cheguei aqui por duas
    # tentativas erradas. Comparar CAMINHO nao serve: no repositorio publicado
    # os dois sao arquivos distintos, um copia do outro. Comparar o TEXTO
    # inteiro tambem nao: o CI acrescenta a URL do repositorio ao
    # `publico_declarado`, e o texto passa a diferir sem que nada de identidade
    # tenha mudado.
    #
    # 🔑 O que decide e se os dois catalogos dizem coisas diferentes sobre
    # QUEM. Se dizem o mesmo, um nasceu do outro e nao ha o que comparar.
    _so_ident = ("pessoa_empresa", "projeto_interno", "caminho_do_disco")
    _d_ex = json.load(io.open(_ex_priv, encoding="utf-8"))
    _d_real = json.load(io.open(mp.FONTE, encoding="utf-8"))
    _mesmo_texto = all(_d_ex.get(k) == _d_real.get(k) for k in _so_ident)
    if _mesmo_texto:
        print("  (pulado: aqui o catalogo real NASCE do exemplo, entao sao o")
        print("   mesmo texto. A comparacao se faz na casa, que tem os dois.)")
    else:
        _ex_texto = io.open(_ex_priv, encoding="utf-8",
                            errors="replace").read()
        _achou = []
        for _nome_m, _rx in REAIS:
            for _l in _ex_texto.split(chr(10)):
                if _rx.search(mp.limpa_publicos(_l, PUB_EX)):
                    _achou.append("%s: %s" % (_nome_m, _l.strip()[:50]))
                    break
        marcar("o EXEMPLO nao carrega nenhum termo do catalogo real",
               not _achou, str(_achou[:3]))

vazio = os.path.join(SANDBOX, "vazio.json")
io.open(vazio, "w", encoding="utf-8").write(
    '{"pessoa_empresa": [], "projeto_interno": ["X"], '
    '"caminho_do_disco": ["Y"], "incidente_com_data": ["Z"], '
    '"contato_url": ["W"]}')
try:
    mp.carregar_marcas(vazio)
    levantou2 = False
except ValueError:
    levantou2 = True
except Exception:                                           # noqa: BLE001
    levantou2 = False
marcar("com UM grupo vazio, levanta erro nomeando o grupo", levantou2)

# E O CODIGO DAS PECAS, agora sem os nomes, passa no detector REAL.
#
# ⚠️ A pergunta mudou, e a antiga era fraca de um jeito que
# so se ve depois: ela conferia uma lista de 5 nomes ESCRITOS AQUI. Isto e
# frageis por dois lados ao mesmo tempo — a lista envelhece calada quando o
# catalogo ganha um nome, e ela propria planta no teste os nomes que o teste
# diz nao dever existir. Agora a pergunta e feita ao detector de verdade,
# sobre o CODIGO de verdade, e nenhum nome e digitado.
#
# A comparacao e so do CODIGO (`ds.so_codigo`), de proposito: docstring e
# comentario PODEM citar exemplo, porque e neles que mora o contexto e e
# exatamente isso que o destilador reescreve. O que nao pode e o nome estar
# na LOGICA — foi de la que ele saiu hoje de manha.
for peca in ("medir_privacidade.py", "destilar.py", "o_basico.py"):
    fonte_peca = chr(10).join(ds.so_codigo(
        io.open(os.path.join(AQUI, peca), encoding="utf-8").read()))
    sujos = sorted({n for n, rx in REAIS if rx.search(fonte_peca)
                    and n in ("pessoa/empresa", "projeto interno")})
    marcar("nenhum nome real na LOGICA de %s" % peca,
           not sujos, "(familias ainda la: %s)" % sujos)


# -- 3. MUTACAO --------------------------------------------------------------
print("\n== 3. MUTACAO ==")

if FALHA:
    print("  PULADA - a secao 1/2 teve %d falha(s): baseline morto." % FALHA)
    print("\n=== RESULTADO: %d PASS / %d FALHA / mutacao NAO AVALIADA ==="
          % (PASS, FALHA))
    inv.PECAS = PECAS_ORIG
    ds.SAIDA = SAIDA_ORIG
    shutil.rmtree(SANDBOX, ignore_errors=True)
    sys.exit(1)

MARCAS_ORIG = list(mp.MARCAS)
MECANICAS_ORIG = list(ds.MECANICAS)
SUJEIRA_ORIG = ds.sujeira
CAMINHO_ORIG = ds.caminho_do_alvo


def limpar_saida():
    if os.path.isdir(ds.SAIDA):
        shutil.rmtree(ds.SAIDA, ignore_errors=True)


def restaurar():
    mp.MARCAS = list(MARCAS_ORIG)
    ds.MECANICAS = list(MECANICAS_ORIG)
    ds.sujeira = SUJEIRA_ORIG
    ds.caminho_do_alvo = CAMINHO_ORIG


def mut_medidor_cego():
    mp.MARCAS = []


def mut_sujeira_sempre_vazia():
    ds.sujeira = lambda t: []


def mut_sem_trocas_mecanicas():
    ds.MECANICAS = []


def mut_alcance_so_da_peca():
    """O defeito original: varrer a lista lendo SO a coluna do nome."""
    def so_a_peca(nome):
        for _cat, n, pasta, _teste, _ in inv.PECAS:
            if n == nome:
                return inv.caminho(pasta, n)
        return ""
    ds.caminho_do_alvo = so_a_peca


MUTACOES = [
    ("o medidor de privacidade fica cego",
     "e o modo de falha do sanitizador: troca o que conhece, publica o resto, "
     "e o que ele nao conhecia vaza calado",
     mut_medidor_cego,
     lambda: all(publica(n) for n in ("pessoa", "projeto", "data", "contato")),
     "as 4 pecas SUJAS passam a ser publicadas"),
    ("o coletor de sujeira sempre devolve lista vazia",
     "o gate roda, nao ve nada, e libera tudo com a maior conviccao",
     mut_sujeira_sempre_vazia,
     lambda: all(publica(n) for n in ("pessoa", "projeto")),
     "as pecas sujas passam a ser publicadas"),
    ("as trocas mecanicas sao removidas (mutacao inversa)",
     "prova que a troca de caminho esta viva: sem ela, a peca que so tinha "
     "caminho de disco passa a ser RECUSADA",
     mut_sem_trocas_mecanicas,
     lambda: not publica("so_caminho"),
     "a peca so_caminho passa a ser recusada"),
    ("o alcance volta a ler so a coluna do NOME (mutacao inversa)",
     "e o defeito que deixava publicar peca SEM a prova dela: o teste some do "
     "fluxo e ninguem percebe, porque o que falta nao aparece em lugar nenhum",
     mut_alcance_so_da_peca,
     lambda: not ds.rascunho(os.path.splitext(PROVA_SUJA)[0]),
     "o TESTE deixa de ser alcancavel pelo rascunho"),
]

sobreviveram = []
for nome, porque, aplicar, verificar, esperado in MUTACOES:
    restaurar()
    limpar_saida()
    aplicar()
    try:
        detectada = bool(verificar())
    except Exception as e:                                  # noqa: BLE001
        detectada = False
        porque += "  (erro: %s)" % type(e).__name__
    if not detectada:
        sobreviveram.append(nome)
    print("  [%s] %s" % ("DETECTADA" if detectada else "SOBREVIVEU", nome))
    print("           " + porque)
    print("           esperado: %s" % esperado)
restaurar()
limpar_saida()


# -- 4. CONTROLE -------------------------------------------------------------
print("\n== 4. controle: restaurado, o veredito volta ==")
for nome in ("pessoa", "projeto", "data", "contato"):
    marcar("controle: %s volta a ser recusada" % nome, not publica(nome))
marcar("controle: a peca limpa volta a ser liberada", publica("limpa"))


# -- fim ---------------------------------------------------------------------
print("\n== prova final: a pasta publicado/ real nao foi tocada ==")
inv.PECAS = PECAS_ORIG
ds.SAIDA = SAIDA_ORIG
ds.RASCUNHO = RASCUNHO_ORIG
depois_real = sorted(os.listdir(PUBLICADO_REAL)) \
    if os.path.isdir(PUBLICADO_REAL) else []
marcar("publicado/ real tem exatamente os mesmos arquivos",
       depois_real == ANTES_REAL,
       "(antes=%s, depois=%s)" % (ANTES_REAL, depois_real))

shutil.rmtree(SANDBOX, ignore_errors=True)

print("\n=== RESULTADO: %d PASS / %d FALHA / %d mutacao(oes) sobreviveram ==="
      % (PASS, FALHA, len(sobreviveram)))
for nome in sobreviveram:
    print("   mutacao nao detectada: " + nome)
sys.exit(1 if (FALHA or sobreviveram) else 0)
