# Dados

Esta pasta guarda os dados do pipeline. Nenhum arquivo de dados é versionado: os originais vêm de
fontes públicas e todo o restante é regenerado pelo pipeline. No Git ficam apenas este README e o
`MANIFEST.json`.

| Pasta | Conteúdo | Como é produzida |
| --- | --- | --- |
| `raw/` | `RDRJ2401.dbc` original e sua conversão para Parquet, sem tratamento | download oficial; `hospital-analytics convert` |
| `processed/` | camada tratada: campos originais intactos e colunas derivadas | `hospital-analytics build-processed` |
| `reference/incoming/` | tabelas oficiais de referência (SIGTAP, IBGE, CNES, TabWin do SIH), como foram obtidas | cópia manual dos arquivos oficiais |
| `powerbi/` | modelo estrela em CSV para o Power BI | `hospital-analytics powerbi` |

O `MANIFEST.json` registra, para o arquivo original e para cada derivado, a origem, a data de
obtenção, o tamanho, o SHA-256 e a impressão digital do conteúdo. Os arquivos de referência são
declarados da mesma forma em `config/params.yaml`. O comando `hospital-analytics verify` confere
todos eles e aponta qualquer arquivo ausente ou alterado.

Origem de cada arquivo e como recuperá-los: [`docs/01_fontes_de_dados.md`](../docs/01_fontes_de_dados.md).
