# Reconciliação dos indicadores

Comparação entre os valores históricos (`config/params.yaml` → `historical_reference`) e os
valores reproduzidos. Preenchida a partir da Fase 2.

Status: ⏳ pendente · ✅ reproduzido · 🟡 reproduzido com critério identificado ·
🟠 divergente com explicação · 🔴 divergente sem explicação.

Critérios de aceite: contagens e somas monetárias **exatas** (ao centavo); médias e percentuais
iguais com **2 casas decimais**.

| # | Indicador | Base | Histórico | Reproduzido | Critério usado | Status |
|---|---|---|---:|---:|---|---|
| 1 | Registros | completa | 73.046 | 73.046 | Linhas do Parquet bruto = registros do cabeçalho DBF | ✅ |
| 2 | Colunas | completa | 113 | 113 | Campos do DBF | ✅ |
| 3 | Soma `VAL_TOT` | completa | R$ 125.440.636,13 | R$ 125.440.636,13 | Soma exata em `Decimal` do texto original; 0 vazios, 0 malformados; confirmada também no DuckDB (`DECIMAL(18,2)`) | ✅ |
| 4 | Saídas em 2023 | completa | 29.279 | | | ⏳ |
| 5 | Saídas em 2024 | completa | 43.767 | | | ⏳ |
| 6 | Permanência média | completa | 6,12 | | | ⏳ |
| 7 | Idade média | completa | 43,96 | | | ⏳ |
| 8 | Valor médio | completa | R$ 1.717,28 | | | ⏳ |
| 9 | Óbitos | completa | 4.664 | | | ⏳ |
| 10 | Mortalidade bruta | completa | 6,38% | | | ⏳ |
| 11 | Registros | `IDENT` 1 | 72.383 | | | ⏳ |
| 12 | Soma `VAL_TOT` | `IDENT` 1 | R$ 123.858.470,15 | | | ⏳ |
| 13 | Valor médio | `IDENT` 1 | R$ 1.711,15 | | | ⏳ |
| 14 | Permanência média | `IDENT` 1 | 5,93 | | | ⏳ |
| 15 | Óbitos | `IDENT` 1 | 4.656 | | | ⏳ |
| 16 | Registros | `IDENT` 5 | 663 | | | ⏳ |
| 17 | Soma `VAL_TOT` | `IDENT` 5 | R$ 1.582.165,98 | | | ⏳ |
| 18 | Valor médio | `IDENT` 5 | R$ 2.386,37 | | | ⏳ |
| 19 | Permanência média | `IDENT` 5 | 27,90 | | | ⏳ |
| 20 | Óbitos | `IDENT` 5 | 8 | | | ⏳ |
| 21 | AIHs repetidas (ocorrências) | completa | 56 | | | ⏳ |
| 22 | AIHs repetidas (números distintos) | completa | 50 | | | ⏳ |
| 23 | Concentração top 10% | ? | 58,20% | | | ⏳ |
| 24 | Cirúrgicos | ? | 51,57% | | | ⏳ |
| 25 | Clínicos | ? | 44,38% | | | ⏳ |
| 26 | Grupos com diferenças (preservação) | — | 0 | | | ⏳ |

## Observações da Fase 2

- Base reproduzida a partir do `.dbc` com SHA-256 `a3f0ea9a…0d7dfc9c` e data de atualização do
  cabeçalho DBF **2025-02-08** (ver `data/MANIFEST.json`). Não há registro de qual versão do arquivo
  foi usada no projeto original; a coincidência exata das três referências indica que o conteúdo
  é o mesmo nesses aspectos.
- Encoding corrigido para CP850 (D-019): somente o texto de 23 valores de `AUD_JUST` mudou;
  registros, colunas e `VAL_TOT` foram revalidados (Pandas e DuckDB concordam).
- `DIAGSEC9` e `INFEHOSP`, citadas no histórico como sem preenchimento, estão 100% vazias na base
  recuperada, o que é consistente com o histórico. Também estão 100% vazias: `NUM_PROC`,
  `CPF_AUT`, `GESTOR_DT` e `DIAGSEC8` (a auditar na Fase 3).
