# Decisões metodológicas e técnicas

Registro no estilo ADR (*Architecture Decision Record*). Cada decisão tem identificador estável;
decisões não são apagadas — quando mudam, recebem status **Substituída** e apontam para a nova.

Status: **Adotada** · **Pendente** (aguarda verificação) · **Substituída**.

---

## D-001 — Dados brutos imutáveis e camadas separadas
**Status:** Adotada (Fase 1)
**Contexto:** o projeto original separava camada bruta e processada.
**Decisão:** `data/raw/` contém o `.dbc` oficial e sua conversão direta, nunca alterados após
gravados; transformações geram novos arquivos em `data/processed/`.
**Motivo:** permite refazer qualquer etapa e auditar cada transformação a partir da origem.

## D-002 — Dados fora do Git
**Status:** Adotada (Fase 1)
**Decisão:** nada em `data/` é versionado, exceto `.gitkeep`, `README.md` e um manifesto
(`MANIFEST.json`, Fase 2) com URL, data de download e SHA-256. O `.gitignore` usa lista de
permissão e há testes (`tests/test_repository_hygiene.py`) que verificam o comportamento real do Git.
**Motivo:** dados públicos são reobtidos da fonte oficial; o manifesto garante que saberemos se o
arquivo baixado mudou.

## D-003 — Indicadores históricos são referências de reconciliação
**Status:** Adotada (Fase 1)
**Decisão:** os valores recuperados ficam em `config/params.yaml` (`historical_reference`), cada um
com status (`recorded`, `needs_verification`, `criterion_unknown`). Resultados reproduzidos são
comparados a eles, **nunca ajustados** para coincidir. Divergências são documentadas em
[`reconciliacao.md`](reconciliacao.md).

## D-004 — Nenhum registro é excluído
**Status:** Adotada (Fase 1)
**Decisão:** AIHs com número repetido são investigadas e marcadas (colunas derivadas), não
removidas. Filtros de análise são explícitos e documentados por indicador.

## D-005 — Competência ≠ datas de ocorrência
**Status:** Adotada (Fase 1)
**Decisão:** `ANO_CMPT`/`MES_CMPT` (competência), `DT_INTER` (internação) e `DT_SAIDA` (saída) são
tratados como dimensões distintas. Todo indicador declara qual delas usa.

## D-006 — Valores monetários exatos
**Status:** Adotada (Fase 1)
**Decisão:** valores de referência são armazenados como texto e lidos como `decimal.Decimal`
(`hospital_analytics.config.to_money`, que rejeita `float`). Comparações de somas monetárias são
exatas ao centavo.
**Motivo:** `float` não representa centavos exatamente; somas de 73 mil valores podem divergir.

## D-007 — Ambiente: Python 3.13, uv e lockfile
**Status:** Adotada (Fase 1)
**Decisão:** Python 3.13 (`.python-version`), dependências declaradas no `pyproject.toml` com
versões mínimas e fixadas exatamente no `uv.lock`. Instalação com `uv sync --locked`.
**Evidência:** `pyreaddbc 2.0.4` possui binário compilado para CPython 3.13 e foi testada em
ambiente descartável antes da adoção.
**Observação:** versões resolvidas incluem pandas 3.1 e DuckDB 2.0, provavelmente mais novas que as
do projeto original (não registradas). Mudanças de comportamento do pandas 3 (tipo `string` padrão,
*copy-on-write*) são uma possível fonte de divergência e serão consideradas na reconciliação.

## D-008 — Leitura do `.dbc`: pyreaddbc + dbfread
**Status:** Adotada (Fase 1) — validação final na Fase 2
**Decisão:** `pyreaddbc.dbc2dbf` descompacta `.dbc` → `.dbf`; `dbfread` lê o `.dbf`. Encoding e
tipos serão definidos na Fase 2 com base no arquivo real.
**Licença:** `pyreaddbc` é AGPL-3.0. Uso como dependência para análise é compatível; a escolha
da licença deste projeto deve considerar isso (pendente).

## D-009 — Lógica em `src/`, notebook para apresentação
**Status:** Adotada (Fase 1)
**Decisão:** funções do pipeline ficam no pacote `hospital_analytics` (layout `src/`) e são
testadas; o notebook importa e apresenta resultados.
**Motivo:** código em notebook é difícil de testar e de revisar em diffs.

## D-010 — Autoria dos commits
**Status:** Adotada (Fase 1)
**Decisão:** `user.name`/`user.email` configurados **apenas neste repositório** (`git config` local),
com endereço noreply do GitHub, sem expor e-mail pessoal no histórico público.

---

## Decisões pendentes

| ID | Tema | Depende de |
|---|---|---|
| P-001 | Interpretação de `IDENT`, `COD_IDADE`, `DIAS_PERM`, `MORTE`, `CAR_INT` | Documentação oficial (início da Fase 3) |
| P-002 | Campo de permanência usado nos indicadores | P-001 + testes na Fase 4 |
| P-003 | Conversão de idade (`COD_IDADE`) | P-001 + testes na Fase 4 |
| P-004 | Critério de concentração de gastos (top 10%) | Fase 4 |
| P-005 | Campo de classificação clínico/cirúrgico | Fase 4 |
| P-006 | Papel de cada arquivo Parquet (`raw` / `processed` / `_tratado`) | Fase 2–3 |
| P-007 | Licença do projeto | Antes da Fase 6 |
