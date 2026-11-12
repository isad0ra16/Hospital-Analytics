# data/

Os arquivos de dados **não são versionados** (ver decisão D-002 em
[`docs/decisoes_metodologicas.md`](../docs/decisoes_metodologicas.md)). Eles são obtidos da fonte
oficial do DATASUS e regenerados pelo pipeline.

| Camada | Conteúdo | Regra |
|---|---|---|
| `raw/` | `RDRJ2401.dbc` oficial e sua conversão direta para Parquet | Imutável após gravado |
| `processed/` | Versões tipadas e tratadas (colunas derivadas) | Regenerável a partir de `raw/` |

`MANIFEST.json` (versionado) registra, para cada arquivo: origem oficial, cópia arquivada (Release
do GitHub), data do download, tamanho, SHA-256, versão dos dados e, para derivados, ferramentas e
impressão digital do conteúdo. Detecta republicações do DATASUS e qualquer alteração local.

| Arquivo | Papel |
|---|---|
| `raw/RDRJ2401.dbc` | Original do DATASUS (somente leitura) |
| `raw/RDRJ2401.parquet` | Conversão direta, sem tratamento: 113 colunas de texto |
| `reference/incoming/` | Arquivos oficiais de referência (SIGTAP, IBGE, CNES, TabWin SIH), exatamente como obtidos; conferidos por tamanho e SHA-256 (`config/params.yaml`) antes de qualquer leitura |
| `powerbi/` | Modelo estrela exportado (CSV UTF-8) para o Power BI; regenerado por `make powerbi` |

Recuperação do zero: `make fetch-data && make convert && make validate`
(ver [`docs/recuperacao_dados.md`](../docs/recuperacao_dados.md)).
