# fundação

A máquina que faz a casa construir direito sem depender de ninguém lembrar.

*[English](README.en.md)*

---

Todo mundo que trabalha com um agente de código acaba com a mesma coleção de
regras: sempre escreva teste, não commite segredo, registre a decisão. Elas
ficam num `CLAUDE.md`, num `AGENTS.md`, num `.cursorrules`. E aí o agente lê,
concorda, e na sessão seguinte esquece.

O diagnóstico que originou este repositório foi dito assim:

> *"tem muita coisa que a gente não faz. ou se faz eu não tenho o
> conhecimento, ou às vezes faz e às vezes esquece, depende de eu lembrar de
> ficar pedindo."*

Regra escrita em prosa não segura nada. O que segura é uma peça que mede, e
outra que barra. É o que está aqui.

---

## A régua que vale para tudo neste repositório

> Aviso que não reprova é decoração.

Nenhuma peça daqui existe para sugerir. Cada uma ou devolve um número que você
pode conferir, ou recusa a escrever o arquivo. E cada uma prova o próprio
resultado antes de gravar:

- o `ligar_ci` roda o comando de teste antes de escrever o workflow. Se o teste
  falha, não há CI. Um CI que roda o comando errado fica verde sem testar nada,
  e verde falso é pior que vermelho, porque ninguém volta a olhar;
- o `destilar` mede a própria saída antes de publicar. Se sobrou uma linha com
  contexto privado, não escreve nada e mostra a linha;
- o `inventario` executa o teste de cada peça. Peça que existe, tem chamador e
  cujo teste reprova não está no ar: está quebrada, e o mapa diz isso na cara.

---

## O que tem aqui

### medida: responder com número, não com impressão

| peça | a pergunta que ela responde |
|---|---|
| `o_basico.py` | *todo projeto da casa cuida do básico?* Sete itens por projeto: identidade, é repositório git, `.gitignore`, tem teste escrito, o CI roda o teste, varredura de segredo, decisões registradas |
| `inventario.py` | *a máquina está de pé?* Para cada peça: existe no disco, tem quem a chame, o teste dela passa agora |

O `o_basico` separa "tem teste" de "o CI roda o teste" de propósito. É o par
onde quase todo projeto mente para si mesmo.

### conserto: escrever a correção, não listá-la

| peça | o que faz |
|---|---|
| `ligar_ci.py` | descobre a forma de teste que o projeto já tem (`pytest`, `npm test`, `go test`, script próprio), roda o comando, e só então escreve o workflow |
| `consertar.py` | escreve no *working tree* o que falta (identidade, varredura de segredo, `.gitignore`) e mostra o que escreveu. Quem commita é você |

### régua: tirar a decisão do olho e pôr numa conta

| peça | o que decide |
|---|---|
| `regua_de_trava.py` | que trava de publicação este projeto exige, lida do contrato do próprio projeto (`efeito_no_mundo`, `dado_de_cliente`, `lifecycle`). Devolve três partes, e omitir qualquer uma o inutiliza: o que é recomendado, o que custa, e a saída que existe hoje |
| `regua_de_complexidade.py` | quanto rigor de processo uma tarefa merece. Cinco dimensões de 1 a 5 decidem `SIMPLE`, `STANDARD` ou `COMPLEX` |

A régua de trava é derivada, e não uma recomendação genérica, por um motivo:
"este projeto é sério?" é pergunta que cada dia responde diferente, e
recomendação que não muda com a resposta vira ruído que se aprende a pular.

### publicação: o que sai daqui foi medido antes de sair

| peça | o que faz |
|---|---|
| `medir_privacidade.py` | acha contexto privado num arquivo: pessoa, empresa, projeto interno, caminho de disco, incidente com data, contato |
| `destilar.py` | prepara uma peça para publicação, e recusa o que não limpou |
| `vitrine.py` | gera uma página com o estado da casa |

🔴 O `destilar` é o oposto de um sanitizador, e isso é o ponto. Sanitizador
silencioso dá falsa confiança: troca o que conhece, publica o resto, e o que
ele não conhecia vaza calado. Aqui ele troca só o mecânico (caminho de disco),
mede a própria saída, e se sobrou uma linha com contexto privado não escreve
nada. Linha que cita cliente ou incidente é decisão, não filtro: quem escreve a
versão pública é gente, com a linha na frente.

Este README e as peças acima passaram por ele.

---

## Como rodar

Não há dependência externa. Python 3, e só.

```bash
cp maquina/privacidade.json.exemplo maquina/privacidade.json
cp maquina/mapa.json.exemplo maquina/mapa.json
# abra os dois e ponha os seus nomes, as suas contas, as suas peças

python maquina/inventario.py          # a máquina está de pé?
python maquina/o_basico.py            # a casa cuida do básico?
python maquina/ligar_ci.py --todos    # quem tem teste que nenhum CI roda
python maquina/regua_de_trava.py <pasta-do-projeto>
```

Os dois `.json` são dado, e o dado é seu. Sem eles as peças param com erro, de
propósito: um detector que cai para lista vazia aprova tudo em silêncio, e um
mapa vazio responde "nenhuma peça quebrada" sobre nenhuma peça. Falhar alto é
a escolha, não o descuido.

---

## Os testes

```bash
python -B maquina/testar_inventario.py
python -B maquina/testar_o_basico.py
python -B maquina/testar_ligar_ci.py
python -B maquina/testar_consertar.py
python -B maquina/testar_vitrine.py
python -B maquina/testar_destilar.py
python -B maquina/testar_regua_de_trava.py
python -B maquina/testar_regua_de_complexidade.py
```

Medido: 8 suítes, 150 checagens, 22 mutações, 0 sobrevivente.

Toda suíte tem mutação executável, e é isso que separa este repositório de um
conjunto de testes que passa. A pergunta que um teste verde não responde é
"ele exercitou o caminho?". A mutação responde: quebra-se o alvo de propósito e
exige-se que o teste acuse. Se cegar o detector não muda nada, é porque ele já
não media.

O critério é mais duro que "o teste falhou": exige-se que o alvo mude e nada
além. Mutação grosseira que muda o mundo inteiro se passa por detecção fina do
detector que ela deveria isolar.

---

## A fronteira

Estas peças medem e consertam, e tocam projetos que não são delas. Mas
commitar e empurrar no repositório de outro dono é do dono: a peça prepara e
mostra, e quem publica é você. Nenhuma peça daqui dá `git commit` ou
`git push`.

---

## Como isto nasceu

Este repositório é uma destilação, não um projeto paralelo. As peças rodam todo
dia numa casa de verdade, com cerca de 30 projetos. O que você lê aqui é a
mesma implementação, com o contexto privado reescrito à mão, arquivo por
arquivo, e o resultado medido pelo `medir_privacidade` antes de sair.

Não existem duas implementações. Foi justamente para evitar isso que o
`destilar` foi escrito.

---

## Licença

MIT. Veja [LICENSE](LICENSE).
