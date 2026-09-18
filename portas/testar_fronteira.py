# -*- coding: utf-8 -*-
"""GATE do `fronteira_de_projeto.py` — prova que ele reprova, e que nao cobra pedagio.

Existe porque gate sem teste volta a ser decoracao na primeira refatoracao. Os casos
sao os DOIS lados: o que TEM de ser negado (escrita em projeto alheio) e o que TEM de
passar (`_shared`, hooks, scratchpad, o proprio projeto). So o primeiro lado provaria
que ele nega; so o segundo, que ele nao atrapalha. Sem os dois, apertar o gate mataria
o trabalho legitimo em silencio.

Nao duplica `testar_nome_vs_valor.py` (redator de segredos) nem `testar_recall.py`
(motor de busca): nenhum dos dois olha a que projeto um arquivo pertence.

⚠️ `limpar_marcas()` nao e detalhe: o hook interrompe UMA vez por (sessao, arquivo).
Sem apagar as marcas, a 2a rodada le a marca da 1a, tudo "passa" e o teste leria como
gate morto. Medido — aconteceu comigo na primeira execucao.

🔴 A MUTACAO VIROU CODIGO EM , e a razao e a propria regra da casa.
Ate aqui esta docstring dizia: *"Prova de reversao feita: trocando
`dono = _slug_do_caminho(alvo)` por `dono = ""`, os 3 casos de DENY viraram
PASS"*. Era verdade **naquele dia**, escrita em prosa, e prosa nao roda. Pela
tabela "o que conta como prova" da REGRA #0, *"o gate reprova de verdade"* exige
**mutacao** — quebrar o alvo e ver o gate falhar — e uma reversao feita a mao
seis semanas atras nao prova nada sobre o gate de hoje. As tres mutacoes da
secao 3 sao aquela frase transformada em coisa que roda todo dia.

E elas so valem sobre baseline VIVO: se a secao 1 falhar, a secao 3 nao roda.
Desarmar um detector que ja pegava zero continua pegando zero, e o relatorio sai
todo verde dizendo DETECTADA — [[concept-mutacao-sobre-baseline-morto]].

Chamador: `mente_health.py`, bloco [6e] (cron MenteHealth, diario 9h), e
o mapa da maquina (PECAS), pelo bloco [6u].

Uso:
    python testar_fronteira.py        # exit 0 = aprovado, 1 = reprovado
"""
import glob
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                           # noqa: BLE001
    pass

# 🔴 O UNIVERSO DESTE TESTE E CONSTRUIDO, NAO EMPRESTADO — e a razao foi
# medida ao publicar. Ate aqui os casos apontavam para os projetos REAIS do
# disco de quem escreveu, com
# os nomes por extenso.
#
# Isso tinha DOIS defeitos, e o segundo e o grave:
#
#   1. os nomes sao dado da casa, e destilar trocava-os por outros — que e o
#      certo para publicar;
#   2. trocado o nome, a pasta deixa de existir, o gate nao acha `projeto.yml`
#      em lugar nenhum, e "nao ha dono" LE COMO "pode escrever". Medido: 3
#      casos de DENY viraram PASS. O teste continuava verde na casa de origem
#      e mentia em qualquer outra.
#
# 🔑 Um teste que empresta o disco de quem o escreveu prova aquele disco. Aqui
# ele monta a propria casa: pastas, `projeto.yml` e as pastas de memoria, num
# diretorio temporario que some no fim. O gate roda com `HOME` apontando para
# la, e passa a responder sobre um universo conhecido.
# ⚠️ E ELA NAO PODE NASCER NO TEMPDIR. O gate isenta o diretorio temporario
# de proposito — rascunho nao e entrega — e uma casa montada la dentro teria
# TODOS os caminhos isentos: os casos de DENY virariam PASS e o teste leria
# verde sobre um gate que nunca foi consultado. Medido: 6 de 15 casos.
#
# Ela nasce ao lado do proprio teste, que e o unico lugar que existe nos dois
# arranjos — nesta casa e no repositorio publicado.
CASA = tempfile.mkdtemp(
    prefix="_casa_de_prova_",
    dir=os.path.dirname(os.path.abspath(__file__)))
HOME = CASA
HOOK = os.path.join(CASA, ".claude", "hooks", "fronteira_de_projeto.py")
PERSONAL = os.path.join(CASA, "Projeto", "Pessoal")

# Os projetos de mentira. Cada um ganha `projeto.yml`, que e o que o gate
# procura ao subir o caminho — sem ele, nao ha dono.
_PROJETOS_FALSOS = [
    ("Pessoal", None),
    ("Servico", None),
    ("Produto", "Etapa-Um"),
    ("Produto", "Etapa-Dois"),
    ("Produto", "Etapa-Tres"),
]

# O prefixo com que o agente nomeia a pasta de memoria, MONTADO a partir do
# usuario de mentira desta casa. Escrito por extenso ele carregaria o nome do
# usuario do disco, e a destilacao o trocaria por um marcador — que nao e
# prefixo nenhum, e faria o teste procurar pastas que nao existem.
USUARIO_DE_PROVA = "prova"
PREFIXO_DE_PROVA = "C--" + "-".join(["Users", USUARIO_DE_PROVA, "Projeto"]) + "-"
RAIZ_DE_PROVA = os.path.join(CASA, "Projeto")


def _de_onde_vem(nome):
    """A peca, no arranjo desta casa OU no do repositorio publicado.

    ⚠️ Os dois arranjos existem: aqui as portas ficam ao lado do teste, na
    pasta do agente; no repositorio publicado elas ficam em `portas/` e este
    teste pode ser chamado da raiz. Procurar num lugar so faz o teste
    reprovar dizendo que o hook nao existe — e ele existe, noutro lugar.
    """
    aqui = os.path.dirname(os.path.abspath(__file__))
    for base in (aqui, os.path.join(os.path.dirname(aqui), "portas"),
                 os.path.join(aqui, "portas")):
        caminho = os.path.join(base, nome)
        if os.path.isfile(caminho):
            return caminho
    return ""


def _montar_casa():
    """Cria a casa de mentira: projetos, contratos e pastas de memoria."""
    destino = os.path.join(CASA, ".claude", "hooks")
    os.makedirs(destino, exist_ok=True)
    for nome in ("fronteira_de_projeto.py", "fronteira_lib.py",
                 "memory_lib.py"):
        vem = _de_onde_vem(nome)
        if vem:
            shutil.copy2(vem, os.path.join(destino, nome))

    projetos = []
    for pai, filho in _PROJETOS_FALSOS:
        pasta = os.path.join(CASA, "Projeto", pai)
        if filho:
            pasta = os.path.join(pasta, filho)
        os.makedirs(pasta, exist_ok=True)
        io.open(os.path.join(pasta, "projeto.yml"), "w",
                encoding="utf-8").write("nome: %s\n" % (filho or pai))
        frag = "%s-%s" % (pai, filho) if filho else pai
        projetos.append([frag, frag.lower()])
        os.makedirs(os.path.join(CASA, ".claude", "projects",
                                 PREFIXO_DE_PROVA + frag, "memory"),
                    exist_ok=True)
    # O mais especifico antes do mais geral, que e a regra do casamento por
    # substring: `Produto-Etapa-Um` tem de vir antes de `Produto`.
    projetos.sort(key=lambda p: -len(p[0]))
    projetos.append(["Produto", "produto"])
    os.makedirs(os.path.join(CASA, "Projeto", "_shared"), exist_ok=True)
    io.open(os.path.join(destino, "casa.json"), "w", encoding="utf-8").write(
        json.dumps({"pasta_dos_projetos": "Projeto",
                    "usuario_do_disco": USUARIO_DE_PROVA,
                    "pastas_transversais": ["_shared"],
                    "catalogo_de_ferramentas": "",
                    "projetos": projetos}, ensure_ascii=False))


_montar_casa()

CASOS = [
    ("DENY", PERSONAL, os.path.join(HOME, "Projeto", "Servico", "scripts", "x.py"),
     "codigo de outro projeto"),
    ("DENY", PERSONAL, os.path.join(HOME, ".claude", "projects",
                                    PREFIXO_DE_PROVA + "Produto-Etapa-Um",
                                    "memory", "pendencias_ativas.md"),
     "micro mente de outro projeto"),
    ("DENY", PERSONAL, os.path.join(HOME, "Projeto", "Produto", "Etapa-Tres", "docs", "x.md"),
     "projeto com subpasta"),
    ("PASS", PERSONAL, os.path.join(PERSONAL, "x.md"),
     "o PROPRIO projeto da sessao"),
    ("PASS", PERSONAL, os.path.join(HOME, "Projeto", "_shared", "PADROES.md"),
     "_shared e transversal"),
    ("PASS", PERSONAL, os.path.join(HOME, ".claude", "hooks", "mente_health.py"),
     "hooks: a mente e global"),
    ("PASS", PERSONAL, os.path.join(tempfile.gettempdir(), "rascunho.py"),
     "scratchpad nao e entrega"),
    # os 3 casos da CAIXA. `_slug_do_caminho` fatiava a pasta de
    # memoria do caminho ja passado por `normcase` (minusculo), e
    # `memory_lib.project_dir_to_slug:141` remove o prefixo com um `.replace`
    # LITERAL: em minuscula o prefixo nao sai, a string inteira vai ao
    # `_slug_de_base`, e so escapa quem tem fragmento no PROJECT_MAP — por
    # substring, que e acaso, nao desenho. Medido: 7 das 29 pastas de memoria
    # divergiam, e o gate NEGAVA a escrita na propria memoria delas. Nao e
    # "nome composto": os de nome composto escapavam por acaso, e os de uma
    # palavra so quebravam. O modo de falha e o que importa: projeto novo cujo
    # nome nao esteja no PROJECT_MAP nasce quebrado.
    ("PASS", os.path.join(HOME, "Projeto", "Servico"),
     os.path.join(HOME, ".claude", "projects",
                  PREFIXO_DE_PROVA + "Servico", "memory", "x.md"),
     "memoria do PROPRIO projeto (caixa)"),
    ("PASS", os.path.join(HOME, "Projeto", "Pessoal"),
     os.path.join(HOME, ".claude", "projects",
                  PREFIXO_DE_PROVA + "Pessoal", "memory", "x.md"),
     "memoria do PROPRIO projeto, 2o nome"),
    # O par do de cima, e o que impede o conserto de virar abertura de portao:
    # o mesmo arquivo, de uma sessao ALHEIA, tem de continuar barrado.
    ("DENY", PERSONAL,
     os.path.join(HOME, ".claude", "projects",
                  PREFIXO_DE_PROVA + "Servico", "memory", "x.md"),
     "memoria de projeto alheio (caixa)"),
    # o DONO passa a sair do `projeto.yml`, nao da deducao pelo
    # caminho. Tres casos que a deducao errava, cada um de um jeito:
    #   · uma ETAPA tem contrato, micro mente e repo proprios, e virava o
    #     apelido do projeto pai — a escrita na memoria dela era negada;
    #   · `Projeto\new-project.sh` e um ARQUIVO na raiz da casa, e virava um
    #     "projeto" chamado `new-project-sh` (barrou a edicao do proprio rito);
    #   · uma pasta de worktree resolvia como o projeto de onde ela saiu,
    #     que e o gotcha que ja mordeu esta casa duas vezes.
    ("PASS", os.path.join(HOME, "Projeto", "Produto", "Etapa-Um"),
     os.path.join(HOME, ".claude", "projects",
                  PREFIXO_DE_PROVA + "Produto-Etapa-Um", "memory", "x.md"),
     "memoria do PROPRIO Produto/Etapa-Um"),
    ("PASS", os.path.join(HOME, "Projeto", "Produto", "Etapa-Dois"),
     os.path.join(HOME, ".claude", "projects",
                  PREFIXO_DE_PROVA + "Produto-Etapa-Dois", "memory", "x.md"),
     "memoria do PROPRIO Produto/Etapa-Dois"),
    ("PASS", PERSONAL, os.path.join(HOME, "Projeto", "new-project.sh"),
     "arquivo solto na raiz nao tem dono"),
    # O par que impede o conserto de virar abertura de portao: as etapas
    # sao projetos DIFERENTES, e continuam separadas uma da outra.
    ("DENY", os.path.join(HOME, "Projeto", "Produto", "Etapa-Um"),
     os.path.join(HOME, ".claude", "projects",
                  PREFIXO_DE_PROVA + "Produto-Etapa-Dois", "memory", "x.md"),
     "Etapa-Um NAO escreve na memoria do Etapa-Dois"),
]

# o PID entra na identidade. So o relogio nao basta: duas copias
# do teste iniciadas no MESMO milissegundo geravam o MESMO `MARCA`, logo os
# mesmos `session_id`, e uma via a marca "ja avisei" da outra — casos DENY
# viravam PASS. Medido rodando as duas em paralelo, que e o cenario real desta
# maquina (4 sessoes do Claude vivas hoje). Mesmo tema do dia: identidade que se
# DERIVA de algo colidivel erra; identidade declarada, nao.
MARCA = "gate-fronteira-%d-%d" % (int(time.time() * 1000), os.getpid())


def limpar_marcas():
    r"""Apaga SO as marcas desta execucao do teste.

    🔴 antes daqui o glob era `fronteira_*.json`, e apagava a marca
    de TODA sessao viva da casa. Efeito medido: depois de 4 rodadas deste
    teste, `%TEMP%` tinha **0** marcas — as minhas e as da sessao
    de outra sessao haviam sido varridas junto.

    E isso PRODUZIA um sintoma no trabalho real: a marca e o que faz o gate
    interromper **uma vez** por arquivo. Apagada no meio, o mesmo arquivo era
    negado de novo — que e exatamente o "deny repetido no mesmo alvo" que
    aquela sessao relatou como inexplicado, e que ela atribuiu (errado) ao
    `json.dump` sem `with`. A causa era o teste, nao o gate.

    Teste que altera o estado de quem nao esta sendo testado nao e teste: e
    efeito colateral com resultado. `MARCA` ja era unico por execucao — bastava
    usa-lo tambem aqui.
    """
    for f in glob.glob(os.path.join(tempfile.gettempdir(),
                                    "fronteira_%s*.json" % MARCA)):
        try:
            os.remove(f)
        except OSError:
            pass


def roda(cwd, alvo, sessao, hook=HOOK):
    ent = {"session_id": sessao, "cwd": cwd,
           "tool_input": {"file_path": alvo, "new_string": "x"}}
    # ⚠️ O `HOME` do SUBPROCESSO aponta para a casa construida. Sem isto o
    # gate calcula a raiz dos projetos a partir da casa de quem roda o teste,
    # e responde sobre um universo que o teste nao controla — que era
    # exatamente o defeito.
    amb = dict(os.environ)
    amb["HOME"] = CASA
    amb["USERPROFILE"] = CASA
    try:
        p = subprocess.run([sys.executable, "-B", hook],
                           input=json.dumps(ent).encode("utf-8"),
                           capture_output=True, timeout=90, env=amb)
    except (OSError, subprocess.SubprocessError) as e:
        return "ERRO", str(e)[:80]
    out = p.stdout.decode("utf-8", "replace").strip()
    if not out:
        return "PASS", ""
    try:
        h = json.loads(out).get("hookSpecificOutput", {})
        return ("DENY" if h.get("permissionDecision") == "deny" else "PASS",
                h.get("permissionDecisionReason", "")[:80])
    except ValueError:
        return "PASS", out[:80]


def rodar_casos(hook=HOOK, prefixo="base"):
    """[(esperado, obtido, descricao)] para os 7 casos conhecidos."""
    limpar_marcas()
    fora = []
    for i, (esperado, cwd, alvo, desc) in enumerate(CASOS):
        got, _ = roda(cwd, alvo, "%s-%s-%d" % (MARCA, prefixo, i), hook=hook)
        fora.append((esperado, got, desc))
    limpar_marcas()
    return fora


# Os 3 caminhos que passam por ISENCAO (transversal/rascunho). O quarto PASS —
# `Projeto/Personal/x.md` — passa por outro motivo: e o PROPRIO projeto da
# sessao, e quem o libera e a comparacao `sessao_proj == dono`, coberta pela
# mutacao 2. Medido: a mutacao inversa virou 3 dos 4 e "sobreviveu",
# e o furo estava aqui, nao no gate — eu havia posto num so balde duas coisas
# liberadas por mecanismos diferentes. Mutacao que mira alvo errado acusa
# fraqueza onde nao ha.
SO_ISENCAO = {"_shared e transversal", "hooks: a mente e global",
              "scratchpad nao e entrega"}

# Os 2 casos liberados pelo conserto da CAIXA, e so eles. O terceiro
# caso novo (`memoria de projeto alheio`) fica de FORA de proposito: ele e DENY
# nos dois mundos — antes por comparar lixo contra `personal`, depois por
# comparar um apelido contra outro — entao nao serve de detector.
SO_CAIXA = {"memoria do PROPRIO projeto (caixa)",
            "memoria do PROPRIO projeto, 2o nome"}

# Os casos liberados por o DONO sair do `projeto.yml` em vez do caminho. O
# `arquivo solto` fica de FORA: ele passa por `_slug_do_caminho` devolver "",
# e desfazer a troca no ramo do ALVO nao o afeta — quem o resolve e o ramo do
# cwd. Mutacao que mira alvo errado acusa fraqueza onde nao ha (licao).
SO_DONO = {"memoria do PROPRIO Produto/Etapa-Um",
           "memoria do PROPRIO Produto/Etapa-Dois"}

# ── as mutacoes, cada uma isolando UM detector ──────────────────────────────
# `de` tem de ser unico no arquivo e ASCII puro: casar por trecho acentuado
# torna a mutacao refem do encoding com que o arquivo foi lido, e falha calada.
# O 6o campo restringe quais casos a mutacao deve virar; None = todos do lado.
MUTACOES = [
    ("resolvedor de dono sempre devolve vazio",
     "e a reversao virada codigo: sem dono, nada e de ninguem e "
     "os 3 DENY viram PASS",
     "    dono = _slug_do_caminho(alvo)",
     '    dono = ""',
     "DENY", None),
    ("comparacao entre projeto da sessao e dono anulada",
     "o gate continua sabendo de quem e o arquivo, e para de comparar: "
     "escrever em projeto alheio deixa de ser alheio",
     "    if not sessao_proj or sessao_proj == dono:",
     "    if not sessao_proj or True:",
     "DENY", None),
    ("marca de `ja avisei` sempre respondendo SIM",
     "o modo de falha silencioso: o gate roda, decide negar, e engole a "
     "negacao antes de imprimir",
     "    if alvo in vistos:",
     "    if True:",
     "DENY", None),
    ("isencao do caminho transversal removida (mutacao inversa)",
     "prova que os PASS sao decisao do gate, nao inercia: sem a isencao, "
     "`_shared`, hooks e scratchpad passam a ser barrados",
     "    if not dono:",
     "    if False:",
     "PASS", SO_ISENCAO),
    # ⚠️ ESTA MUTACAO VIROU EQUIVALENTE, e isso e diferente de ela ter
    # quebrado. Ela desfazia o conserto da caixa passando o prefixo da pasta
    # de memoria em minuscula, e provava que `project_dir_to_slug` nao
    # conseguia remove-lo. A troca ainda se aplica — a linha esta la — mas o
    # programa mutado passou a se comportar igual ao original.
    #
    # O motivo e que o reconhecedor saiu do `memory_lib`, com o nome do
    # usuario escrito dentro, e foi para o `fronteira_lib`, que compara por
    # substring insensivel a caixa. Medido: as tres grafias do prefixo
    # (maiuscula, minuscula e caixa misturada) devolvem
    # o mesmo apelido.
    #
    # 🔑 Mutacao equivalente nao e detector fraco: nenhum teste pode acusa-la,
    # porque nao ha diferenca para acusar. Ela fica DECLARADA aqui em vez de
    # apagada em silencio — apagar esconderia que a cobertura daquele risco
    # mudou de lugar. O risco em si continua provado, no grupo 2b, que mede as
    # tres grafias contra o `fronteira_lib` diretamente.
    ("pasta de memoria lida do caminho ja em minusculo (EQUIVALENTE)",
     "o reconhecedor deixou de depender da caixa: o programa mutado se "
     "comporta igual ao original, e nao ha diferenca para um teste acusar",
     "        resto = orig[len(RAIZ_MENTE):].lstrip(",
     "        resto = p[len(RAIZ_MENTE):].lstrip(",
     "EQUIVALENTE", SO_CAIXA),
    ("o dono volta a ser deduzido do caminho (mutacao inversa)",
     "desfaz a troca no lado do CWD: a sessao aberta em "
     "uma etapa volta a se chamar como o projeto pai, deixa de reconhecer a "
     "propria micro mente, e o gate barra a escrita legitima",
     "    raiz_cwd = fl.dono_de_caminho(cwd)",
     "    raiz_cwd = fl.raiz_de_projeto(cwd)",
     "PASS", SO_DONO),
]


def main():
    if not os.path.exists(HOOK):
        print("REPROVADO — o hook nao existe: %s" % HOOK)
        return 1

    print("== 1. os %d casos conhecidos (os dois lados) ==" % len(CASOS))
    falhas = []
    for esperado, got, desc in rodar_casos():
        if got == "ERRO":
            # Mesmo motivo do bloco de mutacao: "nao consegui medir" tem de
            # gritar diferente de "medi e deu errado".
            print("  [ERRO  ] %-34s o hook NAO RODOU — medicao nao aconteceu"
                  % desc)
            falhas.append("%s: ERRO DE EXECUCAO (o hook nao rodou)" % desc)
            continue
        ok = got == esperado
        print("  [%s] %-34s esperava %s, veio %s"
              % ("PASS " if ok else "FALHA", desc, esperado, got))
        if not ok:
            falhas.append("%s: esperava %s, veio %s" % (desc, esperado, got))

    print("\n== 2. interrompe UMA vez por arquivo (a 2a passa) ==")
    limpar_marcas()
    a, _ = roda(CASOS[0][1], CASOS[0][2], MARCA + "-rep")
    b, _ = roda(CASOS[0][1], CASOS[0][2], MARCA + "-rep")
    ok_rep = a == "DENY" and b == "PASS"
    print("  [%s] 1a=%s, 2a=%s" % ("PASS " if ok_rep else "FALHA", a, b))
    if not ok_rep:
        falhas.append("repeticao: esperava DENY depois PASS, veio %s depois %s"
                      % (a, b))
    limpar_marcas()

    # -- 2b. ONDE A CASA MORA E DADO, e some-la e ERRO ----------------------
    # . `RAIZ_PROJ`, o usuario do disco e a lista de pastas
    # transversais sairam do codigo para `casa.json`, porque a regex de
    # caminho trazia o nome do usuario ESCRITO DENTRO DELA e a peca so
    # funcionaria numa maquina. O risco novo e o pior de todos aqui: se o
    # arquivo sumir e a lib cair para um default, ela responde "nao ha dono"
    # para todo caminho — e "nao ha dono" le como "pode escrever" nos dois
    # gates que a chamam. O modo de falha silencioso desta peca e ABRIR o
    # portao, entao ela tem de falhar alto.
    print("\n== 2b. onde a casa mora e DADO, e some-lo e ERRO ==")
    sys.path.insert(0, os.path.dirname(os.path.abspath(HOOK)))
    import fronteira_lib as _fl                              # noqa: E402

    tmpdir = tempfile.mkdtemp(prefix="casa_")
    try:
        sem = os.path.join(tmpdir, "nao_existe.json")
        try:
            _fl.carregar_casa(sem)
            levantou = False
        except Exception:                                    # noqa: BLE001
            levantou = True
        print("  [%s] SEM o casa.json, levanta em vez de usar default"
              % ("PASS " if levantou else "FALHA"))
        if not levantou:
            falhas.append("casa.json ausente nao levantou")

        vazio = os.path.join(tmpdir, "vazio.json")
        io.open(vazio, "w", encoding="utf-8").write(
            '{"pasta_dos_projetos": "", "pastas_transversais": []}')
        try:
            _fl.carregar_casa(vazio)
            levantou2 = False
        except ValueError:
            levantou2 = True
        except Exception:                                    # noqa: BLE001
            levantou2 = False
        print("  [%s] com `pasta_dos_projetos` vazio, levanta ValueError"
              % ("PASS " if levantou2 else "FALHA"))
        if not levantou2:
            falhas.append("pasta_dos_projetos vazio nao levantou")

        bom = os.path.join(tmpdir, "bom.json")
        io.open(bom, "w", encoding="utf-8").write(
            '{"pasta_dos_projetos": "Obras", "usuario_do_disco": "fulano",'
            ' "pastas_transversais": ["_comum"]}')
        raiz, usuario, transv = _fl.carregar_casa(bom)
        ok_bom = (os.path.basename(raiz) == "Obras" and usuario == "fulano"
                  and transv == {"_comum"})
        print("  [%s] casa.json de outra maquina e lido como e"
              % ("PASS " if ok_bom else "FALHA"))
        if not ok_bom:
            falhas.append("casa.json alheio: %r" % ((raiz, usuario, transv),))

        # E a regex acompanha o dado: com outro usuario e outra pasta, ela
        # reconhece o caminho DAQUELA casa. Era isto que o nome escrito na
        # regex impedia, e o impedia calado.
        rx = _fl._monta_regex(raiz, usuario)
        # Montado, nunca escrito: um caminho Windows literal aqui seria
        # trocado por marcador na destilacao, e marcador nao casa regex de
        # caminho nenhuma — a asserção passaria a medir outra coisa.
        _b = chr(92)
        _casa_alheia = _b.join(["C:", "Users", "fulano", "Obras"])
        achou = rx.search(_casa_alheia + _b + "Telhado" + _b + "x.py")
        nao = rx.search(os.path.join(RAIZ_DE_PROVA, "Servico", "x.py"))
        ok_rx = bool(achou) and achou.group(1) == "Telhado" and not nao
        print("  [%s] a regex segue o dado (reconhece a casa alheia, nao a "
              "nossa)" % ("PASS " if ok_rx else "FALHA"))
        if not ok_rx:
            falhas.append("regex nao acompanhou o dado: achou=%r nao=%r"
                          % (achou, nao))
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    if falhas:
        print("\nREPROVADO — %d de %d casos" % (len(falhas), len(CASOS) + 1))
        for f in falhas:
            print("   %s" % f)
        print("\n   mutacao NAO AVALIADA: o baseline esta morto, e desarmar um "
              "detector que ja pega zero continua pegando zero.")
        print("   [[concept-mutacao-sobre-baseline-morto]]")
        return 1

    print("\n== 3. MUTACAO (quebrar o alvo e exigir que o teste ACUSE) ==")
    fonte = io.open(HOOK, encoding="utf-8").read()
    # 🔴 nome UNICO por execucao. Era fixo, e duas rodadas ao mesmo
    # tempo (esta maquina roda varias sessoes do Claude em paralelo — medido
    # hoje: 4 sessoes vivas) escreviam no MESMO arquivo: uma sobrescrevia a
    # mutacao da outra, e o `finally` de uma apagava o mutante da outra no meio
    # da rodada. Sintoma: 4 mutacoes "sobrevivendo" juntas, com os casos
    # resistindo no veredito ORIGINAL — e verde nas rodadas seguintes. Flaky
    # e pior que vermelho: ensina a ignorar a suite.
    mut_py = os.path.join(tempfile.gettempdir(),
                          "mut_fronteira_%s_%d.py" % (MARCA, os.getpid()))
    sobreviveram = []
    try:
        for nome, porque, de, para, lado, so in MUTACOES:
            # 🔴 MUTACAO EQUIVALENTE — a troca se aplica, e o programa mutado
            # se comporta igual ao original. Nenhum teste pode acusa-la,
            # porque nao ha diferenca para acusar.
            #
            # ⚠️ Ela e CONFERIDA, nao dispensada: o trecho tem de continuar no
            # arquivo. Se ele sumir, a declaracao virou mentira sobre um
            # codigo que nao existe mais, e isso volta a ser falha.
            if lado == "EQUIVALENTE":
                achou = fonte.count(de) == 1
                print("  [%s] %s" % ("EQUIVALENTE" if achou
                                     else "DECLARACAO PODRE", nome))
                print("              " + porque)
                if not achou:
                    print("              o trecho declarado equivalente nao "
                          "esta mais no arquivo: a declaracao perdeu o alvo")
                    sobreviveram.append(nome + " (declaracao sem alvo)")
                continue
            if fonte.count(de) != 1:
                print("  [PULADA   ] %s" % nome)
                print("              trecho alvo aparece %d vez(es), nao 1 — a "
                      "mutacao seria ambigua" % fonte.count(de))
                sobreviveram.append(nome + " (trecho nao localizado)")
                continue
            with io.open(mut_py, "w", encoding="utf-8") as fh:
                fh.write(fonte.replace(de, para, 1))
            # DETECTADA quando TODO caso do lado mutado troca de veredito.
            esperado_novo = "PASS" if lado == "DENY" else "DENY"
            alvos = [(e, g, d) for e, g, d in rodar_casos(hook=mut_py, prefixo="mut")
                     if e == lado and (so is None or d in so)]
            # ERRO DE EXECUCAO NAO E MUTACAO SOBREVIVENTE.
            # `roda()` devolve "ERRO" quando o subprocesso estoura o timeout ou
            # nao roda; contado junto com os vereditos, isso vira "4 de 5
            # viraram" e LE como detector fraco. Aconteceu hoje: 1 rodada em ~5,
            # e me mandou cacar um defeito logico que as outras 4 rodadas e o
            # teste isolado (3x, 5 de 5) desmentiam. O instrumento que confunde
            # "nao consegui medir" com "medi e esta ruim" produz uma afirmacao
            # falsa com cara de medida — o mesmo defeito do grep com acento.
            falhou_rodar = [d for _e, g, d in alvos if g == "ERRO"]
            if falhou_rodar:
                print("  [ERRO EXEC] %s" % nome)
                print("              o hook NAO RODOU em %d caso(s): %s"
                      % (len(falhou_rodar), ", ".join(falhou_rodar)))
                print("              isto nao e veredito sobre a mutacao — e "
                      "medicao que nao aconteceu. Rodar de novo.")
                sobreviveram.append(nome + " (NAO MEDIDA — erro de execucao)")
                continue
            virou = sum(1 for _e, g, _d in alvos if g == esperado_novo)
            detectada = virou == len(alvos)
            if not detectada:
                sobreviveram.append(nome)
            print("  [%s] %s" % ("DETECTADA" if detectada else "SOBREVIVEU", nome))
            print("              " + porque)
            print("              %d de %d caso(s) %s viraram %s"
                  % (virou, len(alvos), lado, esperado_novo))
            # quando sobrevive, DIZER QUAL. A contagem sozinha
            # mandou-me caçar um defeito logico que nao existia: o caso que
            # resistia era intermitente, e "4 de 5" nao distingue mutacao fraca
            # de execucao que falhou. Nome e veredito obtido separam as duas.
            if not detectada:
                for _e, g, d in alvos:
                    if g != esperado_novo:
                        print("                 RESISTIU: %-40s veio %s" % (d, g))
    finally:
        try:
            os.remove(mut_py)
        except OSError:
            pass
        limpar_marcas()

    print("\n== 4. controle: com o hook original, tudo volta ao veredito certo ==")
    erros_ctrl = [d for e, g, d in rodar_casos(prefixo="ctrl") if e != g]
    if erros_ctrl:
        print("  [FALHA] o controle divergiu: %s" % ", ".join(erros_ctrl))
        return 1
    print("  [PASS ] os %d casos voltam ao veredito certo" % len(CASOS))

    if sobreviveram:
        print("\nREPROVADO — %d mutacao(oes) sobreviveram" % len(sobreviveram))
        for n in sobreviveram:
            print("   mutacao nao detectada: %s" % n)
        return 1

    print("\nAPROVADO — %d/%d casos, 0 falha, 0 mutacao sobrevivente: nega "
          "projeto alheio, deixa passar transversal, a 2a tentativa passa, "
          "e as %d mutacoes sao acusadas."
          % (len(CASOS) + 1, len(CASOS) + 1, len(MUTACOES)))
    return 0


def _limpar_casa():
    """Apaga a casa de prova. Ela NAO pode sobreviver a rodada.

    🔴 MEDIDO NA PRIMEIRA EXECUCAO: a casa sobrou no disco e o `test_memory`,
    que roda logo depois e varre as pastas de memoria, passou a contar as
    pastas de MENTIRA junto com as de verdade — e reprovou. Um teste que
    deixa lixo no disco quebra o teste seguinte, e o segundo acusa um defeito
    que nao existe.

    ⚠️ So apaga o que ele mesmo criou, e confere o prefixo antes: apagar por
    caminho montado, sem olhar o nome, e como esta casa ja perdeu arquivo.
    """
    nome = os.path.basename(CASA)
    if nome.startswith("_casa_de_prova_") and os.path.isdir(CASA):
        shutil.rmtree(CASA, ignore_errors=True)


if __name__ == "__main__":
    try:
        _codigo = main()
    finally:
        _limpar_casa()
    sys.exit(_codigo)
