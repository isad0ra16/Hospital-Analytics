# Arquitetura

## Visão geral

```text
 DATASUS (FTP oficial)                 GitHub Release data-rdrj2401 (cópia arquivada)
          │  download pela autora (D-011)          │  make fetch-data (API REST + SHA-256)
          ▼                                        ▼
 data/raw/RDRJ2401.dbc ───────── registrado em data/MANIFEST.json (somente leitura)
          │  make convert   (dbc.py → dbf.py → convert.py)
          ▼
 data/raw/RDRJ2401.parquet          CAMADA BRUTA: 113 colunas de texto, sem tratamento
          │  make validate  (validate.py: 73.046 · 113 · R$ 125.440.636,13 · impressões digitais)
          │  make processed (processed.py + dictionary.py)
          ▼
 data/processed/sih_rj_2024_01_tratado.parquet   CAMADA TRATADA: 113 originais + 50 derivadas
          │
          ├── make audit       (audit.py + sql/audit/*.sql)        → reports/audit/
          ├── make indicators  (indicators.py: Pandas × sql/indicators/*.sql) → reports/indicators/
          ├── make analysis    (analysis.py + sql/analysis/*.sql)  → reports/analysis/ (+ figuras)
          └── make powerbi     (powerbi.py + enrichment.py + sql/powerbi/*.sql) → data/powerbi/
                 ▲ referências oficiais verificadas      └── make pbip (pbip.py) → powerbi/*.pbip
```

## Módulos (`src/hospital_analytics/`)

| Módulo | Responsabilidade | Lê | Escreve |
|---|---|---|---|
| `config.py` | parâmetros (`config/params.yaml`), caminhos, dinheiro em `Decimal` | — | — |
| `integrity.py` | SHA-256; impressões digitais de conteúdo (texto e bytes) | arquivos | — |
| `dbc.py` | `.dbc → .dbf` com verificação de tamanho | `.dbc` | `.dbf` temporário |
| `dbf.py` | leitura bruta do DBF; encoding declarado | `.dbf` | — |
| `convert.py` | camada bruta (Arrow, escrita atômica, releitura) | `.dbc` | Parquet bruto |
| `manifest.py` | proveniência; fontes imutáveis; histórico de substituições | manifesto | manifesto |
| `validate.py` | validação da camada bruta | Parquet bruto | — |
| `dictionary.py` | códigos SIH com fonte e status | — | — |
| `processed.py` | camada tratada (derivadas reversíveis / interpretações) | Parquet bruto | Parquet tratado |
| `sql.py` | executor de SQL versionado (views `raw_rd`, `rd`) | Parquets | — |
| `audit.py` | auditoria de qualidade | ambas as camadas | `reports/audit/` |
| `indicators.py` | indicadores, duas engines, reconciliação | camada tratada | `reports/indicators/` |
| `analysis.py` | análises exploratórias descritivas e gráficos (matplotlib) | camada tratada | `reports/analysis/` |
| `reference.py` | leitores das referências oficiais (SIGTAP de largura fixa pelo leiaute do próprio ZIP, IBGE, tabelas TabWin `.cnv`), chaves, cobertura, guarda de enriquecimento | arquivos oficiais | — |
| `reference_diagnose.py` | diagnóstico somente leitura das referências (integridade antes da leitura) | `data/reference/incoming/` | `reports/reference/` |
| `enrichment.py` | carrega as referências verificadas (SHA-256) como tabelas de código únicas; rótulos oficiais dos códigos do RD | `data/reference/incoming/` | — |
| `powerbi.py` | modelo estrela enriquecido: exportação CSV/Parquet, dicionário, Power Query, validação (122 verificações), relatório de enriquecimento | camada tratada + referências + relatórios | `data/powerbi/`, `reports/powerbi/`, `reports/reference/`, `docs/powerbi/` |
| `pbip.py` | projeto Power BI (PBIP): modelo TMDL + relatório PBIR de 6 páginas, gerados do esquema e de `medidas.dax` | esquema + `docs/powerbi/medidas.dax` | `powerbi/`, `docs/powerbi/paginas.md` |
| `cli.py` | comandos `hospital-analytics …` | — | — |

## Princípios de projeto

1. **Camadas imutáveis e regeneráveis.** Nada é sobrescrito; derivados podem ser regenerados e
   comprovados idênticos (impressões digitais no manifesto).
2. **Desconfiar das ferramentas de baixo nível.** Cada passo tem verificação independente (D-014).
3. **Separar formato de interpretação.** Conversões de formato são reversíveis e testadas; a
   interpretação de códigos depende de fonte declarada (D-020, D-021).
4. **Dinheiro exato.** Centavos inteiros e `Decimal`; nunca `float` em comparações monetárias.
5. **Duas engines.** Pandas e DuckDB precisam concordar nos agregados (D-024).
6. **SQL versionado.** Consultas em `sql/` com cabeçalho e parâmetros `$nome` (nunca concatenação).
7. **Saídas determinísticas e sem dados sensíveis** (D-026).
8. **Falhar alto.** Formatos inesperados, encoding contraditório, registros excluídos, colisões de
   nomes e divergência entre engines interrompem a execução com mensagem clara.

## Testes

`tests/` usa **apenas dados sintéticos** (`tests/synthetic_data.py`), gerados em diretórios
temporários, incluindo um compressor PKWare DCL mínimo para exercitar o `dbc2dbf` real e um conjunto
com leiaute SIH que inclui casos difíceis (unidades de idade, AIH repetida tipo 1+5, precisão
reduzida). Valores esperados vêm de um oráculo independente em Python puro. Executar: `make check`.
