# Plano operacional de enriquecimento — fontes oficiais de referência

> **Status:** plano para aprovação. Nada foi baixado, integrado ou publicado. O modelo, os dados e
> o pipeline permanecem intactos. Este arquivo ainda **não** foi versionado.

## Como os endereços foram classificados

O ambiente de execução não alcança nenhum site oficial (403 na política de rede; FTP do DATASUS
sem resposta). Nenhum endereço pôde ser aberto daqui. Classificação usada:

| Classe | Significado |
|---|---|
| **V — verificado por uso** | o projeto já baixou um arquivo oficial deste endereço, com SHA-256 conferido |
| **C2 — corroborado (2 fontes)** | aparece no código-fonte de duas ferramentas públicas independentes que baixam dados do DATASUS (`microdatasus` 7109ec2; `PySUS` 2.11.7) |
| **C1 — corroborado (1 fonte)** | aparece no código de uma dessas ferramentas |
| **K — candidato** | conhecimento prévio, sem corroboração; **não usar sem confirmação no site** |

Ferramentas de terceiros servem só para localizar endereços oficiais — **nenhum dado delas é usado**.

**Regra para nomes de arquivos:** onde o nome exato não está corroborado, o passo é **listar o
diretório oficial** e enviar a listagem; os nomes reais saem dessa listagem, não deste documento.

## Fontes

### 1. Dicionário SIH/SUS e tabelas auxiliares do TabWin (prioridade 1)

| Item | Detalhe |
|---|---|
| Necessário | (a) documentação oficial do layout do RD (Informe Técnico); (b) tabelas de conversão do TabWin para o SIH (arquivos de conversão que o DATASUS usa para decodificar os campos do RD) |
| Endereço | raiz dos dados do SIH: `ftp://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/200801_/` — **V** (pasta `Dados/`). Subpastas de auxiliares e de documentação ao lado de `Dados/`: **K** (o padrão `…/200801_/Auxiliar/TAB_xxx.zip` é **C1** para o SIA e o CNES, mas **não** para o SIH) |
| Versão | o pacote vigente na data do download; registrar data e SHA-256. Para o layout, a versão que cubra a competência 2024-01 |
| Relacionamento | campos de código do RD (`ESPEC`, `CAR_INT`, `COBRANCA`, `NAT_JUR`, `GESTAO`, `IDENT`, `COD_IDADE`, `MARCA_UTI`, `MUNIC_RES`/`MUNIC_MOV`, `PROC_REA`, `DIAG_PRINC`) ↔ código das tabelas de conversão |
| Uso | confirmar ou corrigir o dicionário secundário (P-001, P-009), rotular `ESPEC` 10/14/87 (P-010), `NAT_JUR` e `GESTAO` |
| Riscos | tabelas de conversão podem agrupar códigos ou ter rótulos abreviados; formato próprio do TabWin (a ser lido sem tratamento e documentado); versão do pacote pode não corresponder exatamente a jan/2024 |

### 2. CNES — estabelecimentos (prioridade 2)

| Item | Detalhe |
|---|---|
| Necessário | cadastro de estabelecimentos do RJ na competência 2024-01 e, se o arquivo de dados não trouxer nomes, o pacote auxiliar do CNES |
| Endereço | `ftp://ftp.datasus.gov.br/dissemin/publicos/CNES/200508_/Dados/` — **C2**; grupo `ST` = "Estabelecimentos" — **C1** (PySUS). Subpasta e nome do arquivo do RJ 2024-01: **K** → listar. Pacote auxiliar: `ftp://ftp.datasus.gov.br/dissemin/publicos/CNES/200508_/Auxiliar/TAB_CNES.zip` — **C1** |
| Alternativa | portal OpenDataSUS `https://dadosabertos.saude.gov.br` — **C2** como portal; conjunto específico do CNES: **K** |
| Versão | **competência 2024-01**, UF RJ (a mesma do RD) |
| Relacionamento | `dim_estabelecimento.cnes` (7 dígitos, texto) ↔ campo de código CNES do cadastro |
| Riscos | o arquivo `ST` pode **não conter nome** do estabelecimento (verificar colunas após o download); estabelecimentos desativados ou renomeados entre competências; possível mais de uma linha por CNES (checar unicidade); CNES presente no RD e ausente no cadastro do mês |

### 3. SIGTAP — procedimentos (prioridade 3)

| Item | Detalhe |
|---|---|
| Necessário | Tabela Unificada de procedimentos (código, nome, grupo, subgrupo, forma de organização) |
| Endereço | portal SIGTAP do DATASUS — **K** (não corroborado); a área de downloads do portal indica os arquivos por competência |
| Versão | **competência 2024-01** |
| Relacionamento | `dim_procedimento.procedimento_cod` (10 dígitos, texto) ↔ código do procedimento; `grupo_cod` ↔ código do grupo (confirma P-011) |
| Riscos | procedimentos de AIHs de longa permanência iniciadas antes de 2024 podem não existir na tabela de 2024-01 (procedimento extinto) → cobertura < 100%, buscar competência anterior **documentada**; arquivo da competência é um pacote com várias tabelas (layout no próprio pacote) |

### 4. CID-10 — diagnósticos (prioridade 4)

| Item | Detalhe |
|---|---|
| Necessário | tabelas de categorias (3 caracteres) e subcategorias (4 caracteres) com descrição em português |
| Endereço | publicação da CID-10 pelo DATASUS — **K** (não corroborado) |
| Versão | a versão publicada pelo DATASUS vigente em 2024 (registrar a indicada no site) |
| Relacionamento | `fato.diagnostico_principal_cod` (3–4 caracteres, sem ponto) ↔ subcategoria (4) ou categoria (3); cria a futura `dim_diagnostico` (3.759 códigos no RD) |
| Riscos | códigos do RD sem ponto vs. tabela com ponto (normalizar só o ponto, documentado); códigos de 3 caracteres no RD (sem subcategoria); códigos não pertencentes à CID-10 padrão; atualizações da tabela ao longo do tempo |

### 5. IBGE — municípios e UF (prioridade 5)

| Item | Detalhe |
|---|---|
| Necessário | lista de municípios com código IBGE de 7 dígitos, nome e UF |
| Endereço | site do IBGE `https://www.ibge.gov.br/` — **C1** como site; produto específico (API de Localidades ou Divisão Territorial Brasileira — DTB): **K** |
| Versão | DTB de referência que cubra jan/2024 (registrar o ano da DTB) |
| Relacionamento | `dim_municipio_residencia.municipio_residencia_cod` e `dim_estabelecimento.municipio_estabelecimento_cod` (6 dígitos) ↔ **6 primeiros dígitos** do código IBGE (o 7º é dígito verificador — **confirmar na documentação da DTB**); `uf_*_cod` ↔ código de UF |
| Riscos | o prefixo de 6 dígitos precisa ser **único** na tabela (testar); códigos especiais do SIH (ex.: "ignorado", municípios criados ou extintos) sem correspondência; os arquivos auxiliares do TabWin (item 1) podem trazer a tabela de municípios já no formato de 6 dígitos — **comparar as duas fontes**, se ambas forem obtidas |

## Licenciamento

Dados do DATASUS e do IBGE são publicações oficiais de acesso público. A **licença ou os termos de
uso específicos não foram verificados** para nenhum dos arquivos. No download, registrar o texto
ou a página de termos de cada fonte (captura da página ou link), para documentar no manifesto e no
README. A publicação de tabelas de referência no GitHub (Release) depende dessa verificação.

## Instruções de download no Windows

Use o **PowerShell**. Escreva `curl.exe` (com `.exe`): no Windows PowerShell 5, `curl` sozinho é
um apelido de outro comando.

**Passo 1 — listar os diretórios (não baixa nada; envie-me o texto da saída):**

```powershell
curl.exe --list-only ftp://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/200801_/
```
```powershell
curl.exe --list-only ftp://ftp.datasus.gov.br/dissemin/publicos/CNES/200508_/
```
```powershell
curl.exe --list-only ftp://ftp.datasus.gov.br/dissemin/publicos/CNES/200508_/Dados/
```

Repita `--list-only` nas subpastas que aparecerem (ex.: a de auxiliares do SIH e a do grupo `ST`
do CNES). Alternativa sem linha de comando: cole o endereço `ftp://…` na barra de endereços do
**Explorador de Arquivos** do Windows.

**Passo 2 — baixar cada arquivo identificado na listagem** (substitua pelo caminho exato listado):

```powershell
curl.exe -O ftp://ftp.datasus.gov.br/dissemin/publicos/<caminho exato da listagem>
```

**Passo 3 — registrar a integridade de cada arquivo:**

```powershell
Get-FileHash .\<arquivo> -Algorithm SHA256; (Get-Item .\<arquivo>).Length
```

**SIGTAP, CID-10, IBGE e OpenDataSUS (sites web):** abra o site oficial no navegador, navegue até a
área de downloads, baixe o arquivo da versão/competência indicada acima e anote: **URL exata da
página e do arquivo**, data do download, versão/competência informada no site e os termos de uso.

**Entrega dos arquivos:** como no `.dbc` (Release do repositório criada por você, ex. `ref-2024-01`)
— somente após verificar os termos de uso. Para cada arquivo, informe: URL, data, versão, tamanho
e SHA-256.

## Testes de aceitação do enriquecimento

O enriquecimento só pode **acrescentar colunas às dimensões**. Critérios obrigatórios:

1. **Fato intocado:** `fato_registro_aih.csv` **byte a byte idêntico** ao atual (mesmo SHA-256 de
   `reports/powerbi/export_summary.json`) → 73.046 registros e R$ 125.440.636,13 por construção.
2. **Dimensões sem perda ou duplicação:** contagem de linhas e conjunto de chaves de cada dimensão
   iguais aos atuais (240, 262, 1.094, …); a junção com a referência é feita a partir da dimensão
   (`left join`) e a chave da referência precisa ser **única** (teste dedicado; falha se houver
   duplicata).
3. **As 64 verificações atuais continuam passando** (chaves, 0 órfãos, join sem duplicação, totais,
   medidas = indicadores validados) e os SHA-256 das camadas bruta e tratada continuam iguais
   (`make verify`).
4. **Cobertura reportada, não forçada:** para cada dimensão, % de códigos com nome oficial e lista
   dos não encontrados (vão para a página de qualidade); sem correspondência aproximada.
5. **Proveniência:** cada referência registrada em `data/MANIFEST.json` (URL, data, versão/competência,
   SHA-256, termos) e conferida antes do uso.
6. **Conferência com a fonte secundária:** tabela comparando rótulos do dicionário atual × oficiais;
   divergências listadas e decididas explicitamente (nunca sobrescritas em silêncio).
7. **Reprodutibilidade:** duas exportações seguidas com SHA-256 idênticos.

## Lista priorizada do que obter

| # | O quê | Como | Classe do endereço |
|---|---|---|---|
| 1 | **Listagens** de `SIHSUS/200801_/`, `CNES/200508_/` e `CNES/200508_/Dados/` (e subpastas relevantes) | `curl.exe --list-only` (passo 1) — enviar o texto | raiz V / C2 |
| 2 | Pacote de tabelas auxiliares do TabWin para o SIH + documentação do layout do RD | da listagem do item 1 | K (pasta a confirmar) |
| 3 | Cadastro de estabelecimentos do CNES, RJ, competência 2024-01 + `TAB_CNES.zip` | da listagem do item 1 | C2 / C1 |
| 4 | Tabela Unificada SIGTAP, competência 2024-01 | portal SIGTAP (navegador) | K |
| 5 | Tabelas da CID-10 (categorias e subcategorias) | publicação do DATASUS (navegador) | K |
| 6 | Municípios IBGE (DTB que cubra jan/2024) | site do IBGE (navegador) | K |

Após receber as listagens (item 1), atualizo este plano com os **nomes exatos** dos arquivos e só
então peço a sua aprovação para integrar.
