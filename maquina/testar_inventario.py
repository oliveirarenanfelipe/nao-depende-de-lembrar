# -*- coding: utf-8 -*-
"""Prova do `inventario.py` — com mutação nos dois sentidos.

    python maquina/testar_inventario.py

O mapa da máquina só vale se ACUSAR quando a máquina quebra. Um inventário
que diz "tudo ok" porque não olha nada é pior que nenhum: dá a sensação de
cobertura sem a cobertura.

Por isso as checagens aqui são quase todas sobre o ACUSAR — peça sumida do
disco, teste que reprova, peça sem teste — e a mutação desarma justamente a
execução do teste, que é a única coisa que o mapa sabe e um README não.

CHAMADOR: o verificador diário de saúde da casa.
"""
import io
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
import inventario as inv                                    # noqa: E402

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


def escreve(p, t):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, "w", encoding="utf-8", newline=chr(10)).write(t)


print("== PROVA DO MAPA DA MAQUINA ==" + N)

print("== 1. O MAPA DA CASA REAL ==")
real = inv.levantar(rodar_testes=False)
diz("lista as %d pecas declaradas" % len(inv.PECAS),
    len(real) == len(inv.PECAS))
sumidas = [d["nome"] for d in real if not d["existe"]]
diz("nenhuma peca da maquina sumiu do disco", not sumidas, str(sumidas))
diz("toda peca declara QUEM a chama",
    all(d["chamador"] for d in real),
    str([d["nome"] for d in real if not d["chamador"]]))

print(N + "== 2. ACUSA QUANDO A MAQUINA QUEBRA ==")
banca = tempfile.mkdtemp(prefix="inv-")
pecas_orig = inv.PECAS
try:
    escreve(os.path.join(banca, "peca_boa.py"), "print('ok')" + N)
    escreve(os.path.join(banca, "testar_boa.py"), "print('ok')" + N)
    escreve(os.path.join(banca, "peca_ruim.py"), "print('ok')" + N)
    escreve(os.path.join(banca, "testar_ruim.py"),
            "import sys" + N + "sys.exit(1)" + N)

    inv.PECAS = [
        ("t", "peca_boa", banca, "testar_boa.py", "alguem"),
        ("t", "peca_ruim", banca, "testar_ruim.py", "alguem"),
        ("t", "peca_sumida", banca, "", "alguem"),
    ]
    d = inv.levantar(rodar_testes=True)
    por = {x["nome"]: x for x in d}

    diz("peca com teste que PASSA fica verde",
        por["peca_boa"]["passa"] is True)
    diz("peca com teste que REPROVA e ACUSADA",
        por["peca_ruim"]["passa"] is False)
    diz("peca que nao existe no disco e ACUSADA",
        not por["peca_sumida"]["existe"])
    diz("peca sem teste e ACUSADA como sem teste",
        not por["peca_sumida"]["teste_existe"])

    print(N + "== 3. MUTACAO (desarmar a execucao tem de cegar o mapa) ==")
    roda_orig = inv.roda
    try:
        inv.roda = lambda p: True          # finge que tudo passa
        cego = {x["nome"]: x
                for x in inv.levantar(rodar_testes=True)}
        det = cego["peca_ruim"]["passa"] is True
    finally:
        inv.roda = roda_orig
    print("  [%s] sem rodar o teste, a peca QUEBRADA aparece verde"
          % ("DETECTADA" if det else "SOBREVIVEU"))
    if not det:
        FALHA += 1

    print("  -- controle --")
    volta = {x["nome"]: x for x in inv.levantar(rodar_testes=True)}
    diz("com a execucao armada, volta a acusar",
        volta["peca_ruim"]["passa"] is False)

    print(N + "== 4. O MODO RAPIDO NAO MENTE ==")
    r = {x["nome"]: x for x in inv.levantar(rodar_testes=False)}
    diz("sem rodar, o veredito e `nao sei` e nao `passa`",
        r["peca_ruim"]["passa"] is None and r["peca_boa"]["passa"] is None)

    # -- 5. A FONTE DO MAPA E DADO, E SUMIR COM ELA E ERRO --------------------
    # O mapa saiu do codigo para `mapa.json` porque a copia publicada lia os
    # hooks da casa de origem. O risco NOVO que isso cria e o unico que nao se
    # descobre depois: se o arquivo sumir e a peca cair para lista vazia, ela
    # responde `nenhuma peca quebrada` sobre NENHUMA peca — e o painel fica
    # verde sobre o nada. Entao a regra e falhar alto, e e o que se prova aqui.
    print(N + "== 5. o mapa e DADO, e some-lo e ERRO (nao lista vazia) ==")

    try:
        inv.carregar_mapa(os.path.join(banca, "nao_existe.json"))
        levantou = False
    except Exception:                                       # noqa: BLE001
        levantou = True
    diz("SEM o mapa, levanta erro em vez de devolver lista vazia", levantou)

    vazio = os.path.join(banca, "mapa_vazio.json")
    escreve(vazio, '{"pecas": []}' + N)
    try:
        inv.carregar_mapa(vazio)
        levantou2 = False
    except ValueError:
        levantou2 = True
    except Exception:                                       # noqa: BLE001
        levantou2 = False
    diz("com `pecas` vazio, levanta ValueError", levantou2)

    torto = os.path.join(banca, "mapa_torto.json")
    escreve(torto, '{"pecas": [{"camada": "t", "nome": "x", '
                   '"onde": "LUGAR_QUE_NAO_EXISTE", "teste": "", '
                   '"chamador": "alguem"}]}' + N)
    try:
        inv.carregar_mapa(torto)
        levantou3 = False
    except ValueError:
        levantou3 = True
    except Exception:                                       # noqa: BLE001
        levantou3 = False
    diz("lugar desconhecido REPROVA, nao vira caminho inventado", levantou3)

    bom = os.path.join(banca, "mapa_bom.json")
    escreve(bom, '{"pecas": [{"camada": "t", "nome": "x", "onde": "FUND", '
                 '"teste": "testar_x.py", "chamador": "alguem"}]}' + N)
    lidas = inv.carregar_mapa(bom)
    diz("mapa valido vira a tupla que o resto da peca espera",
        lidas == [("t", "x", inv.FUND, "testar_x.py", "alguem")], str(lidas))

    # A mutacao do grupo 5: o carregador para de gritar e passa a engolir.
    # E o modo de falha silencioso do dado ausente — o painel fica verde
    # porque nao ha nada para estar vermelho.
    carregar_orig = inv.carregar_mapa
    try:
        inv.carregar_mapa = lambda fonte=None: []
        inv.PECAS = inv.carregar_mapa()
        mudo = inv.levantar(rodar_testes=False)
        det = mudo == []
    finally:
        inv.carregar_mapa = carregar_orig
        inv.PECAS = [("t", "peca_boa", banca, "testar_boa.py", "alguem"),
                     ("t", "peca_ruim", banca, "testar_ruim.py", "alguem"),
                     ("t", "peca_sumida", banca, "", "alguem")]
    print("  [%s] mapa vazio faz o inventario medir ZERO peca e nao acusar"
          % ("DETECTADA" if det else "SOBREVIVEU"))
    if not det:
        FALHA += 1

    print("  -- controle --")
    diz("com o mapa de volta, o inventario volta a listar",
        len(inv.levantar(rodar_testes=False)) == 3)
finally:
    inv.PECAS = pecas_orig
    shutil.rmtree(banca, ignore_errors=True)

print(N + "=== RESULTADO: %d PASS / %d FALHA ===" % (PASS, FALHA))
sys.exit(1 if FALHA else 0)
