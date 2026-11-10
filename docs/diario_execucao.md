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

Commits: `c66f8fb`, `bfded14`, `f5a9987`, `92e055b`, `5c9817c`, `273e474`. *(hashes do branch original; equivalentes no branch `-v2` na tabela de 2026-11-10 — histórico sem linhas automáticas)*

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

## 2026-11-10 — Fase 5: análises exploratórias ✅ implementada

`make analysis` → `reports/analysis/` (relatório + 4 figuras reproduzíveis byte a byte): perfil
demográfico, hospitalar, mortalidade, financeiro, permanência, distribuição temporal. Descritivas,
sem causalidade. Achado: os 241 registros com `VAL_TOT` = 0 são exatamente os de `ESPEC` = 87.

**Defeitos encontrados e corrigidos:** coluna ausente na consulta de procedimentos; valor médio sem
arredondamento; chaves `_cents` com valores em reais; pirâmide etária com eixo assimétrico e número
da curva de Lorenz inconsistente com o indicador (ambos vistos ao inspecionar os gráficos).

**Testes:** 150 ✅ · ruff ✅. Pipeline completo reproduzido em clone limpo sem alterações.

## 2026-11-10 — Histórico sem linhas automáticas (branch `work/hospital-analytics-reconstruction-v2`)

Diretriz da autora: commits apenas com a identidade dela, sem coautoria automática nem referências
de sessão. Os 13 commits do branch de desenvolvimento foram **recriados** sobre o mesmo `main`
(`d50f9ad`) com `git commit-tree`: **mesma árvore de arquivos, mesmo autor/committer e mesmas datas**;
das mensagens foram removidas somente as linhas automáticas. Verificado par a par (13/13) e pela
igualdade da árvore final. Sem *force push*; `main`, tag `data-rdrj2401`, Release e o branch original
não foram alterados.

| Original | Recriado (v2) | Commit |
|---|---|---|
| `c66f8fb` | `9ead2e6` | feat: add untreated .dbc to Parquet raw-layer pipeline with integrity checks |
| `bfded14` | `571a1de` | data: register RDRJ2401.dbc and its raw Parquet conversion in the manifest |
| `f5a9987` | `d88247c` | docs: document raw data pipeline, recovery strategy and Phase 2 decisions |
| `92e055b` | `87aa0c3` | fix: keep manifest unchanged when regenerating identical derived files |
| `5c9817c` | `4b854a4` | fix: decode DBF text with the code page declared in its header (CP850) |
| `273e474` | `6638d93` | data: regenerate raw Parquet with CP850 and document decision D-019 |
| `16f4786` | `2fd77d8` | docs: mark Phase 2 as technically complete and start execution log |
| `36b6746` | `ea63797` | feat: add processed layer, data audit and historical indicators with SQL |
| `aa7a044` | `7db4c95` | data: record processed layer and generate audit and reconciliation reports |
| `745cbcc` | `d7e5117` | docs: document data quality, indicators, architecture and decisions D-020 to D-027 |
| `b989edb` | `76c7cee` | feat: add descriptive exploratory analyses with versioned SQL and charts |
| `4e282aa` | `dc11265` | data: generate exploratory analysis report and figures |
| `4a34a3a` | `40695a5` | docs: rewrite README for portfolio and document exploratory analyses |

Commits adicionais no v2: proveniência dos indicadores em termos neutros ("registros de conversas
anteriores"); hook `commit-msg` versionado (`scripts/git-hooks/`, ativação explícita com `make hooks`)
e convenções em `CONTRIBUTING.md`.

Pendente (decisão da autora): os 3 commits do `main` (`c1dd436`, `99b96c9`, `d50f9ad`) ainda contêm as
linhas automáticas; o branch original segue preservado até a verificação do v2.

## 2026-11-10 — Fase 6: camada analítica para Power BI ✅ implementada (dashboard não iniciado)

Branch `work/powerbi-model` (a partir do `-v3`; `main` inalterado — substituição da M2 pendente).

- Modelo estrela: `fato_registro_aih` (73.046) + 9 dimensões + 2 tabelas auxiliares; esquema único
  em `powerbi.py`; SQL em `sql/powerbi/`; `make powerbi`.
- Privacidade medida (k-anonimato): datas reduzidas a mês (registros únicos 89,4% → 19,9%).
- Validação da exportação real: **64/64** verificações (chaves, 0 órfãos, join sem duplicação,
  total R$ 125.440.636,13, medidas = indicadores validados). Testes: 175 ✅.
- Enriquecimento oficial: todos os hosts candidatos recusados pela política de rede → pendente
  (P-012), plano em `docs/powerbi/fontes_referencia.md`.
