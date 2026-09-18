# Contribuindo

Antes de qualquer coisa, a régua que vale para todo código daqui:

> Aviso que não reprova é decoração.

Se a sua mudança acrescenta algo que apenas avisa, ela vai ser recusada com
essa frase. Peça nova aqui ou devolve um número que dá para conferir, ou
recusa a escrever o arquivo.

---

## O que é aceito

Peça que resolve um problema **medido**. O commit precisa dizer o número: o
que estava errado, quantas vezes aconteceu, e o que mudou depois.

Não é aceito: refatoração por estética, renomear por preferência, abstrair
algo que tem um único caso de uso, ou acrescentar dependência.

Este projeto não tem dependências, e isso é uma escolha. Python 3 puro roda em
qualquer lugar sem `pip install` nenhum.

---

## O rito, e ele não tem atalho

Toda peça nova nasce com quatro coisas no mesmo commit:

1. **A peça.**
2. **O teste dela**, com pelo menos uma mutação executável.
3. **A linha no `mapa.json`.** Peça fora do mapa não é medida, e não ser
   medida lê igual a não existir.
4. **Quem a chama.** Peça que ninguém invoca é defeito, não pendência.

Falta qualquer um dos quatro, a peça não entra.

---

## A mutação é obrigatória, e o motivo

Um teste verde não responde a pergunta que importa: *ele exercitou o caminho?*

A mutação responde. Você quebra o alvo de propósito e exige que o teste acuse.
Se desligar o detector não muda nada, é porque ele já não media.

O critério é mais duro que "o teste falhou". Exige-se que **o alvo mude e nada
além**. Uma mutação grosseira, que muda o mundo inteiro, passa por detecção
fina do detector que ela deveria isolar.

Exemplo do formato que usamos, tirado do `testar_destilar.py`:

```python
MUTACOES = [
    ("o medidor de privacidade fica cego",
     "e o modo de falha do sanitizador: troca o que conhece, publica o resto",
     mut_medidor_cego,
     lambda: all(publica(n) for n in ("pessoa", "projeto")),
     "as pecas SUJAS passam a ser publicadas"),
]
```

Cada mutação carrega o **porquê** e o **esperado**. Mutação sem os dois vira
enfeite na primeira vez que alguém mexe nela.

---

## Rodando

```bash
cp maquina/privacidade.json.exemplo maquina/privacidade.json
cp maquina/mapa.json.exemplo maquina/mapa.json
cp portas/casa.json.exemplo portas/casa.json

python -B maquina/testar_inventario.py    # e as outras suítes
```

As suítes não usam pytest. Cada uma roda sozinha e reporta por código de saída,
porque várias precisam de um sandbox montado antes da primeira asserção.

Antes de abrir um PR, rode todas:

```bash
for t in maquina/testar_*.py portas/testar_*.py; do python -B "$t" || break; done
```

E rode também com o `HOME` apontando para uma pasta vazia. É o cenário de quem
baixou o repositório, e foi ele que achou a maior parte dos defeitos daqui.

---

## Os códigos de saída, e são quatro

Toda peça reporta por código de saída, não por texto. São estes, e não há um
quinto:

| código | significa |
|---|---|
| `0` | nada a acusar |
| `1` | **ACUSOU** — mediu, e o alvo reprovou |
| `2` | não deu para **USAR** — argumento faltando, pasta que não existe |
| `3` | não deu para **MEDIR** — a fonte não respondeu. **Não é um verde** |

A distinção que mais importa é entre `1` e `3`. Um gate que não conseguiu
medir não está aprovando nada, e devolver `0` nesse caso é a falha silenciosa
que este repositório inteiro existe para impedir.

Uma peça com duas razões para reprovar devolve `1` nas duas, e explica a razão
no texto. Número de saída diferente por motivo diferente é como a divergência
entra: aqui o `2` já significou "uso errado" em duas peças e "achou arquivo
solto" numa terceira, e nada acusava.

Isso não é uma convenção escrita e esquecida — o `maquina/inventario.py` roda
`codigos_de_saida()` sobre todas as peças e **reprova** quem usar um número
fora da lista.

---

## O gate do commit

Ligue uma vez por clone:

```bash
git config core.hooksPath .githooks
```

A partir daí, todo `git commit` roda o `maquina/antes_de_publicar.py`, que mede
**três superfícies** do que o repositório está prestes a publicar:

1. o que está versionado — `git ls-files`
2. o que espera um `git add .` — arquivo não rastreado e não ignorado
3. o que a história guarda — as mensagens de commit

As duas últimas são as que nenhum gate de repositório costuma olhar, e foram
exatamente onde o furo apareceu aqui: quatro arquivos que a própria suíte gera
ao rodar, dois deles com o caminho absoluto do disco de quem rodou escrito
dentro, soltos fora do `.gitignore`. Nenhum estava commitado — estavam a um
`git add .` de distância.

Se o gate reprovar, **nada é commitado**. Para passar por cima num caso
legítimo: `git commit --no-verify`.

⚠️ **O hook é a segunda camada, não a primeira.** Ele depende de você ter
rodado o `git config` acima; quem não rodar não tem gate nenhum, e em silêncio.
A defesa que não depende de ninguém lembrar é o job `o-que-sobe` no CI, que
roda em toda PR. O hook existe para dar a resposta antes de gastar uma rodada.

Não usamos a ferramenta `pre-commit`: ela exige `pip install`, e este
repositório declara zero dependência. Um gate que só funciona depois de
instalar algo é um gate que a maioria não liga.

---

## Commits

Prefixo convencional: `feat:`, `fix:`, `docs:`, `test:`, `ci:`, `chore:`.

O corpo do commit diz o que foi **medido**. Um commit que afirma "melhora a
performance" sem número não passa; um que diz "544 s para 39 s, medido com o
worktree fora" passa.

---

## Onde a documentação mora

A explicação de uma peça mora na docstring dela, junto do código, e não num
documento separado. Documento separado apodrece sem ninguém perceber, porque
documento errado se parece com documento certo.

Se a sua peça precisa de explicação longa, ela vai no topo do arquivo.
