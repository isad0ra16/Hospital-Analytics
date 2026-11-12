# Páginas do dashboard (Power BI)

> Gerado a partir de `PAGES` em `src/hospital_analytics/pbip.py` (o mesmo código que gera
> o relatório PBIR em `powerbi/`). Não editar manualmente.

**Estado:** implementado como projeto PBIP (validado contra os esquemas oficiais),
**ainda não aberto no Power BI Desktop** — ver
[`README.md`](README.md#abrir-o-projeto-no-power-bi-desktop). Se o Desktop recusar o
relatório, monte cada página com os visuais abaixo sobre o modelo.

Tela 1280×720. Todas as páginas têm título, rodapé com a fonte e a unidade de análise e, à
direita, cinco segmentações **sincronizadas entre as páginas** (tipo de AIH, caráter,
complexidade, faixa etária, sexo). Rótulos dos códigos: colunas oficiais (`*_oficial`).

Rodapé: *Fonte: SIH/SUS (DATASUS), arquivo RD do RJ, competência 2024-01 · nomes: SIGTAP 2024-01, IBGE, CNES e tabelas TabWin do SIH · unidade: registro de AIH (não é paciente)*
## 1. Visão geral

Internações do SUS no estado do Rio de Janeiro — registros de AIH processados em janeiro de 2024

| Visual | Título | Campos |
|---|---|---|
| Cartão | Registros de AIH — *1 registro ≠ 1 paciente* | Campos: [Registros de AIH] |
| Cartão | AIHs distintas — *números de AIH* | Campos: [AIHs distintas] |
| Cartão | Valor total aprovado — *VAL_TOT, R$* | Campos: [Valor total] |
| Cartão | Valor médio — *por registro* | Campos: [Valor médio por registro] |
| Cartão | Permanência média — *dias, DIAS_PERM* | Campos: [Permanência média (dias)] |
| Cartão | Mortalidade hospitalar — *taxa bruta* | Campos: [Mortalidade hospitalar (razão)] |
| Barras | Registros por tipo de AIH — *Longa permanência: apresentações sucessivas de uma internação* | Eixo: dim_tipo_aih[descricao_oficial]; Valores: [Registros de AIH]; ordenar por [Registros de AIH] (descending) |
| Colunas | Registros por mês de saída — *Competência 2024-01: o mês de saída NÃO é série histórica* | Eixo: dim_mes[ano_mes]; Valores: [Registros de AIH]; ordenar por dim_mes[ano_mes] (ascending) |
| Barras | Valor aprovado por complexidade | Eixo: dim_complexidade[descricao_oficial]; Valores: [Valor total]; ordenar por [Valor total] (descending) |
| Caixa de texto | — | Como ler este painel • A unidade é o registro de AIH do arquivo RD: uma internação longa gera vários registros e não há identificador de paciente. • Competência 2024-01 é o mês de processamento: cada mês de saída contém apenas o que foi apresentado nessa competência. • A mortalidade é bruta (sem ajuste de risco): diferenças refletem o perfil dos casos, não a qualidade do cuidado. • Os totais conferem com o pipeline validado: 73.046 registros e R$ 125.440.636,13. |

## 2. Perfil e origem

Perfil demográfico dos registros e município de residência

| Visual | Título | Campos |
|---|---|---|
| Barras empilhadas (pirâmide) | Registros por faixa etária e sexo — *Perfil dos REGISTROS (o RD não identifica pacientes)* | Eixo: dim_perfil_demografico[faixa_etaria]; Valores: [Registros - masculino (pirâmide)], [Registros - feminino (pirâmide)]; ordenar por dim_perfil_demografico[faixa_etaria] (descending) |
| Barras | Registros por raça/cor (%) — *Inclui "sem informação"* | Eixo: dim_perfil_demografico[raca_cor_descricao_oficial]; Valores: [% dos registros]; ordenar por [% dos registros] (descending) |
| Cartão | Idade média — *anos, pela unidade COD_IDADE* | Campos: [Idade média (anos)] |
| Cartão | Outro município — *residência ≠ estabelecimento* | Campos: [% residentes de outro município] |
| Cartão | Fora do RJ — *UF de residência* | Campos: [% residentes fora do RJ] |
| Colunas | Top 10 municípios de residência — *Nomes: IBGE (código SIH de 6 dígitos)* | Eixo: dim_municipio_residencia[municipio_residencia_rotulo]; Valores: [Registros - top 10 municípios de residência]; ordenar por [Registros - top 10 municípios de residência] (descending) |

## 3. Internações e permanência

Especialidade do leito, caráter da internação, procedimentos e permanência

| Visual | Título | Campos |
|---|---|---|
| Barras | Registros por especialidade do leito | Eixo: dim_especialidade[descricao_oficial]; Valores: [Registros de AIH]; ordenar por [Registros de AIH] (descending) |
| Barras | Permanência média por especialidade (dias) — *Leia por tipo de AIH: na longa permanência, DIAS_PERM é o período do registro* | Eixo: dim_especialidade[descricao_oficial]; Valores: [Permanência média (dias)]; ordenar por [Permanência média (dias)] (descending) |
| Barras | Registros por caráter da internação | Eixo: dim_carater[descricao_oficial]; Valores: [Registros de AIH]; ordenar por [Registros de AIH] (descending) |
| Cartão | Permanência — AIH principal — *dias, tipo 1* | Campos: [Permanência média - AIH principal] |
| Cartão | Longa permanência — *registros tipo 5* | Campos: [Registros de longa permanência] |
| Tabela | Procedimentos realizados — ordenados por número de registros — *Nomes oficiais do SIGTAP, competência 2024-01* | Campos: dim_procedimento[procedimento_nome], dim_procedimento[grupo_nome_sigtap], [Registros de AIH], [Valor total], [Permanência média (dias)], [Mortalidade hospitalar (razão)]; ordenar por [Registros de AIH] (descending) |

## 4. Mortalidade hospitalar

Mortalidade hospitalar bruta por perfil e diagnóstico

| Visual | Título | Campos |
|---|---|---|
| Cartão | Óbitos — *registros com MORTE = 1* | Campos: [Óbitos] |
| Cartão | Mortalidade hospitalar — *todos os registros* | Campos: [Mortalidade hospitalar (razão)] |
| Cartão | Mortalidade — AIH principal — *apenas tipo 1* | Campos: [Mortalidade hospitalar - AIH principal (razão)] |
| Caixa de texto | — | Taxa BRUTA, por registro, sem ajuste por idade, gravidade ou casemix. Não compare estabelecimentos ou grupos como medida de qualidade; não há leitura causal. |
| Barras | Mortalidade por faixa etária — *Tooltip: registros (denominador) e óbitos* | Eixo: dim_perfil_demografico[faixa_etaria]; Valores: [Mortalidade hospitalar (razão)]; Dicas: [Registros de AIH], [Óbitos]; ordenar por dim_perfil_demografico[faixa_etaria] (ascending) |
| Barras | Mortalidade por caráter | Eixo: dim_carater[descricao_oficial]; Valores: [Mortalidade hospitalar (razão)]; Dicas: [Registros de AIH], [Óbitos]; ordenar por [Mortalidade hospitalar (razão)] (descending) |
| Barras | Mortalidade por capítulo CID-10 do diagnóstico principal | Eixo: dim_diagnostico[capitulo]; Valores: [Mortalidade hospitalar (razão)]; Dicas: [Registros de AIH], [Óbitos]; ordenar por [Mortalidade hospitalar (razão)] (descending) |
| Barras | Top 10 diagnósticos principais (registros) — *Descrições: SIGTAP tb_cid 2024-01* | Eixo: dim_diagnostico[diagnostico_rotulo]; Valores: [Registros - top 10 diagnósticos]; Dicas: [Óbitos], [Mortalidade hospitalar (razão)]; ordenar por [Registros - top 10 diagnósticos] (descending) |

## 5. Análise financeira

Valor aprovado (VAL_TOT) e sua concentração

| Visual | Título | Campos |
|---|---|---|
| Cartão | Valor total aprovado — *R$* | Campos: [Valor total] |
| Cartão | Valor médio — *por registro* | Campos: [Valor médio por registro] |
| Cartão | Top 10% dos registros — *parcela do valor; histórico 58,20% não reproduzido* | Campos: [Concentração do valor - top 10%] |
| Linhas | Curva de Lorenz do valor — *Base completa (estática: não responde aos filtros)* | Eixo: aux_curva_lorenz[percentil]; Valores: [Lorenz - % acumulado do valor], [Lorenz - linha de igualdade]; ordenar por aux_curva_lorenz[percentil] (ascending) |
| Barras | Participação no valor por grupo de procedimento (SIGTAP) | Eixo: dim_procedimento[grupo_nome_sigtap]; Valores: [% do valor]; ordenar por [% do valor] (descending) |
| Barras | Top 10 estabelecimentos por valor aprovado — *Nome fantasia no cadastro CNES de 2026-10 (pode diferir do nome em 2024)* | Eixo: dim_estabelecimento[estabelecimento_rotulo]; Valores: [Valor total - top 10 estabelecimentos]; ordenar por [Valor total - top 10 estabelecimentos] (descending) |
| Barras | Valor por esfera jurídica (%) — *Natureza jurídica: TabWin SIH* | Eixo: dim_estabelecimento[esfera_juridica]; Valores: [% do valor]; ordenar por [% do valor] (descending) |

## 6. Qualidade e metodologia

Reconciliação com o histórico, completude dos campos e limitações

| Visual | Título | Campos |
|---|---|---|
| Cartão | Registros excedentes — *registros − AIHs distintas* | Campos: [Registros excedentes de AIH] |
| Cartão | Registros de AIH repetida — *sinalizados, não removidos* | Campos: [Registros de AIH repetida] |
| Cartão | Valor zero — *todos com ESPEC 87* | Campos: [Registros com valor zero] |
| Tabela | Indicadores do histórico × reproduzidos pelo pipeline — *Divergências explicadas, nunca ajustadas* | Campos: ref_indicadores_validados[indicador], ref_indicadores_validados[base], ref_indicadores_validados[historico], ref_indicadores_validados[reproduzido], ref_indicadores_validados[status] |
| Tabela | Completude dos 113 campos originais | Campos: qualidade_campos[campo], qualidade_campos[pct_vazios], qualidade_campos[distintos], qualidade_campos[exportado_powerbi]; ordenar por qualidade_campos[pct_vazios] (descending) |
| Caixa de texto | — | Fontes e limitações Dados: SIH/SUS (DATASUS), arquivo RD do RJ, competência 2024-01; SHA-256 conferido e preservação byte a byte verificada. Nomes oficiais: SIGTAP 2024-01 (procedimentos e CID-10), IBGE (municípios), CNES (nome fantasia, cadastro de 2026-10), tabelas TabWin do SIH (rótulos dos códigos). Cobertura de 100%, junção por código exato. Registro de AIH ≠ paciente ≠ internação: não há medida de pacientes nem de episódios. Mês de saída não é série histórica: a competência reúne o que foi processado em janeiro de 2024. Mortalidade bruta, sem ajuste de risco. Privacidade: sem N_AIH, nascimento, CEP, CPF ou texto livre; datas apenas por mês. Detalhes: docs/ no repositório (decisões D-001 a D-040). |
