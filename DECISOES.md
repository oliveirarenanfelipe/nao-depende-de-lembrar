# Decisões

As escolhas que moldaram este repositório, e por que, inclusive as que foram
recusadas.

Uma decisão registrada é diferente de documentação. Documentação descreve o
presente e apodrece quando o presente muda. Uma decisão descreve um momento e
o que se sabia nele, e continua verdadeira mesmo depois de ser superada. Por
isso nada aqui é editado: decisão que muda ganha uma entrada nova dizendo qual
ela substitui.

A explicação de uma peça continua morando na docstring dela. Aqui fica só o
que nenhuma peça sozinha carrega.

---

## 1. O que identifica a casa é dado, nunca constante de código

Status: aceita.

A lista de nomes de pessoas, de projetos internos e de caminhos de disco vive
em `privacidade.json`. O mapa das peças vive em `mapa.json`. A configuração da
instalação vive em `casa.json`. Nenhum deles é código.

A versão publicada deste repositório já carregou, dentro do `inventario.py`, a
lista de arquivos da máquina de quem o escreveu. Rodando noutro computador,
ele respondia `sem arquivo no disco: 0`, porque continuava olhando uma pasta
que não existia ali. Código publicado que responde bonito sobre o nada é pior
que código não publicado: ninguém desconfia de uma peça que roda.

Daí decorre que toda peça que lê um desses arquivos e não o encontra levanta
erro. Nunca cai para lista vazia, pelo motivo da decisão 2.

---

## 2. Dado ausente puxa para o lado do não

Status: aceita.

Uma peça sem o seu dado não continua com uma lista vazia. O que ela faz
depende de para que lado a lista vazia empurra:

| dado ausente | o que acontece |
|---|---|
| `mapa.json` | erro. Sem peças, o inventário responderia "nenhuma peça quebrada" sobre nenhuma peça |
| `seeds_inseguros.json` | o gate nega toda gravação, dizendo por quê. Um detector sem padrões aprovaria qualquer código |
| `publicar_isentos.json` | zero isentos. Aqui a lista vazia reprova mais, e por isso não precisa levantar erro |

A regra não é falhar alto sempre. É que a ausência do dado nunca pode produzir
uma aprovação.

---

## 3. Toda peça tem prova por mutação

Status: aceita.

Um teste que passa não prova que o detector detecta. Prova que ele não
explodiu. O que prova é quebrar o alvo de propósito e exigir que o teste
acuse.

Cada suíte daqui desarma a peça que testa. Cega o medidor, esvazia o catálogo,
desliga a execução do teste, e falha se a suíte continuar verde. Uma mutação
que sobrevive é uma asserção que não existe.

O critério de uma boa mutação: o alvo muda e nada além. Uma mutação que quebra
o mundo inteiro prova que o teste roda, não que ele mede.

---

## 4. Zero dependência, e isso é uma restrição de desenho

Status: aceita.

Python puro, biblioteca padrão. Nada de `requirements.txt`, nada de
`pip install` para rodar as peças ou as suítes. O `coverage` aparece só no CI,
para medir, e nenhuma peça o importa.

Cada dependência é uma pergunta a mais para quem clona, do tipo "qual versão?"
e "e no Windows?", além de uma superfície a mais para o dependabot. Uma
ferramenta que existe para ser instalada em qualquer lugar não pode exigir um
ambiente montado antes de provar que funciona.

Por esse critério rejeitamos ferramentas boas, como na decisão 6.

---

## 5. Não vamos para o PyPI

Status: aceita.

A instalação é `git clone`. Não há `pyproject.toml`, não há pacote.

As peças não são uma biblioteca que se importa. São comandos que se rodam
sobre um repositório, e metade delas são hooks que o agente lê de uma pasta
específica. O `pip install` não resolveria nada disso, e criaria uma obrigação
de manutenção, com versões, compatibilidade e um nome reservado para sempre,
em troca de conveniência nenhuma.

O gatilho para reabrir: alguém precisar `import` de uma peça dentro do próprio
código, e não ter como. Até lá, não.

---

## 6. A ferramenta `pre-commit` foi recusada; o hook é sh mais Python

Status: aceita. Decorre da 4.

O gate do commit é um `.githooks/pre-commit` em `sh` chamando Python puro,
ligado com `git config core.hooksPath .githooks`.

A ferramenta `pre-commit` exige `pip install pre-commit` antes de proteger
qualquer coisa. Um gate que só funciona depois de instalar algo é um gate que
a maioria não liga.

O que se perde, dito na frente: a ferramenta traz um catálogo grande de
verificadores prontos e resolve o versionamento deles. Nada disso faz falta
enquanto o gate for um comando só.

---

## 7. Isenção se declara por nome, nunca por prefixo

Status: aceita.

O `publicar_isentos.json` mapeia nome exato de arquivo para o motivo, em uma
linha. Se o motivo não cabe numa linha, não é isenção: é buraco.

O gate de publicação já isentou por prefixo de nome, o `EXEMPLO-`, e deixou
passar quatro linhas privadas. Isenção por prefixo cresce sozinha, porque
basta batizar o próximo arquivo igual e ninguém precisa decidir isentar nada.
A por nome não cresce e cabe numa justificativa.

Há uma exceção, e ela é estreita. O `forma_publica` isenta uma linha que é
inteiramente estrutura de arquivo, como o cabeçalho de versão de um changelog.
Cada padrão é ancorado nas duas pontas e tem prova de que não casa prosa,
porque uma forma frouxa não isenta uma linha: desliga o detector.

---

## 8. O `ruff` roda como linter, não como formatador

Status: recusada, a parte do formatador.

O `ruff check` está no CI. O `ruff format` não está, e não vai estar.

Medido, o `ruff format` reescreveria 3.074 linhas de uma vez. O custo real não
é o diff. É que o `git blame` de praticamente todo o repositório passaria a
apontar para um commit de formatação, apagando de quem e de quando veio cada
decisão. As peças também são prosa longa em português, com quebras de linha
escolhidas para o texto ler bem, e um formatador não distingue isso de código
mal alinhado.

O gatilho para reabrir: contribuidores regulares, quando a consistência
automática passa a valer mais que a autoria das linhas.

---

## 9. Sem filtro por caminho no CI

Status: recusada.

O CI roda tudo em toda PR.

A suíte inteira leva segundos e o CI tem três jobs. Filtrar por caminho
exigiria uma ação de terceiro no pipeline, contra a decisão 4, para economizar
um tempo que não é gasto. E filtro por caminho tem um modo de falha próprio e
silencioso: a mudança que o filtro não previu passa sem teste.

---

## 10. O gate que força declarar o fato foi recusado

Status: recusada.

Um repositório de referência tem um gate opcional que barra a primeira edição
de cada arquivo numa sessão e exige que o agente declare quatro coisas antes de
tentar de novo: quem importa o arquivo, que interface pública a mudança afeta,
que dado ele lê e escreve, e a instrução do usuário citada palavra por palavra.
A ideia é boa e o raciocínio dela é correto: investigar cria consciência que a
auto-avaliação não cria.

Não adotamos, por três motivos somados.

O primeiro é que ele é opcional até no repositório de origem, desligado por
padrão e descrito lá mesmo como atrito deliberado. Adotar ligado o que o autor
deixou desligado é ignorar o que ele aprendeu usando.

O segundo é que a casa já paga esse custo por outro caminho. A regra de
precisão obriga a ler o arquivo antes de afirmar qualquer coisa sobre ele, e
sete portas já barram a escrita por motivos concretos. Um oitavo bloqueio que
pede uma declaração em texto livre mede o que foi digitado, não o que foi
lido — e declaração em texto livre é exatamente o tipo de verificação que um
agente com pressa aprende a preencher.

O terceiro é o custo de operação. Ele barra a primeira edição de todo arquivo,
o que numa sessão de vinte arquivos são vinte interrupções. Gate que interrompe
demais é gate que alguém desliga, e aí ele deixa de valer para tudo.

O gatilho para reabrir: uma sessão em que uma edição cega cause estrago
rastreável, com o arquivo e a linha. Aí o caso deixa de ser teórico e a
pergunta passa a ser qual o desenho certo, não se vale a pena.

---

## 11. Quatro códigos de saída, e um guardião

Status: aceita.

O `0` é nada a acusar, o `1` é acusou, o `2` é não deu para usar, e o `3` é
não deu para medir.

A convenção já existia sem estar escrita, e já havia divergido: o `2`
significava "uso errado" em duas peças e "achou arquivo solto" numa terceira.
Duas peças dizendo coisas diferentes com o mesmo número é pior que não ter
número, porque quem lê o código de saída num script decide errado e nada
acusa.

Ela não apodrece porque não virou documento. O `inventario.py` varre as peças
e reprova quem usar um número fora da lista. Esta entrada explica o porquê; a
garantia é o código.
