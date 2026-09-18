# -*- coding: utf-8 -*-
r"""A SEGURANÇA INTERROMPE NA PORTA — hook PreToolUse de Edit|Write em CÓDIGO.

Pergunta do dono da casa, que é a origem deste arquivo:

    *"como que exatamente funciona quando eu peço para vc aprender algo para se
    tornar nosso modo de trabalho, ou seja, segurança tem que ser algo que a
    gente não pode abrir mão, e ai aprendemos, nos proximos projetos como isso
    vai ficar?"*

O QUE A MEDIÇÃO RESPONDEU (contra os 6 gates PreToolUse existentes):
**nenhum deles olhava a segurança do código.** O `bash_na_porta` defende a mente
de comando destrutivo; o `soberano`, a `fronteira` e o `catalogo` defendem a
organização; o `humanizar` defende o texto. O código que eu escrevo passava sem
ninguém olhar.

A R3 do soberano manda criar toda peça nova já com os 10 vetores. Isso é REGRA
ESCRITA, e a própria casa já decidiu que *"aviso que não reprova é decoração"*.
A prova de que não segurava: os seeds acharam **88 arquivos com TLS
desligado**, e num deles a senha real dele subia por esse canal. Ficou assim
por meses, com a R3 em vigor o tempo todo.

A ESCADA DE FORÇA, e por que este arquivo é o degrau que faltava:

    texto no soberano ....... vale enquanto eu lembro de ler
    recall / catálogo ....... vale quando a palavra encosta
    varredura diária [6j] ... acha no dia seguinte
    GATE NA PORTA ........... impede de nascer      <- este arquivo

E é isto que responde *"nos próximos projetos como vai ficar"*: os hooks moram
em `~/.claude/settings.json`, que é GLOBAL. O projeto 17 nasce com este gate
ativo sem ninguém instalar nada — ao contrário da regra escrita, que depende de
eu abrir o soberano e lembrar.

INTERROMPE UMA VEZ POR ARQUIVO, como os irmãos: às vezes o padrão é legítimo
(script local contra servidor de teste). A 2ª gravação passa, e o porquê fica
registrado na resposta.

FONTE DOS PADRÕES: `seguranca_seeds.py` — a mesma da varredura diária, para não
haver duas verdades.
TESTE DE MUTAÇÃO: `testar_seguranca_na_porta.py`.
CHAMADOR: `~/.claude/settings.json`, bloco PreToolUse `Edit|Write`.
"""
import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import seguranca_seeds  # noqa: E402

CODIGO = (".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs", ".sh", ".sql",
          ".go", ".rb", ".php", ".java", ".yml", ".yaml", ".tf")
ESTADO = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "seguranca_na_porta.estado.json")

# Fora do alcance, e cada um com motivo:
#  - hooks/ e o proprio seeds_inseguros.json: aqui MORAM os padroes; o arquivo
#    que descreve o defeito casaria com ele mesmo.
#  - test/spec/fixture: teste precisa poder escrever o caso ruim.
#  - node_modules/.git/dist/build/.venv: nao e codigo nosso.
# A lista saiu daqui e virou `seguranca_seeds.ISENTOS` / `e_isento()`.
# Motivo medido: a varredura diaria [6j] tinha isencoes MENORES que as do gate,
# e 11 dos 13 alertas dela eram fixture de teste. Duas verdades sobre "quem nao
# se audita" e a mesma classe que o modulo foi criado para impedir.


def ja_avisei(sessao, alvo):
    chave = "%s|%s" % (sessao or "?", alvo)
    try:
        with io.open(ESTADO, encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception:                                       # noqa: BLE001
        d = {}
    agora = time.time()
    d = {k: v for k, v in d.items() if agora - v < 86400}
    visto = chave in d
    d[chave] = agora
    try:
        with io.open(ESTADO, "w", encoding="utf-8") as fh:
            json.dump(d, fh)
    except Exception:                                       # noqa: BLE001
        pass
    return visto


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                       # noqa: BLE001
        pass
    try:
        ent = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
    except (ValueError, AttributeError):
        return
    ti = ent.get("tool_input") or {}
    alvo = ti.get("file_path") or ""
    if not alvo.lower().endswith(CODIGO):
        return
    if seguranca_seeds.e_isento(alvo):
        return

    texto = ti.get("content") or ti.get("new_string") or ""
    if not texto.strip():
        return
    # 🔴 SEM OS SEEDS, ESTE GATE NEGA — nao passa. Houve um tempo em que o
    # devolvia lista vazia em silencio quando o JSON faltava, e o gate
    # respondia `permitido` para todo codigo. Medido ao rodar a peca destilada
    # numa pasta sem o dado: tres familias que barram passaram a aprovar, e o
    # veredito lido de fora era "o codigo esta limpo".
    #
    # Negar aqui e a mesma escolha do gate do Bash diante da fronteira
    # quebrada: quando o detector nao pode AFIRMAR que o codigo e seguro, ele
    # nao finge que pode. Gate que morre em silencio parece gate que aprovou.
    try:
        achados = seguranca_seeds.varrer(texto, limite=6)
    except seguranca_seeds.SeedsAusentes as e:
        _emitir_deny([
            "PARE — o detector de defaults inseguros esta CEGO.",
            "",
            "  · %s" % e,
            "",
            "Isto NEGA em vez de passar de proposito: um detector sem padroes "
            "responde 'nada encontrado' para todo codigo, e 'nada encontrado' "
            "le igual a 'codigo limpo'.",
            "",
            "O QUE FAZER: restaure `seeds_inseguros.json` ao lado do "
            "`seguranca_seeds.py` (ha um `.exemplo` no repositorio). Para "
            "seguir enquanto conserta, escreva o codigo e revise a mao.",
        ])
        return

    # As perguntas de ARQUIVO (teto de token, filtro por dono) precisam do texto
    # final inteiro. Num Edit chega so o pedaco, e julgar o arquivo pelo pedaco
    # da falso positivo aqui: a defesa costuma estar fora do trecho editado
    # ([[concept-a-condicao-de-arquivo-julgada-sobre-o-pedaco]]). Entao montamos
    # o conteudo final: no Write e o proprio `content`; no Edit, o arquivo do
    # disco com a substituicao aplicada. Se nao der para montar, NAO se opina.
    final = None
    if ti.get("content"):
        final = texto
    elif ti.get("old_string") is not None:
        try:
            with io.open(alvo, encoding="utf-8") as fh:
                atual = fh.read()
            final = atual.replace(ti["old_string"], texto, 1)
        except OSError:
            final = None
    if final:
        achados += seguranca_seeds.varrer_arquivo(final)

    if not achados:
        return
    if ja_avisei(ent.get("session_id"), os.path.abspath(alvo)):
        return

    linhas = [
        "PARE — este código nasce com um default inseguro.",
        "",
        "`%s` — %d ocorrência(s):" % (os.path.basename(alvo), len(achados)),
        "",
    ]
    for fam, n, trecho in achados:
        linhas.append("  · linha %-4d [%s]" % (n, fam))
        linhas.append("      %s" % trecho)
        conserto = seguranca_seeds.conserto_de(fam)
        if conserto:
            linhas.append("      ➜ %s" % conserto)
    linhas += [
        "",
        "A regra manda criar toda peça nova já com os vetores conhecidos. Isto "
        "aqui é o mecanismo dela: a mesma checagem achou 88 arquivos com o TLS "
        "desligado, e num deles uma senha real subia por esse canal — com a "
        "regra escrita e em vigor o tempo todo.",
        "",
        "Conserte ANTES de gravar. O detalhe de cada família e o conserto estão "
        "no checklist de auditoria de segurança da casa.",
        "",
        "Se o padrão for legítimo aqui (script local, servidor de teste), repita "
        "a gravação — a 2ª passa — e diga na resposta POR QUE é legítimo.",
    ]
    _emitir_deny(linhas)


def _emitir_deny(linhas):
    """A recusa, no formato que o harness entende. Uma so saida, um so lugar."""
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "\n".join(linhas)}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
