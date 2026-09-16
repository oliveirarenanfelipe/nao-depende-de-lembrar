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
except Exception:                                           # noqa: BLE001
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import destilar as ds                                       # noqa: E402
import inventario as inv                                    # noqa: E402
import medir_privacidade as mp                              # noqa: E402

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
       len(mp.MARCAS) == 5 and os.path.isfile(FONTE_FALSA))

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
marcar("as %d familias carregam do JSON real" % len(REAIS), len(REAIS) == 5)

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

sem_arquivo = os.path.join(SANDBOX, "nao_existe.json")
try:
    mp.carregar_marcas(sem_arquivo)
    levantou = False
except Exception:                                           # noqa: BLE001
    levantou = True
marcar("SEM o arquivo, levanta erro (nao devolve lista vazia)", levantou)

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
