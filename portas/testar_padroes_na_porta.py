#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Teste do `padroes_na_porta.py` — o gate das regras de CONSTRUCAO da casa.

Padrao da casa (igual ao testar_bash_na_porta e ao testar_gama_na_porta):
  1. DEVE BARRAR - os casos que o gate existe para pegar
  2. DEVE PASSAR - senao o gate vira pedra no caminho e alguem o desliga
  3. ESCOPO      - regra com `escopo` so vale no caminho dela
  4. DEGRAU      - regra de `vigia` NAO pode barrar na porta
  5. MUTACAO     - desarma cada detector e exige que os casos DEIXEM de ser pegos
  6. CONTROLE    - com tudo no lugar, os casos voltam a ser pegos

GUARD contra o erro: se a secao 1 falhar, a mutacao NAO roda. Naquele
dia, 4 mutacoes vieram "DETECTADAS" num gate que nao bloqueava nada — desarmar
um detector que ja pega zero continua pegando zero.

CHAMADOR: bloco [6n] do `mente_health.py` (varredura diaria, 9h).
RODAR:    python ~/.claude/hooks/testar_padroes_na_porta.py
"""

import io
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import padroes_na_porta as gate                             # noqa: E402

PASS = 0
FALHA = 0

# 🔴 OS CAMINHOS SAO MONTADOS, NAO ESCRITOS — e a razao foi medida ao publicar.
# Escritos por extenso, eles carregam o nome do usuario do disco, e a troca
# mecanica da destilacao os transformava em `<CLAUDE>\hooks\algum_gate.py`. Um
# marcador nao e caminho nenhum: o gate nao reconhecia o alvo, nao barrava, e
# esta suite passou a acusar 4 falhas de "passou e nao devia" na versao
# publicada.
#
# 🔑 O pior nao e a falha — e o que ela seria se ninguem rodasse fora de casa:
# um teste lendo VERDE sobre um gate que nunca foi consultado. Montado a
# partir da HOME, o caminho e real na maquina de quem quer que rode.
_HOME = os.path.expanduser("~")
HOOK = os.path.join(_HOME, ".claude", "hooks", "algum_gate.py")
PROJ = os.path.join(_HOME, "Projeto", "Projeto-Um", "scripts", "algo.py")


def lp(x):
    sys.stdout.buffer.write((x + "\n").encode("utf-8", "replace"))


def marcar(nome, ok, extra=""):
    global PASS, FALHA
    if ok:
        PASS += 1
        lp("  PASS  " + nome)
    else:
        FALHA += 1
        lp("  FALHA " + nome + ("   " + extra if extra else ""))


def rodar(alvo, texto, sessao="s"):
    """Chama o gate como o harness chama. Devolve (bloqueou, motivo)."""
    entrada = json.dumps({"session_id": sessao, "tool_name": "Write",
                          "tool_input": {"file_path": alvo, "content": texto}})
    stdin_antigo, stdout_antigo = sys.stdin, sys.stdout
    cap = io.StringIO()
    try:
        sys.stdin = type("F", (), {"buffer": io.BytesIO(entrada.encode())})()
        sys.stdout = cap
        gate.main()
    finally:
        sys.stdin, sys.stdout = stdin_antigo, stdout_antigo
    s = cap.getvalue().strip()
    if not s:
        return False, ""
    try:
        d = json.loads(s)
    except ValueError:
        return False, s
    h = d.get("hookSpecificOutput") or {}
    return h.get("permissionDecision") == "deny", \
        h.get("permissionDecisionReason", "")


# -- estado isolado ----------------------------------------------------------
SANDBOX = tempfile.mkdtemp(prefix="padroes_teste_")
gate.ESTADO = os.path.join(SANDBOX, "estado.json")
assert not os.path.normcase(gate.ESTADO).startswith(
    os.path.normcase(os.path.dirname(os.path.abspath(gate.__file__)))), \
    "o estado do teste apontaria para a pasta real de hooks"

lp("== 0. as regras carregam? ==")
marcar("regras de porta carregadas", len(gate.carregar("porta")) > 0)
marcar("regras de vigia carregadas", len(gate.carregar("vigia")) > 0)

# -- 1. DEVE BARRAR ----------------------------------------------------------
lp("\n== 1. DEVE BARRAR ==")
b, m = rodar(HOOK, "import json, sys\ndef main():\n    e = json.load(sys.stdin)\n", "b1")
marcar("hook lendo json.load(sys.stdin)", b, "(passou e nao devia)")
marcar("  ...e a recusa traz o CONSERTO", "sys.stdin.buffer.read()" in m,
       "(motivo sem conserto)")
marcar("  ...e a recusa traz a FONTE", "PADROES.md#" in m)

b, _ = rodar(HOOK, 'import json\nprint(json.dumps({"a": 1}))\n', "b2")
marcar("hook que imprime json sem reconfigure utf-8", b)

# -- 2. DEVE PASSAR ----------------------------------------------------------
lp("\n== 2. DEVE PASSAR (senao o gate vira pedra) ==")
b, _ = rodar(HOOK, ('import json, sys\n'
                    'sys.stdout.reconfigure(encoding="utf-8")\n'
                    'print(json.dumps({"a": 1}))\n'), "p1")
marcar("hook COM reconfigure passa (`exige` funciona)", not b)

b, _ = rodar(HOOK, ('import json, sys\n'
                    'e = json.loads(sys.stdin.buffer.read().decode("utf-8"))\n'), "p2")
marcar("hook lendo stdin em BYTES passa", not b)

b, _ = rodar(HOOK, "x = 1 + 1\n", "p3")
marcar("codigo limpo passa", not b)

b, _ = rodar(HOOK, "# json.load(sys.stdin)  <- so um comentario\n", "p4")
marcar("linha comentada nao conta", not b)

rodar(HOOK, "import json, sys\ne = json.load(sys.stdin)\n", "dupla")
b2, _ = rodar(HOOK, "import json, sys\ne = json.load(sys.stdin)\n", "dupla")
marcar("2a tentativa no mesmo arquivo passa", not b2)

# -- 2b. AS REGRAS MINERADAS EM  (a 2a leva, de 5 para 15) --------------
# Cada par aqui e "o defeito / a defesa". O contra-caso nao e enfeite: uma
# regra que barra o defeito E o conserto e pior que regra nenhuma, porque
# ensina a desligar o gate. Os numeros de calibragem de cada uma estao no
# campo `calibrado` do `padroes_casa.json`.
lp("\n== 2b. AS REGRAS MINERADAS EM  ==")

_ALGUM = os.path.join(_HOME, "Projeto", "Algum")
PS1 = os.path.join(_ALGUM, "scripts", "tarefa.ps1")
WORKER = os.path.join(_ALGUM, "workers", "api.js")
SH = os.path.join(_ALGUM, "scripts", "vps", "run.sh")

CASOS = [
    # (nome, alvo, texto do DEFEITO, texto da DEFESA)
    ("ps1-crlf-bom", PS1,
     '$t = @"\nmanuten\u00e7\u00e3o\n"@\nWrite-Host $t\n',
     '\ufeff$t = @"\r\nmanuten\u00e7\u00e3o\r\n"@\r\nWrite-Host $t\r\n'),
    ("auth-fail-closed", WORKER,
     "if (env.API_SECRET && recebido !== env.API_SECRET) return json(401);\n",
     ("if (!env.API_SECRET) return json(403);\n"
      "if (!tsEqual(recebido, env.API_SECRET)) return json(401);\n")),
    ("replace-silencioso", PROJ,
     ("s = open(p).read()\n"
      "s = s.replace('antigo', 'novo')\n"
      "open(p, 'w').write(s)\n"),
     ("s = open(p).read()\n"
      "assert 'antigo' in s\n"
      "s = s.replace('antigo', 'novo')\n"
      "open(p, 'w').write(s)\n")),
    # ⚠️ O conserto aqui MUDOU, e quem obrigou foi o teste. A defesa
    # antiga era so `printf` no lugar de `echo`, e ela passou a ser barrada
    # pela regra `secret-guard-tamanho`, criada horas depois: trocar o `echo`
    # resolve a quebra de linha invisivel e NAO resolve o valor vazio. As duas
    # regras juntas exigem printf E guard de tamanho, e o conserto incompleto
    # so apareceu porque este teste afirma os dois lados de cada regra.
    ("wrangler-secret-echo", SH,
     'echo "$TOKEN" | wrangler secret put MEU_TOKEN\n',
     ('SEG=$(printf %s "$TOKEN" | tr -d "\\r\\n")\n'
      'if [ ${#SEG} -lt 20 ]; then exit 1; fi\n'
      'printf %s "$SEG" | wrangler secret put MEU_TOKEN\n')),
    ("windows-start-process-nonewwindow", PS1,
     '\ufeffStart-Process -NoNewWindow python x.py\r\n',
     '\ufeffStart-Process -WindowStyle Hidden python x.py\r\n'),
    ("dia-utc-fatiado", PROJ,
     "por_dia.setdefault(ts[:10], []).append(x)\n",
     ("d = datetime.fromisoformat(ts.replace('Z', '+00:00'))"
      ".astimezone().date().isoformat()\n"
      "por_dia.setdefault(d, []).append(x)\n")),
    ("python-buffer-log", SH,
     "python3 scripts/coletar.py >> /var/log/app/coletar.log 2>&1\n",
     "python3 -u scripts/coletar.py >> /var/log/app/coletar.log 2>&1\n"),
    ("waituntil-cf-budget", WORKER,
     "const DEBOUNCE_MS = 30000;\nsetTimeout(() => processar(), 30 * 1000);\n",
     "const DEBOUNCE_MS = 8000;\nsetTimeout(() => processar(), 8 * 1000);\n"),
    ("pep668-pip-install", SH,
     "pip3 install requests\n",
     "python3 -m venv .venv && .venv/bin/pip install requests\n"),
    ("secret-guard-tamanho", SH,
     "cat /proc/$PID/environ | cut -d= -f2 | gh secret set BOT_SECRET\n",
     ('SEG=$(cat /proc/$PID/environ | cut -d= -f2 | tr -d "\\r\\n")\n'
      'if [ ${#SEG} -lt 20 ]; then exit 1; fi\n'
      'printf %s "$SEG" | gh secret set BOT_SECRET\n')),
    ("evolution-payload-v1", WORKER,
     "await fetch(url, { body: JSON.stringify({ number, "
     "textMessage: { text: msg } }) });\n",
     "await fetch(url, { body: JSON.stringify({ number, text: msg }) });\n"),
    ("normalizacao-de-um-lado-so", PROJ,
     'if limpar(palavra) == "60 GB":\n    trocar()\n',
     ('alvo = limpar("60 GB")\n'
      'if limpar(palavra) == alvo:\n    trocar()\n')),
    ("ffmpeg-shortest-com-copy", PROJ,
     'cmd = ["ffmpeg", "-i", src, "-af", "apad", "-c:v", "copy",\n'
     '       "-c:a", "aac", "-shortest", out]\n',
     'cmd = ["ffmpeg", "-i", src, "-c:v", "copy", "-c:a", "aac", out]\n'),
    ("ffmpeg-shortest-com-copy (ordem inversa)", PROJ,
     'cmd = ["ffmpeg", "-i", src, "-shortest", "-c:a", "aac",\n'
     '       "-c:v", "copy", out]\n',
     'cmd = ["ffmpeg", "-i", src, "-c:a", "aac", "-c:v", "copy", out]\n'),
    # ⚠️ `wrangler-deploy-name-sem-config` MOROU AQUI por uma hora,
    # e foi rebaixada para `vigia` no mesmo dia: ao abrir o gate para `.yml`
    # ela acusou 2 workflows de um projeto que estao CORRETOS. O wrangler resolve a
    # config a partir do ENTRY POINT, nao do diretorio de trabalho - o que
    # esta escrito, dentro do proprio `workers/wrangler.toml`
    # contra um erro identico. O caso vive agora na lista de vigia, abaixo.
    ("llm-direto-para-o-cliente-sem-sanitizar", PROJ,
     ("texto = data['content'][0]['text'].strip()\n"
      "send_whatsapp(numero, texto)\n"),
     ("texto = data['content'][0]['text'].strip()\n"
      "linhas = [l for l in texto.split(chr(10))\n"
      "          if not l.lstrip().startswith('#')]\n"
      "send_whatsapp(numero, chr(10).join(linhas).strip())\n")),
    ("disparo-em-lote-sem-ritmo-da-casa",
     os.path.join(_HOME, "Projeto", "Projeto-Um", "Etapa", "scripts",
                  "resgate.py"),
     ('for n in lista:\n'
      '    send_whatsapp(n, msg)\n'
      '    time.sleep(12)\n'),
     ('from ritmo_humano import pausa\n'
      'for n in lista:\n'
      '    send_whatsapp(n, msg)\n'
      '    pausa()\n')),
    ("crase-em-comentario-de-worker", WORKER,
     ('const HTML = `<!DOCTYPE html>\n'
      '  // aqui uso `saveCliente` para gravar\n'
      '  <div>oi</div>\n`;\n'),
     ('const HTML = `<!DOCTYPE html>\n'
      '  // aqui uso saveCliente para gravar\n'
      '  <div>oi</div>\n`;\n')),
    ("git-status-como-prova-de-nao-rodou", PROJ,
     ('r = run(["git", "status", "--porcelain"], capture_output=True)\n'
      'assert r.stdout.decode().strip() == "", "o gerador rodou"\n'),
     ('antes = os.path.getmtime(alvo)\n'
      'rodar()\n'
      'assert os.path.getmtime(alvo) == antes, "o gerador rodou"\n')),
    ("worktree-basename-raiz", PROJ,
     ('raiz = run(["git", "rev-parse", "--show-toplevel"]).stdout.strip()\n'
      'nome = os.path.basename(raiz)\n'),
     ('gd = run(["git", "rev-parse", "--git-dir"]).stdout.strip()\n'
      'gc = run(["git", "rev-parse", "--git-common-dir"]).stdout.strip()\n'
      'if gd != gc:\n'
      '    return   # worktree linkado: nao gera o artefato\n')),
]

for i, (nome, alvo, ruim, bom) in enumerate(CASOS):
    b, m = rodar(alvo, ruim, "nova%d_ruim" % i)
    marcar("%s BARRA o defeito" % nome, b, "(passou e nao devia)")
    if b:
        # A 1a palavra do nome do caso E o id da regra; o resto (ex.: "(ordem
        # inversa)") distingue dois casos da MESMA regra. Comparar o nome
        # inteiro fazia o 2o caso falhar por um motivo que nao era o gate.
        marcar("  ...e a recusa nomeia a regra", nome.split(" ")[0] in m)
    b, _ = rodar(alvo, bom, "nova%d_bom" % i)
    marcar("  ...e DEIXA PASSAR o conserto", not b,
           "(barrou o proprio conserto - isto desliga o gate)")

# -- 2c. O PEDACO DO `Edit` NAO E O ARQUIVO ----------------------------------
# O falso positivo: `exige` e `so_se` perguntam pelo ARQUIVO, e num
# `Edit` a ferramenta manda so o trecho novo. Sem compor o contexto, a defesa
# que mora 150 linhas acima conta como ausente (falso positivo) e o sinal de
# `so_se` que mora no resto do arquivo conta como inexistente (falso NEGATIVO,
# que e pior: gate mudo com cara de gate funcionando).
lp("\n== 2c. num `Edit`, a condicao de ARQUIVO olha o arquivo ==")

ARQ = os.path.join(SANDBOX, "com_defesa.py")
with io.open(ARQ, "w", encoding="utf-8") as _fh:
    _fh.write('import sys\nsys.stdout.reconfigure(encoding="utf-8")\n'
              '# ... 150 linhas ...\n')
HOOK_REAL = os.path.join(os.path.dirname(gate.ESTADO), "hooks", "x.py")


def rodar_edit(alvo, novo, sessao):
    entrada = json.dumps({"session_id": sessao, "tool_name": "Edit",
                          "tool_input": {"file_path": alvo,
                                         "new_string": novo}})
    stdin_antigo, stdout_antigo = sys.stdin, sys.stdout
    cap = io.StringIO()
    try:
        sys.stdin = type("F", (), {"buffer": io.BytesIO(entrada.encode())})()
        sys.stdout = cap
        gate.main()
    finally:
        sys.stdin, sys.stdout = stdin_antigo, stdout_antigo
    s = cap.getvalue().strip()
    if not s:
        return False, ""
    d = json.loads(s)
    h = d.get("hookSpecificOutput") or {}
    return h.get("permissionDecision") == "deny", \
        h.get("permissionDecisionReason", "")


ARQ_HOOK = os.path.join(SANDBOX, "hooks", "gate_ficticio.py")
os.makedirs(os.path.dirname(ARQ_HOOK), exist_ok=True)
with io.open(ARQ_HOOK, "w", encoding="utf-8") as _fh:
    _fh.write('import sys, json\n'
              'sys.stdout.reconfigure(encoding="utf-8")\n'
              + "# enchimento\n" * 150)
b, _ = rodar_edit(ARQ_HOOK, 'print(json.dumps({"a": 1}))\n', "ed1")
marcar("`exige` que mora no ARQUIVO isenta um `Edit` parcial", not b,
       "(falso positivo: julgou o pedaco, nao o arquivo)")

ARQ_ENVIO = os.path.join(SANDBOX, "disparador.py")
with io.open(ARQ_ENVIO, "w", encoding="utf-8") as _fh:
    _fh.write('def enviar_mensagem(n, t):\n'
              '    requests.post(URL, json={"number": n})\n'
              '\n\ndef main():\n    pass\n')
b, _ = rodar_edit(ARQ_ENVIO, "main()\n", "ed2")
marcar("`so_se` que mora no ARQUIVO ainda arma a regra num `Edit`", b,
       "(falso NEGATIVO: o sinal de envio estava no resto do arquivo)")

# -- 3. ESCOPO ---------------------------------------------------------------
lp("\n== 3. ESCOPO: regra de hook nao vale fora de hooks/ ==")
b, _ = rodar(PROJ, "import json, sys\ne = json.load(sys.stdin)\n", "e1")
marcar("mesmo codigo em projeto comum NAO barra", not b,
       "(barrou fora do escopo)")

# -- 4. DEGRAU ---------------------------------------------------------------
lp("\n== 4. DEGRAU: regra de VIGIA nao barra na porta ==")
TXT_VIGIA = 'import json\njson.dump(d, open("estado.json", "w"))\n'
b, _ = rodar(PROJ, TXT_VIGIA, "v1")
marcar("regra marcada `onde: vigia` nao barra", not b,
       "(uma regra de vigia esta barrando)")
achou_vigia = gate.violacoes(PROJ, TXT_VIGIA, "vigia")
marcar("  ...mas a MESMA regra acha quando chamada como vigia",
       len(achou_vigia) > 0)

# As quatro de vigia, uma a uma: a que acha 235, a que acha 286, a que acha
# 140 e a que acha 49. Nenhuma pode barrar - juntas elas parariam metade da
# casa, e um gate que para metade da casa e um gate que alguem desliga.
# (nome, texto, alvo) — o alvo importa: regra com `escopo` so vale no caminho
# dela, e `instalador-sobrescreve-sem-conferir` e limitada a `.sh`.
for _nome, _txt, _alvo in [
        ("modulo-reconfigura-stdout",
         'import io, sys\nsys.stdout = io.TextIOWrapper(sys.stdout.buffer)\n',
         PROJ),
        ("flag-env-valor-invalido",
         "ligado = os.getenv('GATE_X', '').lower() == 'true'\n", PROJ),
        ("falha-nao-e-vazio",
         "try:\n    return api()\nexcept Exception:\n    return []\n", PROJ),
        ("busca-pdf-sem-normalizar",
         't = page.extract_text()\nif "fonte calibrada" in texto:\n'
         '    print("achou")\n', PROJ),
        ("varre-a-pasta-onde-escreve",
         'for p in SAIDA.glob("*.pdf"):\n    processar(p)\n'
         '(SAIDA / "novo.pdf").write_bytes(dados)\n', PROJ),
        ("indexa-por-telefone",
         'indice = {}\nfor c in clientes:\n    indice[wa] = c\n', PROJ),
        ("wrangler-deploy-name-sem-config",
         "npx wrangler deploy empresapulse-crm.js --name empresapulse-crm\n", SH),
        ("instalador-sobrescreve-sem-conferir",
         "cat > /opt/servico/run_alerta.sh << 'SCRIPT'\n"
         "echo oi\nSCRIPT\n", SH)]:
    b, _ = rodar(_alvo, _txt, "v_" + _nome)
    marcar("%s nao barra na porta" % _nome, not b)
    marcar("  ...e acha como vigia",
           any(a[0] == _nome for a in gate.violacoes(_alvo, _txt, "vigia")))

# -- 5. MUTACAO --------------------------------------------------------------
lp("\n== 5. MUTACAO (desarma o detector; os casos tem de DEIXAR de ser pegos) ==")
if FALHA:
    lp("  PULADA - a secao 1 teve %d falha(s): o baseline esta morto." % FALHA)
    lp("           Desarmar detector que ja pega zero continua pegando zero.")
    lp("\n=== RESULTADO: %d PASS / %d FALHA / mutacao NAO AVALIADA ==="
       % (PASS, FALHA))
    shutil.rmtree(SANDBOX, ignore_errors=True)
    sys.exit(1)

CARREGAR_ORIG = gate.carregar
CODIGO_ORIG = gate.CODIGO
sobreviveram = []

MUT = [
    ("nenhuma regra carregada",
     "sem regra, nada e defeito",
     lambda: setattr(gate, "carregar", lambda onde="porta": []),
     [(HOOK, "import json, sys\ne = json.load(sys.stdin)\n")]),
    ("lista de extensoes de codigo esvaziada",
     "se nada e codigo, o gate nunca dispara",
     lambda: setattr(gate, "CODIGO", ()),
     [(HOOK, "import json, sys\ne = json.load(sys.stdin)\n")]),
    ("regras de porta viram regras de vigia",
     "se a porta nao tem regra, a escrita passa direto",
     lambda: setattr(gate, "carregar",
                     lambda onde="porta": CARREGAR_ORIG("vigia")
                     if onde == "porta" else CARREGAR_ORIG(onde)),
     [(HOOK, "import json, sys\ne = json.load(sys.stdin)\n")]),
    # -- as tres capacidades que o motor ganhou --------------------
    ("`seeds_bloco` esvaziado",
     "o defeito de 2+ linhas volta a ser invisivel: `} catch (e) {` numa "
     "linha e `return [];` na outra sao, cada um sozinho, codigo legitimo",
     lambda: setattr(gate, "carregar", lambda onde="porta": [
         t[:10] + ([],) + t[11:] for t in CARREGAR_ORIG(onde)]),
     [(WORKER,
       "if (env.API_SECRET && recebido !== env.API_SECRET) return json(401);\n"),
      (PROJ, ("s = open(p).read()\n"
              "s = s.replace('antigo', 'novo')\n"
              "open(p, 'w').write(s)\n"))]),
    # ⚠️ A mutacao do `olha_comentario` MOROU AQUI por uma hora e
    # saiu: a regra da crase deixou de usar o campo (passou a ancorar no
    # inicio do template, nao no comentario), entao desligar a capacidade
    # nao mudava mais nada e a mutacao "sobrevivia" sempre. Mutacao de
    # capacidade que ninguem usa nao mede o gate - mede o vazio, e some do
    # placar como se fosse defeito. Volta no dia em que uma regra usar.
    ("`nao_tem` desarmado",
     "a regra de AUSENCIA para de existir - um .ps1 sem BOM/CRLF nao tem "
     "linha errada para apontar, entao sem `nao_tem` ele passa inteiro",
     # `t[:11] + (None,) + t[12:]` e nao `t[:11] + (None,)`: a forma curta
     # amputava o ultimo campo da tupla, e quebrou no dia em que o motor
     # ganhou o 13o (`olha_comentario`). Mutacao que muda a FORMA do dado
     # testa o teste, nao o gate.
     lambda: setattr(gate, "carregar", lambda onde="porta": [
         t[:11] + (None,) + t[12:] for t in CARREGAR_ORIG(onde)]),
     [(PS1, '$t = @"\nmanutenção\n"@\nWrite-Host $t\n')]),
]

# A 4a mutacao nao cabe na tabela acima porque nao mexe em regra, e sim em
# QUAL TEXTO as condicoes de arquivo enxergam. Ela prova o conserto de 2c:
# se o gate voltar a julgar o pedaco do `Edit`, a regra armada por `so_se`
# emudece - e um gate mudo passa no teste de "nao barrou nada errado".
VIOLACOES_ORIG = gate.violacoes


def _sem_contexto(alvo, texto, onde="porta", contexto=None):
    return VIOLACOES_ORIG(alvo, texto, onde)          # ignora o contexto

for i, (nome, porque, aplicar, casos) in enumerate(MUT):
    gate.carregar = CARREGAR_ORIG
    gate.CODIGO = CODIGO_ORIG
    aplicar()
    ainda = 0
    for j, (alvo, txt) in enumerate(casos):
        b, _ = rodar(alvo, txt, "mut%d_%d" % (i, j))
        if b:
            ainda += 1
    det = ainda == 0
    if not det:
        sobreviveram.append(nome)
    lp("  [%s] %s" % ("DETECTADA" if det else "SOBREVIVEU", nome))
    lp("           " + porque)
gate.carregar = CARREGAR_ORIG
gate.CODIGO = CODIGO_ORIG

gate.violacoes = _sem_contexto
b, _ = rodar_edit(ARQ_ENVIO, "main()\n", "mut_ctx")
gate.violacoes = VIOLACOES_ORIG
if b:
    sobreviveram.append("contexto do `Edit` ignorado")
lp("  [%s] contexto do `Edit` ignorado" % ("DETECTADA" if not b else
                                           "SOBREVIVEU"))
lp("           sem o arquivo, o `so_se` nao acha o sinal de envio e a regra "
   "emudece")

# -- 5b. CUSTO: regra lenta nao congela a escrita de arquivo -----------------
# Este gate roda em TODO Edit/Write. Uma regra lenta nao deixa o dia mais
# lento: ela CONGELA a escrita, e o sintoma que chega ao dono da casa e "o Claude
# travou", nao "a regra X e ruim".
#
# Medido, e por isso esta secao existe: um seed candidato meu com
# quantificador aninhado — `(?:[ \t]+(?!try\b)[^\n]*\n){0,6}` — NAO TERMINOU
# em 60 segundos sobre 40 KB do `monitor_empresa.py`. Backtracking exponencial.
# O `re` do Python nao tem timeout e regex em C nao se interrompe por thread,
# entao a defesa nao pode ser no relogio: e impedir a regra de ENTRAR.
lp("\n== 5b. CUSTO: nenhuma regra pode congelar o `Edit` ==")
try:
    import calibrar_padroes as cal                          # noqa: E402
    _tudo = [(os.path.getsize(c), c) for c in cal.arquivos()]
    _tudo.sort(reverse=True)
    _amostra = [cal.ler(c) for _s, c in _tudo[:8]]
    _lentas = []
    for _r in gate.carregar("todas"):
        # Por INDICE e nao por desempacotamento: a tupla do `carregar` cresce
        # quando o motor ganha campo, e um `a, b, c = r` quebra o teste inteiro
        # por um motivo que nada tem a ver com o que ele mede. Aconteceu no
        # 13o campo (`olha_comentario`).
        _rid, _rxs, _bl, _nt = _r[0], _r[9], _r[10], _r[11]
        _ms = cal.custo([x.pattern for x in _rxs],
                        [x.pattern for x in _bl],
                        _nt.pattern if _nt else None, _amostra)
        if _ms > cal.TETO_MS:
            _lentas.append((_rid, _ms))
    marcar("as %d regras rodam abaixo de %d ms no pior arquivo"
           % (len(gate.carregar("todas")), cal.TETO_MS), not _lentas,
           "(" + ", ".join("%s=%.0fms" % x for x in _lentas) + ")")

    # E o cronometro acima NAO basta, porque so mede o que TERMINA. O caso
    # que congela e o que nao termina, e para esse a unica defesa e ler o
    # padrao antes de executa-lo.
    _perigosas = []
    for _r in gate.carregar("todas"):
        for _rx in list(_r[9]) + list(_r[10]) + ([_r[11]] if _r[11] else []):
            _culpa = cal.quantificador_aninhado(_rx.pattern)
            if _culpa:
                _perigosas.append((_r[0], _culpa[:40]))
    marcar("nenhuma regra tem quantificador ANINHADO", not _perigosas,
           "(" + ", ".join("%s: %s" % x for x in _perigosas) + ")")

    # mutacao do detector: ele PEGA o padrao que de fato travou 3 vezes em
    # , e nao acusa os padroes que estao no JSON hoje
    _EXPLOSIVO = (r"for\s+\w+\s+in\s+[^\n]{1,80}:\n"
                  r"(?:[ \t]+(?!try\b)[^\n]*\n){0,6}[ \t]+[^\n]{0,80}"
                  r"(send_whatsapp|enviar_mensagem)\s*\(")
    marcar("  ...e o detector PEGA o padrao que travou de verdade",
           bool(cal.quantificador_aninhado(_EXPLOSIVO)),
           "(deixou passar o caso que motivou a defesa)")
    marcar("  ...sem acusar `(a|b)?` nem `(x|y)\\s*`",
           not cal.quantificador_aninhado(r"(abc|def)?\s*(1[2-9]|\d{3,})\s*"))
except Exception as _e:                                     # noqa: BLE001
    marcar("o custo das regras foi medido", False,
           "(%s: %s)" % (type(_e).__name__, _e))

# -- 6. CONTROLE -------------------------------------------------------------
lp("\n== 6. controle: com tudo no lugar, o caso volta a ser pego ==")
b, _ = rodar(HOOK, "import json, sys\ne = json.load(sys.stdin)\n", "ctrl")
marcar("controle: json.load(sys.stdin) volta a ser pego", b)

shutil.rmtree(SANDBOX, ignore_errors=True)

lp("\n=== RESULTADO: %d PASS / %d FALHA / %d mutacao(oes) sobreviveram ==="
   % (PASS, FALHA, len(sobreviveram)))
for n in sobreviveram:
    lp("   mutacao nao detectada: " + n)
sys.exit(1 if (FALHA or sobreviveram) else 0)
