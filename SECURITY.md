# Segurança e privacidade

Este documento diz o que estas peças fazem com o seu disco e com os seus
dados. Ele existe porque elas leem arquivos fora da própria pasta, e quem
instala um portão no próprio fluxo de trabalho merece saber o que ele alcança.

---

## O que cada peça toca

| peça | lê | escreve | sai da máquina |
|---|---|---|---|
| `o_basico.py` | todos os projetos sob a raiz configurada | nada | não |
| `inventario.py` | as peças declaradas no `mapa.json` | nada | não |
| `ligar_ci.py` | arquivos de teste do projeto alvo | um workflow, só com `--escrever` | não |
| `consertar.py` | o projeto alvo | `projeto.yml`, `.gitleaks.toml`, `.gitignore` no *working tree* | não |
| `vitrine.py` | o resultado das medidas | uma página HTML | não |
| `medir_privacidade.py` | o arquivo que você mandar | nada | não |
| `destilar.py` | as peças da máquina | a pasta `publicado/` | não |
| `regua_de_trava.py` | o `projeto.yml` do alvo | nada | não |
| `portas/*.py` | o comando que o agente vai executar | um log ao lado da peça | não |

Nenhuma peça faz requisição de rede. Não há telemetria, não há coleta, não há
chamada para servidor nenhum. Se você cortar a internet, tudo continua
funcionando igual.

---

## O que nunca sai daqui

As peças rodam inteiramente na sua máquina. O que elas escrevem fica no seu
disco, e o que elas leem não vai a lugar nenhum.

Três arquivos de dado ficam fora do repositório de propósito, e o `.gitignore`
os barra:

- `maquina/privacidade.json`, os nomes que você não quer publicar
- `maquina/mapa.json`, onde as suas peças moram
- `portas/casa.json`, onde os seus projetos moram e o seu usuário de disco

Cada um tem um `.exemplo` versionado, com valores fictícios. O `.gitignore` foi
provado, não prometido: com os três arquivos reais no disco, um `git add -A`
não pega nenhum.

Se você acrescentar um arquivo de dado próprio, acrescente-o ao `.gitignore` no
mesmo commit.

---

## O `consertar.py` escreve em projetos que não são dele

Esta é a coisa mais invasiva aqui, e é deliberada: a peça existe para consertar
vários projetos de uma vez. Duas garantias:

1. Sem `--aplicar`, ela não escreve nada. O padrão é diagnosticar.
2. Ela nunca faz `git commit` nem `git push`. Escreve no *working tree* e
   mostra o que escreveu. Publicar é decisão de quem é dono do repositório.

Nenhuma peça deste repositório executa `git commit` ou `git push`.

---

## As portas executam antes de você

Uma porta é um hook `PreToolUse`: o agente a executa antes de rodar um comando
ou gravar um arquivo, e ela pode negar.

Ela recebe, pela entrada padrão, o comando ou o conteúdo que o agente ia
executar. Esse texto é lido, testado contra padrões, e descartado.

Quando nega, ela grava uma linha no log de auditoria (`gates.log`, ao lado da
peça): data, tipo, e o motivo recortado em 150 caracteres.

A válvula é explícita: um comando com `# GATE-OK: <motivo>` passa. Isso é
intencional, porque portão sem porta de saída ensina a contornar por fora.

⚠️ O log pode conter o começo do motivo da recusa, que às vezes inclui parte do
comando. Se você trabalha com comandos que carregam segredo, olhe o `gates.log`
antes de compartilhar a pasta.

### Duas recusas que valem ser ditas aqui

**`git --no-verify` é negado**, e junto com ele as formas curtas `git commit -n`
e `-an`, que fazem exatamente a mesma coisa e são mais fáceis de digitar. Um
detector que só procura `--no-verify` dá a sensação de cobertura e deixa a
porta aberta do lado que ninguém lê.

Pular o hook de commit é pular a verificação, e a verificação é o que mede o
que vai subir. Não conserta a falha que ela apontou: apaga o aviso e deixa a
falha subir junto.

**Editar uma configuração de linter que já existe é negado.** `ruff.toml`,
`.eslintrc`, `.prettierrc`, `biome.json`, `.flake8` e os outros da mesma
família. Conserte o código, não afrouxe a regra — desligar a regra faz o aviso
sumir e a falha ficar, e ela deixa de valer para o projeto inteiro dali em
diante, sem ninguém ter decidido isso.

Criar uma configuração nova continua liberado. O que se barra é mexer na que já
está valendo. As duas recusas cedem na segunda tentativa, com o motivo no
registro.

---

## Os padrões de terceiro, e a licença deles

O `seeds_inseguros.json.exemplo` traz três famílias de padrões escritas aqui.
As outras seis que a casa de origem usa vêm do projeto
[`trailofbits/insecure-defaults`](https://github.com/trailofbits/insecure-defaults),
sob CC-BY-SA-4.0, uma licença copyleft incompatível com o MIT deste
repositório. Elas não estão aqui.

Se quiser as seis, pegue na fonte e respeite a licença dela. Com apenas as
três o detector é mais fraco, e o arquivo diz isso na cara em vez de parecer
completo.

---

## Reportar uma vulnerabilidade

Abra uma
[issue](https://github.com/oliveirarenanfelipe/nao-depende-de-lembrar/issues).

Este é um projeto de uma pessoa só, sem SLA. Se o problema for sério e você
preferir não abrir em público, diga isso na issue sem o detalhe, e combinamos
outro canal.

---

## O que este projeto não garante

Dito na cara, porque promessa vaga é pior que ausência de promessa:

- as portas não são sandbox. Elas barram padrões conhecidos, e quem escreve o
  padrão sou eu. Um comando destrutivo que ninguém previu passa;
- o `medir_privacidade` acha o que está no seu catálogo. O que não estiver lá,
  ele não vê;
- nada aqui substitui revisão humana antes de publicar.
