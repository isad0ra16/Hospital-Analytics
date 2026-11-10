# Hospital Analytics — SIH/SUS RJ (competência 01/2024)

Análise reproduzível de dados públicos de internações hospitalares do Sistema Único de Saúde
(SUS), a partir do **SIH/SUS — Sistema de Informações Hospitalares**, disponibilizado pelo
DATASUS, para o estado do **Rio de Janeiro**, competência **janeiro de 2024**.

> **Status:** projeto em **reconstrução** — Fase 2 de 6 (dados): base bruta recuperada e validada;
> aguardando revisão.
> O projeto original foi perdido junto com o computador em que estava; esta versão está sendo
> reconstruída a partir da documentação e dos indicadores recuperados, com cada resultado
> reconciliado contra os valores históricos. Ver [`docs/historico_recuperado.md`](docs/historico_recuperado.md).

## Objetivo

1. Reconstruir o pipeline original (coleta → conversão → auditoria → indicadores → SQL → análises).
2. Reproduzir e **reconciliar** os indicadores históricos, documentando critérios e divergências.
3. Só então propor novas análises e melhorias.

## Fonte de dados

| Item | Valor |
|---|---|
| Sistema | SIH/SUS — arquivos RD (AIH Reduzida) |
| Fonte | DATASUS / Ministério da Saúde |
| UF | Rio de Janeiro (RJ) |
| Competência | 2024-01 |
| Arquivo | `RDRJ2401.dbc` |

**Competência ≠ período de ocorrência.** A competência é o mês de processamento da AIH; as datas
de internação (`DT_INTER`) e de saída (`DT_SAIDA`) podem ser anteriores. Os dados **não** são
versionados neste repositório: são baixados da fonte oficial e regenerados pelo pipeline
(ver [`data/README.md`](data/README.md)).

## Estrutura

```text
├── config/params.yaml        # parâmetros da fonte e referências históricas de reconciliação
├── data/                     # dados NÃO versionados; só MANIFEST.json e README
├── scripts/                  # recuperação dos dados (fetch_source.sh)
├── docs/                     # histórico recuperado, decisões, dicionário, reconciliação
├── notebooks/                # apresentação dos resultados (lógica fica em src/)
├── reports/                  # saídas finais
├── sql/                      # consultas DuckDB
├── src/hospital_analytics/   # código do pipeline (Python)
└── tests/                    # testes automatizados
```

## Como reproduzir

Pré-requisitos: [uv](https://docs.astral.sh/uv/) e `make`.

```bash
make install   # cria .venv com as versões exatas do uv.lock
make check     # lint + testes
```

Dados (não versionados; recuperados da Release `data-rdrj2401` e conferidos pelo SHA-256):

```bash
make fetch-data   # baixa o RDRJ2401.dbc original e verifica a integridade
make convert      # converte para Parquet sem tratamento (camada bruta)
make validate     # 73.046 registros · 113 colunas · VAL_TOT R$ 125.440.636,13
```

Detalhes em [`docs/pipeline_dados.md`](docs/pipeline_dados.md) e
[`docs/recuperacao_dados.md`](docs/recuperacao_dados.md).

## Princípios

- **Dados brutos imutáveis** e transformações rastreáveis; nenhum registro é excluído.
- **Indicadores históricos são referências de reconciliação**, nunca metas a forçar.
- **Interpretação de campos baseada na documentação oficial** do DATASUS.
- **Unidade de análise = registro de AIH**, não paciente.

## Roteiro

- [x] Fase 1 — Estrutura, ambiente e documentação base
- [ ] Fase 2 — Recuperação dos dados (download oficial, checksum, Parquet)
- [ ] Fase 3 — Auditoria e tratamento
- [ ] Fase 4 — Reprodução e reconciliação dos indicadores
- [ ] Fase 5 — SQL (DuckDB) e análises
- [ ] Fase 6 — Documentação final e portfólio

## Documentação

- [Histórico recuperado](docs/historico_recuperado.md)
- [Decisões metodológicas](docs/decisoes_metodologicas.md)
- [Dicionário de variáveis](docs/dicionario_variaveis.md)
- [Reconciliação dos indicadores](docs/reconciliacao.md)
- [Pipeline de dados](docs/pipeline_dados.md)
- [Recuperação dos dados](docs/recuperacao_dados.md)

## Autoria

Isadora Veiga — projeto de portfólio (Ciência da Computação: dados, SQL e saúde).
