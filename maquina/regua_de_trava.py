# -*- coding: utf-8 -*-
r"""A TRAVA DE PUBLICACAO SAI DO CONTRATO, NAO DA MAO.

Nasceu de uma pergunta do dono da casa, verbatim:

    *"dependendo do que vamos criar profissionalmente essas travas tem que ser
    mais profissionais, estou errado?"*

    *"se abrirmos projetos novos, eu acho que vale esse lembrete, de que e
    recomendado ter o git x para poder rodar y feature mas que tem a saida que
    ta sendo criada"*

DE ONDE VEIO A PERGUNTA. Um push num projeto em producao foi RECUSADO pelo
proprio GitHub — `! [remote rejected] main -> main (protected branch hook
declined)` — e a ordem foi aprender com o mecanismo em vez de contorna-lo.

O QUE AQUELE REPO TEM, medido na API: `required_status_checks` com 3
contextos, `enforce_admins: true` (vale ate para o dono — foi isso que
barrou), `allow_force_pushes: false`, `allow_deletions: false`. E
`required_approving_review_count: 0`: nao e burocracia com outra pessoa, e
trava contra o acidente.

🔴 O OBSTACULO, medido no mesmo dia: protecao de branch NAO EXISTE em repo
privado de conta Free. Todos os repos privados testados devolveram
`403 "Upgrade to GitHub Pro or make this repository public"`; so os PUBLICOS
responderam. Onde a conta tem plano pago, funciona.
Obstaculo medido nao e ausencia de caminho: existe a saida local, e ela
esta escrita em cada recomendacao abaixo.

POR QUE A REGUA E DERIVADA, e nao uma recomendacao generica. "Este projeto e
profissional?" e uma pergunta que cada sessao responde diferente, e recomendacao
que nao muda com a resposta vira ruido que se aprende a pular. Os campos que
decidem JA existem no `projeto.yml` — `efeito_no_mundo`, `dado_de_cliente`,
`lifecycle` — e foram respondidos no rito que funda o projeto, pelo dono, no dia zero.
A regua so LE o que ele ja disse. E a regra que vale para tudo aqui: defeito
pontual nao vira item de lista, vira capacidade que a estrutura garante.

O LEMBRETE TEM TRES PARTES, e omitir qualquer uma o inutiliza — foi ele quem
exigiu a terceira: **o que e recomendado · o que custa · a saida que existe
aqui**. Recomendacao sem custo faz prometer o que nao se pode pagar;
recomendacao sem saida deixa o projeto sem nada enquanto a conta nao muda.

Chamador: o rito que funda projeto novo, no mesmo commit.
Prova: `maquina/testar_regua_de_trava.py`, com mutacao.
"""
from __future__ import annotations

import io
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001,S110 - sem stdout nao ha para onde avisar
    pass

# 🔴 O CAMINHO DA PROPRIA MAQUINA E DERIVADO DO DISCO, e nao pode ser uma
# constante. Aqui ela mora dentro da casa; no repositorio publico ela E a raiz.
# Uma string fixa estaria errada num dos dois mundos, e — pior — obrigaria a
# versao publicada a divergir da interna numa linha de CODIGO, que e a unica
# divergencia que a D-04 proibe. Derivar de `__file__` acerta nos dois e tira
# o nome do projeto de dentro da logica, de uma vez.
AQUI = os.path.dirname(os.path.abspath(__file__))

# ── os niveis ───────────────────────────────────────────────────────────────
# Ordem: do mais forte para o mais fraco. O primeiro que casar vence, porque a
# trava se dimensiona pelo PIOR estrago possivel, nunca pela media.
DURA, MEDIA, NENHUMA = "dura", "media", "nenhuma"

# `efeito_no_mundo` que exige trava dura: o push vira efeito irreversivel no
# mundo real sem ninguem no meio. Sao os mesmos verbos da R2 do soberano.
EFEITO_DURO = {"deploy", "cobranca"}
EFEITO_MEDIO = {"publica", "mensagem"}


def erro(msg):
    """Diagnostico vai para stderr; stdout fica so com resultado.

    Quem chama esta peca num `|` ou num `>` precisa poder separar as duas
    coisas. Misturadas, quem consome tem de adivinhar qual linha e resultado e
    qual e reclamacao.
    """
    sys.stderr.write(msg + chr(10))


def nivel(efeito: str, dado_de_cliente: str, lifecycle: str) -> str:
    """O nivel de trava que este contrato exige. So le, nao opina."""
    efeito = (efeito or "").strip().lower()
    cliente = (dado_de_cliente or "").strip().lower()
    ciclo = (lifecycle or "").strip().lower()
    if efeito in EFEITO_DURO:
        return DURA
    if cliente == "sim":
        return DURA                      # LGPD: o estrago nao volta atras
    if efeito in EFEITO_MEDIO:
        return MEDIA
    if ciclo == "producao":
        return MEDIA                     # ja tem gente dependendo
    return NENHUMA


def _porque(efeito, cliente, ciclo):
    """A frase que diz QUAL resposta dele puxou este nivel. Sem ela o lembrete
    vira opiniao da maquina, e opiniao se discute; resposta dele, nao."""
    efeito = (efeito or "").strip().lower()
    cliente = (cliente or "").strip().lower()
    ciclo = (ciclo or "").strip().lower()
    if efeito in EFEITO_DURO:
        return "voce respondeu `efeito_no_mundo: %s`" % efeito
    if cliente == "sim":
        return "voce respondeu `dado_de_cliente: sim`"
    if efeito in EFEITO_MEDIO:
        return "voce respondeu `efeito_no_mundo: %s`" % efeito
    if ciclo == "producao":
        return "voce respondeu `lifecycle: producao`"
    return ("voce respondeu `efeito_no_mundo: %s`, `dado_de_cliente: %s` e "
            "`lifecycle: %s`" % (efeito or "nenhum", cliente or "nao",
                                 ciclo or "experimental"))


# As tres partes, por nivel. Cada valor e (recomendado, custo, saida_daqui).
TEXTO = {
    DURA: (
        "protecao de branch com verificacao OBRIGATORIA: o GitHub recusa o "
        "push se o teste falhar, e `enforce_admins` faz isso valer ate para "
        "voce. Mais `allow_force_pushes: false` e `allow_deletions: false`, "
        "para a historia nao poder ser reescrita.",
        "NAO existe em repo privado de conta Free — a API devolve `403 "
        "Upgrade to GitHub Pro or make this repository public` [medido]. "
        "Ou o repo e publico, ou o plano e pago (`Team US$4/usuario/mes nos 12 "
        "primeiros meses` [medido: github.com/pricing]).",
        "hook `pre-push` local que roda o teste do projeto e RECUSA o push "
        "quando ele falha. E gratis e funciona hoje. Fraqueza declarada, nao "
        "escondida: roda na sua maquina, se contorna com `--no-verify`, e nao "
        "protege o que chega de fora.",
    ),
    MEDIA: (
        "CI que roda o teste a cada push, e o resultado vinculado ao merge.",
        "o CI em si e gratis no GitHub Actions. O que custa e o BLOQUEIO — "
        "vincular o resultado exige protecao de branch, e ela cai no mesmo "
        "`403` do nivel acima quando o repo e privado em conta Free.",
        "`python %s/ligar_ci.py <projeto>` liga o CI ao teste que " % AQUI +
        "o projeto ja tem, e o `mente_health [6u]` cobra todo dia. Enquanto o "
        "bloqueio do GitHub nao existir, quem barra e a leitura do veredito.",
    ),
    NENHUMA: (
        "nenhuma trava de publicacao. Dito de proposito: silencio aqui leria "
        "como esquecimento, e recomendacao que nao muda com a resposta vira "
        "ruido que se aprende a pular.",
        "zero.",
        "o `.gitleaks.toml` no `pre-commit` ja e o piso da casa e vale para "
        "todo projeto. Se o `efeito_no_mundo` mudar depois, reabra esta regua: "
        "`python %s/regua_de_trava.py <pasta-do-projeto>`." % AQUI,
    ),
}


def lembrete(efeito: str, dado_de_cliente: str, lifecycle: str,
             nome: str = "") -> str:
    """O texto pronto para o terminal e para o disco."""
    n = nivel(efeito, dado_de_cliente, lifecycle)
    rec, custo, saida = TEXTO[n]
    cab = "TRAVA DE PUBLICACAO — nivel %s" % n.upper()
    if nome:
        cab += " (%s)" % nome
    return "\n".join([
        "",
        "  " + "-" * 68,
        "  " + cab,
        "  " + "-" * 68,
        "  Por que este nivel: %s." % _porque(efeito, dado_de_cliente,
                                             lifecycle),
        "",
        "  RECOMENDADO : %s" % rec,
        "",
        "  CUSTO       : %s" % custo,
        "",
        "  A SAIDA AQUI: %s" % saida,
        "  " + "-" * 68,
        "",
    ])


# ── ler o contrato do disco, para a regua servir tambem a projeto ja nascido ─
def campos(pasta: str) -> dict:
    """Le `efeito_no_mundo`, `dado_de_cliente` e `lifecycle` de um projeto.yml.

    Deliberadamente NAO importa `fundacao_na_porta.ler_projeto_yml`: aquele e um
    gate e devolve os 10 campos com validacao propria; aqui bastam 3, e importar
    um hook amarraria a maquina ao diretorio do agente, que e a fronteira que o
    `maquina/LEIA.md` mandou nao cruzar. O formato lido e o mesmo `chave: valor`
    de uma linha, e nao ha segunda gramatica: campo ausente vira "".
    """
    alvo = os.path.join(pasta, "projeto.yml")
    fora = {"efeito_no_mundo": "", "dado_de_cliente": "", "lifecycle": ""}
    if not os.path.isfile(alvo):
        return fora
    for linha in io.open(alvo, encoding="utf-8", errors="replace"):
        linha = linha.strip()
        if not linha or linha.startswith("#") or ":" not in linha:
            continue
        chave, _, valor = linha.partition(":")
        chave = chave.strip()
        if chave in fora:
            fora[chave] = valor.split("#")[0].strip()
    return fora


def main(argv) -> int:
    if len(argv) >= 4:
        efeito, cliente, ciclo = argv[1], argv[2], argv[3]
        nome = argv[4] if len(argv) > 4 else ""
    elif len(argv) == 2:
        pasta = argv[1]
        if not os.path.isdir(pasta):
            erro("pasta nao existe: %s" % pasta)
            return 2
        c = campos(pasta)
        efeito, cliente, ciclo = (c["efeito_no_mundo"], c["dado_de_cliente"],
                                  c["lifecycle"])
        nome = os.path.basename(os.path.abspath(pasta))
    else:
        print("A trava de publicacao sai do contrato, nao da mao.")
        print("\nuso:")
        print("  python regua_de_trava.py <pasta-do-projeto>")
        print("  python regua_de_trava.py <efeito> <dado_de_cliente> "
              "<lifecycle> [nome]")
        return 2
    print(lembrete(efeito, cliente, ciclo, nome))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
