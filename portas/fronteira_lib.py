# -*- coding: utf-8 -*-
r"""FRONTEIRA_LIB — o UNICO reconhecedor de "de que projeto e este caminho?".

Por que existe
--------------
Dois gates precisam da mesma resposta e nao podiam responder cada um do seu
jeito: `fronteira_de_projeto.py` (Edit|Write) e `bash_na_porta.py` (Bash).
Duas gramaticas para a mesma identidade sao duas identidades, e isso ja custou
caro aqui: dois reconhecedores divergiram, e **145 notas de um projeto eram
estrangeiras dentro do proprio projeto**.

O QUE ELE NAO FAZ: nao mexe em `memory_lib.PROJECT_MAP`. O proprio
`fronteira_de_projeto.py` avisa, na linha 49, que mexer no mapa muda como o
recall pontua projeto. Aqui o caminho e reduzido a PASTA-RAIZ do projeto ANTES
de ir ao `detect_project` — que e exatamente a forma para a qual ele foi feito
(ele nasceu recebendo o cwd, que e a raiz).

O DEFEITO QUE ISTO CONSERTA `[medido]`
--------------------------------------
O reconhecedor antigo juntava TODO o caminho com hifen:

    <projetos>\Nome-Do-Projeto             -> nome-do-projeto
    <projetos>\Nome-Do-Projeto\docs        -> nome-do-projeto-docs   (!)

Quando o projeto esta num mapa conhecido, o casamento por substring salva.
Quando NAO esta, a subpasta vira outro projeto e o gate barra escrita legitima
dentro de casa. Medido: **15 dos 33** diretorios sofriam disso.

Gate que reprova o caso legitimo ensina a contornar o gate. Foi assim que uma
sessao aprendeu a repetir a gravacao ate passar, e a repeticao virou habito.

Chamadores: `fronteira_de_projeto.py`, `bash_na_porta.py`.
Teste: `testar_fronteira.py` (o grupo 2b prova o carregamento do `casa.json`)
       e `testar_fronteira_bash.py` (o acoplamento com a porta do Bash).

⚠️ Por muito tempo esta linha citou um arquivo de teste que NUNCA existiu. E o
mesmo defeito que esta casa ja pegou duas vezes — o rotulo da prova escrito no
codigo e a prova ausente do disco — e passou despercebido porque esta peca nao
estava no mapa da maquina: ninguem media se o teste que ela declara existe.
Peca fora do mapa nao e medida, e nao ser medida le igual a nao existir.
"""
from __future__ import annotations

import io
import json
import os
import re
import tempfile

HOME = os.path.expanduser("~")

# 🔴 ONDE A CASA MORA SAIU DO CODIGO, e o sintoma seria mudo. A regex
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

# Caminho sob a pasta dos projetos em qualquer das grafias que aparecem num
# comando de shell: caminho Windows com barra invertida ou normal, caminho
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
      · uma pasta guarda-chuva com duas etapas dentro: cada etapa e um projeto
        com contrato, memoria e repo proprios, e as duas viravam o nome do pai
        — a escrita na propria memoria delas era negada;
      · `Projeto\\new-project.sh` e um ARQUIVO na raiz, e virava um "projeto"
        chamado `new-project-sh` (apanhei disto ao vivo, editando o rito);
      · um WORKTREE dentro de outro projeto resolvia como o projeto de origem
        — o gotcha que ja mordeu esta casa duas vezes.

    A lição veio de fora: um dev descrevendo a arquitetura dele passa
    `tenant_id` como CAMPO, e a casa adivinhava o equivalente a partir de uma
    string de caminho. Campo declarado nao erra de tres jeitos; deducao erra.
    O campo aqui e a EXISTENCIA do `projeto.yml` — o contrato de partida, que
    esta commitado em 25 projetos desta casa.

    🔴 NAO consertei `raiz_de_projeto`, e o motivo e o raio, medido antes: ela
    tem 4 chamadores, e `bash_na_porta.py:306,380` compara o resultado dela com
    `raizes_citadas()` — uma regex que extrai UM nivel. Se `raiz_de_projeto`
    passasse a devolver o caminho de dois niveis, o par divergiria e a porta
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
