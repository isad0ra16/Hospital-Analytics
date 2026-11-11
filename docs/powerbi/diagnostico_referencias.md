# Diagnóstico das referências oficiais — enriquecimento das dimensões

> **Status:** diagnóstico concluído; **integração não autorizada**. Nenhuma dimensão de produção e
> nenhum arquivo do fato foram alterados (`fato_registro_aih.csv` byte a byte idêntico ao de
> `reports/powerbi/export_summary.json`). Relatório sanitizado: apenas agregados — nenhum nome,
> CPF/CNPJ, endereço, telefone ou e-mail. Dados completos: `reports/reference/diagnostico_referencias.json`
> (gerado por `hospital-analytics reference-diagnose`).

## 1. Proveniência e integridade

Arquivos transferidos pela Release em **rascunho** `ref-2024-01` (não publicada, sem tag) para
`data/reference/incoming/` (ignorada pelo git). Conferidos no ambiente contra o tamanho e o SHA-256
calculados **pela autora na origem** (Windows) — classe **A1** para todos.

| Arquivo | Origem oficial | Competência / versão | Bytes | SHA-256 |
|---|---|---|---:|---|
| `TabelaUnificada_202401_v2402072029.zip` | `ftp2.datasus.gov.br/pub/sistemas/tup/downloads/` | 2024-01 (`DT_COMPETENCIA`) | 2.031.390 | `ea520664…0f13a367` |
| `STRJ2401.dbc` | `ftp.datasus.gov.br/…/CNES/200508_/Dados/ST/` | 2024-01 (`COMPETEN`) | 1.416.490 | `13f364d6…0b13736f`* |
| `municipios_ibge.json` | API IBGE `…/localidades/municipios` | consulta da autora (data a registrar) | 2.470.036 | `86ecdccd…6c9c02` |
| `CADGERRJ.dbf` | `TAB_CNES.zip` → `DBF/` | cadastro atualizado em **2026-10-15** | 25.397.490 | `f667b7e7…c1d2f80de4` |
| `RJ_municip.cnv` | `TAB_CNES.zip` → `CNV/` | pacote vigente no download | 6.365 | `ce45aad9…20153b752b0` |
| `TP_PFPJ.CNV` | `TAB_CNES.zip` → `CNV/` | pacote vigente no download | 200 | `d36dc029…94bd07b8ff` |
| `Estabelecimento.def` | `TAB_CNES.zip` | pacote vigente no download | 25.631 | `778d442a…2c91200d` |

\* hashes completos em `config/params.yaml` (`reference_sources`). O `TAB_CNES.zip` (128 MB) não foi
transferido; apenas os quatro arquivos extraídos dele, com hash individual.

## 2. Layouts e codificações reais

| Fonte | Estrutura | Codificação | Evidência |
|---|---|---|---|
| SIGTAP | `*_layout.txt` (`Coluna,Tamanho,Inicio,Fim,Tipo`, posições 1-based inclusivas); 4.787 procedimentos, 14.238 CID, 8 grupos — 0 linhas fora da largura | **CP1252** | 12 nomes usam 0x93/0x94/0x96 (aspas e travessão), que Latin-1 decodifica como controle; leitor ajustado (D-034) |
| CNES ST | DBF, 30.375 registros, 220 colunas, **sem nome** do estabelecimento | não declarada (só códigos usados) | — |
| CNES CADGER | DBF, 59.898 registros, 0 excluídos, 22 campos (inclui `FANTASIA`, `RAZ_SOCI`, `CPF_CNPJ`, endereço, telefone, e-mail) | **CP1252** (*language driver* 0x58) | bytes acentuados decodificam como `ÃÇÉÓÚ` em CP1252 e como desenho de caixa em CP850 |
| IBGE | lista JSON; `id` de 7 dígitos, nome, UF (27 UFs) | UTF-8 | acentos corretos; 0 caracteres de controle |
| TabWin `.cnv` | 1ª linha = nº de categorias e largura; cada linha = sequência, rótulo, códigos (lista, faixa `a-b`, vazio) | CP1252 | `RJ_municip.cnv` 93 categorias; `TP_PFPJ.CNV` 3 |

## 3. Cobertura, ausências e ambiguidades

| Dimensão (chaves do modelo) | Referência | Chave da referência | Cobertura | Ausentes | Ambíguos |
|---|---|---|---:|---:|---:|
| `dim_procedimento` (1.094) | SIGTAP `tb_procedimento` | `CO_PROCEDIMENTO` única | **100%** | 0 | 0 |
| diagnósticos do fato (3.759) | SIGTAP `tb_cid` | `CO_CID` única (3 ou 4 car.) | **100%** | 0 | 0 |
| grupos SIGTAP (4) | SIGTAP `tb_grupo` | `CO_GRUPO` | **100%** | 0 | 0 |
| `dim_estabelecimento` (240) | CNES ST e CADGER | `CNES` única nos dois | **100%** | 0 | 0 |
| `dim_municipio_residencia` (262) | IBGE (6 primeiros dígitos) | prefixo único | **100%** | 0 | 0 |
| municípios dos estabelecimentos (82) | IBGE (6 primeiros dígitos) | prefixo único | **100%** | 0 | 0 |

Chaves únicas em todas as referências ⇒ junções a partir das dimensões **não multiplicam linhas**.

## 4. Consistência entre fontes

| Verificação | Resultado |
|---|---|
| Município do estabelecimento: RD × ST × CADGER | idêntico nos 240 |
| Natureza jurídica: RD × ST | idêntica nos 240 |
| Tipo de gestão: RD × ST | mapeamento 1:1 — `1` ↔ `M` (209), `2` ↔ `E` (31) |
| Municípios RJ (92): código SIH × `RJ_municip.cnv` (DATASUS) × IBGE | 92/92 no CNV; **nomes CNV = IBGE nos 92** (acentos/hífens normalizados) ⇒ código SIH de 6 dígitos = código IBGE sem o dígito verificador |
| Grupos SIGTAP: rótulos atuais (conhecimento prévio) × `tb_grupo` oficial | iguais nos 4 (grupo 05: grafia oficial "orgãos") ⇒ resolve P-011 |
| Competência: SIGTAP × CNES ST × RD | 2024-01 nos três |

## 5. Fonte dos nomes dos estabelecimentos e segurança

- **Fonte identificada no próprio TabWin:** `Estabelecimento.def` define "Nome Fantasia - RJ" como
  `CNES → FANTASIA` em `DBF\CADGERRJ.DBF`.
- **Pessoa jurídica:** os 240 têm `PF_PJ = 3`. Em `TP_PFPJ.CNV`, `3` é listado explicitamente como
  "Pessoa Jurídica", mas também cai na faixa `0-3` de "Não informado" (precedência do formato não
  verificada). Evidência independente: `CPF_CNPJ` com **14 dígitos (CNPJ) nos 240** ⇒ pessoa jurídica.
- **Sinais de dados pessoais em `FANTASIA` (240):** 0 sequências de 11+ dígitos; 0 nomes iniciados
  por títulos pessoais ("DR", "DRA", "CONSULTÓRIO"); 0 vazios.
- **Uso seguro:** apenas `FANTASIA`. `RAZ_SOCI`, `CPF_CNPJ`, endereço, telefone e e-mail **não** saem
  do ambiente e **não** são propostos.

## 6. Riscos e limitações

| Risco | Medida |
|---|---|
| **Defasagem temporal:** CADGER atualizado em 2026-10-15, não em 2024-01 | nomes podem diferir dos de jan/2024 (renomeações); rotular como "nome no cadastro CNES de 2026-10"; os 240 seguem ativos (`EXCLUIDO = 0`) |
| **Nomes repetidos:** 2 nomes fantasia compartilhados por 4 estabelecimentos (405 registros) | rótulo de exibição com o código: `FANTASIA (CNES)` |
| **Possível truncamento:** 3 nomes ocupam os 60 caracteres do campo (612 registros) | documentar; não completar nomes |
| IBGE: data da consulta não registrada | registrar a data informada pela autora no manifesto antes da integração |
| Municípios fora do RJ (170): apenas IBGE, sem segunda fonte | documentado |
| Grafia oficial do SIGTAP com erros pontuais ("orgãos") | manter o texto oficial literal |

## 7. Colunas propostas (aguardam aprovação)

Somente **colunas novas nas dimensões** (e uma dimensão nova); nenhuma coluna existente removida,
fato byte a byte inalterado, guarda `enrichment_guard` obrigatória.

| Tabela | Coluna nova | Origem | Tipo |
|---|---|---|---|
| `dim_procedimento` | `procedimento_nome` | SIGTAP `tb_procedimento.NO_PROCEDIMENTO` | texto |
| `dim_procedimento` | `grupo_nome_sigtap` | SIGTAP `tb_grupo.NO_GRUPO` (texto oficial literal) | texto |
| `dim_procedimento` | `procedimento_fonte` | "SIGTAP 2024-01 (TabelaUnificada_202401_v2402072029)" | texto |
| **`dim_diagnostico`** (nova, 3.759 linhas) | `diagnostico_cod` (chave), `diagnostico_nome`, `diagnostico_fonte` | SIGTAP `tb_cid.CO_CID`, `NO_CID` | texto |
| `dim_municipio_residencia` | `municipio_residencia_ibge`, `municipio_residencia_nome`, `uf_residencia_sigla`, `municipio_residencia_fonte` | IBGE `id`, `nome`, `UF.sigla` | texto |
| `dim_estabelecimento` | `estabelecimento_nome` | CADGER `FANTASIA` | texto |
| `dim_estabelecimento` | `estabelecimento_rotulo` | `FANTASIA (CNES)` — desambiguação | texto |
| `dim_estabelecimento` | `municipio_estabelecimento_nome`, `uf_estabelecimento_sigla` | IBGE | texto |
| `dim_estabelecimento` | `estabelecimento_nome_fonte` | "CNES CADGERRJ (cadastro de 2026-10-15)" | texto |

Nova relação proposta: `fato_registro_aih[diagnostico_principal_cod]` → `dim_diagnostico[diagnostico_cod]`
(N:1, direção única). Fora do escopo agora (fontes não obtidas): descrições de `NAT_JUR` e `GESTAO`
(`NATJUR.CNV`, `TPGESTAO.CNV`) e o dicionário SIH (`TAB_SIH.zip`).
