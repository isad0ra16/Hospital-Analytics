# 4. Modelagem: esquema estrela enriquecido

## Objetivo

Transformar a camada tratada num modelo dimensional para o Power BI que (1) não confunda unidades de
análise, (2) traga nomes oficiais no lugar de códigos e (3) preserve a tabela fato byte a byte.

Código: `powerbi.py`, `enrichment.py`, `reference.py`, SQL em `sql/powerbi/` · Comando: `hospital-analytics powerbi`
· Anexos gerados: [`dicionario_campos.md`](powerbi/dicionario_campos.md),
[`consultas_power_query.pq`](powerbi/consultas_power_query.pq), [`medidas.dax`](powerbi/medidas.dax)
· Decisões: D-028 a D-038.

## Conceitos — leia antes de usar o modelo

| Conceito | O que é nesta base | Medida |
| --- | --- | --- |
| **Registro de AIH** | uma linha do arquivo RD (73.046) | `[Registros de AIH]` — unidade de todas as taxas |
| **AIH distinta** | um número de AIH (72.990); uma AIH pode ter vários registros | `[AIHs distintas]` |
| **Internação** | episódio de cuidado; a longa permanência gera vários registros e a base não permite reconstruir episódios com segurança | **não existe medida** |
| **Paciente** | pessoa; **não há identificador de paciente** no RD | **não existe medida**; o perfil demográfico descreve o registro |

**Competência ≠ série histórica.** Os meses de saída vão de 2023-08 a 2024-01 e os de internação
desde 2012, mas cada mês contém **apenas** o que foi apresentado na competência 2024-01: a contagem
por mês não é a produção hospitalar daquele mês.

**`DIAS_PERM` na longa permanência.** Na AIH tipo 5, `DIAS_PERM` mede o período coberto pelo registro
(2 a 31 dias), enquanto `DT_SAIDA − DT_INTER` pode somar anos (`dias_entre_datas`, diferente em 660
registros, todos tipo 5). As medidas de permanência usam `DIAS_PERM` (reproduz 6,12 / 5,93 / 27,90) e
devem ser lidas **por tipo de AIH**.

## Esquema estrela

```text
                               dim_mes
                  (ativa) mes_saida │ ┆ mes_internacao (inativa → USERELATIONSHIP)
                                    ▼ ▼
 dim_estabelecimento ── cnes ─▶ ┌──────────────────────┐ ◀─ municipio_residencia_cod ── dim_municipio_residencia
 dim_procedimento ── proc. ────▶ │  fato_registro_aih   │ ◀─ perfil_id ── dim_perfil_demografico
 dim_diagnostico ── CID ───────▶ │  1 linha = 1 registro│ ◀─ tipo_aih_cod ── dim_tipo_aih
 dim_especialidade ─────────────▶ │  de AIH (73.046)     │ ◀─ complexidade_cod ── dim_complexidade
 dim_carater ───────────────────▶ └──────────────────────┘

 Tabelas auxiliares, sem relacionamento: ref_indicadores_validados · qualidade_campos · aux_curva_lorenz
```

| Tabela | Granularidade | Linhas | Chave |
| --- | --- | ---: | --- |
| `fato_registro_aih` | registro de AIH | 73.046 | `registro_id` |
| `dim_mes` | mês (anos 2012–2024 completos) | 156 | `mes` |
| `dim_estabelecimento` | CNES | 240 | `cnes` |
| `dim_municipio_residencia` | município de residência | 262 | `municipio_residencia_cod` |
| `dim_procedimento` | procedimento SIGTAP realizado | 1.094 | `procedimento_cod` |
| `dim_diagnostico` | código CID-10 do diagnóstico principal | 3.759 | `diagnostico_cod` |
| `dim_especialidade` · `dim_carater` · `dim_complexidade` · `dim_tipo_aih` | código | 12 · 4 · 2 · 2 | `*_cod` |
| `dim_perfil_demografico` | faixa etária × sexo × raça/cor | 78 | `perfil_id` |
| `ref_indicadores_validados` | indicador reconciliado | 26 | `indicador_id` |
| `qualidade_campos` | campo original do RD | 113 | `campo` |
| `aux_curva_lorenz` | percentil de registros (0–100), base completa | 101 | `percentil` |

**Relacionamentos.** Todos muitos-para-um, com filtro em direção única (dimensão → fato):

| Coluna do fato | Dimensão | Ativo |
| --- | --- | --- |
| `mes_saida` | `dim_mes[mes]` | sim |
| `mes_internacao` | `dim_mes[mes]` | não — ativado pela medida `[Registros por mês de internação]` |
| `cnes` | `dim_estabelecimento[cnes]` | sim |
| `municipio_residencia_cod` | `dim_municipio_residencia[municipio_residencia_cod]` | sim |
| `procedimento_cod` | `dim_procedimento[procedimento_cod]` | sim |
| `diagnostico_principal_cod` | `dim_diagnostico[diagnostico_cod]` | sim |
| `especialidade_cod`, `carater_cod`, `complexidade_cod`, `tipo_aih_cod` | dimensões de código | sim |
| `perfil_id` | `dim_perfil_demografico[perfil_id]` | sim |

**AIHs repetidas no modelo.** Os 56 registros excedentes (50 números de AIH, 106 registros) são
apresentações sucessivas, não duplicatas. Nada é removido: `aih_ocorrencias` e `aih_repetida` sinalizam
esses registros e `[AIHs distintas]` conta números de AIH. Somar valores por registro é correto, porque
cada registro é uma cobrança; contar "internações" por registro não é.

**Decisões de desenho.**

- Granularidade do fato = registro, com chave técnica `registro_id` (posição no arquivo). `N_AIH` é
  substituído por `aih_id`, um posto denso determinístico, apenas para contagens distintas. Consolidar
  por AIH perderia os valores cobrados por período e exigiria regras não documentadas (D-028).
- Relações muitos-para-um, direção única. O município do **estabelecimento** é atributo de
  `dim_estabelecimento` (todos os atributos dependem do CNES: verificado) e não se relaciona com
  `dim_municipio_residencia`, para que residência e estabelecimento nunca se confundam. A data de
  internação é a única relação inativa, usada via `USERELATIONSHIP` (D-029).
- Um único esquema em Python (`powerbi.TABLES`) gera a exportação, o dicionário de campos, as consultas
  Power Query com tipos explícitos, o projeto Power BI e os testes. CSV UTF-8 (ponto decimal, datas
  ISO, nulo = vazio, booleanos 0/1; códigos como texto); Parquet opcional (D-031).

## Enriquecimento com nomes oficiais

Colunas **acrescentadas** às dimensões por junção de **código exato** a partir da dimensão; nenhuma
coluna original é alterada (D-035).

| Dimensão | Colunas para os visuais | Fonte |
| --- | --- | --- |
| `dim_estabelecimento` | `estabelecimento_rotulo` (nome + CNES), `municipio_estabelecimento_nome`, `esfera_juridica`, `natureza_juridica_descricao`, `gestao_descricao` | CNES CADGERRJ, IBGE, TabWin SIH |
| `dim_municipio_residencia` | `municipio_residencia_rotulo`, `municipio_residencia_nome`, `uf_residencia_sigla`, `municipio_residencia_ibge` | IBGE |
| `dim_procedimento` | `procedimento_nome`, `grupo_nome_sigtap`, `subgrupo_nome`, `forma_organizacao_nome` | SIGTAP 2024-01 |
| `dim_diagnostico` | `diagnostico_rotulo`, `categoria_nome`, `capitulo` (ordenado por `capitulo_ordem`) | SIGTAP `tb_cid`, TabWin `CID10CAP.CNV` |
| dimensões de código | `descricao_oficial` (a secundária fica em `descricao`) | TabWin `LEITOS`, `CARATEND`, `COMPLEX2`, `IDENT` |
| `dim_perfil_demografico` | `sexo_descricao_oficial`, `raca_cor_descricao_oficial` | TabWin `SEXO`, `RACACOR` |

**Regras de junção.**

- Município: o código SIH de 6 dígitos é o código IBGE sem o dígito verificador — o prefixo de 6
  dígitos é único na lista do IBGE e, para os 92 municípios do RJ presentes, os nomes do
  `RJ_municip.cnv` do DATASUS coincidem com os do IBGE.
- Procedimento: estrutura do código SIGTAP grupo (2) + subgrupo (2) + forma (2) + sequência (3) +
  dígito; subgrupo e forma são prefixos de 4 e 6 dígitos, e **todos** os prefixos derivados existem nas
  tabelas oficiais.
- Tabelas TabWin: a chave é o trecho do campo a partir da posição declarada no `RD2008.DEF`, com a
  largura do cabeçalho (ex.: 3 primeiros caracteres da CID para o capítulo). Códigos aparecem em mais
  de uma categoria (faixa "pega-tudo" antes de códigos específicos, hierarquias); o leitor aplica "o
  item mais específico vence" e "o último listado vence" e **falha** se as duas regras divergirem.
  Nos 12 arquivos reais, elas concordam para todos os códigos do modelo (D-037).

**Salvaguardas.** Tamanho e SHA-256 conferidos antes da leitura; chave de referência duplicada é erro
(evita multiplicar linhas); cada dimensão tem exatamente as chaves distintas do fato; cobertura
conferida por coluna e **nunca forçada** — código sem correspondência fica vazio e reprova a
verificação; nenhuma correspondência aproximada ou por nome.

**Resultado** ([`reports/reference/enriquecimento.md`](../reports/reference/enriquecimento.md)):

| Dimensão | Referência | Cobertura |
| --- | --- | ---: |
| `dim_procedimento` (1.094), com grupo, subgrupo e forma | SIGTAP | 100% |
| `dim_diagnostico` (3.759), com categoria e capítulo | SIGTAP `tb_cid`, `CID10CAP.CNV` | 100% |
| `dim_estabelecimento` (240) | CNES CADGER (e ST no diagnóstico) | 100% |
| `dim_municipio_residencia` (262) e municípios dos estabelecimentos (82) | IBGE | 100% |
| dimensões de código e perfil | TabWin SIH | 100% |

**Consistência entre fontes** (diagnóstico): município do estabelecimento idêntico em RD × ST × CADGER
nos 240; natureza jurídica idêntica em RD × ST; gestão com mapeamento 1:1 (`1` ↔ `M` em 209, `2` ↔ `E`
em 31); grupos SIGTAP do conhecimento prévio iguais aos da `tb_grupo` oficial; competência 2024-01 no
SIGTAP, no CNES ST e no RD.

**Rótulos secundário × oficial.** Iguais na maioria; três divergências, decididas a favor do texto
oficial: especialidade 03 ("Clínicos" × "Clínico"), tipo de AIH 1 ("Principal" × "Normal") e os textos
abreviados de caráter 05/06. `ESPEC` 10, 14 e 87, sem rótulo secundário, recebem o oficial (D-036).
Textos oficiais são mantidos literais, inclusive abreviações e grafias ("orgãos").

## Medidas DAX

31 medidas em [`medidas.dax`](powerbi/medidas.dax), cada uma com formato, denominador e limitação
documentados. Convenções (D-032): razões retornam a fração e são **formatadas** como porcentagem (sem
×100); divisões com `DIVIDE`; concentração top 10% com `TOPN` desempatado por `registro_id` (exatamente
k registros); rankings (top 10/15) com `RANKX` sobre o rótulo único da dimensão; nenhuma medida de
"internações" ou "pacientes". Cada medida tem um equivalente em SQL calculado sobre os CSV exportados
e conferido com os indicadores reconciliados
([`reports/powerbi/medidas_referencia.json`](../reports/powerbi/medidas_referencia.json)).

A tabela `aux_curva_lorenz` usa a mesma definição da análise exploratória (registros em ordem
crescente de valor, corte ⌊n·p/100⌋) e é estática: não responde aos filtros.

## Privacidade e risco de reidentificação

Os microdados do RD são públicos e não contêm nomes, mas combinações de atributos
(quasi-identificadores) podem tornar um registro único.

**Não exportados:** `N_AIH` (substituído por `aih_id`), `NASC`, `CEP`, `CPF_AUT`, `GESTOR_CPF`,
`INSC_PN`, textos livres `AUD_JUST`/`SIS_JUST`, CNPJs e as **datas por dia** (só o mês). `aih_id`
**não é anonimização**: quem tiver o arquivo público pode reconstruir a correspondência; serve para não
expor o número da AIH em visuais.

**k-anonimato medido** (registros únicos na base de 73.046):

| Quasi-identificadores | Únicos (k = 1) | k < 5 |
| --- | ---: | ---: |
| faixa etária + sexo + raça/cor | 0,0% | 0,0% |
| + município de residência | 1,4% | 5,3% |
| + município + estabelecimento | 9,9% | 24,4% |
| idade exata + sexo + município + **datas por dia** | **89,4%** | 99,5% |
| idade exata + sexo + município + **meses** (exportação adotada) | **19,9%** | 45,1% |
| faixa + sexo + raça + município + meses | 7,3% | 19,3% |

164 municípios de residência têm menos de 5 registros. Reduzir as datas a mês derruba os registros
únicos de 89,4% para 19,9% sem perder nenhuma análise (a permanência continua exata em dias) (D-030).

**Nomes acrescentados.** A própria definição oficial do TabWin para o CNES (`Estabelecimento.def`)
obtém "Nome Fantasia - RJ" do campo `FANTASIA` do `CADGERRJ`; por isso esse é o campo usado. Do
cadastro só são lidos o código e o nome fantasia dos estabelecimentos presentes no fato. Os 240 são
pessoas jurídicas: têm `PF_PJ` = 3, que `TP_PFPJ.CNV` rotula como pessoa jurídica, e `CPF_CNPJ` com 14
dígitos (CNPJ). Todos estão ativos no cadastro (`EXCLUIDO` = 0), e nenhum nome tem sequência de 11 ou
mais dígitos nem título pessoal. Razão social, CNPJ, endereço, telefone e e-mail nunca
são carregados (teste em `tests/test_enrichment.py`). Dois nomes fantasia são compartilhados por 4
estabelecimentos: os visuais usam `estabelecimento_rotulo` = `nome (CNES)`, único (D-038).

**Publicação.** O nível de registro mantém risco residual. Antes de publicar um `.pbix` com dados
importados, avaliar uma versão **agregada** (faixa etária no lugar da idade exata, supressão de
células com menos de 5 registros, municípios pequenos agrupados) — decisão P-013. Os CSV de
`data/powerbi/` não são versionados.

## Verificações

`hospital-analytics powerbi` executa 122 verificações sobre os arquivos exportados
([`05_validacao.md`](05_validacao.md#modelo-analítico)).

## Limitações

- Nomes de estabelecimentos do cadastro de 2026-10, não de 2024-01; três nomes ocupam os 60 caracteres
  do campo (possível truncamento, não completado).
- Municípios fora do RJ (170) têm apenas o IBGE como fonte, sem segunda conferência.
- O município do estabelecimento não tem dimensão própria: mapas por estabelecimento usam o atributo.
