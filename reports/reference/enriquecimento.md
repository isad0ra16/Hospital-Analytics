# Enriquecimento das dimensões — cobertura e rótulos oficiais

> Gerado por `hospital-analytics powerbi` a partir dos CSV exportados. Não editar manualmente. Apenas agregados e rótulos de códigos (nenhum dado de pessoa).

## Cobertura por coluna

| Tabela | Coluna | Linhas | Preenchidas | % | Valores distintos |
|---|---|---:|---:|---:|---:|
| `dim_estabelecimento` | `estabelecimento_nome` | 240 | 240 | 100.00 | 238 |
| `dim_estabelecimento` | `municipio_estabelecimento_nome` | 240 | 240 | 100.00 | 82 |
| `dim_estabelecimento` | `natureza_juridica_descricao` | 240 | 240 | 100.00 | 16 |
| `dim_estabelecimento` | `esfera_juridica` | 240 | 240 | 100.00 | 6 |
| `dim_estabelecimento` | `gestao_descricao` | 240 | 240 | 100.00 | 2 |
| `dim_municipio_residencia` | `municipio_residencia_nome` | 262 | 262 | 100.00 | 259 |
| `dim_municipio_residencia` | `uf_residencia_sigla` | 262 | 262 | 100.00 | 26 |
| `dim_procedimento` | `procedimento_nome` | 1094 | 1094 | 100.00 | 1094 |
| `dim_procedimento` | `grupo_nome_sigtap` | 1094 | 1094 | 100.00 | 4 |
| `dim_procedimento` | `subgrupo_nome` | 1094 | 1094 | 100.00 | 30 |
| `dim_procedimento` | `forma_organizacao_nome` | 1094 | 1094 | 100.00 | 106 |
| `dim_diagnostico` | `diagnostico_nome` | 3759 | 3759 | 100.00 | 3758 |
| `dim_diagnostico` | `capitulo` | 3759 | 3759 | 100.00 | 20 |
| `dim_especialidade` | `descricao_oficial` | 12 | 12 | 100.00 | 12 |
| `dim_carater` | `descricao_oficial` | 4 | 4 | 100.00 | 4 |
| `dim_complexidade` | `descricao_oficial` | 2 | 2 | 100.00 | 2 |
| `dim_tipo_aih` | `descricao_oficial` | 2 | 2 | 100.00 | 2 |
| `dim_perfil_demografico` | `sexo_descricao_oficial` | 78 | 78 | 100.00 | 2 |
| `dim_perfil_demografico` | `raca_cor_descricao_oficial` | 78 | 78 | 100.00 | 6 |

## Rótulos: fonte secundária × fonte oficial

Os visuais usam a coluna oficial. A coluna secundária é mantida (nada é sobrescrito).

| Tabela | Código | Secundária | Oficial | Situação |
|---|---|---|---|---|
| `dim_especialidade` (especialidade_cod) | `01` | Cirúrgico | Cirúrgico | igual |
| `dim_especialidade` (especialidade_cod) | `02` | Obstétricos | Obstétricos | igual |
| `dim_especialidade` (especialidade_cod) | `03` | Clínicos | Clínico | diferente — adotado o oficial |
| `dim_especialidade` (especialidade_cod) | `04` | Crônicos | Crônicos | igual |
| `dim_especialidade` (especialidade_cod) | `05` | Psiquiatria | Psiquiatria | igual |
| `dim_especialidade` (especialidade_cod) | `06` | Pneumologia sanitária (tisiologia) | Pneumologia Sanitária (Tisiologia) | igual (grafia) |
| `dim_especialidade` (especialidade_cod) | `07` | Pediátricos | Pediátricos | igual |
| `dim_especialidade` (especialidade_cod) | `08` | Reabilitação | Reabilitação | igual |
| `dim_especialidade` (especialidade_cod) | `09` | Leito dia / cirúrgicos | Leito Dia / Cirúrgicos | igual (grafia) |
| `dim_especialidade` (especialidade_cod) | `10` | — | Leito Dia / Aids | novo (sem rótulo secundário) |
| `dim_especialidade` (especialidade_cod) | `14` | — | Leito Dia / Saúde Mental | novo (sem rótulo secundário) |
| `dim_especialidade` (especialidade_cod) | `87` | — | Saúde Mental (Clínico) | novo (sem rótulo secundário) |
| `dim_carater` (carater_cod) | `01` | Eletivo | Eletivo | igual |
| `dim_carater` (carater_cod) | `02` | Urgência | Urgência | igual |
| `dim_carater` (carater_cod) | `05` | Outros tipos de acidente de trânsito | Outros tipo de acidente de trânsito | diferente — adotado o oficial |
| `dim_carater` (carater_cod) | `06` | Outros tipos de lesões e envenenamentos por agentes químicos ou físicos | Out tp lesões e envenen por agent quím físicos | diferente — adotado o oficial |
| `dim_complexidade` (complexidade_cod) | `02` | Média complexidade | Média complexidade | igual |
| `dim_complexidade` (complexidade_cod) | `03` | Alta complexidade | Alta complexidade | igual |
| `dim_tipo_aih` (tipo_aih_cod) | `1` | Principal | Normal | diferente — adotado o oficial |
| `dim_tipo_aih` (tipo_aih_cod) | `5` | Longa permanência | Longa permanência | igual |
| `dim_perfil_demografico` (sexo_cod) | `1` | Masculino | Masculino | igual |
| `dim_perfil_demografico` (sexo_cod) | `3` | Feminino | Feminino | igual |
| `dim_perfil_demografico` (raca_cor_cod) | `01` | Branca | Branca | igual |
| `dim_perfil_demografico` (raca_cor_cod) | `02` | Preta | Preta | igual |
| `dim_perfil_demografico` (raca_cor_cod) | `03` | Parda | Parda | igual |
| `dim_perfil_demografico` (raca_cor_cod) | `04` | Amarela | Amarela | igual |
| `dim_perfil_demografico` (raca_cor_cod) | `05` | Indígena | Indígena | igual |
| `dim_perfil_demografico` (raca_cor_cod) | `99` | Sem informação | Sem informação | igual |
| `dim_procedimento` (grupo_cod) | `02` | Procedimentos com finalidade diagnóstica | Procedimentos com finalidade diagnóstica | igual |
| `dim_procedimento` (grupo_cod) | `03` | Procedimentos clínicos | Procedimentos clínicos | igual |
| `dim_procedimento` (grupo_cod) | `04` | Procedimentos cirúrgicos | Procedimentos cirúrgicos | igual |
| `dim_procedimento` (grupo_cod) | `05` | Transplantes de órgãos, tecidos e células | Transplantes de orgãos, tecidos e células | igual (grafia) |

## Nomes de estabelecimentos

- Grupos de nome fantasia repetido: 2 (4 estabelecimentos) — usar `estabelecimento_rotulo` (nome + CNES), que é único.
