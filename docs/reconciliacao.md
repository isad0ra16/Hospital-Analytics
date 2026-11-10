# Reconciliação dos indicadores

Comparação entre os valores históricos (`config/params.yaml` → `historical_reference`) e os
valores reproduzidos (Fases 2–4).

Status: ⏳ pendente · ✅ reproduzido · 🟡 reproduzido com critério identificado ·
🟠 divergente com explicação · 🔴 divergente sem explicação.

Critérios de aceite: contagens e somas monetárias **exatas** (ao centavo); médias e percentuais
iguais com **2 casas decimais**.

| # | Indicador | Base | Histórico | Reproduzido | Critério usado | Status |
|---|---|---|---:|---:|---|---|
| 1 | Registros | completa | 73.046 | 73.046 | linhas = registros do cabeçalho DBF | ✅ |
| 2 | Colunas | completa | 113 | 113 | campos do DBF | ✅ |
| 3 | Soma `VAL_TOT` | completa | R$ 125.440.636,13 | R$ 125.440.636,13 | soma exata (Pandas = DuckDB) | ✅ |
| 4 | Saídas em 2023 | completa | 29.279 | 29.279 | ano de `DT_SAIDA` | ✅ |
| 5 | Saídas em 2024 | completa | 43.767 | 43.767 | ano de `DT_SAIDA` | ✅ |
| 6 | Permanência média | completa | 6,12 | 6,12 (6,1249) | média de `DIAS_PERM` | 🟡 |
| 7 | Idade média | completa | 43,96 | 43,96 (43,9613) | média de `IDADE` **sem** `COD_IDADE` — critério incorreto; corrigida: 43,85 | 🟡 ⚠️ |
| 8 | Valor médio | completa | R$ 1.717,28 | R$ 1.717,28 | `VAL_TOT` / registros | ✅ |
| 9 | Óbitos | completa | 4.664 | 4.664 | `MORTE` = 1 | 🟡 |
| 10 | Mortalidade bruta | completa | 6,38% | 6,39% (6,3850) | óbitos / registros; só truncamento dá 6,38 | 🟠 |
| 11 | Registros | AIH tipo 1 | 72.383 | 72.383 | `IDENT` = 1 | ✅ |
| 12 | Soma `VAL_TOT` | AIH tipo 1 | R$ 123.858.470,15 | R$ 123.858.470,15 | | ✅ |
| 13 | Valor médio | AIH tipo 1 | R$ 1.711,15 | R$ 1.711,15 | | ✅ |
| 14 | Permanência média | AIH tipo 1 | 5,93 | 5,93 (5,9255) | `DIAS_PERM` | 🟡 |
| 15 | Óbitos | AIH tipo 1 | 4.656 | 4.656 | `MORTE` = 1 | 🟡 |
| 16 | Registros | AIH tipo 5 | 663 | 663 | `IDENT` = 5 | ✅ |
| 17 | Soma `VAL_TOT` | AIH tipo 5 | R$ 1.582.165,98 | R$ 1.582.165,98 | | ✅ |
| 18 | Valor médio | AIH tipo 5 | R$ 2.386,37 | R$ 2.386,37 | | ✅ |
| 19 | Permanência média | AIH tipo 5 | 27,90 | 27,90 (27,8989) | `DIAS_PERM` | 🟡 |
| 20 | Óbitos | AIH tipo 5 | 8 | 8 | `MORTE` = 1 | 🟡 |
| 21 | AIHs repetidas (ocorrências) | completa | 56 | 56 | registros excedentes | 🟡 |
| 22 | AIHs repetidas (números distintos) | completa | 50 | 50 | | ✅ |
| 23 | Concentração top 10% | ? | 58,20% | 57,74% (completa) · 58,27% (tipo 1) | critério não recuperado | 🔴 |
| 24 | Cirúrgicos | AIH tipo 1 | 51,57% | 51,57% | participação no **valor**, grupo SIGTAP 04 | 🟡 |
| 25 | Clínicos | AIH tipo 1 | 44,38% | 44,38% | participação no **valor**, grupo SIGTAP 03 | 🟡 |
| 26 | Grupos com diferenças (preservação) | — | 0 | 0 | redefinido: impressão digital das colunas originais idêntica em bruto e tratado | 🟡 |

Tabela gerada com valores exatos e definições completas:
[`reports/indicators/reconciliation.md`](../reports/indicators/reconciliation.md). Detalhes em
[`indicadores.md`](indicadores.md).

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
