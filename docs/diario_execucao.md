# Diário de execução

Registro cronológico do progresso, para que a continuidade não dependa da memória de nenhuma
conversa. Cada entrada: o que foi feito, como foi validado, commits e pendências.

Branch de desenvolvimento: `work/hospital-analytics-reconstruction` (o `main` só recebe merge com
aprovação da autora).

## 2026-11-10 — Fase 1 (publicada no `main`, `d50f9ad`)

Estrutura, ambiente (Python 3.13 + uv.lock), configuração com referências históricas, testes de
consistência e de higiene do repositório, documentação base.

## 2026-11-10 — Fase 2: recuperação dos dados ✅ concluída tecnicamente

- Ambiente em nuvem não alcança o DATASUS (D-011). Arquivo baixado pela autora e arquivado na
  Release `data-rdrj2401`; SHA-256 `a3f0ea9a…0d7dfc9c` conferido em três lugares.
- Pipeline `.dbc → .dbf → Arrow → Parquet` sem tratamento, com salvaguardas contra falhas
  silenciosas do `dbc2dbf` e do `dbfread` (D-012 a D-018).
- Encoding CP850 adotado (D-019) com prova de preservação dos bytes.

| Critério obrigatório | Resultado |
|---|---|
| Registros | 73.046 ✅ |
| Colunas | 113 ✅ |
| `VAL_TOT` | R$ 125.440.636,13 ✅ (Pandas = DuckDB) |
| Hash do original preservado | `a3f0ea9a…0d7dfc9c` ✅ |
| Nenhuma perda / alteração indevida | impressão digital dos bytes idêntica; 23 células de texto mudaram (somente `AUD_JUST`) ✅ |
| Testes e lint | 108 testes ✅ · ruff ✅ |
| Recuperação em clone limpo | `fetch-data → convert → validate` ✅, sem alterações no repositório |

Commits: `c66f8fb`, `bfded14`, `f5a9987`, `92e055b`, `5c9817c`, `273e474`.
