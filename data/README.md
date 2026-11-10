# data/

Os arquivos de dados **não são versionados** (ver decisão D-002 em
[`docs/decisoes_metodologicas.md`](../docs/decisoes_metodologicas.md)). Eles são obtidos da fonte
oficial do DATASUS e regenerados pelo pipeline.

| Camada | Conteúdo | Regra |
|---|---|---|
| `raw/` | `RDRJ2401.dbc` oficial e sua conversão direta para Parquet | Imutável após gravado |
| `processed/` | Versões tipadas e tratadas (colunas derivadas) | Regenerável a partir de `raw/` |

`MANIFEST.json` (Fase 2) registrará, para cada arquivo bruto: URL de origem, data do download,
tamanho e SHA-256 — permitindo detectar se o DATASUS republicou o arquivo.
