# Reconciliação dos indicadores — sih_rj_2024_01_tratado.parquet

> Gerado por `hospital-analytics indicators`. Não editar manualmente.

Pandas × DuckDB: **concordam em todos os agregados**.

| Indicador | Histórico | Reproduzido (arredondado) | Valor exato | Diferença | Status |
|---|---:|---:|---:|---:|---|
| Registros (base completa) | 73.046 | 73.046 | 73046.000000 | 0 | ✅ reproduzido |
| Valor total (base completa) | R$ 125.440.636,13 | R$ 125.440.636,13 | 125440636.130000 | 0.00 | ✅ reproduzido |
| Valor médio por registro (base completa) | R$ 1.717,28 | R$ 1.717,28 | 1717.282755 | 0.00 | ✅ reproduzido |
| Permanência média (base completa) | 6,12 | 6,12 | 6.124921 | 0.00 | 🟡 critério identificado |
| Óbitos (base completa) | 4.664 | 4.664 | 4664.000000 | 0 | 🟡 critério identificado |
| Registros (AIH tipo 1) | 72.383 | 72.383 | 72383.000000 | 0 | ✅ reproduzido |
| Valor total (AIH tipo 1) | R$ 123.858.470,15 | R$ 123.858.470,15 | 123858470.150000 | 0.00 | ✅ reproduzido |
| Valor médio por registro (AIH tipo 1) | R$ 1.711,15 | R$ 1.711,15 | 1711.154140 | 0.00 | ✅ reproduzido |
| Permanência média (AIH tipo 1) | 5,93 | 5,93 | 5.925480 | 0.00 | 🟡 critério identificado |
| Óbitos (AIH tipo 1) | 4.656 | 4.656 | 4656.000000 | 0 | 🟡 critério identificado |
| Registros (AIH tipo 5) | 663 | 663 | 663.000000 | 0 | ✅ reproduzido |
| Valor total (AIH tipo 5) | R$ 1.582.165,98 | R$ 1.582.165,98 | 1582165.980000 | 0.00 | ✅ reproduzido |
| Valor médio por registro (AIH tipo 5) | R$ 2.386,37 | R$ 2.386,37 | 2386.374027 | 0.00 | ✅ reproduzido |
| Permanência média (AIH tipo 5) | 27,90 | 27,90 | 27.898944 | 0.00 | 🟡 critério identificado |
| Óbitos (AIH tipo 5) | 8 | 8 | 8.000000 | 0 | 🟡 critério identificado |
| Idade média — critério histórico (base completa) | 43,96 | 43,96 | 43.961285 | 0.00 | 🟡 critério identificado |
| Idade média em anos — corrigida (base completa) | — | — | 43.853393 | — | 🆕 novo |
| Mortalidade bruta (base completa) | 6,38% | 6,39% | 6.385018 | 0.01 | 🟠 divergente (explicado) |
| Saídas em 2023 | 29.279 | 29.279 | 29279.000000 | 0 | ✅ reproduzido |
| Saídas em 2024 | 43.767 | 43.767 | 43767.000000 | 0 | ✅ reproduzido |
| AIHs repetidas — registros excedentes | 56 | 56 | 56.000000 | 0 | 🟡 critério identificado |
| AIHs repetidas — números distintos | 50 | 50 | 50.000000 | 0 | ✅ reproduzido |
| Concentração: 10% dos registros de maior VAL_TOT (base completa) | 58,20% | 57,74% | 57.742678 | -0.46 | 🔴 divergente |
| Concentração: 10% de maior VAL_TOT (AIH tipo 1) | 58,20% | 58,27% | 58.268221 | 0.07 | 🔴 divergente |
| Cirúrgicos — participação no valor (AIH tipo 1) | 51,57% | 51,57% | 51.566139 | 0.00 | 🟡 critério identificado |
| Clínicos — participação no valor (AIH tipo 1) | 44,38% | 44,38% | 44.376531 | 0.00 | 🟡 critério identificado |

## Definições

### Registros (base completa)
- **Definição:** Número de registros de AIH
- **Campos:** — · **Fórmula:** `count(*)`
- **Denominador:** — · **Filtros:** nenhum (base completa)

### Valor total (base completa)
- **Definição:** Soma de VAL_TOT
- **Campos:** VAL_TOT · **Fórmula:** `sum(val_tot_cents) / 100`
- **Denominador:** — · **Filtros:** nenhum (base completa)

### Valor médio por registro (base completa)
- **Definição:** Valor total dividido pelo número de registros
- **Campos:** VAL_TOT · **Fórmula:** `sum(val_tot_cents) / count(*) / 100`
- **Denominador:** registros · **Filtros:** nenhum (base completa)

### Permanência média (base completa)
- **Definição:** Média de dias de permanência
- **Campos:** DIAS_PERM · **Fórmula:** `avg(DIAS_PERM)`
- **Denominador:** registros · **Filtros:** nenhum (base completa)
- **Nota:** Campo não registrado no histórico; DIAS_PERM reproduz os três valores. QT_DIARIAS e DT_SAIDA−DT_INTER não reproduzem.

### Óbitos (base completa)
- **Definição:** Registros com óbito
- **Campos:** MORTE · **Fórmula:** `count(*) where MORTE = '1'`
- **Denominador:** — · **Filtros:** nenhum (base completa)
- **Nota:** Campo não registrado no histórico; MORTE = 1 coincide registro a registro com COBRANCA 4x (óbito).

### Registros (AIH tipo 1)
- **Definição:** Número de registros de AIH
- **Campos:** — · **Fórmula:** `count(*)`
- **Denominador:** — · **Filtros:** IDENT = '1'

### Valor total (AIH tipo 1)
- **Definição:** Soma de VAL_TOT
- **Campos:** VAL_TOT · **Fórmula:** `sum(val_tot_cents) / 100`
- **Denominador:** — · **Filtros:** IDENT = '1'

### Valor médio por registro (AIH tipo 1)
- **Definição:** Valor total dividido pelo número de registros
- **Campos:** VAL_TOT · **Fórmula:** `sum(val_tot_cents) / count(*) / 100`
- **Denominador:** registros · **Filtros:** IDENT = '1'

### Permanência média (AIH tipo 1)
- **Definição:** Média de dias de permanência
- **Campos:** DIAS_PERM · **Fórmula:** `avg(DIAS_PERM)`
- **Denominador:** registros · **Filtros:** IDENT = '1'
- **Nota:** Campo não registrado no histórico; DIAS_PERM reproduz os três valores. QT_DIARIAS e DT_SAIDA−DT_INTER não reproduzem.

### Óbitos (AIH tipo 1)
- **Definição:** Registros com óbito
- **Campos:** MORTE · **Fórmula:** `count(*) where MORTE = '1'`
- **Denominador:** — · **Filtros:** IDENT = '1'
- **Nota:** Campo não registrado no histórico; MORTE = 1 coincide registro a registro com COBRANCA 4x (óbito).

### Registros (AIH tipo 5)
- **Definição:** Número de registros de AIH
- **Campos:** — · **Fórmula:** `count(*)`
- **Denominador:** — · **Filtros:** IDENT = '5'

### Valor total (AIH tipo 5)
- **Definição:** Soma de VAL_TOT
- **Campos:** VAL_TOT · **Fórmula:** `sum(val_tot_cents) / 100`
- **Denominador:** — · **Filtros:** IDENT = '5'

### Valor médio por registro (AIH tipo 5)
- **Definição:** Valor total dividido pelo número de registros
- **Campos:** VAL_TOT · **Fórmula:** `sum(val_tot_cents) / count(*) / 100`
- **Denominador:** registros · **Filtros:** IDENT = '5'

### Permanência média (AIH tipo 5)
- **Definição:** Média de dias de permanência
- **Campos:** DIAS_PERM · **Fórmula:** `avg(DIAS_PERM)`
- **Denominador:** registros · **Filtros:** IDENT = '5'
- **Nota:** Campo não registrado no histórico; DIAS_PERM reproduz os três valores. QT_DIARIAS e DT_SAIDA−DT_INTER não reproduzem.

### Óbitos (AIH tipo 5)
- **Definição:** Registros com óbito
- **Campos:** MORTE · **Fórmula:** `count(*) where MORTE = '1'`
- **Denominador:** — · **Filtros:** IDENT = '5'
- **Nota:** Campo não registrado no histórico; MORTE = 1 coincide registro a registro com COBRANCA 4x (óbito).

### Idade média — critério histórico (base completa)
- **Definição:** Média aritmética do campo IDADE, sem considerar a unidade (COD_IDADE)
- **Campos:** IDADE · **Fórmula:** `avg(IDADE)`
- **Denominador:** registros · **Filtros:** nenhum
- **Nota:** ⚠️ Critério metodologicamente incorreto: mistura dias, meses, anos e centenas de anos (COD_IDADE 2/3/4/5). Reproduz o histórico; não usar em conclusões.

### Idade média em anos — corrigida (base completa)
- **Definição:** Média da idade convertida para anos conforme COD_IDADE
- **Campos:** COD_IDADE, IDADE · **Fórmula:** `avg(age_years); 2: IDADE/365,25 · 3: IDADE/12 · 4: IDADE · 5: 100+IDADE`
- **Denominador:** registros com unidade válida · **Filtros:** nenhum
- **Nota:** Interpretação de COD_IDADE por fonte secundária (microdatasus).

### Mortalidade bruta (base completa)
- **Definição:** Óbitos por 100 registros de AIH (não por paciente)
- **Campos:** MORTE · **Fórmula:** `100 × óbitos / registros`
- **Denominador:** registros (inclui AIH tipo 5) · **Filtros:** nenhum
- **Nota:** Unidade de análise: registro de AIH.
- **Divergência:** 4.664 / 73.046 = 6,38501…%: arredondamento (half-up ou bancário) dá 6,39%; apenas truncamento em 2 casas dá 6,38%. Nenhum numerador/denominador alternativo testado dá 6,38%. Explicação provável: truncamento (não confirmável).

### Saídas em 2023
- **Definição:** Registros por ano de DT_SAIDA
- **Campos:** DT_SAIDA · **Fórmula:** `count(*) where year(discharge_date) = 2023`
- **Denominador:** — · **Filtros:** nenhum

### Saídas em 2024
- **Definição:** Registros por ano de DT_SAIDA
- **Campos:** DT_SAIDA · **Fórmula:** `count(*) where year(discharge_date) = 2024`
- **Denominador:** — · **Filtros:** nenhum

### AIHs repetidas — registros excedentes
- **Definição:** Registros além do primeiro para números de AIH que se repetem
- **Campos:** N_AIH · **Fórmula:** `Σ (ocorrências − 1) sobre N_AIH com ocorrências > 1`
- **Denominador:** — · **Filtros:** nenhum
- **Nota:** Hipótese da Fase 1 confirmada: 56 excedentes, 50 números, 106 registros. Nenhum registro é removido.

### AIHs repetidas — números distintos
- **Definição:** Números de AIH com mais de um registro
- **Campos:** N_AIH · **Fórmula:** `count(N_AIH com ocorrências > 1)`
- **Denominador:** — · **Filtros:** nenhum

### Concentração: 10% dos registros de maior VAL_TOT (base completa)
- **Definição:** Participação no VAL_TOT dos k = ⌊0,1·n⌋ registros de maior valor
- **Campos:** VAL_TOT · **Fórmula:** `100 × Σ top-k / Σ total`
- **Denominador:** VAL_TOT total · **Filtros:** nenhum
- **Nota:** Variantes testadas: base completa ⌊⌋/⌈⌉ 57,74/57,75; AIH tipo 1 58,27; VAL_SH 58,96; VAL_SH+VAL_SP 57,81; sem zeros 57,67; por N_AIH 57,74; por hospital 50,32.

### Concentração: 10% de maior VAL_TOT (AIH tipo 1)
- **Definição:** Mesma definição, restrita à AIH tipo 1 (variante mais próxima do histórico)
- **Campos:** VAL_TOT · **Fórmula:** `100 × Σ top-k / Σ total`
- **Denominador:** VAL_TOT total (tipo 1) · **Filtros:** IDENT = '1'
- **Nota:** Variante mais próxima, mas diferente (58,27 ≠ 58,20).

### Cirúrgicos — participação no valor (AIH tipo 1)
- **Definição:** Participação no VAL_TOT dos procedimentos do grupo SIGTAP 04
- **Campos:** PROC_REA, VAL_TOT · **Fórmula:** `100 × Σ VAL_TOT (grupo 04) / Σ VAL_TOT`
- **Denominador:** VAL_TOT total (tipo 1) · **Filtros:** IDENT = '1'
- **Nota:** O histórico mede VALOR, não número de internações (por contagem: 44,97%).

### Clínicos — participação no valor (AIH tipo 1)
- **Definição:** Participação no VAL_TOT dos procedimentos do grupo SIGTAP 03
- **Campos:** PROC_REA, VAL_TOT · **Fórmula:** `100 × Σ VAL_TOT (grupo 03) / Σ VAL_TOT`
- **Denominador:** VAL_TOT total (tipo 1) · **Filtros:** IDENT = '1'
- **Nota:** O histórico mede VALOR, não número de internações (por contagem: 54,25%).
