# -*- coding: utf-8 -*-
r"""FRONTEIRA_LIB — o UNICO reconhecedor de "de que projeto e este caminho?".

Por que existe
---------------------------
Dois gates precisam da mesma resposta e nao podiam responder cada um do seu
jeito: `fronteira_de_projeto.py` (Edit|Write) e `bash_na_porta.py` (Bash).
Duas gramaticas para a mesma identidade e o defeito de
[[concept_a_identidade_do_registro_tem_de_ser_uma]], e ele ja custou caro aqui:
em  o `detect_project` e o `project_dir_to_slug` divergiam, e 145 notas do
um projeto eram estrangeiras dentro dele mesmo.

O QUE ELE NAO FAZ: nao mexe em `memory_lib.PROJECT_MAP`. O proprio
`fronteira_de_projeto.py` avisa, na linha 49, que mexer no mapa muda como o
recall pontua projeto. Aqui o caminho e reduzido a PASTA-RAIZ do projeto ANTES
de ir ao `detect_project` — que e exatamente a forma para a qual ele foi feito
(ele nasceu recebendo o cwd, que e a raiz).

O DEFEITO QUE ISTO CONSERTA `[medido]`
---------------------------------------------
`detect_project` junta TODO o caminho depois de `Projeto\` com hifen:

    Projeto\Central-Comando-360            -> central-comando-360
    Projeto\Central-Comando-360\docs       -> central-comando-360-docs   (!)

Quando o projeto esta no `PROJECT_MAP`, o casamento por substring salva
(`Personal\_candidaturas` -> `personal`). Quando NAO esta, a subpasta vira outro
projeto e o gate barra escrita legitima dentro de casa. Medido: **15 dos 33**
diretorios da pasta dos projetos sofrem disso: todos os que nao tem
entrada no mapa e carregam subpasta.

Gate que reprova o caso legitimo ensina a contornar o gate. Foi assim que a
outra sessao aprendeu a repetir a gravacao ate passar, e a repeticao virou
habito — o mesmo mecanismo do guard da D27.

Chamadores: `fronteira_de_projeto.py`, `bash_na_porta.py`.
Teste: `testar_fronteira.py` (o grupo 2b prova o carregamento do `casa.json`)
       e `testar_fronteira_bash.py` (o acoplamento com a porta do Bash).

⚠️ Ate  esta linha dizia `testar_fronteira_lib.py`, e esse arquivo
NUNCA existiu. E o mesmo defeito que a casa ja pegou duas vezes — o rotulo da
prova escrito no codigo e a prova ausente do disco — e ele passou despercebido
porque esta peca nao estava no mapa da maquina: ninguem media se o teste que
ela declara existe. Peca fora do mapa nao e medida, e nao ser medida le igual
a nao existir.
"""
from __future__ import annotations

import io
import json
import os
import re
import tempfile

HOME = os.path.expanduser("~")

# 🔴 ONDE A CASA MORA SAIU DO CODIGO EM , e o sintoma seria mudo. A regex
# logo abaixo tinha o nome do usuario do disco escrito dentro dela:
#
#     r"(?:Users[\\/]+olive[\\/]+)?"
#
# Numa maquina que nao fosse aquela, a peca nao quebraria: ela apenas deixaria
# de reconhecer os caminhos de quem baixou, e um gate que nao reconhece nada
# nao barra nada. Nao barrar e justamente o que ninguem percebe — ao contrario
# de um erro, que aparece.
#
# E o mesmo conserto de `privacidade.json`, `mapa.json` e `reescritas.json`,
# agora pela quarta vez: o que identifica a casa e DADO, nunca constante de
# codigo.
FONTE_CASA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "casa.json")


def carregar_casa(fonte=None):
    """(raiz_dos_projetos, usuario_do_disco, transversais) — do disco.

    ⚠️ Sem o arquivo isto NAO cai para um default. Uma fronteira que nao sabe
    onde a casa comeca responde "nao ha dono" para todo caminho, e "nao ha
    dono" le como "pode escrever" em todos os chamadores. O modo de falha
    silencioso aqui e abrir o portao, nao fecha-lo.
    """
    with io.open(fonte or FONTE_CASA, encoding="utf-8") as fh:
        d = json.load(fh)
    pasta = (d.get("pasta_dos_projetos") or "").strip()
    if not pasta:
        raise ValueError(
            "casa.json sem `pasta_dos_projetos`. Sem ela a fronteira responde "
            "'nao ha dono' para todo caminho, e 'nao ha dono' le como 'pode "
            "escrever' em todos os chamadores.")
    transversais = {t.lower() for t in (d.get("pastas_transversais") or [])}
    # Vazio e uma resposta legitima (casa sem pasta compartilhada), ao
    # contrario da pasta dos projetos. Por isso este campo nao levanta.
    usuario = (d.get("usuario_do_disco") or "").strip() or os.path.basename(
        HOME)
    return os.path.join(HOME, pasta), usuario, transversais


RAIZ_PROJ, USUARIO, TRANSVERSAIS = carregar_casa()


def carregar_projetos(fonte=None):
    """[(fragmento, apelido)] — o mapa dos projetos, do disco.

    🔴 ESTA LISTA ESTAVA ESCRITA A MAO EM TRES ARQUIVOS, e as tres divergiram.
    Medido, com o efeito real e nenhum deles sendo uma quebra:

      · abrindo um projeto de segunda geracao, uma copia resolvia para o
        apelido da PRIMEIRA geracao, ja aposentada — e a memoria carregada era
        a de 3 notas em vez da de 43;
      · para outro projeto, uma copia devolvia um apelido curto e a outra o
        apelido com a etapa, e so o segundo tem pasta no disco;
      · oito projetos com memoria nao estavam em copia nenhuma.

    🔑 As duas primeiras RESPONDEM, com o projeto errado. E o modo de falha
    que esta casa mais paga: o que emudece, nao o que grita.

    ⚠️ Lista vazia e ERRO. Sem o mapa, todo caminho cai no apelido derivado
    do nome da pasta — o que, dentro de uma SUBPASTA, devolve o nome dela e
    nao o do projeto. Memoria de projeto inexistente le como projeto sem
    memoria, e a sessao comeca cega sem avisar.
    """
    with io.open(fonte or FONTE_CASA, encoding="utf-8") as fh:
        crus = (json.load(fh).get("projetos") or [])
    pares = [(str(a), str(b)) for a, b in crus if a and b]
    if not pares:
        raise ValueError(
            "casa.json sem `projetos`. Sem o mapa, o apelido sai do nome da "
            "pasta — e numa subpasta isso devolve um projeto que nao existe, "
            "fazendo a sessao comecar cega sem avisar.")
    return pares


PROJETOS = carregar_projetos()

# O prefixo que o agente usa para nomear a pasta de memoria de um projeto, e o
# trecho de caminho que marca onde os projetos comecam. Os dois saem do DADO:
# escritos a mao, carregavam o nome do usuario do disco.
PREFIXO_MEMORIA = "C--" + os.path.join("Users", USUARIO, os.path.basename(
    RAIZ_PROJ)).replace(os.sep, "-") + "-"
# 🔴 DERIVADO DE `RAIZ_PROJ`, NAO REMONTADO. A primeira versao montava
# `\Users\<usuario>\<pasta>\` a partir dos pedacos — e com isso assumia que a
# pasta dos projetos mora dentro de `Users`. Numa casa onde ela mora noutro
# lugar, o trecho nunca casa, o caminho cai no fallback do nome da PASTA, e
# `Produto\Etapa-Um` devolve `etapa-um` em vez de `produto-etapa-um`.
#
# 🔑 O valor ja estava calculado logo acima. Remontar um dado que existe e
# como copiar uma lista: as duas versoes divergem no primeiro caso que o
# autor nao imaginou.
_RAIZ_MINUSCULA = os.path.normcase(RAIZ_PROJ).replace("/", os.sep) + os.sep


def apelido_de_base(base):
    """`Meu-Modulo` -> `meu-modulo`. O UNICO reconhecedor de identidade.

    As duas pontas — a nota, que vem do nome da pasta de memoria, e a busca,
    que vem do diretorio de trabalho — passam por aqui. Senao viram duas
    gramaticas para o mesmo projeto, que foi o defeito medido.
    """
    for frag, apelido in PROJETOS:
        if frag.lower() == base.lower() or frag.lower() in base.lower():
            return apelido
    return re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")


def apelido_da_pasta_de_memoria(dirname):
    """O apelido a partir do nome da pasta de memoria do projeto."""
    return apelido_de_base(dirname.replace(PREFIXO_MEMORIA, ""))


def apelido_do_diretorio(cwd):
    """O apelido do projeto dono de um diretorio de trabalho.

    ⚠️ A NORMALIZACAO E O PONTO, e foi por falta dela que tres pecas desta
    casa discordavam. Um caminho com subpasta, casado cru por substring,
    devolve o apelido do projeto PAI — a entrada no mapa usa hifen e o caminho
    usa barra. Aqui o trecho depois da pasta dos projetos e normalizado
    ANTES de procurar, e as duas pontas passam a falar a mesma lingua.
    """
    norm = cwd.replace("/", os.sep).rstrip(os.sep)
    i = norm.lower().find(_RAIZ_MINUSCULA)
    if i >= 0:
        resto = norm[i + len(_RAIZ_MINUSCULA):]
        if resto:
            return apelido_de_base(resto.replace(os.sep, "-"))
    base = os.path.basename(norm)
    return apelido_de_base(base) if base else ""

# Caminho sob a pasta dos projetos em qualquer das grafias que aparecem num
# comando de shell, nas tres grafias que aparecem (Windows, POSIX e Git Bash),
# `~/<pasta>/...`. O grupo 1 e sempre a pasta-raiz do projeto.
_P = r"[\w.\-]+"


def _monta_regex(pasta, usuario):
    """A regex de caminho, montada a partir do dado. Nunca escrita a mao."""
    return re.compile(
        r"(?:[A-Za-z]:[\\/]+|/[A-Za-z]/|~[\\/]+)"
        r"(?:Users[\\/]+" + re.escape(usuario) + r"[\\/]+)?" +
        re.escape(os.path.basename(pasta)) + r"[\\/]+(" + _P + r")",
        re.I,
    )


RE_CAMINHO_PROJETO = _monta_regex(RAIZ_PROJ, USUARIO)


def raiz_de_projeto(caminho: str) -> str:
    """Pasta-raiz do projeto dono de `caminho`, ou '' quando nao se aplica.

    '' significa "este gate nao tem o que dizer": caminho fora de `Projeto\\`,
    pasta transversal, ou rascunho. Nunca significa "pode".
    """
    if not caminho:
        return ""
    p = os.path.normcase(os.path.abspath(caminho))
    if p.startswith(os.path.normcase(tempfile.gettempdir())):
        return ""
    raiz = os.path.normcase(RAIZ_PROJ)
    if not (p == raiz or p.startswith(raiz + os.sep)):
        return ""
    resto = p[len(raiz):].lstrip("\\/")
    if not resto:
        return ""
    primeira = resto.split(os.sep)[0]
    return "" if primeira.lower() in TRANSVERSAIS else primeira


def dono_de_caminho(caminho: str) -> str:
    """Pasta-projeto dona de `caminho`, relativa a `Projeto\\`, ou '' quando nao
    se aplica. Sobe do caminho ate a pasta mais proxima que tenha `projeto.yml`.

    POR QUE ESTA FUNCAO EXISTE, e por que ela e NOVA em vez de um
    conserto dentro de `raiz_de_projeto`.

    A identidade do projeto era DEDUZIDA: `raiz_de_projeto` pega a primeira
    pasta sob `Projeto\\`, e isso errava de tres jeitos diferentes, todos
    medidos no mesmo dia:
      · as etapas de um mesmo projeto tem contrato, micro mente e repo
        proprios, e viravam o apelido do PAI — a escrita na propria memoria
        deles era negada;
      · `Projeto\\new-project.sh` e um ARQUIVO na raiz, e virava um "projeto"
        chamado `new-project-sh` (apanhei disto ao vivo, editando o rito);
      · uma pasta de WORKTREE resolvia como o projeto de onde ela saiu —
        o gotcha que ja mordeu esta casa duas vezes.

    A lição veio de fora: um dev descrevendo a arquitetura dele passa
    `tenant_id` como CAMPO, e a casa adivinhava o equivalente a partir de uma
    string de caminho. Campo declarado nao erra de tres jeitos; deducao erra.
    O campo aqui e a EXISTENCIA do `projeto.yml` — o contrato de dia zero, que
    esta commitado em 25 projetos.

    🔴 NAO consertei `raiz_de_projeto`, e o motivo e o raio, medido antes: ela
    tem 4 chamadores, e `bash_na_porta.py:306,380` compara o resultado dela com
    `raizes_citadas()` — uma regex que extrai UM nivel. Se `raiz_de_projeto`
    passasse a devolver a subpasta, o par divergiria e o `bash_na_porta`
    acusaria escrita em projeto alheio DENTRO do proprio projeto: regressao
    pior que o defeito. Funcao nova deixa aquele par intacto.

    O worktree sai de graca: ele nao tem `projeto.yml` proprio, entao a subida
    passa por ele e para no projeto de verdade. Nao ha lista de excecao para
    manter — [[concept-lista-fechada-contra-gerador-livre]].

    FALLBACK: projeto sem contrato nenhum volta a `raiz_de_projeto`, para o
    gate nao perder o que ja acertava enquanto o retrofit nao termina.
    """
    if not caminho:
        return ""
    orig = os.path.abspath(caminho)
    p = os.path.normcase(orig)
    if p.startswith(os.path.normcase(tempfile.gettempdir())):
        return ""
    raiz = os.path.normcase(RAIZ_PROJ)
    if not p.startswith(raiz + os.sep):
        return ""                        # inclui o proprio `Projeto\`: nao e projeto
    # Fatia de `orig`, nao de `p`: devolver a pasta em minusculo e exatamente o
    # defeito consertado hoje de manha no `fronteira_de_projeto.py:86`, onde a
    # caixa perdida quebrava o `project_dir_to_slug`. `normcase` no Windows so
    # troca caixa e separador, entao o corte cai no mesmo indice.
    partes = orig[len(raiz):].lstrip("\\/").split(os.sep)
    if not partes or not partes[0]:
        return ""
    if partes[0].lower() in TRANSVERSAIS:
        return ""
    # Da pasta mais FUNDA para a mais rasa: o contrato mais proximo do arquivo
    # e o dono. `Personal\\vault-captura\\x.py` para em `vault-captura`, nao em
    # `Personal` — embora os dois tenham contrato.
    #
    # `partes` pode terminar num ARQUIVO; testar `projeto.yml` dentro de um
    # arquivo so devolve False, entao nao ha caso especial a escrever.
    for corte in range(len(partes), 0, -1):
        rel = os.sep.join(partes[:corte])
        if os.path.isfile(os.path.join(RAIZ_PROJ, rel, "projeto.yml")):
            return rel
    # Sem contrato em lugar nenhum da subida: o comportamento de antes — MAS um
    # projeto e uma PASTA. `Projeto\new-project.sh` e um arquivo solto na raiz,
    # e o fallback sozinho o devolvia como se fosse um projeto chamado
    # `new-project.sh` (foi o que barrou a edicao do proprio rito, hoje). Um
    # arquivo na raiz e da casa, nao de um projeto: nao ha dono a declarar.
    if not os.path.isdir(os.path.join(RAIZ_PROJ, partes[0])):
        return ""
    return raiz_de_projeto(caminho)


def raizes_citadas(texto: str) -> set:
    """Pastas-raiz de projeto mencionadas num comando de shell."""
    achadas = set()
    for m in RE_CAMINHO_PROJETO.finditer(texto or ""):
        nome = m.group(1)
        if nome.lower() not in TRANSVERSAIS:
            achadas.add(nome)
    return achadas


def mesmo_projeto(a: str, b: str) -> bool:
    return bool(a) and bool(b) and a.lower() == b.lower()
