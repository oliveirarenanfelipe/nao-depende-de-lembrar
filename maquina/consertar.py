# -*- coding: utf-8 -*-
"""O CONSERTO — o elo que faltava entre MEDIR e ARRUMAR.

    python maquina/consertar.py             # o que da para consertar, sem tocar
    python maquina/consertar.py --aplicar   # conserta (local; NUNCA commita)
    python maquina/consertar.py --json      # para o bloco [6u] do mente_health
    python maquina/consertar.py --projeto Nome [--aplicar]

POR QUE ESTA PECA EXISTE
------------------------
A frase que definiu o projeto inteiro:

    *"tem muita coisa que a gente nao faz. ou se faz eu nao tenho o
    conhecimento, ou as vezes faz e as vezes esquece, depende de eu lembrar de
    ficar pedindo."*

Ate aqui a maquina respondia METADE disso. O `o_basico` MEDIA os 30 projetos
todo dia e dizia, por exemplo, que faltavam 18 CIs. O `ligar_ci` SABIA
consertar CI. E nada ligava os dois: alguem tinha de ler o numero e rodar o
conserto. Esse alguem era eu, quando lembrava — que e exatamente a frase acima,
um nivel abaixo.

Medir sem consertar nao e diagnostico, e uma lista de defeitos para cacar um a
um — o habito que ja tinha sido nomeado como errado nesta casa:
*"ele tem que ser consertado automaticamente quando a gente resolver nosso
problema estrutural."* Esta peca e esse conserto automatico.

🔴 O QUE ELA NAO CONSERTA, E POR QUE (a recusa e a parte mais importante)
------------------------------------------------------------------------
Duas colunas do `o_basico` ficam de fora DE PROPOSITO. Nao e limitacao
tecnica; e que consertar automatico ali produziria uma mentira verde:

  · `tst` (teste escrito) — teste gerado por maquina nao testa nada e passa
    sempre. A D-05 ja diz: *"CI sem teste para rodar e verde permanente, e
    verde que nao testa nada e a unica coisa pior que CI nenhum."* Gerar
    esqueleto de teste faria o placar subir e a casa piorar.
  · `dec` (decisoes registradas) — decisao e CONTEUDO, nao estrutura. Um
    `DECISIONS.md` vazio vira reliquia, e a casa ja tem a prova medida: o unico
    documento de requisitos de verdade tem UM commit, congelado enquanto o
    projeto produzia 18 stories.

Para esses dois a peca ACUSA com nome e caminho, e nao escreve. Numero que
sobe porque a maquina se auto-serviu e pior que numero parado.

🔑 PROVA ANTES DE GRAVAR (D-03), caso a caso
--------------------------------------------
A regra da casa e *peca que produz artefato prova o artefato antes de grava-lo*.
Aqui cada familia tem uma prova diferente, e o tipo de prova esta declarado:

  projeto.yml  EXECUTAVEL, antes   o texto passa pelo `fundacao_na_porta
                                   .ler_projeto_yml` e os 10 campos aparecem
  .gitleaks    EXECUTAVEL, antes   o TOML e parseado de verdade (tomllib)
  .gitignore   EXECUTAVEL, depois  grava e pergunta ao `git check-ignore` se
                                   ele esta em vigor; se nao, DESFAZ
  CI           EXECUTAVEL, antes   delegado ao `ligar_ci`, que roda o comando
                                   de teste e recusa emitir o que nao passa

E no fim de tudo ela REMEDE a casa e exige que o placar tenha subido. Conserto
que nao move o medidor nao foi conserto — foi arquivo escrito.

A FRONTEIRA, e ela e a mesma do `CLAUDE.md` deste projeto: esta maquina
legitimamente TOCA outros projetos, porque mede e conserta a casa inteira. Mas
**commitar e empurrar no repositorio de outro dono e dele**. Esta peca escreve
no working tree e mostra o que escreveu. Quem publica e quem responde pelo
repositorio.

CHAMADOR: o verificador diario de saude da casa (diagnostico, sem
`--aplicar`), e a mao de quem opera, quando quiser aplicar.
PROVA:    `maquina/testar_consertar.py`, com mutacao.
"""
import io
import json
import os
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                           # noqa: BLE001
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import ligar_ci                                             # noqa: E402
import o_basico as ob                                       # noqa: E402

HOOKS = os.path.join(os.path.expanduser("~"), ".claude", "hooks")


def _porta_fundacao():
    """O gate do contrato, importado tarde: se ele quebrar, o conserto do
    `projeto.yml` para — e nao leva junto os outros tres."""
    if HOOKS not in sys.path:
        sys.path.insert(0, HOOKS)
    import fundacao_na_porta
    return fundacao_na_porta


# Os 10 campos do contrato, para quando o gate NAO esta na maquina.
#
# 🔴 ELA E INDEPENDENTE DO TEMPLATE DE PROPOSITO, e o caminho ate aqui tem
# duas curvas que valem mais que a lista:
#
#   1. escrevi a lista a mao e ela divergiu na primeira execucao — tres campos
#      que o `CONTRATO` nao tem;
#   2. troquei por uma lista DERIVADA do proprio `CONTRATO`, e a suite acusou
#      na hora: a mutacao "contrato sem 8 dos 10 campos" passou a SOBREVIVER,
#      porque derivar do template e comparar o template consigo mesmo. Era
#      literalmente a peca concordando com ela propria, que e o defeito que o
#      comentario logo abaixo diz estar evitando.
#
# Entao a lista fica aqui, escrita, e quem garante que ela nao envelhece e o
# `testar_consertar.py`: ele exige que ela bata com o que o `CONTRATO` gera E,
# onde o gate existe, com o que o gate cobra. Lista digitada com guardiao
# executavel e diferente de lista digitada e esquecida.
CAMPOS_DO_CONTRATO = ["nome", "owner", "lifecycle", "o_que_e",
                      "efeito_no_mundo", "dado_de_cliente", "onde_roda",
                      "teste", "ci", "trabalho_aberto"]


def _ler_contrato_fraco(texto):
    """Le `chave: valor` do contrato que esta peca acabou de gerar.

    🔴 POR QUE ISTO EXISTE, e por que NAO e uma segunda implementacao do gate.
    O `conserta_id` so grava depois de provar que o texto e legivel — e o
    leitor de verdade e o do gate, porque duas pecas concordando sobre o mesmo
    arquivo vale mais que uma peca concordando consigo mesma. So que o gate
    vive fora desta pasta e nao acompanha a maquina quando ela e publicada:
    medido ao rodar a versao destilada numa casa vazia, onde `conserta_id`
    respondia `nao consegui provar contra o gate` e simplesmente NUNCA
    escrevia. Publicar uma peca com um quarto das funcoes morta e pior que nao
    publicar: quem baixa nao sabe que aquilo nunca funcionou.
    """
    campos = {}
    for linha in texto.split(chr(10)):
        nu = linha.split("#")[0].strip()
        if ":" not in nu:
            continue
        chave, _, valor = nu.partition(":")
        chave = chave.strip()
        if chave:
            campos[chave] = valor.strip()
    return campos


# ── os artefatos, e cada um veio de um lugar que ja existia na casa ──────────

# Reusado do `.gitleaks.toml` que a casa ja escreveu em 5 projetos
# (#209sec). Inventar um segundo formato seria criar duas verdades sobre "o que
# conta como segredo" — o defeito de
# [[concept_a_identidade_do_registro_tem_de_ser_uma]].
GITLEAKS = """# gitleaks — trava de secret. Estende as regras padrao.
# Escrito por `maquina/consertar.py`, no formato que a casa ja usa.
# Dado ou falso positivo especifico: acrescentar por caso.
[extend]
useDefault = true

[allowlist]
description = "Vendor/build/lock — nunca secret nosso"
paths = [
  '''(^|/)node_modules/''',
  '''(^|/)\\.next/''',
  '''(^|/)\\.venv/''',
  '''(^|/)dist/''',
  '''(^|/)build/''',
  '''(^|/)out/''',
  '''package-lock\\.json$''',
  '''pnpm-lock\\.yaml$''',
  '''yarn\\.lock$''',
  '''.*\\.min\\.(js|css)$''',
]
"""

IGNORE_BASE = [".env", ".env.*", "!.env.example", ".DS_Store", "Thumbs.db"]
IGNORE_PY = ["__pycache__/", "*.pyc", ".venv/", "venv/", ".pytest_cache/"]
IGNORE_JS = ["node_modules/", "dist/", "build/", ".next/", "out/"]

# O contrato de 10 campos, com os valores VAZIOS. A decisao e dura e esta
# registrada: *"o rito nao inventa placeholder"* — placeholder
# preencheria o campo e o gate deixaria passar sem ninguem ter respondido, que
# e o defeito exato que o rito existe para matar. Campo vazio faz o gate cobrar,
# com o nome do que falta.
CONTRATO = """# O contrato de partida deste projeto.
#
# Gerado VAZIO por `maquina/consertar.py`. Isto e deliberado: o gate
# `fundacao_na_porta.py` vai RECUSAR a primeira escrita de codigo aqui ate os
# campos serem respondidos, e e assim que ele cobra a pergunta em vez de
# aceitar uma resposta inventada por maquina.
#
# O detalhe de cada campo esta em `Projeto/_shared/projeto.yml.modelo`.

nome: %(nome)s
owner:
# experimental | producao | pausado | aposentado
lifecycle:
# Uma frase: o que este projeto constroi, e para quem.
o_que_e:
# nenhum | publica | mensagem | cobranca | deploy
efeito_no_mundo:
# nao | sim
dado_de_cliente:
# local | github_actions | cloudflare | railway | vps | hostgator | aws | outro
onde_roda:
# nenhum | manual | automatizado
teste:
# nao | sim
ci:
# onde mora a fila de trabalho aberto
trabalho_aberto:
"""


def _grava(caminho, texto):
    pasta = os.path.dirname(caminho)
    if pasta:
        os.makedirs(pasta, exist_ok=True)
    with io.open(caminho, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(texto)


# ── os quatro consertos ─────────────────────────────────────────────────────

def conserta_ign(base, nome, aplicar):
    alvo = os.path.join(base, ".gitignore")
    if os.path.isfile(alvo):
        return None, "ja existe"
    linhas = list(IGNORE_BASE)
    rel = [a[len(base) + 1:] for a in ob.arquivos(base)]
    if any(r.endswith(".py") for r in rel):
        linhas += IGNORE_PY
    if any(r.endswith((".js", ".ts", ".tsx", ".mjs")) for r in rel) or \
            os.path.isfile(os.path.join(base, "package.json")):
        linhas += IGNORE_JS
    texto = "\n".join(linhas) + "\n"
    if not aplicar:
        return True, "escreveria %d linhas" % len(linhas)
    _grava(alvo, texto)
    # PROVA DEPOIS, com desfazer: pergunta ao proprio git se o arquivo entrou em
    # vigor. Texto plausivel que o git nao le e o modo de falha desta familia.
    try:
        r = subprocess.run(["git", "check-ignore", "-q", ".env"],
                           cwd=base, capture_output=True, timeout=60)
        vale = r.returncode == 0
    except Exception:                                       # noqa: BLE001
        vale = False
    if not vale:
        os.remove(alvo)
        return False, "o git NAO leu o .gitignore escrito — desfeito"
    return True, "escrito e conferido no `git check-ignore`"


def conserta_id(base, nome, aplicar):
    alvo = os.path.join(base, "projeto.yml")
    if os.path.isfile(alvo):
        return None, "ja existe"
    texto = CONTRATO % {"nome": os.path.basename(base)}
    # PROVA ANTES: o leitor do proprio gate enxerga os 10 campos neste texto?
    # Quando o gate esta na maquina, e ELE quem responde — prova cruzada entre
    # duas pecas. Quando nao esta (a maquina publicada nao o leva junto), a
    # prova ainda acontece, com o leitor fraco daqui, e o detalhe DIZ qual das
    # duas foi. Prova fraca declarada e honesta; prova que nao acontece e o
    # verde sobre o nada.
    prova = "gate"
    try:
        porta = _porta_fundacao()
        pasta = os.path.join(base, ".prova_contrato")
        _grava(os.path.join(pasta, "projeto.yml"), texto)
        campos = porta.ler_projeto_yml(pasta)
        obrigatorios = list(porta.OBRIGATORIOS)
        try:
            os.remove(os.path.join(pasta, "projeto.yml"))
            os.rmdir(pasta)
        except OSError:
            pass
    except ImportError:
        prova = "leitor proprio (o gate nao esta nesta maquina)"
        campos = _ler_contrato_fraco(texto)
        obrigatorios = list(CAMPOS_DO_CONTRATO)
    except Exception as e:                                  # noqa: BLE001
        return False, "nao consegui provar contra o gate (%s)" % type(e).__name__
    faltando = [c for c in obrigatorios if c not in campos]
    if faltando:
        return False, "o leitor nao veria os campos: %s" % ", ".join(faltando)
    if not aplicar:
        return True, "escreveria o contrato com os 10 campos vazios (%s)" % prova
    _grava(alvo, texto)
    return True, "escrito vazio, provado pelo %s" % prova


def conserta_sec(base, nome, aplicar):
    alvo = os.path.join(base, ".gitleaks.toml")
    if os.path.isfile(alvo):
        return None, "ja existe"
    # PROVA ANTES: o TOML e parseado de verdade. Config invalida faz o gitleaks
    # abortar, e um scanner que aborta le igual a um scanner que nao achou nada
    # — [[concept-a-cegueira-que-responde-200]].
    try:
        import tomllib
        tomllib.loads(GITLEAKS)
    except ImportError:
        pass                        # Python < 3.11: segue sem esta prova
    except Exception as e:                                  # noqa: BLE001
        return False, "o TOML nao parseia (%s)" % type(e).__name__
    if not aplicar:
        return True, "escreveria a config no formato que a casa ja usa"
    _grava(alvo, GITLEAKS)
    return True, "escrito no formato que a casa ja usa"


def conserta_cit(base, nome, aplicar):
    """Delegado ao `ligar_ci`, que ja roda o comando antes de emitir o CI.

    ⚠️ So se aplica a quem TEM teste escrito. Sem esta guarda o conserto era
    tentado nos 13 projetos sem teste e devolvia 17 recusas de "sem receita"
    `[medido na 1a rodada]` — ruido que dizia "recusei consertar" onde a
    verdade era "nao ha o que ligar", e que ja aparece na recusa `tst`. Relatorio
    que infla a coluna do fracasso ensina a ignorar a coluna.
    """
    if not ob.medir_projeto(base)["tst"]:
        return None, "sem teste escrito — nao ha o que o CI rode (ver `tst`)"
    try:
        ok = ligar_ci.um(nome, escrever=aplicar)
    except Exception as e:                                  # noqa: BLE001
        return False, "o ligar_ci quebrou (%s)" % type(e).__name__
    return (True, "CI escrito, com o comando provado antes") if ok else \
        (False, "o ligar_ci recusou (sem receita, ou o teste nao passa)")


CONSERTOS = [
    ("ign", ".gitignore", conserta_ign),
    ("id", "contrato projeto.yml", conserta_id),
    ("sec", "varredura de segredo", conserta_sec),
    ("cit", "CI que RODA o teste", conserta_cit),
]

RECUSADOS = [
    ("tst", "teste escrito",
     "teste gerado por maquina passa sempre; o placar subiria e a casa "
     "pioraria (D-05)"),
    ("dec", "decisoes registradas",
     "decisao e conteudo, nao estrutura; arquivo vazio vira reliquia "
     "(o prd.md de 1 commit)"),
]


def levantar(aplicar=False, so=None):
    dados, _fora = ob.medir()
    antes = {k: sum(1 for v in dados.values() if v[k]) for k in ob.ITENS}
    acoes, recusas = [], []
    for nome in sorted(dados):
        if so and so != nome:
            continue
        base = os.path.join(ob.RAIZ, nome.replace("/", os.sep))
        for chave, rotulo, funcao in CONSERTOS:
            if dados[nome][chave]:
                continue
            feito, detalhe = funcao(base, nome, aplicar)
            if feito is None:
                continue
            acoes.append({"projeto": nome, "item": chave, "rotulo": rotulo,
                          "ok": bool(feito), "detalhe": detalhe})
        for chave, rotulo, porque in RECUSADOS:
            if not dados[nome][chave]:
                recusas.append({"projeto": nome, "item": chave,
                                "rotulo": rotulo, "porque": porque})
    depois = antes
    if aplicar:
        dados2, _ = ob.medir()
        depois = {k: sum(1 for v in dados2.values() if v[k]) for k in ob.ITENS}
    return acoes, recusas, antes, depois, len(dados)


def main():
    aplicar = "--aplicar" in sys.argv
    so = None
    if "--projeto" in sys.argv:
        i = sys.argv.index("--projeto")
        if i + 1 < len(sys.argv):
            so = sys.argv[i + 1]

    acoes, recusas, antes, depois, total = levantar(aplicar, so)
    feitas = [a for a in acoes if a["ok"]]
    falhas = [a for a in acoes if not a["ok"]]

    if "--json" in sys.argv:
        print(json.dumps({
            "projetos": total, "aplicou": aplicar,
            "consertaveis": len(feitas), "recusou_conserto": len(falhas),
            "nao_se_conserta": len(recusas),
            "antes": antes, "depois": depois,
            "subiu": {k: depois[k] - antes[k] for k in antes},
        }, ensure_ascii=False))
        return 0

    print("O CONSERTO — %d projetos, modo %s"
          % (total, "APLICAR" if aplicar else "diagnostico"))
    print()
    if feitas:
        print("  DA PARA CONSERTAR (%d):" % len(feitas))
        for a in feitas:
            print("    %-28s %-22s %s"
                  % (a["projeto"][:28], a["rotulo"], a["detalhe"]))
    else:
        print("  nada a consertar nas 4 familias automaticas.")
    if falhas:
        print()
        print("  TENTOU E RECUSOU (%d) — a peca nao grava o que nao provou:"
              % len(falhas))
        for a in falhas:
            print("    %-28s %-22s %s"
                  % (a["projeto"][:28], a["rotulo"], a["detalhe"]))
    if recusas:
        print()
        print("  NAO SE CONSERTA SOZINHO (%d) — de proposito:" % len(recusas))
        vistos = set()
        for r in recusas:
            if r["item"] not in vistos:
                vistos.add(r["item"])
                print("    [%s] %s" % (r["item"], r["porque"]))
        for item in sorted(vistos):
            quais = [r["projeto"] for r in recusas if r["item"] == item]
            print("    %-5s %d projeto(s): %s%s"
                  % (item, len(quais), ", ".join(quais[:5]),
                     " ..." if len(quais) > 5 else ""))

    print()
    print("  PLACAR  %s" % "  ".join("%s %d" % (k, antes[k]) for k in ob.ITENS))
    if aplicar:
        print("  DEPOIS  %s" % "  ".join("%s %d" % (k, depois[k])
                                         for k in ob.ITENS))
        subiu = sum(depois[k] - antes[k] for k in ob.ITENS)
        # O GATE DA PROPRIA PECA. Conserto que nao move o medidor nao foi
        # conserto, foi arquivo escrito — e o pior desfecho possivel aqui e
        # sair verde tendo gravado coisa nenhuma.
        if feitas and subiu <= 0:
            print("  !! GRAVEI %d conserto(s) e o placar NAO subiu. Isto e "
                  "falha: o medidor nao viu o que a peca escreveu." % len(feitas))
            return 1
        print("  o placar subiu %d ponto(s)." % subiu)
        print()
        print("  🔴 NADA FOI COMMITADO. Escrever no working tree de outro "
              "projeto e desta maquina; publicar no repositorio dele e de "
              "quem responde por ele.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
