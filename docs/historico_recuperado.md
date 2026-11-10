# Histórico recuperado

Este documento registra **o que foi recuperado** do projeto original, perdido junto com o
computador em que estava. A fonte são conversas anteriores com o ChatGPT. **Nenhum código-fonte
original foi recuperado**: todo o código deste repositório é uma reconstrução e não deve ser
apresentado como cópia dos scripts originais.

Legenda: ✅ informação histórica registrada · ❓ hipótese ou critério a verificar.

## 1. Fonte de dados

| Item | Valor | |
|---|---|---|
| Sistema | SIH/SUS (DATASUS) | ✅ |
| UF / competência | RJ / janeiro de 2024 | ✅ |
| Arquivo original | `RDRJ2401.dbc` | ✅ |
| Registros | 73.046 | ✅ |
| Colunas | 113 | ✅ |
| Soma de `VAL_TOT` | R$ 125.440.636,13 | ✅ |
| Saídas (`DT_SAIDA`) em 2023 | 29.279 | ✅ |
| Saídas (`DT_SAIDA`) em 2024 | 43.767 | ✅ |

Os campos `ANO_CMPT`, `MES_CMPT`, `DT_INTER` e `DT_SAIDA` eram tratados separadamente. ✅

## 2. Estrutura anterior (mínima conhecida)

```text
Projects/
├── data/
│   ├── raw/RDRJ2401.parquet
│   └── processed/
│       ├── sih_rj_2024_01.parquet
│       └── sih_rj_2024_01_tratado.parquet
└── Hospital Analytics RJ.ipynb
```

O papel exato de cada arquivo Parquet não foi registrado. ❓

Seções do notebook original: (1) coleta e tratamento; (2) validação e qualidade; (3) consultas
SQL com DuckDB; (4) perfil demográfico; (5) diagnósticos e mortalidade; (6) procedimentos
hospitalares; (7) análise financeira; (8) conclusões. ✅

Tecnologias: Python, Pandas, Jupyter, Parquet, SQL, DuckDB. ✅ Versões não registradas. ❓

## 3. Pipeline e auditoria (registrado)

- Conversão de `.dbc` para formato utilizável e armazenamento em Parquet (camadas bruta e
  processada). ✅ Ferramenta de conversão não registrada. ❓
- Auditoria: tipos, valores ausentes, colunas totalmente vazias (ex.: `DIAGSEC9`, `INFEHOSP`),
  duplicidades, datas, valores financeiros, codificações (ex.: `COD_IDADE`). ✅
- AIHs repetidas **não** eram excluídas automaticamente (possíveis registros válidos). ✅
- "56 ocorrências de repetição envolvendo 50 números distintos de AIH". ✅ Critério de contagem
  não registrado. ❓
- Preservação validada: 73.046 registros e `VAL_TOT` mantidos; `grupos_com_diferencas = 0`. ✅
  Grupos comparados não registrados. ❓

## 4. Indicadores registrados

### Base completa

| Indicador | Valor | Critério |
|---|---:|---|
| Registros | 73.046 | ✅ |
| Valor total | R$ 125.440.636,13 | ✅ |
| Permanência média | 6,12 dias | ❓ campo não registrado |
| Idade média | 43,96 anos | ❓ tratamento de `COD_IDADE` não registrado |
| Valor médio por registro | R$ 1.717,28 | ✅ |
| Óbitos | 4.664 | ❓ campo não registrado |
| Mortalidade bruta | 6,38% | ❓ ver inconsistência I-1 |

### Por tipo de AIH (`IDENT`)

| Indicador | Tipo 1 ("normal") | Tipo 5 ("continuidade") |
|---|---:|---:|
| Registros | 72.383 | 663 |
| Valor total | R$ 123.858.470,15 | R$ 1.582.165,98 |
| Valor médio | R$ 1.711,15 | R$ 2.386,37 |
| Permanência média | 5,93 dias | 27,90 dias |
| Óbitos | 4.656 | 8 |

Os rótulos "normal" e "continuidade" são os do histórico; a nomenclatura oficial será
confirmada na documentação do DATASUS. ❓

### Outras análises (critério desconhecido ❓)

- Concentração: 10% dos registros de maior gasto ≈ 58,20% do gasto.
- Classificação das internações: cirúrgicos 51,57%, clínicos 44,38% (soma 95,95%).

## 5. Verificação de consistência interna (feita na reconstrução)

Automatizada em [`tests/test_historical_reference.py`](../tests/test_historical_reference.py).

| Verificação | Resultado |
|---|---|
| 29.279 + 43.767 = 73.046 | ✅ consistente |
| 72.383 + 663 = 73.046 | ✅ consistente |
| R$ 123.858.470,15 + R$ 1.582.165,98 = R$ 125.440.636,13 | ✅ consistente (exato) |
| 4.656 + 8 = 4.664 | ✅ consistente |
| Valores médios = soma ÷ registros (geral, tipo 1, tipo 5) | ✅ consistentes |
| Permanência geral × média ponderada dos tipos (≈ 6,124–6,134) | ✅ compatível com 6,12 (no limite) |
| **I-1.** Mortalidade: 4.664 ÷ 73.046 = 6,3850% → arredonda para **6,39%** | ⚠️ registrado 6,38% |
| **I-2.** 56 "ocorrências" em 50 números: só é coerente como linhas excedentes | ⚠️ hipótese |
