## O que muda

<!-- Uma frase. O que este PR faz que nao era feito antes. -->

## O numero

<!-- OBRIGATORIO. O que estava errado, quantas vezes, e o que mudou depois.
     "melhora a performance" nao passa. "544 s para 39 s, medido com o
     worktree fora" passa. -->

## O rito

Peca nova nasce com as quatro coisas no MESMO commit:

- [ ] a peca
- [ ] o teste dela, com pelo menos uma mutacao executavel
- [ ] a linha no `mapa.json` (peca fora do mapa nao e medida)
- [ ] quem a chama (peca que ninguem invoca e defeito, nao pendencia)

## A prova

- [ ] as suites passam na minha maquina
- [ ] as suites passam com `HOME` numa pasta VAZIA (o cenario de quem baixou)
- [ ] `ruff check --config ruff.toml .` sem erro
- [ ] a mutacao ACUSA: quebrei o alvo de proposito e o teste reprovou

<!-- O ultimo item e o que importa. Teste verde nao responde "ele exercitou o
     caminho?"; a mutacao responde. -->
