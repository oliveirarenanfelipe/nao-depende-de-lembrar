# -*- coding: utf-8 -*-
"""Prova do `seguranca_na_porta.py` — o portão barra E deixa passar.

🔴 POR QUE ESTE ARQUIVO NASCEU DOIS DIAS DEPOIS DO PORTÃO: o
`seguranca_na_porta.py` declarava na própria docstring *"TESTE DE
MUTAÇÃO: testar_seguranca_na_porta.py"* — e o arquivo não existia em lugar
nenhum `[medido: a varredura do disco devolveu nada]`. O portão
rodou dois dias com a prova afirmada no papel e ausente no disco. É a família
[[concept-o-rotulo-nao-e-a-prova-o-produtor-e]] dentro de casa.

O que se prova aqui, nesta ordem:

  1. cada caso conhecido recebe o veredito certo (barrar / passar)
  2. MUTAÇÃO: quebrar a fonte dos padrões e exigir que o portão PARE de barrar

Os casos de "passar" pesam tanto quanto os de "barrar": portão que reprova
código legítimo é portão que a gente desliga, e aí não protege nada.

⚠️ Sessão NOVA por caso, de propósito. O portão interrompe uma vez por
arquivo+sessão; reusar a sessão silencia do 2º caso em diante e faz caso bom
aparecer como falha. Aconteceu na 1ª versão desta prova.

CHAMADOR: `~/.claude/hooks/mente_health.py`, bloco [6t].
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(AQUI, "seguranca_na_porta.py")
SEEDS_PY = os.path.join(AQUI, "seguranca_seeds.py")
# alvo ficticio em projeto real: precisa escapar dos ISENTOS do gate
ALVO = os.path.join(os.path.expanduser("~"), "Projeto", "Personal",
                    "_prova_portao_seguranca.py")

CASOS = [
    # --- familia casa-aprendeu: o caso dos 88 arquivos com a senha dele
    ("TLS desligado (casa-aprendeu)", True,
     'import ssl\nctx = ssl.create_default_context()\n'
     'ctx.verify_mode = ssl.CERT_NONE\n'),

    # --- familia casa-portugues: o buraco de vocabulario
    ("segredo em portugues", True,
     # ⚠️ A senha de mentira nao leva o nome de empresa nenhuma. Ela existe
     # para o detector ter o que achar, e qualquer string serve — mas uma que
     # PARECE credencial de alguem vira, ela propria, o dado que este gate
     # existe para impedir. Achado ao destilar a peca.
     'SENHA = "trocar-antes-de-usar-123"\ndef entrar():\n    return SENHA\n'),

    # --- familia execucao-perigosa
    ("shell=True com entrada", True,
     'import subprocess\ndef rodar(cmd):\n'
     '    return subprocess.run(cmd, shell=True)\n'),

    # --- vetor 24: chamada de LLM paga sem teto de saida
    ("LLM sem max_tokens (anthropic)", True, '''
import anthropic
def responder(msg):
    c = anthropic.Anthropic()
    return c.messages.create(model="claude-sonnet-5",
                             messages=[{"role": "user", "content": msg}])
'''),
    ("LLM sem max_tokens (openai)", True, '''
from openai import OpenAI
def responder(msg):
    return OpenAI().chat.completions.create(model="gpt-4o",
        messages=[{"role": "user", "content": msg}])
'''),
    ("LLM COM max_tokens", False, '''
import anthropic
def responder(msg):
    c = anthropic.Anthropic()
    return c.messages.create(model="claude-sonnet-5", max_tokens=1024,
                             messages=[{"role": "user", "content": msg}])
'''),

    # --- vetor 23: busca vetorial sem filtro de dono
    ("busca vetorial sem filtro", True,
     'def buscar(indice, pergunta):\n'
     '    return indice.similarity_search(pergunta, k=5)\n'),
    ("busca vetorial COM filtro", False,
     'def buscar(indice, pergunta, tenant):\n'
     '    return indice.similarity_search(pergunta, k=5, '
     'filter={"tenant": tenant})\n'),

    # --- os que NAO podem ser barrados
    ("codigo comum", False, 'def somar(a, b):\n    return a + b\n'),
    ("comentario citando max_tokens", False,
     '# por max_tokens quando isto virar chamada de LLM\ndef rascunho():\n'
     '    return None\n'),
    ("mapa de papeis, nao credencial", False,
     'PAPEIS = {"admin": "admin", "operador": "operador"}\n'),
]

_N = [0]


def porta(texto):
    """True se o portao NEGOU a gravacao."""
    _N[0] += 1
    ent = {"session_id": "prova-%d-%d" % (os.getpid(), _N[0]),
           "tool_name": "Write",
           "tool_input": {"file_path": ALVO, "content": texto}}
    p = subprocess.run([sys.executable, "-B", HOOK],
                       input=json.dumps(ent).encode(), capture_output=True)
    saida = (p.stdout or b"").decode("utf-8", "replace")
    if not saida.strip():
        return False, ""
    try:
        h = (json.loads(saida).get("hookSpecificOutput") or {})
    except ValueError:
        return False, saida[:60]
    negou = h.get("permissionDecision") == "deny"
    fam = ""
    for linha in (h.get("permissionDecisionReason") or "").splitlines():
        if "[" in linha and "linha" in linha:
            fam = linha.strip()[:46]
            break
    return negou, fam


def rodar_casos(silencioso=False):
    falhas = []
    if not silencioso:
        print("%-34s %-8s %-8s %s" % ("caso", "devia", "portao", "familia"))
    for nome, deve, codigo in CASOS:
        negou, fam = porta(codigo)
        ok = (negou == deve)
        if not ok:
            falhas.append(nome)
        if not silencioso:
            print("%-34s %-8s %-8s %s%s"
                  % (nome, "BARRAR" if deve else "passar",
                     "barrou" if negou else "passou", fam,
                     "" if ok else "   << FALHOU"))
    return falhas


MUTACOES = [
    ("teto de token sai da lista",
     '"defesa": r"max_tokens|max_output_tokens|maxTokens|maxOutputTokens"',
     '"defesa": r"max_tokens|max_output_tokens|maxTokens|maxOutputTokens|def "',
     "LLM sem max_tokens (anthropic)"),
    ("gatilho da busca vetorial apagado",
     r'"gatilho": r"\.(?:similarity_search\w*|max_marginal_relevance_search)\s*\(|"',
     '"gatilho": r"ESTE_PADRAO_NAO_EXISTE_EM_LUGAR_NENHUM|"',
     "busca vetorial sem filtro"),
]


def main():
    print("== 1. os casos conhecidos ==")
    falhas = rodar_casos()
    print("")
    print("RESULTADO: %d de %d" % (len(CASOS) - len(falhas), len(CASOS)))
    for f in falhas:
        print("   FALHA: %s" % f)
    if falhas:
        print("")
        print("portao com veredito errado: mutacao nao se roda sobre base quebrada")
        print("   [[concept-mutacao-sobre-baseline-morto]]")
        return 1

    print("")
    print("== 1b. SEM os seeds, o portao NEGA — nao passa ==")
    # 🔴 O `carregar()` devolvia lista vazia em silencio quando o JSON faltava,
    # e o gate respondia `permitido` para TODO codigo. Medido ao rodar a peca
    # destilada numa pasta sem o dado: tres familias que barram passaram a
    # aprovar, e o veredito lido de fora era "o codigo esta limpo".
    #
    # Detector vazio e indistinguivel de detector que nao achou nada, e esse e
    # o unico erro aqui que nao se descobre depois.
    import seguranca_seeds as _ss  # noqa: E402
    _tmp = tempfile.mkdtemp(prefix="seeds_")
    try:
        for rotulo, conteudo in (("arquivo ausente", None),
                                 ("JSON vazio", "{}"),
                                 ("JSON quebrado", "{isto nao e json")):
            _f = os.path.join(_tmp, "seeds_%s.json" % rotulo.split()[0])
            if conteudo is not None:
                io.open(_f, "w", encoding="utf-8").write(conteudo)
            try:
                _ss.carregar(fonte=_f)
                levantou = False
            except _ss.SeedsAusentes:
                levantou = True
            except Exception:                               # noqa: BLE001
                levantou = False
            print("  [%s] %-18s levanta SeedsAusentes em vez de devolver []"
                  % ("OK " if levantou else "FALHA", rotulo))
            if not levantou:
                falhas.append("seeds %s nao levantou" % rotulo)

        # E o gate, diante disso, NEGA.
        #
        # ⚠️ O JSON e movido DE VERDADE, e nao ha atalho: o gate roda em
        # SUBPROCESSO, entao trocar `_ss.SEEDS` neste processo nao o alcanca.
        # A primeira versao disto fazia exatamente isso e lia "o gate nao
        # negou" — a mutacao nao chegava ao alvo. Mutacao que nao alcanca o
        # alvo nao prova nada sobre ele.
        _guardado = _ss.SEEDS + ".teste.bak"
        os.rename(_ss.SEEDS, _guardado)
        try:
            negou, motivo = porta("import x\nSENHA = \"abc123\"\n")
        finally:
            os.rename(_guardado, _ss.SEEDS)
        ok_nega = negou
        print("  [%s] o gate NEGA quando o detector esta cego"
              % ("OK " if ok_nega else "FALHA"))
        if not ok_nega:
            falhas.append("gate nao negou com os seeds ausentes: %r"
                          % motivo[:70])
    finally:
        shutil.rmtree(_tmp, ignore_errors=True)

    if falhas:
        print("")
        print("a garantia de falhar-alto quebrou: mutacao nao avaliada")
        return 1

    print("")
    print("== 2. mutacao: quebrar a fonte e exigir que o portao PARE de barrar ==")
    original = io.open(SEEDS_PY, "rb").read()
    shutil.copy2(SEEDS_PY, SEEDS_PY + ".mut.bak")
    pegas, aplicadas = 0, 0
    try:
        for nome, de, para, caso_alvo in MUTACOES:
            texto = original.decode("utf-8")
            if de not in texto:
                print("  [PULADA ] %-38s (trecho nao encontrado)" % nome)
                continue
            aplicadas += 1
            io.open(SEEDS_PY, "wb").write(
                texto.replace(de, para, 1).encode("utf-8"))
            alvo = [c for c in CASOS if c[0] == caso_alvo][0]
            negou, _ = porta(alvo[2])
            io.open(SEEDS_PY, "wb").write(original)
            pegas += 0 if negou else 1
            print("  [%s] %-38s alvo: %s"
                  % ("ESCAPOU" if negou else "PEGA   ", nome, caso_alvo))
    finally:
        io.open(SEEDS_PY, "wb").write(original)
        assert io.open(SEEDS_PY, "rb").read() == original, "RESTAURACAO FALHOU"
        try:
            os.remove(SEEDS_PY + ".mut.bak")
        except OSError:
            pass

    print("")
    print("MUTACAO: %d de %d" % (pegas, aplicadas))
    print("fonte restaurada byte a byte: OK")
    return 0 if (aplicadas and pegas == aplicadas) else 1


if __name__ == "__main__":
    sys.exit(main())
