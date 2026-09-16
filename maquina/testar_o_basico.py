# -*- coding: utf-8 -*-
"""Prova do `o_basico.py` — com mutação nos dois sentidos.

    python _shared/testar_o_basico.py

Este teste existe por causa de um erro concreto: a 1ª versão do medidor disse
que **um dos projetos não rodava teste no CI**, porque conhecia `npm test` e
não conhecia `turbo test`. O detector respondeu "não" sobre o produto com
cliente real, e ia virar alarme falso. Por isso metade das checagens aqui é sobre a
capacidade de RECONHECER forma — não sobre contar projeto.

Tudo roda numa casa de mentira montada em pasta temporária. A casa real é
lida só na última checagem.

CHAMADOR: o verificador diário de saúde da casa.
"""
import io
import os
import re as _re
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import o_basico as ob                                       # noqa: E402

PASS = 0
FALHA = 0
N = chr(10)


def diz(rotulo, ok, extra=""):
    global PASS, FALHA
    if ok:
        PASS += 1
        print("  PASS  %s" % rotulo)
    else:
        FALHA += 1
        print("  FALHA %s%s" % (rotulo, ("   -> " + extra) if extra else ""))


def escreve(caminho, texto):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with io.open(caminho, "w", encoding="utf-8", newline="") as fh:
        fh.write(texto)


def casa_de_mentira():
    """Uma casa com um projeto de cada tipo, para o medidor ter o que achar."""
    raiz = tempfile.mkdtemp(prefix="basico-")

    # 1. COMPLETO, e o CI roda teste na forma `turbo test`
    p = os.path.join(raiz, "completo")
    escreve(os.path.join(p, "projeto.yml"), "nome: completo" + N)
    os.makedirs(os.path.join(p, ".git", "hooks"))
    escreve(os.path.join(p, ".git", "hooks", "pre-commit"), "#!/bin/sh" + N)
    escreve(os.path.join(p, ".gitignore"), "node_modules" + N)
    escreve(os.path.join(p, "src", "x.test.ts"), "test('x', () => {})" + N)
    escreve(os.path.join(p, "DECISIONS.md"), "# decisoes" + N)
    escreve(os.path.join(p, ".github", "workflows", "ci.yml"),
            "jobs:" + N + "  t:" + N + "    steps:" + N +
            "      - run: pnpm exec turbo test" + N)

    # 2. teste que NINGUEM roda — o buraco que a peca existe para ver
    p = os.path.join(raiz, "orfao")
    os.makedirs(os.path.join(p, ".git"))
    escreve(os.path.join(p, "test_x.py"), "def test_x(): pass" + N)
    escreve(os.path.join(p, ".github", "workflows", "deploy.yml"),
            "jobs:" + N + "  d:" + N + "    steps:" + N +
            "      - run: npm run build" + N)

    # 3. pasta que NAO e projeto
    escreve(os.path.join(raiz, "so_uma_pasta", "foto.txt"), "nada" + N)

    # 4. o mesmo projeto vivendo tambem como WORKTREE dentro de outro
    p = os.path.join(raiz, "hospedeiro")
    os.makedirs(os.path.join(p, ".git"))
    escreve(os.path.join(p, "DECISIONS.md"), "# dono" + N)
    wt = os.path.join(p, "completo-wt")
    escreve(os.path.join(wt, ".git"), "gitdir: ../../completo/.git/wt" + N)
    escreve(os.path.join(wt, "src", "x.test.ts"), "test('x', () => {})" + N)
    return raiz


print("== PROVA DO MEDIDOR DO BASICO ==" + N)
raiz = casa_de_mentira()
try:
    dados, fora = ob.medir(raiz)
    n, placar, orfaos = ob.resumo(dados)

    print("== 1. LE A CASA COMO ELA E ==")
    diz("conta 3 projetos e deixa a pasta solta de fora",
        n == 3 and fora == ["so_uma_pasta"], "n=%d fora=%s" % (n, fora))
    diz("o projeto completo marca os 7 itens",
        all(dados["completo"][k] for k in ob.ITENS))
    diz("reconhece `turbo test` como CI que roda teste",
        "turbo test" in dados["completo"]["_prova_ci"],
        dados["completo"]["_prova_ci"])
    diz("o orfao tem teste e NAO tem CI que rode",
        dados["orfao"]["tst"] and not dados["orfao"]["cit"])
    diz("workflow que so faz build nao conta como teste",
        dados["orfao"]["_workflows"] == 1 and not dados["orfao"]["cit"])
    diz("o BURACO e nomeado", orfaos == ["orfao"], str(orfaos))
    diz("worktree nao vira projeto novo nem duplica teste",
        "completo-wt" not in dados and dados["hospedeiro"]["tst"] is False,
        str(sorted(dados)))

    print(N + "== 2. RECONHECE AS FORMAS (foi aqui que a 1a versao errou) ==")
    FORMAS = [
        ("turbo test", "      - run: pnpm exec turbo test"),
        ("npm test", "      - run: npm test"),
        ("pytest", "      - run: pytest -q"),
        ("vitest", "      - run: npx vitest run"),
        ("go test", "      - run: go test ./..."),
        ("script da casa", "      - run: python scripts/testar_tudo.py"),
    ]
    for rotulo, linha in FORMAS:
        p = os.path.join(raiz, "forma")
        shutil.rmtree(p, ignore_errors=True)
        os.makedirs(os.path.join(p, ".git"))
        escreve(os.path.join(p, "test_x.py"), "def test_x(): pass" + N)
        escreve(os.path.join(p, ".github", "workflows", "ci.yml"),
                "jobs:" + N + "  t:" + N + "    steps:" + N + linha + N)
        v = ob.medir_projeto(p)
        diz("reconhece `%s`" % rotulo, v["cit"], v["_prova_ci"])
    shutil.rmtree(os.path.join(raiz, "forma"), ignore_errors=True)

    print(N + "== 3. MUTACAO (quebrar tem de fazer o numero MUDAR) ==")
    ci = os.path.join(raiz, "completo", ".github", "workflows", "ci.yml")
    guardado = io.open(ci, encoding="utf-8", newline="").read()
    escreve(ci, guardado.replace("pnpm exec turbo test", "pnpm run build"))
    d2, _ = ob.medir(raiz)
    _, _, orf2 = ob.resumo(d2)
    det = (not d2["completo"]["cit"]) and "completo" in orf2
    print("  [%s] sem o comando de teste, o completo cai para o buraco"
          % ("DETECTADA" if det else "PASSOU BATIDO"))
    if not det:
        FALHA += 1
    escreve(ci, guardado)

    cmd_orig = ob.CMD_TESTE
    ob.CMD_TESTE = _re.compile(r"NUNCA_VAI_CASAR_XYZ")
    d3, _ = ob.medir(raiz)
    _, pl3, _ = ob.resumo(d3)
    det2 = pl3["cit"] == 0 and placar["cit"] > 0
    print("  [%s] reconhecedor cego zera o `ci-t` (%d -> %d)"
          % ("DETECTADA" if det2 else "PASSOU BATIDO",
             placar["cit"], pl3["cit"]))
    if not det2:
        FALHA += 1
    ob.CMD_TESTE = cmd_orig

    d4, _ = ob.medir(raiz)
    _, pl4, orf4 = ob.resumo(d4)
    diz("restaurado, o numero volta ao de antes",
        pl4 == placar and orf4 == orfaos)
finally:
    shutil.rmtree(raiz, ignore_errors=True)

print(N + "== 4. A CASA REAL ==")
# ⚠️ ESTA SECAO MEDE A LEITURA, NUNCA O TAMANHO. A versao anterior exigia
# `len(reais) > 10` — o numero DESTA casa escrito dentro do teste, que reprova
# em qualquer outra. Apareceu ao rodar a maquina destilada fora daqui: com as
# contas de exemplo, quase todo repo vira "de terceiro" e a conta cai para 3.
# O comportamento estava certo; o teste e que media a casa em vez de medir o
# medidor. E o mesmo padrao do mapa e dos nomes, so que aqui nem dado era: era
# um palpite sobre o mundo de quem roda.
# E a raiz inexistente LEVANTA, com a causa na mensagem — nao devolve vazio,
# que leria como "casa sem nada quebrado", e nao explode tres frames abaixo
# com um `FileNotFoundError` cru sobre um caminho que nem parece a raiz.
try:
    ob.medir(os.path.join(tempfile.gettempdir(), "casa-que-nao-existe"))
    erro = ""
except ValueError as e:
    erro = str(e)
except Exception as e:                                      # noqa: BLE001
    erro = "TIPO ERRADO: %s" % type(e).__name__
diz("raiz inexistente levanta ValueError nomeando a RAIZ",
    "nao existe" in erro and "RAIZ" in erro, erro[:70] or "(nao levantou)")

if os.path.isdir(ob.RAIZ):
    reais, _ = ob.medir()
    diz("a casa real e lida sem quebrar", isinstance(reais, dict))
    completos = [v for v in reais.values() if all(k in v for k in ob.ITENS)]
    diz("todo projeto lido responde os %d itens" % len(ob.ITENS),
        len(completos) == len(reais),
        "%d de %d" % (len(completos), len(reais)))
    diz("nenhuma pasta temporaria de teste sobrou na casa",
        not any(p.startswith("basico-") for p in os.listdir(ob.RAIZ)))
else:
    # Dito na cara, e nao em silencio: teste que se pula calado vira
    # decoracao. Quem roda isto sem a casa montada le a linha e sabe o que
    # deixou de ser medido.
    print("  (nao medido: `%s` nao existe nesta maquina — as checagens acima"
          % ob.RAIZ)
    print("   ja provaram o medidor contra a casa de mentira)")

print(N + "=== RESULTADO: %d PASS / %d FALHA ===" % (PASS, FALHA))
sys.exit(1 if FALHA else 0)
