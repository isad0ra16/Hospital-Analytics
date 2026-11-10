# Indicadores (Fase 4)

Tabela completa, gerada e reproduzível: [`reports/indicators/reconciliation.md`](../reports/indicators/reconciliation.md)
(`make indicators`). Código: `indicators.py` · SQL: `sql/indicators/`.

## Método

1. **Duas implementações independentes:** Pandas e DuckDB (SQL versionado) calculam os mesmos
   agregados exatos (somas inteiras em centavos/dias, contagens). Resultado: **concordam em todos
   os agregados** (a soma fracionária de `age_years` é comparada com tolerância relativa 10⁻¹²).
2. **Médias e percentuais em `Decimal`** a partir desses agregados; arredondamento *half-up* na
   precisão do valor histórico; o valor exato também é publicado.
3. **Valores históricos lidos de `config/params.yaml`** (fonte única).
4. **Status por regra fixa:** ✅ igual, critério documentado · 🟡 igual, critério identificado nesta
   reconstrução · 🟠 diferente, com explicação · 🔴 diferente, sem explicação · 🆕 novo.
5. **Denominadores explícitos:** indicadores da base completa e por tipo de AIH não se misturam.

## Resultado

| Situação | Indicadores |
|---|---|
| ✅ reproduzidos (critério documentado) | registros, valor total e valor médio (base completa, tipo 1, tipo 5); saídas 2023/2024; números de AIH repetidos |
| 🟡 reproduzidos com critério identificado | permanência (3), óbitos (3), idade média histórica, AIHs repetidas (excedentes), cirúrgicos/clínicos |
| 🟠 divergente com explicação | mortalidade bruta (6,38% × 6,39%) |
| 🔴 divergente sem explicação | concentração top 10% (58,20%) |
| 🆕 novo | idade média em anos (corrigida) |

**22 das 24 referências históricas comparadas foram reproduzidas exatamente** (12 ✅ e 10 🟡, na precisão
registrada); as 2 restantes são a mortalidade (🟠) e a concentração top 10% (🔴, testada em duas
variantes de base).

## Achados metodológicos

### 1. Idade média: o critério histórico está incorreto
O valor histórico **43,96** só é reproduzido pela média de `IDADE` **sem** considerar `COD_IDADE`,
somando dias, meses e anos como se fossem anos (ex.: um recém-nascido de 15 dias conta como 15).
A média convertida para anos é **43,85**. Ambos são publicados; **use o corrigido** em conclusões.

### 2. "Cirúrgicos 51,57% / clínicos 44,38%" mede valor, não internações
Reproduzido exatamente como a **participação no `VAL_TOT`** dos grupos SIGTAP 04 (cirúrgicos) e 03
(clínicos) do procedimento realizado, **apenas AIHs tipo 1**. Por contagem de registros, as
proporções se invertem: 44,97% cirúrgicos e 54,25% clínicos. A frase "51,57% das internações foram
cirúrgicas" seria **incorreta**.

### 3. Mortalidade: 6,38% × 6,39%
4.664 / 73.046 = 6,38501…%. Arredondamento (half-up ou bancário) → 6,39%; somente truncamento → 6,38%.
Nenhum numerador/denominador alternativo testado (tipo 1, números de AIH únicos) produz 6,38%.
Explicação provável: truncamento na formatação original — **não confirmável** sem o código perdido.
O valor correto, arredondado, é **6,39%**. Unidade: óbitos por 100 registros de AIH (não por paciente).

### 4. Concentração de gastos: não reproduzida
Definição adotada: participação no `VAL_TOT` dos k = ⌊0,1·n⌋ registros de maior valor (empates no
corte não alteram a soma). Base completa: **57,74%**. Variantes testadas (limitadas, para não
procurar um número): ⌈⌉ 57,75; AIH tipo 1 58,27; `VAL_SH` 58,96; `VAL_SH+VAL_SP` 57,81; sem zeros
57,67; por número de AIH 57,74; por hospital 50,32. Nenhuma dá 58,20%. O histórico dizia
"aproximadamente"; o critério exato não foi recuperado. **Não usar 58,20%.**

### 5. "Tipo 5" é longa permanência
Segundo a fonte secundária, `IDENT` 5 = **longa permanência** (3 = continuação, ausente neste
arquivo). O rótulo histórico "continuidade" é mantido apenas como referência histórica.

### 6. Permanência usa `DIAS_PERM`
`DIAS_PERM` reproduz 6,12 / 5,93 / 27,90; `QT_DIARIAS` (5,44) e diferença de datas (14,65) não.
