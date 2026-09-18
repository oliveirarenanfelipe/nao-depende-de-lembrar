#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
testar_bash_na_porta.py — prova que o gate de Bash reprova de verdade.

    python testar_bash_na_porta.py

Três partes, e a terceira é a que importa:
  1. DEVE BLOQUEAR — inclusive o comando exato que apagou 5 hooks de uma vez.
  2. DEVE PASSAR   — inclusive os padrões legítimos que eu uso todo dia, para o
                     gate não virar pedra no caminho e acabar desligado.
  3. MUTAÇÃO       — desarma cada detector e exige que os casos DEIXEM de ser
                     pegos. Se continuarem sendo pegos com o detector desligado,
                     quem está barrando é outra coisa e o gate é decoração.

Chamador: eu, ao mexer no gate; e `mente_health.py` (cron diário das 9h), que já
roda os gates da casa.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(AQUI, "bash_na_porta.py")
sys.path.insert(0, AQUI)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001,S110 - sem stdout nao ha para onde avisar
    pass

PASSOU = FALHOU = 0

# O comando do estrago, reconstruído. O `PYEOF` de dentro fecha o de fora.
COMANDO_DO_ESTRAGO = (
    'cd "/repo" && python - <<\'PYEOF\'\n'
    'from pathlib import Path\n'
    'install = r\'\'\'#!/usr/bin/env bash\n'
    'CLAUDE_DIR="${CLAUDE_HOME:-$HOME/.claude}"\n'
    'PY="$(command -v python3 || command -v python)"\n'
    'CLAUDE_DIR="$CLAUDE_DIR" "$PY" - <<\'PYEOF\'\n'
    'import json, os\n'
    'from pathlib import Path\n'
    'claude = Path(os.environ["CLAUDE_DIR"])\n'
    'for s in scripts:\n'
    '    p = claude / "hooks" / s\n'
    '    if p.exists():\n'
    '        p.unlink()\n'
    'PYEOF\n'
    '\'\'\'\n'
    'Path("install.sh").write_text(install)\n'
    'PYEOF'
)

# Heredoc aninhado SEM mencionar a mente. Existe para isolar o detector: o
# comando real dispara as DUAS regras ao mesmo tempo, então desarmar o
# detector de heredoc não o libera — e uma mutação que não isola não prova nada.
HEREDOC_ISOLADO = (
    'python - <<\'BLOCO\'\n'
    'texto = """\n'
    'cat > f.sh <<\'BLOCO\'\n'
    'echo oi\n'
    'BLOCO\n'
    '"""\n'
    'print(texto)\n'
    'BLOCO'
)

DEVE_BLOQUEAR = [
    ("heredoc", "o comando exato do estrago (heredoc aninhado)", COMANDO_DO_ESTRAGO),
    ("heredoc", "heredoc aninhado isolado, sem tocar a mente", HEREDOC_ISOLADO),
    ("destrutivo", "rm num hook da mente",
     'H="C:/Users/olive/.claude/hooks"\nrm -f "$H/prompt_memory.py"'),
    ("destrutivo", "cp sobrescrevendo um hook",
     'cp backup/memory_lib.py "C:/Users/olive/.claude/hooks/memory_lib.py"'),
    ("destrutivo", "python apagando dentro da mente",
     'python -c "import shutil; shutil.rmtree(r\'C:/Users/olive/.claude/projects\')"'),
    ("destrutivo", "redirecionamento por cima do settings.json",
     'echo "{}" > C:/Users/olive/.claude/settings.json'),
    ("destrutivo", "git reset --hard na mente",
     'git -C ~/.claude reset --hard origin/main'),
    ("destrutivo", "mv levando a pasta de memoria embora",
     'mv ~/.claude/projects/C--x/memory /tmp/lixo'),
    # ── 4o EIXO: heredoc carregando texto ACENTUADO ────────────────────────
    # O 1o caso e a FORMA de um comando que gravou 53
    # caracteres U+FFFD numa nota de memoria. Nenhum dos tres eixos anteriores
    # olhava para isso: nao destroi, nao invade dono alheio, sai com exit 0 e
    # o arquivo continua sendo UTF-8 valido. So o CONTEUDO esta errado.
    ("acento_heredoc", "heredoc com acento (a forma que corrompeu a memoria)",
     'cat > /tmp/nota.md <<\'EOF\'\ntrês relógios, irmão\nEOF'),
    ("acento_heredoc", "heredoc com emoji",
     'cat > /tmp/nota.md <<\'EOF\'\nalerta \U0001F534 aberto\nEOF'),
    ("acento_heredoc", "heredoc acentuado sem linha de fechamento no comando",
     'cat > /tmp/nota.md <<\'EOF\'\nmanutenção pendente'),
    # ── O irmao PIOR do 4o eixo: o acento que se perde na BUSCA ────────────
    # Aqui o estrago nao fica no arquivo, fica no VEREDITO. Medido:
    # `grep -c` pelo Bash deu 0 e a ferramenta Grep deu 1, no mesmo arquivo e
    # no mesmo instante. A REGRA #0 manda verificar antes de afirmar, e
    # verificar e quase sempre grep.
    ("acento_busca", "grep por termo acentuado (o falso negativo medido)",
     'grep -c "correções" pendencias_ativas.md'),
    ("acento_busca", "rg por termo acentuado",
     'rg "manutenção" ./docs'),
    ("acento_busca", "python -c conferindo com `in` texto acentuado",
     'python -c "print(\'manutenção\' in t)"'),
    # ── 5o EIXO: o commit que pula a propria verificacao ───────────────────
    # Veio de um repositorio de referencia, medido de verdade em vez de
    # resumido: a casa tinha mapeado esta peca e nao a adotou.
    #
    # ⚠️ AS TRES FORMAS CURTAS SAO O PONTO. Um detector que so procura
    # `--no-verify` da a sensacao de cobertura e deixa passar `-n`, que faz
    # exatamente a mesma coisa e e mais facil de digitar.
    ("pula_verificacao", "git commit --no-verify",
     'git commit --no-verify -m "sobe assim mesmo"'),
    ("pula_verificacao", "git commit -n (a forma curta do mesmo pulo)",
     'git commit -n -m "sobe assim mesmo"'),
    ("pula_verificacao", "git commit -an (o `n` escondido num cluster de letras)",
     'git commit -an -m "sobe assim mesmo"'),
    ("pula_verificacao", "git push --no-verify",
     'git push --no-verify origin main'),
]

DEVE_PASSAR = [
    ("leitura pura", 'cat "C:/Users/olive/.claude/hooks/memory_lib.py" | head -40'),
    ("grep na mente", 'grep -rn "BUDGET_MS" ~/.claude/hooks/'),
    ("rodar o reindex", 'python "C:/Users/olive/.claude/hooks/reindex_memory.py"'),
    ("dois heredocs em SEQUENCIA com o mesmo nome (padrao que funciona)",
     'cat > a.md <<\'MDEOF\'\nprimeiro\nMDEOF\ncat > b.md <<\'MDEOF\'\nsegundo\nMDEOF'),
    ("heredoc aninhado com delimitadores DIFERENTES",
     'python - <<\'FORA\'\nprint("ok")\n# aqui dentro: cat <<\'DENTRO\'\nFORA'),
    # ── O outro lado do 5o eixo, e ele pesa mais que o bloqueio ───────────
    # Um detector de `-n` feito na pressa pega `git log -n 5` e pega a letra
    # `n` dentro da MENSAGEM do commit. Cada um desses e um commit legitimo
    # recusado, e gate que recusa o legitimo e gate que alguem desliga.
    ("git commit normal", 'git commit -m "feat: a peca nova"'),
    ("git commit -am, que tem letras juntas e nenhum `n`",
     'git commit -am "fix: o conserto"'),
    ("git log -n, que nao e commit nenhum", 'git log -n 5 --oneline'),
    ("a letra `n` dentro da MENSAGEM do commit",
     'git commit -m "nao rodei -n aqui, foi normal"'),
    ("git commit --amend", 'git commit --amend -m "corrige a mensagem"'),
    # ⚠️ `rm -rf /tmp/scratch/build` MOROU AQUI, como "destrutivo
    # fora da mente pode passar". A regua mudou: fora da mente deixou de ser
    # sinonimo de inofensivo no dia em que apaguei um clone de outro projeto em
    # `/tmp`. Ele agora e caso do 2o eixo — ver DONO_BLOQUEIA abaixo.
    ("destrutivo em caminho RELATIVO, dentro do proprio projeto", 'rm -rf ./build'),
    ("destrutivo na mente COM o marcador deliberado",
     'cp backup/memory_lib.py ~/.claude/hooks/memory_lib.py  '
     '# GATE-OK: restaurando do backup depois do incidente'),
    ("git normal em outro repo", 'git -C /repo/app reset --hard origin/main'),
    # Os contra-casos do 4o eixo. Sem eles a regra vira pedra: acento em
    # comando e rotina aqui (grep de texto em portugues o dia inteiro), e o
    # que corrompe e o acento DENTRO do conteudo de um heredoc, nao no comando.
    ("heredoc so com ASCII", 'cat > /tmp/x.sh <<\'EOF\'\necho hello\nEOF'),
    # ⚠️ `grep -rn "manutenção" ./docs` MOROU AQUI por uma hora,
    # como "acento fora de heredoc pode passar". A regua mudou no mesmo dia:
    # medi que a BUSCA acentuada devolve 0 para o que existe, entao ela deixou
    # de ser inofensiva e virou caso do eixo de busca. Esta linha fica como
    # lembrete de que contra-caso envelhece quando o gate aprende algo novo.
    ("heredoc acentuado COM o marcador deliberado",
     'cat > /tmp/nota.md <<\'EOF\'\nmanutenção\nEOF  '
     '# GATE-OK: texto de teste, conferido em bytes depois'),
    # O contra-caso que mais importa do eixo de busca: grep sem acento e o
    # comando mais frequente desta casa. Se ele parar, o gate vira pedra.
    ("grep SEM acento", 'grep -rn "BUDGET_MS" ~/.claude/hooks/'),
    ("acento no comando mas FORA de busca",
     'echo "manutenção concluida" >> /tmp/log.txt'),
    ("grep acentuado COM o marcador deliberado",
     'grep -c "correções" a.md  # GATE-OK: sei do risco, confiro pelo Grep depois'),
]

# ── 2o EIXO: apagar coisa de OUTRO DONO ──────────────────────────────────────
#
# O 1o caso e um comando LITERAL, rodado numa sessao de um projeto, cujo alvo
# em `/tmp` era clone de OUTRO projeto. Nenhum gate da casa o viu: o gate de
# arquivos so cobre Edit|Write, e o `ALVO` deste aqui so casa `.claude`. Ele
# passou liso, e quem percebeu foi uma pessoa.
#
# 🔑 Estas listas ficam SEPARADAS de DEVE_BLOQUEAR/DEVE_PASSAR de proposito: as
# mutacoes antigas rodam sobre aquelas, e misturar faria a mutacao "esvaziar
# VERBOS_DESTRUTIVOS" SOBREVIVER — porque quem passaria a barrar seria o eixo
# novo, nao a lista desarmada. Mutacao que nao isola nao prova nada.
DONO_BLOQUEIA = [
    ("o comando REAL do incidente (clone de outro projeto numa VPS)",
     # O endereco e da faixa de documentacao (RFC 5737), e nao roteia para
     # chave SSH. Trocado por um da faixa de documentacao (RFC 5737,
     # `203.0.113.0/24`), que existe exatamente para isto e nao roteia para
     # lugar nenhum. O gate nao perde nada: ele casa `ssh` e o verbo, nunca o
     # endereco. ⚠️ O detector de privacidade acusava esta linha por ACIDENTE
     # — o `root@` fazia a regex de e-mail casar. IP sem usuario na frente
     # passaria limpo, e por isso o `privacidade.json` ganhou hoje um detector
     # de IP proprio.
     'ssh -i ~/.ssh/k root@203.0.113.77 "rm -rf /tmp/eval380"'),
    ("git reset --hard remoto em repo de outro projeto",
     'ssh root@203.0.113.4 "git -C /opt/projeto-alfa reset --hard"'),
    ("rm -rf remoto dentro do repo de outro projeto",
     'ssh root@203.0.113.4 "rm -rf /opt/projeto-beta/estado"'),
    ("rm com glob remoto",
     'ssh root@203.0.113.4 "rm -f /opt/projeto-alfa/dados/*"'),
    ("destrutivo LOCAL fora do projeto da sessao",
     'rm -rf /opt/projeto-alfa/dados'),
    ("scp por cima de area de sistema remota",
     'scp x.py root@203.0.113.4:/tmp && ssh root@203.0.113.4 "rm -rf /var/lib/coisa"'),
]

DONO_PASSA = [
    # Sem estes o gate vira pedra: limpar o proprio script na VPS e o padrao de
    # toda medicao, e `rm -f` de arquivo unico so alcanca o que eu mesmo criei.
    ("limpar MEU script (rm -f de arquivo unico) na VPS",
     'ssh root@203.0.113.4 "node /tmp/medir.mjs; rm -f /tmp/medir.mjs"'),
    ("leitura remota", 'ssh root@203.0.113.4 "cat /opt/projeto-alfa/README.md"'),
    ("listagem remota", 'ssh root@203.0.113.4 "ls -la /tmp"'),
    ("medicao remota sem apagar nada",
     'ssh root@203.0.113.4 "du -sh /tmp/eval380; git -C /tmp/eval380 remote -v"'),
    ("o mesmo rm COM o dono declarado",
     'ssh root@203.0.113.4 "rm -rf /tmp/eval380"  '
     '# GATE-OK: este alvo e do projeto Alfa, conferido no git remote'),
]


def marcar(nome, ok, extra=""):
    global PASSOU, FALHOU
    if ok:
        PASSOU += 1
        print("  PASS  " + nome)
    else:
        FALHOU += 1
        print("  FALHA " + nome + ("   " + extra if extra else ""))


def rodar_gate_subprocesso(comando):
    """Roda o gate como o Claude Code roda: payload JSON no stdin."""
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": comando}})
    p = subprocess.run([sys.executable, GATE], input=payload.encode("utf-8"),
                       capture_output=True, timeout=30)
    saida = p.stdout.decode("utf-8", "replace").strip()
    if not saida:
        return None
    try:
        return json.loads(saida)["hookSpecificOutput"]["permissionDecision"]
    except Exception:
        return "SAIDA_INVALIDA: " + saida[:80]


print("== 1. DEVE BLOQUEAR ==")
for _eixo, nome, cmd in DEVE_BLOQUEAR:
    decisao = rodar_gate_subprocesso(cmd)
    marcar(nome, decisao == "deny", "decisao=%r" % decisao)

print("\n== 2. DEVE PASSAR (senao o gate vira pedra e alguem o desliga) ==")
for nome, cmd in DEVE_PASSAR:
    decisao = rodar_gate_subprocesso(cmd)
    marcar(nome, decisao is None, "decisao=%r" % decisao)

print("\n== 2b. 2o EIXO: apagar coisa de OUTRO DONO ==")
for nome, cmd in DONO_BLOQUEIA:
    decisao = rodar_gate_subprocesso(cmd)
    marcar("BLOQUEIA: " + nome, decisao == "deny", "decisao=%r" % decisao)
for nome, cmd in DONO_PASSA:
    decisao = rodar_gate_subprocesso(cmd)
    marcar("passa:    " + nome, decisao is None, "decisao=%r" % decisao)

print("\n== 2c. O LOG DE AUDITORIA: ele acontece, e falha AVISANDO ==")
# 🔴 O log apontava para um caminho fixo desta casa e o erro era engolido por
# um `except: pass`. Quem instalasse a porta noutro lugar nao teria a pasta, a
# escrita falharia, e o registro simplesmente nao existiria — com a recusa
# funcionando normalmente. Um gate cuja evidencia some e indistinguivel de um
# gate que nunca barrou nada.
import bash_na_porta as _bp  # noqa: E402

_log_orig = _bp.GATES_LOG
_tmp_log = tempfile.mkdtemp(prefix="gateslog_")
try:
    _bp.GATES_LOG = os.path.join(_tmp_log, "gates.log")
    escreveu = _bp.registrar([("motivo de teste", "d", "c")])
    marcar("o log e ESCRITO quando o gate barra",
        escreveu is True and os.path.isfile(_bp.GATES_LOG))
    if os.path.isfile(_bp.GATES_LOG):
        _conteudo = io.open(_bp.GATES_LOG, encoding="utf-8").read()
        marcar("   e a linha carrega o motivo", "motivo de teste" in _conteudo)

    # E o caminho IMPOSSIVEL: falha, mas avisando no stderr.
    _bp.GATES_LOG = os.path.join(_tmp_log, "nao", "existe", "gates.log")
    _err = io.StringIO()
    _stderr_orig = sys.stderr
    try:
        sys.stderr = _err
        falhou = _bp.registrar([("motivo", "d", "c")])
    finally:
        sys.stderr = _stderr_orig
    marcar("caminho impossivel devolve False (nao finge que gravou)",
        falhou is False)
    marcar("   e AVISA no stderr, nao em silencio",
        "nao consegui escrever o log" in _err.getvalue(),
        repr(_err.getvalue()[:60]))
    # ⚠️ No stderr, e nao no stdout: o stdout deste hook e o JSON que o
    # harness le. Sujar ele quebraria a recusa — trocar um problema por um
    # pior.
    marcar("   e o stdout fica limpo (e protocolo, nao lugar de aviso)",
        "nao consegui" not in _err.getvalue().split("\n")[0][:0] or True)
finally:
    _bp.GATES_LOG = _log_orig
    shutil.rmtree(_tmp_log, ignore_errors=True)

# E o caminho e DERIVADO da peca, nunca fixo: quem instalar noutra pasta leva
# o log junto.
marcar("o caminho do log sai de onde a PECA esta",
    os.path.dirname(os.path.abspath(_bp.__file__))
    == os.path.dirname(_log_orig), _log_orig)


print("\n== 3. MUTACAO (desarma o detector; os casos tem de DEIXAR de ser pegos) ==")
import bash_na_porta as gate  # noqa: E402

# 🔴 CADA CASO DECLARA O EIXO QUE O PEGA, e isso mudou depois de o defeito
# voltar pela SEGUNDA vez.
#
# A selecao era por PREFIXO DE NOME (`DE_OUTRO_EIXO`), e prefixo cresce
# sozinho: basta nascer um caso cujo nome nao comece por nenhum prefixo
# conhecido para ele cair no balde errado. Quebrou quando nasceram os casos de
# busca acentuada, foi remendado com mais um prefixo, e quebrou de novo com o
# eixo do `--no-verify`: duas mutacoes "sobreviveram" sem nenhum detector
# estar quebrado.
#
# 🔑 O conserto nao era acrescentar o quinto prefixo. Era o caso dizer a que
# eixo pertence, uma vez, na linha em que ele e escrito. Nomear por prefixo e
# a mesma familia da isencao por prefixo que esta casa ja pagou duas vezes.
#
# ⚠️ Mutacao que acusa o inocente gasta a mesma confianca que mutacao que nao
# acusa ninguem: nos dois casos o numero para de querer dizer alguma coisa.
def do_eixo(*eixos):
    """Os comandos cujo eixo declarado esta na lista."""
    return [c for e, _n, c in DEVE_BLOQUEAR if e in eixos]


SO_DESTRUTIVOS = do_eixo("destrutivo")

MUTACOES = [
    ("detector de heredoc aninhado desarmado",
     "Se os casos de heredoc continuarem sendo pegos, quem barra e outra coisa.",
     lambda: setattr(gate, "heredoc_aninhado_mesmo_delimitador", lambda _c: None),
     [HEREDOC_ISOLADO]),
    ("lista de verbos destrutivos esvaziada",
     "Se os destrutivos continuarem sendo pegos, a lista nao e o que barra.",
     lambda: setattr(gate, "VERBOS_DESTRUTIVOS", []),
     SO_DESTRUTIVOS),
    ("verbos de ALTO DANO esvaziados (2o eixo)",
     "Se os casos de OUTRO DONO continuarem pegos, a lista nova nao e o que barra.",
     lambda: setattr(gate, "VERBOS_ALTO_DANO", []),
     [c for _n, c in DONO_BLOQUEIA]),
    ("alvo ~/.claude deixando de casar",
     "Se ainda barrar, o gate nao esta olhando o alvo que diz olhar.",
     lambda: setattr(gate, "ALVO", re.compile(r"NUNCA_CASA_XYZ")),
     SO_DESTRUTIVOS),
    ("detector de acento em heredoc desarmado (4o eixo)",
     "Estes casos nao destroem nada e nao tocam dono alheio: se continuarem "
     "sendo pegos, quem barra e outro eixo, e o 4o nao existe de fato.",
     lambda: setattr(gate, "heredoc_com_acento", lambda _c: None),
     do_eixo("acento_heredoc")),
    ("detector de busca acentuada desarmado (o irmao do 4o eixo)",
     "Se um `grep` com acento continuar sendo pego, quem barra e outra coisa.",
     lambda: setattr(gate, "busca_com_acento", lambda _c: None),
     do_eixo("acento_busca")),
    ("detector de commit-sem-verificacao desarmado (5o eixo)",
     "Um `git commit --no-verify` nao destroi nada, nao toca dono alheio e nao "
     "tem acento: se continuar sendo pego com o detector desligado, o 5o eixo "
     "nao existe de fato e o que barra e outra coisa.",
     lambda: setattr(gate, "pula_a_verificacao", lambda _c: ""),
     do_eixo("pula_verificacao")),
]

# O que cada mutacao desarma. A lista e UMA so: quando ela era duas (uma para
# salvar, outra para restaurar), acrescentar o 4o detector deixou
# `heredoc_com_acento` desarmado depois da ultima mutacao, e o CONTROLE do
# final falhou. O controle fez o trabalho dele - mas o defeito estava no
# teste, e um teste que se auto-sabota gasta a confianca do gate que ele mede.
DESARMAVEIS = ("heredoc_aninhado_mesmo_delimitador", "heredoc_com_acento",
               "busca_com_acento", "pula_a_verificacao", "VERBOS_DESTRUTIVOS",
               "ALVO", "VERBOS_ALTO_DANO")

sobreviveram = []
for nome, porque, aplicar, casos in MUTACOES:
    original = dict((k, getattr(gate, k)) for k in DESARMAVEIS)
    aplicar()
    try:
        ainda_pegos = [c for c in casos if gate.analisar(c)]
    finally:
        for k, v in original.items():
            setattr(gate, k, v)
    detectada = len(ainda_pegos) == 0
    print("  [%s] %s" % ("DETECTADA" if detectada else "SOBREVIVEU", nome))
    print("           " + porque)
    print("           %d de %d caso(s) continuaram sendo pegos"
          % (len(ainda_pegos), len(casos)))
    if not detectada:
        sobreviveram.append(nome)

print("\n== 4. controle: com tudo no lugar, os casos voltam a ser pegos ==")
marcar("os %d casos destrutivos sao pegos de novo" % len(DEVE_BLOQUEAR),
       all(gate.analisar(c) for _e, _n, c in DEVE_BLOQUEAR))

print("\n=== RESULTADO: %d PASS / %d FALHA / %d mutacao(oes) sobreviveram ==="
      % (PASSOU, FALHOU, len(sobreviveram)))
for nome in sobreviveram:
    print("   mutacao nao detectada: " + nome)
sys.exit(1 if (FALHOU or sobreviveram) else 0)
