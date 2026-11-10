# Fontes oficiais para enriquecimento (nomes e descrições)

> **Situação: investigação — nada incorporado.** Do ambiente de execução, **todos** os servidores
> oficiais testados foram recusados pela política de rede (HTTP 403 no proxy, 2026-11-10):
> `servicodados.ibge.gov.br`, `www.ibge.gov.br`, `ftp.ibge.gov.br`, `sigtap.datasus.gov.br`,
> `cnes.datasus.gov.br`, `apidadosabertos.saude.gov.br`, `dadosabertos.saude.gov.br`,
> `www2.datasus.gov.br`, `datasus.saude.gov.br`; e o FTP do DATASUS não responde (D-011).
> As fontes abaixo são **candidatas**, indicadas a partir de conhecimento prévio das publicações
> oficiais; URLs, versões e licenças estão marcadas **"a verificar"** até serem confirmadas no
> próprio site. Enquanto isso, as dimensões mantêm os códigos e a pendência fica registrada.

## Candidatas por domínio

| Domínio | Fonte oficial candidata | O que forneceria | Versão a usar | Licença / termos | Situação |
|---|---|---|---|---|---|
| Municípios e UF | **IBGE — API de Localidades** (`servicodados.ibge.gov.br/api/v1/localidades/municipios`, documentação em `servicodados.ibge.gov.br/api/docs/localidades`) | código de 7 dígitos, nome do município, UF, região | atual (a API não versiona por data) | dados públicos do IBGE — **a verificar** | a verificar |
| Municípios e UF (alternativa versionada) | **IBGE — Divisão Territorial Brasileira (DTB)**, publicação anual (página "Divisão Territorial Brasileira" em `ibge.gov.br`, arquivos no FTP do IBGE) | mesma informação, com ano de referência | DTB 2023 ou 2024 (cobre jan/2024) | **a verificar** | a verificar |
| Estabelecimentos | **CNES/DATASUS — base de dados mensal** (página de downloads do `cnes.datasus.gov.br`, arquivo da competência) | nome fantasia, razão social, tipo de estabelecimento | **competência 2024-01** (mesma do RD) | dados públicos do Ministério da Saúde — **a verificar** | a verificar |
| Estabelecimentos (alternativa) | **OpenDataSUS** — conjunto "Cadastro Nacional de Estabelecimentos de Saúde" (`dadosabertos.saude.gov.br`) | idem | competência mais próxima de 2024-01 | **a verificar** (o portal declara licença por conjunto) | a verificar |
| Procedimentos | **SIGTAP/DATASUS — Tabela Unificada** (`sigtap.datasus.gov.br`; arquivos mensais "TabelaUnificada_AAAAMM") | nome do procedimento, grupo, subgrupo, forma de organização | **competência 2024-01** (procedimentos vigentes na competência) | **a verificar** | a verificar |
| Diagnósticos | **CID-10 — DATASUS** (páginas e arquivos CSV da CID-10 em `www2.datasus.gov.br/cid10`) | descrição de categorias (3 caracteres) e subcategorias (4) | versão publicada pelo DATASUS (a confirmar qual) | **a verificar** | a verificar |
| Todos os códigos do SIH (alternativa única) | **Arquivos auxiliares do TabWin para o SIH/SUS** (pasta de auxiliares ao lado de `Dados` no FTP do DATASUS) | tabelas de conversão oficiais usadas pelo próprio DATASUS para decodificar o RD (municípios, procedimentos, CID, especialidade, etc.) | pacote vigente para a competência | **a verificar** | a verificar — também resolveria P-009/P-010 |

## Plano de integração (após verificar e obter os arquivos)

1. **Obtenção:** download do arquivo oficial (pela autora, como o `.dbc`, ou por este ambiente se os
   hosts forem liberados), registro em `data/MANIFEST.json` como **nova fonte** (URL, data, versão
   ou competência, tamanho, SHA-256, licença) e arquivamento em uma Release dedicada.
2. **Camada de referência:** `data/reference/<fonte>.parquet`, convertido sem tratamento (mesmas
   regras da camada bruta), com os campos de código mantidos como texto.
3. **Junção somente por código exato.** Sem correspondência aproximada ou por nome.
   - IBGE: o RD usa código de município com **6 dígitos**; o IBGE publica 7 (o 7º é dígito
     verificador). A junção usaria os 6 primeiros dígitos do código IBGE **e verificaria que esse
     prefixo é único** na tabela de referência — regra a documentar a partir da fonte.
   - CNES, SIGTAP, CID-10: código idêntico ao do RD (CID-10: subcategoria de 4 caracteres e
     categoria de 3, conforme o código).
4. **Validação obrigatória** (testes): cobertura (% de códigos do fato encontrados, por dimensão,
   com a lista dos não encontrados), unicidade da chave na referência, nenhuma alteração no número
   de linhas do fato, total financeiro preservado.
5. **Colunas novas nas dimensões** (ex.: `municipio_nome`, `uf_sigla`, `estabelecimento_nome`,
   `procedimento_nome`, `diagnostico_descricao` + `fonte_nome` com fonte e versão); códigos sem
   correspondência ficam com nome vazio e são listados na página de qualidade.
6. Depois disso: `dim_diagnostico` (CID-10) e o mapa por município passam a ser viáveis.

## Decisão necessária

- **Opção A — liberar hosts no ambiente:** adicionar à lista de hosts permitidos apenas os
  domínios oficiais necessários (ex.: `servicodados.ibge.gov.br`, `sigtap.datasus.gov.br`,
  `cnes.datasus.gov.br`, `www2.datasus.gov.br`). Requer aprovação no aviso do ambiente; o DATASUS
  pode continuar inacessível pelo mesmo motivo do FTP (D-011).
- **Opção B — download pela autora:** baixar os arquivos nos sites oficiais e disponibilizá-los
  como na Release `data-rdrj2401` (preferencialmente o pacote de auxiliares do TabWin para o SIH, que
  cobre vários domínios de uma vez), registrando URL, data e versão.
