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

## 2026-11-10 — Fase 3: auditoria e camada tratada ✅ implementada · Fase 4: indicadores ✅ implementada

**Dicionário:** fonte primária inacessível; fonte secundária `microdatasus` corroborada pelos dados
(D-020). `IDENT` 5 = longa permanência (não "continuidade").

**Camada tratada** (`make processed`): 113 originais intactos (impressão digital = bruta) + 50
derivadas; 39 conversões verificadas reversíveis; 0 datas inválidas; 1 valor com precisão reduzida
pela largura do campo (`VAL_UTI`, D-022).

**Auditoria** (`make audit`): 0 duplicatas exatas; 56 registros excedentes em 50 números de AIH
(46 envolvem tipos 1 e 5 — não são duplicatas); datas consistentes; `MORTE` ⇔ `COBRANCA` 4x;
`DIAS_PERM` ≠ datas apenas em 660 registros tipo 5.

**Indicadores** (`make indicators`): Pandas = DuckDB em todos os agregados; 22 de 24 referências
históricas reproduzidas (12 ✅, 10 🟡); mortalidade 🟠 (6,39 × 6,38: truncamento provável);
concentração top 10% 🔴 (57,74 × 58,20; critério não recuperado).

**Achados:** idade histórica ignora `COD_IDADE` (corrigida 43,85 publicada ao lado, D-025);
"cirúrgicos 51,57%" é participação no **valor** (por contagem 44,97%).

**Defeitos encontrados e corrigidos durante a execução:** colisão de nomes ignorando caixa no
DuckDB (`dt_inter` × `DT_INTER`, D-023); mudança de API do DuckDB 2.0 (`fetchone`); parâmetro `NULL`
sem tipo no SQL; contagem incorreta em documento (corrigida após verificação no relatório).

**Testes:** 145 ✅ · ruff ✅.

**Bloqueios:** P-009 (fonte primária do dicionário) — requer download pela autora.
