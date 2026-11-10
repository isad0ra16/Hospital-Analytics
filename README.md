# Hospital Analytics — SIH/SUS RJ (competência 01/2024)

Análise **reproduzível e auditável** das internações hospitalares do SUS no Rio de Janeiro, a partir
dos microdados públicos do **SIH/SUS** (DATASUS), arquivo `RDRJ2401` — 73.046 registros de AIH,
R$ 125.440.636,13.

> **Status:** reconstrução no branch `work/hospital-analytics-reconstruction` (aguardando revisão
> para merge no `main`). Fases 1–2 concluídas; Fases 3–5 implementadas e pendentes de revisão.

## O problema

O projeto original (notebook, scripts e dados tratados) foi perdido com o computador em que estava.
Restaram a documentação e os indicadores calculados. Este repositório **reconstrói o projeto a partir
dessas evidências**: cada resultado é recalculado e **reconciliado** com o valor histórico, sem jamais
ajustar dados para "bater" — divergências são investigadas e documentadas.

## Resultados confirmados

| | Histórico | Reproduzido | |
|---|---:|---:|---|
| Registros · colunas | 73.046 · 113 | 73.046 · 113 | ✅ |
| Valor total (`VAL_TOT`) | R$ 125.440.636,13 | R$ 125.440.636,13 | ✅ exato ao centavo |
| AIH tipo 1 · tipo 5 (registros) | 72.383 · 663 | 72.383 · 663 | ✅ |
| Permanência média (geral · tipo 1 · tipo 5) | 6,12 · 5,93 · 27,90 | idem | 🟡 critério identificado (`DIAS_PERM`) |
| Óbitos | 4.664 | 4.664 | 🟡 (`MORTE`) |
| Saídas em 2023 · 2024 | 29.279 · 43.767 | idem | ✅ |

**22 de 24 referências históricas reproduzidas exatamente**; Pandas e DuckDB concordam em todos os
agregados. Tabela completa: [`reports/indicators/reconciliation.md`](reports/indicators/reconciliation.md).

### Achados da reconstrução

- **Idade média histórica (43,96) usa critério incorreto:** ignora a unidade `COD_IDADE` (dias e meses
  somados como anos). Corrigida: **43,85 anos** — publicada ao lado, sem apagar o histórico.
- **"Cirúrgicos 51,57%" mede valor, não internações:** é a participação no `VAL_TOT` (AIH tipo 1).
  Por número de registros, os cirúrgicos são 44,97%.
- **Mortalidade:** 4.664 / 73.046 = 6,385…% → **6,39%** (o histórico 6,38% só se explica por truncamento).
- **Concentração de gastos (58,20%) não reproduzida:** 57,74% pelo critério documentado; o critério
  original não foi recuperado. *Não use 58,20%.*
- **"Tipo 5" é longa permanência** (não "continuidade"), segundo a fonte secundária e os dados.
- **Encoding:** o DBF declara CP850; a correção alterou só 23 textos e foi **provado** que nenhum byte
  original mudou.

Detalhes: [`docs/indicadores.md`](docs/indicadores.md) · [`docs/qualidade_dados.md`](docs/qualidade_dados.md) ·
[`docs/analises.md`](docs/analises.md).

![Internações por faixa etária e sexo](reports/analysis/figures/age_pyramid.png)

## Arquitetura

```text
DATASUS (FTP) ─┐                    ┌─ make fetch-data: Release do GitHub + verificação SHA-256
               ▼                    ▼
        data/raw/RDRJ2401.dbc  (imutável; data/MANIFEST.json)
               │ make convert   .dbc → .dbf → Arrow → Parquet (sem tratamento, CP850)
        data/raw/RDRJ2401.parquet          ← make validate
               │ make processed  originais intactos + 50 colunas derivadas reversíveis
        data/processed/sih_rj_2024_01_tratado.parquet
               ├─ make audit       → reports/audit/
               ├─ make indicators  → reports/indicators/   (Pandas × DuckDB)
               └─ make analysis    → reports/analysis/     (+ figuras)
```

Módulos e princípios: [`docs/arquitetura.md`](docs/arquitetura.md). Pipeline e camadas:
[`docs/pipeline_dados.md`](docs/pipeline_dados.md).

## Tecnologias

Python 3.13 · pandas · PyArrow/Parquet · DuckDB (SQL versionado em `sql/`) · pyreaddbc + dbfread ·
matplotlib · pytest · ruff · uv (lockfile) · GitHub Releases (arquivamento dos dados brutos).

## Como reproduzir

Pré-requisitos: [uv](https://docs.astral.sh/uv/), `make` e a CLI `gh` (para baixar o arquivo arquivado).

```bash
make install      # ambiente idêntico (uv.lock)
```
```bash
make fetch-data   # RDRJ2401.dbc da Release data-rdrj2401, conferido pelo SHA-256 do manifesto
```
```bash
make pipeline     # convert → validate → processed → audit → indicators → analysis
```
```bash
make check        # lint + 150 testes (somente dados sintéticos)
```

Um clone limpo reproduz **bit a bit** os relatórios versionados (verificado). Estratégia de
recuperação: [`docs/recuperacao_dados.md`](docs/recuperacao_dados.md).

## Metodologia (princípios)

- **Dados brutos imutáveis**; cada derivado registrado no manifesto com SHA-256 e impressão digital.
- **Nenhum registro removido**: AIHs repetidas (56 excedentes em 50 números) são sinalizadas, não excluídas.
- **Competência ≠ data de ocorrência**: 40% das saídas são de 2023 apesar da competência 2024-01.
- **Dinheiro exato** (centavos inteiros, `Decimal`); **duas engines** devem concordar.
- **Interpretação com fonte declarada** e **saídas sem dados identificáveis**.
- Decisões com contexto, alternativas e consequências: [`docs/decisoes_metodologicas.md`](docs/decisoes_metodologicas.md).

## Limitações

- O dicionário de variáveis usa **fonte secundária** (`microdatasus`), corroborada pelos dados; a fonte
  primária do DATASUS não pôde ser consultada do ambiente de execução (pendência P-009).
- Unidade de análise = **registro de AIH**, não paciente; sem ajuste de risco: as taxas são descritivas.
- Uma única competência; não há série temporal.
- O arquivo do DATASUS pode ser republicado; esta análise usa a versão com SHA-256 `a3f0ea9a…0d7dfc9c`
  (cabeçalho atualizado em 2025-02-08).

## Documentação

[Histórico recuperado](docs/historico_recuperado.md) · [Decisões](docs/decisoes_metodologicas.md) ·
[Dicionário](docs/dicionario_variaveis.md) · [Reconciliação](docs/reconciliacao.md) ·
[Indicadores](docs/indicadores.md) · [Qualidade](docs/qualidade_dados.md) · [Análises](docs/analises.md) ·
[Arquitetura](docs/arquitetura.md) · [Pipeline](docs/pipeline_dados.md) ·
[Recuperação](docs/recuperacao_dados.md) · [Diário de execução](docs/diario_execucao.md)

## Roteiro

- [x] Fase 1 — Estrutura, ambiente e documentação base
- [x] Fase 2 — Recuperação dos dados (download oficial, checksum, Parquet, CP850)
- [x] Fase 3 — Auditoria e camada tratada *(revisão pendente)*
- [x] Fase 4 — Reprodução e reconciliação dos indicadores *(revisão pendente)*
- [x] Fase 5 — SQL (DuckDB) e análises exploratórias *(revisão pendente)*
- [ ] Fase 6 — Notebook de apresentação, licença e publicação

## Autoria

Isadora Veiga — projeto de portfólio (Ciência da Computação: engenharia e análise de dados, SQL, saúde).
