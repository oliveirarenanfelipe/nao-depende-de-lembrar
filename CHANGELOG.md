# Changelog

Formato: [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).
Versionamento: [SemVer](https://semver.org/lang/pt-BR/).

## [Nao lancado]

### Adicionado

- **as DUAS portas que faltavam**: `padroes_na_porta` (39 regras de construcao,
  cada uma nascida de um defeito real, com o detector e o conserto dentro) e
  `fronteira_de_projeto` (impede uma sessao aberta num projeto de escrever no
  projeto de outro dono). Com o `calibrar_padroes`, que mede se alguma regra
  nova congela o editor.
- **`maquina/montar_repo.py` + `arranjo.json`**: monta o repositorio e prova o
  ARRANJO. Todo arquivo tem destino declarado, todo destino tem fonte, nenhum
  marcador de troca ficou em codigo, e o painel de fatos do README ainda bate
  com o que as suites respondem.
- **as trocas de data como regra**: a data de um incidente e removida por
  troca mecanica, e o NUMERO que a regra carrega fica. 71 reescritas manuais
  identicas viraram 14 linhas de dado.
- **`maquina/antes_de_publicar.py`**: o gate do `push`. Mede as tres
  superficies do que o repositorio vai publicar: o que esta versionado
  (`git ls-files`), o que espera um `git add .` e as mensagens de commit. As
  duas ultimas nenhum gate de repositorio costuma olhar, e foi onde o furo
  apareceu. Com prova por mutacao nas duas superficies.
- **`maquina/publicar_isentos.json`**: os arquivos que o gate nao mede,
  declarados por nome exato e com o motivo em uma linha.
- **`.githooks/pre-commit`**: o gate na porta do commit, em `sh` mais Python
  puro. Ligado com `git config core.hooksPath .githooks`. Provado com um
  repositorio de verdade: o commit sujo e barrado e nao entra na historia, e
  o `--no-verify` continua sendo a valvula.
- **`DECISOES.md`**: as dez decisoes que moldaram o repositorio, incluindo as
  recusadas e o gatilho para reabrir cada uma.
- **job `o-que-sobe`** no CI, com `fetch-depth: 0`. Sem ele a superficie das
  mensagens mediria um commit so e diria que o historico esta limpo.
- **workflow `release`**: a tag vira Release do GitHub com o trecho do
  CHANGELOG daquela versao. A release so nasce depois das suites passarem na
  mesma revisao, e nao usa acao de terceiro.
- **`inventario.codigos_de_saida()`**: o guardiao da taxonomia de erro.
  Reprova qualquer peca que use um codigo fora de `0`, `1`, `2` e `3`.
- **`maquina/montar_repo.py`**: monta o repositorio a partir do
  `arranjo.json` e prova o ARRANJO, nao so o conteudo. Tres perguntas: todo
  arquivo tem destino declarado, todo destino tem fonte, e o painel de fatos
  do README ainda bate com o que as suites respondem. Com prova por mutacao
  nas tres.
- **`maquina/arranjo.json`**: o mapeamento do que sobe, com que nome e em que
  pasta. Ate aqui isso vivia num script escrito na hora de montar e jogado
  fora depois, o que e a mesma coisa que nao existir.
- **o painel de fatos do README** passou a ser gerado e conferido no CI. Ele
  dizia `9 suites, 199 checagens` com o repositorio em 16 e 314.
- **a porta do Bash barra `git --no-verify`**, e tambem as formas curtas
  `git commit -n` e `-an`, que fazem o mesmo e sao mais faceis de digitar.
- **a porta de engenharia protege config de linter que JA existe** — ruff,
  eslint, prettier, biome, flake8 e outros. Conserte o codigo, nao afrouxe a
  regra. Criar config nova continua liberado.

### Corrigido

- **duas reguas do que e privado**. O `limpa_publicos` so era chamado pelo
  `destilar.sujeira()`; o `medir_privacidade` nao o usava. O `--conferir`
  respondia `LIMPO` enquanto o medidor acusava 28 linhas nos mesmos arquivos.
  A regua passou a ser uma so, o `mp.marcas_da_linha()`.
- **`.gitignore` incompleto**: quatro arquivos gerados por rodar a suite
  ficavam soltos, dois deles com o caminho absoluto do disco de quem rodou
  escrito dentro.
- **`2` com dois significados**: era "uso errado" em duas pecas e "achou
  arquivo solto" numa terceira.

## [0.1.0] - 2026-09-18

Primeira versao publica. Nove pecas da maquina, seis portas e as bibliotecas
que elas usam, com nove suites de teste e mutacao executavel.

### Adicionado

- **medida**: `o_basico` (7 itens por projeto) e `inventario` (existe, tem
  chamador, o teste passa agora).
- **conserto**: `ligar_ci` (roda o comando antes de escrever o CI) e
  `consertar` (escreve no working tree, nunca commita).
- **regua**: `regua_de_trava` (le o contrato do projeto) e
  `regua_de_complexidade` (5 dimensoes decidem o rigor).
- **publicacao**: `medir_privacidade`, `destilar` (recusa o que nao limpou) e
  `vitrine`.
- **portas**: `bash_na_porta` (4 eixos), `catalogo_na_porta`,
  `fundacao_na_porta`, `soberano_na_porta`, `humanizar_na_porta` e
  `seguranca_na_porta`, mais `fronteira_lib` e `seguranca_seeds`.
- CI rodando as 9 suites com `permissions: contents: read`.
- `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` e `.gitattributes`.

### Seguranca

- **Injecao de comando no `ligar_ci`**: o nome do arquivo de teste vinha do
  disco e era interpolado num comando com `shell=True`. Um arquivo chamado
  `testar_x.py && <comando>` executava o comando. Agora a execucao e por lista
  de argumentos, sem shell, e nome com metacaractere fica fora do CI com
  aviso. Provado por teste que planta o arquivo hostil e exige que a sonda nao
  exista.
- **Falso negativo no `seguranca_seeds`**: `carregar()` devolvia lista vazia em
  silencio quando o JSON faltava, e o gate passava a APROVAR todo codigo. Agora
  levanta `SeedsAusentes`, e a porta NEGA com a explicacao.
- **Log de auditoria mudo**: o `gates.log` apontava para um caminho fixo e o
  erro de escrita era engolido. O caminho passou a ser derivado da peca, e a
  falha avisa no stderr.
- Detector de **IP publico** acrescentado ao catalogo de privacidade: um IP
  real de servidor so era acusado por acidente, pela regex de e-mail.
- Detector do **slug de projeto do agente**, que carrega o nome do usuario do
  disco e passava limpo por todos os detectores.

### Notas

- Tres arquivos de dado ficam fora do repositorio, cada um com `.exemplo`.
- Os seeds de `trailofbits/insecure-defaults` (CC-BY-SA-4.0) nao sao
  redistribuidos: o `.exemplo` traz so as 3 familias proprias.

[0.1.0]: https://github.com/oliveirarenanfelipe/nao-depende-de-lembrar/releases/tag/v0.1.0
