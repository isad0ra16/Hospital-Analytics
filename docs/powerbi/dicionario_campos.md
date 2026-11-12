# Dicionário de campos — modelo Power BI

> Gerado a partir de `src/hospital_analytics/powerbi.py` (`TABLES`). Não editar manualmente.

## `fato_registro_aih`

- **Granularidade:** 1 linha por registro de AIH do arquivo RD (não é paciente nem, necessariamente, internação)
- **Chave:** `registro_id`

| Campo | Tipo (Power Query) | Pode ser nulo | Origem | Descrição |
|---|---|---|---|---|
| `registro_id` | `Int64.Type` | não | ordem física | Chave técnica: posição do registro no arquivo (1..n) |
| `aih_id` | `Int64.Type` | não | N_AIH | Pseudônimo determinístico do N_AIH (posto denso); só para contagem distinta |
| `competencia` | `type text` | não | ANO_CMPT, MES_CMPT | Competência de processamento (AAAA-MM) — não é data de ocorrência |
| `mes_saida` | `type date` | não | DT_SAIDA | Mês da saída, 1º dia do mês (relação ATIVA com dim_mes) |
| `mes_internacao` | `type date` | não | DT_INTER | Mês da internação, 1º dia do mês (relação INATIVA com dim_mes) |
| `cnes` | `type text` | não | CNES | Estabelecimento (chave de dim_estabelecimento) |
| `municipio_residencia_cod` | `type text` | não | MUNIC_RES | Município de residência (chave de dim_municipio_residencia) |
| `procedimento_cod` | `type text` | não | PROC_REA | Procedimento realizado, código SIGTAP (chave de dim_procedimento) |
| `diagnostico_principal_cod` | `type text` | não | DIAG_PRINC | Diagnóstico principal, código CID-10 (chave de dim_diagnostico) |
| `especialidade_cod` | `type text` | não | ESPEC | Especialidade do leito (chave de dim_especialidade) |
| `carater_cod` | `type text` | não | CAR_INT | Caráter da internação (chave de dim_carater) |
| `complexidade_cod` | `type text` | não | COMPLEX | Complexidade (chave de dim_complexidade) |
| `tipo_aih_cod` | `type text` | não | IDENT | Tipo de AIH: 1 principal, 5 longa permanência (chave de dim_tipo_aih) |
| `perfil_id` | `Int64.Type` | não | COD_IDADE, IDADE, SEXO, RACA_COR | Perfil demográfico do registro (chave de dim_perfil_demografico) |
| `valor_total` | `Currency.Type` | não | VAL_TOT | Valor total do registro (R$, 2 casas, exato) |
| `valor_total_centavos` | `Int64.Type` | não | VAL_TOT | Valor total em centavos (inteiro, para conferência exata) |
| `dias_permanencia` | `Int64.Type` | não | DIAS_PERM | Dias de permanência do registro (na AIH tipo 5: dias do período coberto) |
| `dias_entre_datas` | `Int64.Type` | não | DT_INTER, DT_SAIDA | DT_SAIDA − DT_INTER em dias (difere de DIAS_PERM na longa permanência) |
| `idade_anos` | `type number` | sim | COD_IDADE, IDADE | Idade em anos convertida pela unidade COD_IDADE (6 casas) |
| `obito` | `Int64.Type` | não | MORTE | 1 = óbito (MORTE = 1); 0 = não |
| `aih_ocorrencias` | `Int64.Type` | não | N_AIH | Nº de registros com o mesmo N_AIH |
| `aih_repetida` | `Int64.Type` | não | N_AIH | 1 = o N_AIH aparece em mais de um registro (apenas sinalização) |

## `dim_mes`

- **Granularidade:** 1 linha por mês, anos completos cobrindo todos os meses de internação e saída
- **Chave:** `mes`

| Campo | Tipo (Power Query) | Pode ser nulo | Origem | Descrição |
|---|---|---|---|---|
| `mes` | `type date` | não | calendário | Mês (1º dia do mês) |
| `ano` | `Int64.Type` | não | calendário | Ano |
| `trimestre` | `Int64.Type` | não | calendário | Trimestre (1–4) |
| `mes_num` | `Int64.Type` | não | calendário | Mês (1–12) |
| `ano_mes` | `type text` | não | calendário | Ano-mês (AAAA-MM) |
| `ano_mes_ordem` | `Int64.Type` | não | calendário | Ordenação de ano_mes (AAAAMM) |
| `mes_abrev` | `type text` | não | calendário | Mês abreviado (pt-BR) |

## `dim_estabelecimento`

- **Granularidade:** 1 linha por CNES presente no fato
- **Chave:** `cnes`

| Campo | Tipo (Power Query) | Pode ser nulo | Origem | Descrição |
|---|---|---|---|---|
| `cnes` | `type text` | não | CNES | Código CNES do estabelecimento |
| `municipio_estabelecimento_cod` | `type text` | não | MUNIC_MOV | Município do ESTABELECIMENTO (≠ residência) |
| `uf_estabelecimento_cod` | `type text` | não | MUNIC_MOV | 2 primeiros dígitos do código do município |
| `natureza_juridica_cod` | `type text` | não | NAT_JUR | Natureza jurídica (código) |
| `gestao_cod` | `type text` | não | GESTAO | Tipo de gestão (código) |
| `estabelecimento_nome` | `type text` | sim | CNES CADGERRJ.FANTASIA | Nome fantasia no cadastro CNES (cadastro vigente no download, não 2024-01) |
| `estabelecimento_rotulo` | `type text` | sim | CNES CADGERRJ.FANTASIA | Nome fantasia (CNES) — único; usar nos visuais (há nomes repetidos) |
| `municipio_estabelecimento_nome` | `type text` | sim | IBGE | Município do estabelecimento |
| `uf_estabelecimento_sigla` | `type text` | sim | IBGE | UF do estabelecimento |
| `natureza_juridica_descricao` | `type text` | sim | TabWin SIH/SUS natjur.cnv | Natureza jurídica (texto oficial) |
| `esfera_juridica` | `type text` | sim | TabWin SIH/SUS esferajur.cnv | Esfera: administração pública (federal, estadual, municipal), empresarial, sem fins lucrativos |
| `gestao_descricao` | `type text` | sim | TabWin SIH/SUS GESTAO.CNV | Tipo de gestão (texto oficial) |
| `estabelecimento_nome_fonte` | `type text` | sim | CNES | Fonte e data do cadastro do nome |

## `dim_municipio_residencia`

- **Granularidade:** 1 linha por município de residência presente no fato
- **Chave:** `municipio_residencia_cod`

| Campo | Tipo (Power Query) | Pode ser nulo | Origem | Descrição |
|---|---|---|---|---|
| `municipio_residencia_cod` | `type text` | não | MUNIC_RES | Código do município de RESIDÊNCIA (6 dígitos) |
| `uf_residencia_cod` | `type text` | não | MUNIC_RES | 2 primeiros dígitos do código do município |
| `municipio_residencia_ibge` | `type text` | sim | IBGE | Código IBGE de 7 dígitos |
| `municipio_residencia_nome` | `type text` | sim | IBGE | Nome do município de residência |
| `uf_residencia_sigla` | `type text` | sim | IBGE | UF de residência (sigla) |
| `municipio_residencia_rotulo` | `type text` | sim | IBGE | Município (UF) — único; usar nos visuais |
| `municipio_residencia_fonte` | `type text` | sim | IBGE | Fonte do nome |

## `dim_procedimento`

- **Granularidade:** 1 linha por procedimento realizado presente no fato
- **Chave:** `procedimento_cod`

| Campo | Tipo (Power Query) | Pode ser nulo | Origem | Descrição |
|---|---|---|---|---|
| `procedimento_cod` | `type text` | não | PROC_REA | Código SIGTAP do procedimento realizado |
| `grupo_cod` | `type text` | não | PROC_REA | Grupo SIGTAP (2 primeiros dígitos) |
| `grupo_descricao` | `type text` | sim | dicionário | Descrição do grupo SIGTAP |
| `grupo_fonte` | `type text` | sim | dicionário | Fonte/status da descrição do grupo |
| `procedimento_nome` | `type text` | sim | SIGTAP tb_procedimento | Nome oficial do procedimento |
| `grupo_nome_sigtap` | `type text` | sim | SIGTAP tb_grupo | Nome oficial do grupo (texto literal) |
| `subgrupo_cod` | `type text` | não | PROC_REA | Subgrupo SIGTAP (4 primeiros dígitos) |
| `subgrupo_nome` | `type text` | sim | SIGTAP tb_sub_grupo | Nome oficial do subgrupo |
| `forma_organizacao_cod` | `type text` | não | PROC_REA | Forma de organização SIGTAP (6 primeiros dígitos) |
| `forma_organizacao_nome` | `type text` | sim | SIGTAP tb_forma_organizacao | Nome oficial da forma de organização |
| `procedimento_fonte` | `type text` | sim | SIGTAP | Fonte e competência dos nomes |

## `dim_diagnostico`

- **Granularidade:** 1 linha por código CID-10 de diagnóstico principal presente no fato
- **Chave:** `diagnostico_cod`

| Campo | Tipo (Power Query) | Pode ser nulo | Origem | Descrição |
|---|---|---|---|---|
| `diagnostico_cod` | `type text` | não | DIAG_PRINC | Código CID-10 (3 ou 4 caracteres, sem ponto) |
| `diagnostico_nome` | `type text` | sim | SIGTAP tb_cid | Descrição oficial do código |
| `diagnostico_rotulo` | `type text` | sim | SIGTAP tb_cid | Código · descrição — usar nos visuais |
| `categoria_cod` | `type text` | não | DIAG_PRINC | Categoria CID-10 (3 primeiros caracteres) |
| `categoria_nome` | `type text` | sim | SIGTAP tb_cid | Descrição oficial da categoria |
| `capitulo_ordem` | `Int64.Type` | sim | TabWin SIH/SUS CID10CAP.CNV | Ordenação do capítulo CID-10 (1–22) |
| `capitulo` | `type text` | sim | TabWin SIH/SUS CID10CAP.CNV | Capítulo CID-10 (texto oficial) |
| `diagnostico_fonte` | `type text` | sim | SIGTAP | Fonte e competência das descrições |

## `dim_especialidade`

- **Granularidade:** 1 linha por código de ESPEC presente no fato
- **Chave:** `especialidade_cod`

| Campo | Tipo (Power Query) | Pode ser nulo | Origem | Descrição |
|---|---|---|---|---|
| `especialidade_cod` | `type text` | não | ESPEC | Código de especialidade do leito (ESPEC) |
| `descricao` | `type text` | sim | dicionário | Descrição do código (especialidade do leito) — fonte secundária |
| `fonte` | `type text` | não | dicionário | Fonte/status da interpretação do código |
| `descricao_oficial` | `type text` | sim | TabWin SIH/SUS | Descrição oficial (especialidade do leito) — usar nos visuais |
| `fonte_oficial` | `type text` | sim | TabWin SIH/SUS | Pacote e tabela de conversão oficiais |

## `dim_carater`

- **Granularidade:** 1 linha por código de CAR_INT presente no fato
- **Chave:** `carater_cod`

| Campo | Tipo (Power Query) | Pode ser nulo | Origem | Descrição |
|---|---|---|---|---|
| `carater_cod` | `type text` | não | CAR_INT | Código de caráter da internação (CAR_INT) |
| `descricao` | `type text` | sim | dicionário | Descrição do código (caráter da internação) — fonte secundária |
| `fonte` | `type text` | não | dicionário | Fonte/status da interpretação do código |
| `descricao_oficial` | `type text` | sim | TabWin SIH/SUS | Descrição oficial (caráter da internação) — usar nos visuais |
| `fonte_oficial` | `type text` | sim | TabWin SIH/SUS | Pacote e tabela de conversão oficiais |

## `dim_complexidade`

- **Granularidade:** 1 linha por código de COMPLEX presente no fato
- **Chave:** `complexidade_cod`

| Campo | Tipo (Power Query) | Pode ser nulo | Origem | Descrição |
|---|---|---|---|---|
| `complexidade_cod` | `type text` | não | COMPLEX | Código de complexidade (COMPLEX) |
| `descricao` | `type text` | sim | dicionário | Descrição do código (complexidade) — fonte secundária |
| `fonte` | `type text` | não | dicionário | Fonte/status da interpretação do código |
| `descricao_oficial` | `type text` | sim | TabWin SIH/SUS | Descrição oficial (complexidade) — usar nos visuais |
| `fonte_oficial` | `type text` | sim | TabWin SIH/SUS | Pacote e tabela de conversão oficiais |

## `dim_tipo_aih`

- **Granularidade:** 1 linha por código de IDENT presente no fato
- **Chave:** `tipo_aih_cod`

| Campo | Tipo (Power Query) | Pode ser nulo | Origem | Descrição |
|---|---|---|---|---|
| `tipo_aih_cod` | `type text` | não | IDENT | Código de tipo de AIH (IDENT) |
| `descricao` | `type text` | sim | dicionário | Descrição do código (tipo de AIH) — fonte secundária |
| `fonte` | `type text` | não | dicionário | Fonte/status da interpretação do código |
| `descricao_oficial` | `type text` | sim | TabWin SIH/SUS | Descrição oficial (tipo de AIH) — usar nos visuais |
| `fonte_oficial` | `type text` | sim | TabWin SIH/SUS | Pacote e tabela de conversão oficiais |

## `dim_perfil_demografico`

- **Granularidade:** 1 linha por combinação faixa etária × sexo × raça/cor presente no fato (perfil, não paciente)
- **Chave:** `perfil_id`

| Campo | Tipo (Power Query) | Pode ser nulo | Origem | Descrição |
|---|---|---|---|---|
| `perfil_id` | `Int64.Type` | não | derivado | Chave do perfil |
| `faixa_etaria_ordem` | `Int64.Type` | não | COD_IDADE, IDADE | Ordenação da faixa etária (99 = sem informação) |
| `faixa_etaria` | `type text` | não | COD_IDADE, IDADE | Faixa etária (idade em anos corrigida) |
| `sexo_cod` | `type text` | não | SEXO | Código de sexo |
| `sexo_descricao` | `type text` | sim | dicionário | Sexo (fonte secundária) |
| `raca_cor_cod` | `type text` | não | RACA_COR | Código de raça/cor |
| `raca_cor_descricao` | `type text` | sim | dicionário | Raça/cor (fonte secundária) |
| `sexo_descricao_oficial` | `type text` | sim | TabWin SIH/SUS SEXO.CNV | Sexo (texto oficial) |
| `raca_cor_descricao_oficial` | `type text` | sim | TabWin SIH/SUS RACACOR.CNV | Raça/cor (texto oficial) |

## `aux_curva_lorenz`

- **Granularidade:** 1 linha por percentil de registros (0–100), base completa; sem relacionamento
- **Chave:** `percentil`

| Campo | Tipo (Power Query) | Pode ser nulo | Origem | Descrição |
|---|---|---|---|---|
| `percentil` | `Int64.Type` | não | derivado | Percentil de registros (0–100) |
| `pct_registros` | `type number` | não | VAL_TOT | Fração acumulada de registros, do menor para o maior valor |
| `pct_valor` | `type number` | não | VAL_TOT | Fração acumulada do valor total (VAL_TOT) |
| `igualdade` | `type number` | não | derivado | Linha de igualdade (= pct_registros) |

## `ref_indicadores_validados`

- **Granularidade:** 1 linha por indicador reconciliado (reports/indicators/reconciliation.json); sem relacionamento
- **Chave:** `indicador_id`

| Campo | Tipo (Power Query) | Pode ser nulo | Origem | Descrição |
|---|---|---|---|---|
| `indicador_id` | `type text` | não | reconciliação | Identificador do indicador |
| `indicador` | `type text` | não | reconciliação | Nome do indicador |
| `base` | `type text` | não | reconciliação | Base/escopo (filtro aplicado) |
| `unidade` | `type text` | não | reconciliação | count, money, days, years ou pct |
| `historico` | `type text` | sim | reconciliação | Valor histórico recuperado |
| `reproduzido` | `type text` | sim | reconciliação | Reproduzido na precisão do histórico |
| `valor_exato` | `type number` | não | reconciliação | Valor reproduzido exato (6 casas) |
| `status` | `type text` | não | reconciliação | Status de validação |

## `qualidade_campos`

- **Granularidade:** 1 linha por campo original do RD (reports/audit/audit_rdrj2401.json); sem relacionamento
- **Chave:** `campo`

| Campo | Tipo (Power Query) | Pode ser nulo | Origem | Descrição |
|---|---|---|---|---|
| `campo` | `type text` | não | auditoria | Campo original do arquivo RD |
| `tipo_dbf` | `type text` | não | auditoria | Tipo e tamanho no DBF |
| `vazios` | `Int64.Type` | não | auditoria | Registros com o campo vazio |
| `pct_vazios` | `type number` | não | auditoria | % de registros com o campo vazio |
| `distintos` | `Int64.Type` | não | auditoria | Valores distintos |
| `exportado_powerbi` | `type text` | não | modelo | sim / não (motivo) |

## Relacionamentos

| Fato | Dimensão | Cardinalidade | Ativo | Direção do filtro |
|---|---|---|---|---|
| `fato_registro_aih[mes_saida]` | `dim_mes[mes]` | N:1 | sim | única (dimensão → fato) |
| `fato_registro_aih[mes_internacao]` | `dim_mes[mes]` | N:1 | não (USERELATIONSHIP) | única (dimensão → fato) |
| `fato_registro_aih[cnes]` | `dim_estabelecimento[cnes]` | N:1 | sim | única (dimensão → fato) |
| `fato_registro_aih[municipio_residencia_cod]` | `dim_municipio_residencia[municipio_residencia_cod]` | N:1 | sim | única (dimensão → fato) |
| `fato_registro_aih[procedimento_cod]` | `dim_procedimento[procedimento_cod]` | N:1 | sim | única (dimensão → fato) |
| `fato_registro_aih[diagnostico_principal_cod]` | `dim_diagnostico[diagnostico_cod]` | N:1 | sim | única (dimensão → fato) |
| `fato_registro_aih[especialidade_cod]` | `dim_especialidade[especialidade_cod]` | N:1 | sim | única (dimensão → fato) |
| `fato_registro_aih[carater_cod]` | `dim_carater[carater_cod]` | N:1 | sim | única (dimensão → fato) |
| `fato_registro_aih[complexidade_cod]` | `dim_complexidade[complexidade_cod]` | N:1 | sim | única (dimensão → fato) |
| `fato_registro_aih[tipo_aih_cod]` | `dim_tipo_aih[tipo_aih_cod]` | N:1 | sim | única (dimensão → fato) |
| `fato_registro_aih[perfil_id]` | `dim_perfil_demografico[perfil_id]` | N:1 | sim | única (dimensão → fato) |

## Campos de origem não exportados (privacidade / minimização)

| Campo | Motivo |
|---|---|
| `N_AIH` | identificador da AIH — substituído por aih_id (pseudônimo determinístico) |
| `NASC` | data de nascimento — substituída por idade_anos e faixa etária |
| `DT_INTER (dia)` | exportada só como mês (mes_internacao) — minimização; a permanência em dias é preservada |
| `DT_SAIDA (dia)` | exportada só como mês (mes_saida) — minimização; a permanência em dias é preservada |
| `CEP` | CEP de residência — granularidade desnecessária para o dashboard |
| `CPF_AUT` | CPF — identificador pessoal (100% vazio nesta base) |
| `GESTOR_CPF` | CPF do gestor — identificador pessoal |
| `INSC_PN` | inscrição no pré-natal — identificador |
| `AUD_JUST` | texto livre de auditoria |
| `SIS_JUST` | texto livre do sistema |
