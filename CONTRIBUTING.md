# Convenções do projeto

Este é um projeto pessoal de portfólio. As convenções abaixo garantem histórico limpo,
autoria verdadeira e resultados reproduzíveis.

## Antes de cada commit

```bash
make check        # lint (ruff) + testes (pytest)
```

Dados nunca são versionados (`data/` é ignorado, exceto `README.md` e `MANIFEST.json`); o teste
`tests/test_repository_hygiene.py` verifica isso.

## Mensagens de commit

- Formato [Conventional Commits](https://www.conventionalcommits.org/): `tipo: resumo` — tipos usados:
  `feat`, `fix`, `docs`, `data` (manifesto e relatórios gerados), `build`, `test`, `refactor`.
- Resumo em inglês, no imperativo, até ~72 caracteres; o corpo explica **por que** a mudança foi feita.
- Um commit = uma mudança coerente (código e testes juntos; dados/relatórios gerados em commit próprio).

## Autoria

- Os commits usam a identidade Git configurada **neste repositório** (`git config user.name` /
  `user.email`, com o endereço *noreply* do GitHub da autora). Não alterar autoria de commits.
- Mensagens **não** devem conter linhas automáticas de coautoria (`Co-Authored-By:`), referências de
  sessão (`<Algo>-Session:`) nem avisos de geração automática (`Generated with …`).
- Coautoria **legítima** (uma pessoa que de fato contribuiu) é permitida de forma explícita, no próprio
  commit: `ALLOW_CO_AUTHOR=1 git commit …`.

## Hook de verificação (instalação explícita)

O hook `scripts/git-hooks/commit-msg` aplica as regras de autoria acima. Ele **não** é ativado
automaticamente; cada clone escolhe ativá-lo:

```bash
make hooks            # git config core.hooksPath scripts/git-hooks
```
```bash
make hooks-uninstall  # desativa
```

O comportamento do hook é coberto por `tests/test_commit_msg_hook.py`.

## Branches

Desenvolvimento em branches `work/…`; o `main` só recebe merge após revisão. Sem *force push* e sem
reescrita de histórico publicado sem decisão explícita.
