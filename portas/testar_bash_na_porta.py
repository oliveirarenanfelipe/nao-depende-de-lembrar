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
import json
import os
import re
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(AQUI, "bash_na_porta.py")
sys.path.insert(0, AQUI)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
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
    ("o comando exato do estrago (heredoc aninhado)", COMANDO_DO_ESTRAGO),
    ("heredoc aninhado isolado, sem tocar a mente", HEREDOC_ISOLADO),
    ("rm num hook da mente",
     'H="C:/Users/olive/.claude/hooks"\nrm -f "$H/prompt_memory.py"'),
    ("cp sobrescrevendo um hook",
     'cp backup/memory_lib.py "C:/Users/olive/.claude/hooks/memory_lib.py"'),
    ("python apagando dentro da mente",
     'python -c "import shutil; shutil.rmtree(r\'C:/Users/olive/.claude/projects\')"'),
    ("redirecionamento por cima do settings.json",
     'echo "{}" > C:/Users/olive/.claude/settings.json'),
    ("git reset --hard na mente",
     'git -C ~/.claude reset --hard origin/main'),
    ("mv levando a pasta de memoria embora",
     'mv ~/.claude/projects/C--x/memory /tmp/lixo'),
    # ── 4o EIXO: heredoc carregando texto ACENTUADO ────────────────────────
    # O 1o caso e a FORMA de um comando que gravou 53
    # caracteres U+FFFD numa nota de memoria. Nenhum dos tres eixos anteriores
    # olhava para isso: nao destroi, nao invade dono alheio, sai com exit 0 e
    # o arquivo continua sendo UTF-8 valido. So o CONTEUDO esta errado.
    ("heredoc com acento (a forma que corrompeu a memoria)",
     'cat > /tmp/nota.md <<\'EOF\'\ntrês relógios, irmão\nEOF'),
    ("heredoc com emoji",
     'cat > /tmp/nota.md <<\'EOF\'\nalerta \U0001F534 aberto\nEOF'),
    ("heredoc acentuado sem linha de fechamento no comando",
     'cat > /tmp/nota.md <<\'EOF\'\nmanutenção pendente'),
    # ── O irmao PIOR do 4o eixo: o acento que se perde na BUSCA ────────────
    # Aqui o estrago nao fica no arquivo, fica no VEREDITO. Medido:
    # `grep -c` pelo Bash deu 0 e a ferramenta Grep deu 1, no mesmo arquivo e
    # no mesmo instante. A REGRA #0 manda verificar antes de afirmar, e
    # verificar e quase sempre grep.
    ("grep por termo acentuado (o falso negativo medido)",
     'grep -c "correções" pendencias_ativas.md'),
    ("rg por termo acentuado",
     'rg "manutenção" ./docs'),
    ("python -c conferindo com `in` texto acentuado",
     'python -c "print(\'manutenção\' in t)"'),
]

DEVE_PASSAR = [
    ("leitura pura", 'cat "C:/Users/olive/.claude/hooks/memory_lib.py" | head -40'),
    ("grep na mente", 'grep -rn "BUDGET_MS" ~/.claude/hooks/'),
    ("rodar o reindex", 'python "C:/Users/olive/.claude/hooks/reindex_memory.py"'),
    ("dois heredocs em SEQUENCIA com o mesmo nome (padrao que funciona)",
     'cat > a.md <<\'MDEOF\'\nprimeiro\nMDEOF\ncat > b.md <<\'MDEOF\'\nsegundo\nMDEOF'),
    ("heredoc aninhado com delimitadores DIFERENTES",
     'python - <<\'FORA\'\nprint("ok")\n# aqui dentro: cat <<\'DENTRO\'\nFORA'),
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
for nome, cmd in DEVE_BLOQUEAR:
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

print("\n== 3. MUTACAO (desarma o detector; os casos tem de DEIXAR de ser pegos) ==")
import bash_na_porta as gate  # noqa: E402

# Os casos que SO o eixo destrutivo pega. A lista e por EXCLUSAO explicita de
# quem tem outro dono, porque o filtro antigo (`"heredoc" not in nome`) parou
# de funcionar no dia em que nasceram casos de BUSCA acentuada: eles nao tinham
# "heredoc" no nome, entravam aqui, continuavam sendo pegos pelo eixo deles, e
# duas mutacoes "sobreviveram" sem nenhum detector estar quebrado. Mutacao que
# acusa o inocente gasta a mesma confianca que mutacao que nao acusa ninguem.
DE_OUTRO_EIXO = ("heredoc", "grep ", "rg ", "python -c")
SO_DESTRUTIVOS = [c for n, c in DEVE_BLOQUEAR
                  if not any(n.startswith(p) or p in n for p in DE_OUTRO_EIXO)]

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
     [c for n, c in DEVE_BLOQUEAR
      if "heredoc" in n and ("acentuado" in n or "acento" in n or
                             "emoji" in n)]),
    ("detector de busca acentuada desarmado (o irmao do 4o eixo)",
     "Se um `grep` com acento continuar sendo pego, quem barra e outra coisa.",
     lambda: setattr(gate, "busca_com_acento", lambda _c: None),
     [c for n, c in DEVE_BLOQUEAR
      if n.startswith(("grep ", "rg ", "python -c"))]),
]

# O que cada mutacao desarma. A lista e UMA so: quando ela era duas (uma para
# salvar, outra para restaurar), acrescentar o 4o detector deixou
# `heredoc_com_acento` desarmado depois da ultima mutacao, e o CONTROLE do
# final falhou. O controle fez o trabalho dele - mas o defeito estava no
# teste, e um teste que se auto-sabota gasta a confianca do gate que ele mede.
DESARMAVEIS = ("heredoc_aninhado_mesmo_delimitador", "heredoc_com_acento",
               "busca_com_acento", "VERBOS_DESTRUTIVOS", "ALVO",
               "VERBOS_ALTO_DANO")

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
       all(gate.analisar(c) for _n, c in DEVE_BLOQUEAR))

print("\n=== RESULTADO: %d PASS / %d FALHA / %d mutacao(oes) sobreviveram ==="
      % (PASSOU, FALHOU, len(sobreviveram)))
for nome in sobreviveram:
    print("   mutacao nao detectada: " + nome)
sys.exit(1 if (FALHOU or sobreviveram) else 0)
