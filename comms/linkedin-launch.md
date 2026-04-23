# LinkedIn launch post — claude-atlas

**Quando postar:** quarta ou quinta, 9h-10h BR
**Imagens anexadas:**
1. Screenshot do terminal `claude-atlas check --top 5`
2. Screenshot do HTML report (aba Issues)

**Formatação no LinkedIn:** LinkedIn não renderiza markdown. Cole o texto como está (a partir de "Abri meu..." até a última hashtag). Quebras de linha são preservadas. Emojis funcionam.

---

Abri meu ~/.claude/ ontem e descobri que tenho 72 artefatos de Claude Code.

47 agents. 7 comandos. 18 arquivos CLAUDE.md espalhados por vários projetos.

Não tinha ideia de que havia acumulado esse volume.

O que começou como "deixa eu adicionar só mais um agent pra esse caso" virou uma bagunça silenciosa: dois agents de refactoring com 4 gatilhos em comum (refactor-scout vs refactorer, quase idênticos), dois agents de testing disputando a mesma ativação (api-tester vs performance-benchmarker), e 9 arquivos CLAUDE.md órfãos — a maioria de repos do meu próprio monorepo que deveriam estar se conversando via workspace, mas não estão.

Construí uma ferramenta pra mapear isso: claude-atlas.

Ela escaneia ~/.claude/ + seus repos e detecta:
↳ Duplicatas exatas (mesmo conteúdo, nomes diferentes)
↳ Near-duplicates semânticos via similaridade de Jaccard
↳ Colisões de gatilhos (2+ agents brigando pela mesma ativação)
↳ Overrides (projeto sombreando configuração global sem você perceber)
↳ Órfãos (CLAUDE.md de repos abandonados ou desconectados)

Dois modos:

- claude-atlas check no terminal — output estilo lint, roda em 1 segundo, útil pra pre-commit hook ou alias semanal
- claude-atlas scan gera um HTML interativo com grafo, painel de triagem por severidade, e lista de artefatos isolados

A surpresa ao rodar não foi encontrar caos. Foi descobrir o tamanho que minha setup tinha ficado sem eu perceber. E ver, preto no branco, que existe trabalho de consolidação a fazer — algo que só apareceu porque a ferramenta me mostrou os órfãos agrupados.

MIT license. 100% offline (zero telemetria). Docs em EN + PT-BR.

🔗 https://github.com/grippado/claude-atlas

Se você usa Claude Code há mais de 1 mês, roda aí e me conta nos comentários:
↳ Quantos artefatos apareceram?
↳ Teve alguma surpresa?
↳ Algum agent que você esqueceu que existia?

---

Construído em sessões de pair programming com Claude.ai. Foi um experimento pessoal de ver o quanto dá pra construir com cadência rápida e revisão crítica contínua — saiu do zero a 4 releases em uma semana, com 31 testes passando e roadmap público.

Se interessa esse tipo de workflow (dev assistido por IA mas com disciplina de engenharia), comenta aí que escrevo um post meta sobre o processo.

#claudecode #anthropic #devtools #opensource #python

---

## Engajamento pós-publicação (crítico)

Primeiros 30-60 minutos depois de publicar, o algoritmo do LinkedIn decide se amplifica ou mata o post baseado em engajamento inicial. Então:

- **Responde TODOS os comentários rapidamente.** Mesmo que seja só "valeu [nome]!". Algoritmo prioriza posts com conversação ativa.
- **Se alguém comenta com número** ("rodei e encontrei 45 issues"), responde com pergunta aberta ("qual te surpreendeu mais?"). Isso gera thread.
- **Não compartilha sozinho ainda** — deixa a reação orgânica acontecer.

Depois de 1-2h com boa tração (>15 reações):
- Compartilha em grupos relevantes (Brasil Dev, GoBR, comunidade Claude)
- Manda pra 2-3 amigos devs pedindo feedback explícito
