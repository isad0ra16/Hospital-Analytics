# 1. Fontes de dados

## Objetivo

Identificar exatamente quais arquivos públicos sustentam a análise, como foram obtidos, como se
comprova que são os mesmos e como recuperá-los caso o ambiente seja perdido.

## Fonte principal: SIH/SUS, arquivo RD do Rio de Janeiro

O **Sistema de Informações Hospitalares do SUS (SIH/SUS)**, mantido pelo DATASUS, publica mensalmente
os arquivos **RD** (*AIH Reduzida*): um registro por Autorização de Internação Hospitalar aprovada
no mês de processamento (**competência**).

| Item | Valor |
| --- | --- |
| Arquivo | `RDRJ2401.dbc` — RJ, competência 2024-01 |
| Origem oficial | `ftp://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/200801_/Dados/RDRJ2401.dbc` |
| Obtido em | 2026-11-09, pela autora, em conexão brasileira |
| Tamanho · SHA-256 | 5.632.627 bytes · `a3f0ea9a6ce75099fa8210d81b13736fc4da4ac1acf30e8245c7aa3a0d7dfc9c` |
| Versão | o DATASUS não versiona os arquivos; a versão é identificada pelo SHA-256 e pela data gravada no cabeçalho DBF: **2025-02-08** |
| Conteúdo | 73.046 registros · 113 campos · `VAL_TOT` = R$ 125.440.636,13 |
| Cópia arquivada | asset `RDRJ2401.dbc` da Release `data-rdrj2401` deste repositório, sem modificação |

O SHA-256 foi conferido de forma independente pela autora, pelo GitHub (digest do asset) e no
ambiente de processamento (Linux e Windows). Toda a proveniência está registrada em
[`data/MANIFEST.json`](../data/MANIFEST.json) (decisão D-018).

**Competência não é data de ocorrência.** A competência 2024-01 reúne o que foi processado em janeiro
de 2024: as saídas vão de 2023-08 a 2024-01 e as internações de longa permanência começam em 2012
(D-005; ver [`05_validacao.md`](05_validacao.md#competência-internação-e-saída)).

## Histórico recuperado

O projeto original (um notebook, scripts e dados tratados) foi perdido com o computador em que estava.
Restaram registros com os **valores dos indicadores**, mas nenhum código-fonte: todo o código deste
repositório é uma reconstrução. Esses valores ficam em `config/params.yaml` (`historical_reference`),
cada um com um status (`recorded`, `needs_verification`, `criterion_unknown`), e servem apenas como
**alvos de reconciliação** — os resultados nunca são ajustados para coincidir com eles (D-003).

Estrutura mínima conhecida do projeto original: `data/raw/RDRJ2401.parquet`,
`data/processed/sih_rj_2024_01.parquet` e `…_tratado.parquet`, e o notebook
`Hospital Analytics RJ.ipynb`, com as seções coleta e tratamento, validação e qualidade, consultas SQL
com DuckDB, perfil demográfico, diagnósticos e mortalidade, procedimentos, análise financeira e
conclusões. O papel exato de cada Parquet e as versões das ferramentas não foram registrados. A
comparação valor a valor está em [`05_validacao.md`](05_validacao.md#reconciliação-com-o-histórico).

## Referências oficiais para nomes e descrições

Os microdados trazem apenas códigos. Os nomes vêm de tabelas oficiais obtidas pela autora em
2026-11-10, cada uma declarada em `config/params.yaml` (`reference_sources`) com origem, competência,
tamanho e SHA-256, conferidos **antes** de qualquer leitura (D-033, D-035).

| Fonte | Arquivo(s) | Origem oficial | Competência / versão |
| --- | --- | --- | --- |
| SIGTAP — procedimentos e CID-10 | `TabelaUnificada_202401_v2402072029.zip` | `ftp2.datasus.gov.br/pub/sistemas/tup/downloads/` | 2024-01 (`DT_COMPETENCIA`) |
| IBGE — municípios | `municipios_ibge.json` | `servicodados.ibge.gov.br/api/v1/localidades/municipios` | API não versionada; arquivo salvo em 2026-11-10 19:19 (UTC−3) (D-039) |
| CNES — estabelecimentos (competência) | `STRJ2401.dbc` | `ftp.datasus.gov.br/dissemin/publicos/CNES/200508_/Dados/ST/` | 2024-01 (`COMPETEN`) — usado só no diagnóstico |
| CNES — cadastro e tabelas do TabWin | `CADGERRJ.dbf`, `RJ_municip.cnv`, `TP_PFPJ.CNV`, `Estabelecimento.def` | membros de `TAB_CNES.zip` (`…/CNES/200508_/Auxiliar/`) | pacote vigente no download; cadastro atualizado em **2026-10-15** (D-038) |
| SIH/SUS — dicionário oficial do RD (TabWin) | `RD2008.DEF` e 10 tabelas `.CNV` (`LEITOS`, `IDENT`, `CARATEND`, `COMPLEX2`, `SEXO`, `RACACOR`, `natjur`, `esferajur`, `GESTAO`, `CID10CAP`) | membros de `TAB_SIH.zip` (`…/SIHSUS/200801_/Auxiliar/`) | pacote vigente no download; membros datados de 2026-10-15 (D-036) |

Os pacotes `TAB_CNES.zip` (128 MB) e `TAB_SIH.zip` não são copiados para o projeto: apenas os
membros necessários foram extraídos, com CRC conferido e SHA-256 próprio. O SHA-256 dos pacotes de
origem também está registrado (`tab_cnes`, `tab_sih`). Tamanhos e hashes completos dos 20 arquivos:
`config/params.yaml` → `reference_sources`.

### Formatos e codificações observados

| Fonte | Estrutura | Codificação | Evidência |
| --- | --- | --- | --- |
| SIGTAP | texto de largura fixa; leiaute `*_layout.txt` no próprio ZIP (`Coluna,Tamanho,Inicio,Fim,Tipo`, posições 1-based inclusivas); 4.787 procedimentos, 14.238 CID, 8 grupos | CP1252 | 12 nomes usam 0x93/0x94/0x96 (aspas e travessão), que Latin-1 decodifica como caracteres de controle (D-034) |
| CNES ST | DBF, 30.375 registros, 220 campos, sem o nome do estabelecimento | não declarada | — |
| CNES CADGER | DBF, 59.898 registros, 0 excluídos, 22 campos (inclui nome fantasia, razão social, CPF/CNPJ, endereço, contatos) | CP1252 (*language driver* 0x58) | acentos corretos em CP1252, desenho de caixa em CP850 |
| IBGE | lista JSON; `id` de 7 dígitos, nome, UF (27 UFs) | UTF-8 | sem caracteres de controle |
| TabWin `.cnv` | cabeçalho com nº de categorias e largura da chave; cada linha: [pai] sequência, rótulo, códigos (lista, faixa `a-b`, vazio) | CP1252 | — |
| TabWin `.DEF` | para cada campo do RD, tabela de conversão e posição inicial | CP1252 | `RD2008.DEF` |

O diagnóstico somente leitura das referências (`hospital-analytics reference-diagnose`) gera
[`reports/reference/diagnostico_referencias.json`](../reports/reference/diagnostico_referencias.json):
estrutura, colunas reais, qualidade das chaves e cobertura frente às dimensões.

## Recuperação dos dados

| Camada de proteção | O que guarda | Onde |
| --- | --- | --- |
| Código + manifesto + `params.yaml` | pipeline, testes, URLs, datas, tamanhos, SHA-256, impressões digitais | Git |
| Cópia arquivada do RD | `RDRJ2401.dbc` exatamente como baixado | Release `data-rdrj2401` |
| Fonte oficial | arquivos publicados | FTPs do DATASUS e API do IBGE |

Os derivados (Parquet, CSV) **não precisam de backup**: são regenerados e comprovados idênticos
pelas impressões digitais registradas.

Para recuperar o arquivo original, baixe o asset `RDRJ2401.dbc` da Release `data-rdrj2401` (ou da
`official_url` registrada no manifesto) para `data/raw/` e confira:

```bash
uv run hospital-analytics verify
```

Com a [CLI do GitHub](https://cli.github.com/) instalada, `scripts/fetch_source.sh` faz o download e a
conferência num só passo. Se o
SHA-256 **não** coincidir, o DATASUS republicou o arquivo: registre-o como **nova fonte** (nunca
substitua a atual) e reconcilie todos os indicadores.

Os arquivos de referência devem ser colocados em `data/reference/incoming/` (pasta ignorada pelo
Git), com os nomes da tabela acima; `hospital-analytics verify` confere cada um. Os pacotes auxiliares do DATASUS
são atualizados sem versão no nome e a API do IBGE não é versionada: se um SHA-256 divergir, o arquivo
**não é lido** — registre a nova versão em `config/params.yaml` e reconcilie a cobertura
(`hospital-analytics powerbi`).

**Recomendações:** não editar nem substituir o asset da Release `data-rdrj2401` (outra versão = outra
tag); arquivar também os arquivos de referência numa Release própria (ex.: `ref-2024-01`) — hoje eles
existem apenas na cópia local da autora.

## Limitações

- O DATASUS pode republicar o RD; esta análise vale para a versão `a3f0ea9a…0d7dfc9c`.
- O nome dos estabelecimentos vem do cadastro CNES de 2026-10, não de 2024-01: o arquivo ST da
  competência não traz o nome.
- A data da consulta ao IBGE é o carimbo do arquivo salvo, não um registro da consulta.
- Termos de uso das tabelas oficiais não foram verificados formalmente (são dados públicos de órgãos
  federais).
