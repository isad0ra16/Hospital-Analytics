# Modelo dimensional para Power BI

Camada analítica gerada por `make powerbi` (`src/hospital_analytics/powerbi.py`, SQL em
`sql/powerbi/`). Dicionário completo de campos: [`dicionario_campos.md`](dicionario_campos.md)
(gerado). Medidas: [`medidas.dax`](medidas.dax). Decisões: D-028 a D-033.

## Conceitos — leia antes de usar o modelo

| Conceito | O que é nesta base | Medida |
|---|---|---|
| **Registro de AIH** | uma linha do arquivo RD do SIH/SUS (73.046) | `[Registros de AIH]` — unidade padrão de todas as taxas |
| **AIH distinta** | um número de AIH (72.990); uma AIH pode ter vários registros | `[AIHs distintas]` |
| **Internação** | episódio de cuidado; uma longa permanência gera vários registros e a base não permite reconstruir episódios com segurança | **não existe medida** |
| **Paciente** | pessoa; **não há identificador de paciente** no RD | **não existe medida**; a "dimensão de perfil" descreve o registro, não a pessoa |

**Competência ≠ série histórica.** Todos os registros têm competência 2024-01 (mês de
processamento). Os meses de saída vão de 2023-08 a 2024-01 e os de internação desde 2012, mas cada
mês contém **apenas** o que foi apresentado nessa competência: a contagem por mês **não** é a
produção hospitalar daquele mês. Visuais por mês devem trazer essa ressalva.

**`DIAS_PERM` na longa permanência.** Na AIH tipo 5 (longa permanência — fonte secundária),
`DIAS_PERM` mede o período coberto pelo registro (2 a 31 dias), enquanto `DT_SAIDA − DT_INTER` pode
somar anos (`dias_entre_datas`; difere de `DIAS_PERM` em 660 registros, todos tipo 5). As medidas
de permanência usam `DIAS_PERM` (reproduz o histórico 6,12 / 5,93 / 27,90) e devem ser lidas
**por tipo de AIH**.

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
|---|---|---:|---|
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

### Nomes e descrições oficiais (enriquecimento)

Colunas **acrescentadas** às dimensões por código exato (nenhuma coluna original foi alterada;
fato byte a byte idêntico). Cobertura: **100%** em todas — `reports/reference/enriquecimento.md`.

| Dimensão | Colunas para os visuais | Fonte oficial |
|---|---|---|
| `dim_estabelecimento` | `estabelecimento_rotulo` (nome + CNES), `municipio_estabelecimento_nome`, `esfera_juridica`, `natureza_juridica_descricao`, `gestao_descricao` | CNES CADGERRJ (cadastro de 2026-10-15), IBGE, TabWin SIH |
| `dim_municipio_residencia` | `municipio_residencia_rotulo`, `municipio_residencia_nome`, `uf_residencia_sigla`, `municipio_residencia_ibge` (7 dígitos, para mapas) | IBGE |
| `dim_procedimento` | `procedimento_nome`, `grupo_nome_sigtap`, `subgrupo_nome`, `forma_organizacao_nome` | SIGTAP 2024-01 |
| `dim_diagnostico` | `diagnostico_rotulo`, `categoria_nome`, `capitulo` (ordenar por `capitulo_ordem`) | SIGTAP 2024-01 (`tb_cid`), TabWin SIH (`CID10CAP.CNV`) |
| códigos (`dim_especialidade` …) | `descricao_oficial` | TabWin SIH (`LEITOS`, `CARATEND`, `COMPLEX2`, `IDENT`) |
| `dim_perfil_demografico` | `sexo_descricao_oficial`, `raca_cor_descricao_oficial` | TabWin SIH (`SEXO`, `RACACOR`) |

Limitações: o nome do estabelecimento é o do cadastro **vigente no download**, não o de 2024-01
(D-038); a data da consulta ao IBGE é o carimbo do arquivo (D-039); textos oficiais mantidos
literais, inclusive abreviações ("Out tp lesões e envenen…") e grafias ("orgãos").

## Relacionamentos

Todos **muitos-para-um**, direção de filtro **única** (dimensão → fato), sem relação bidirecional.

| Fato | Dimensão | Ativo |
|---|---|---|
| `mes_saida` | `dim_mes[mes]` | sim |
| `mes_internacao` | `dim_mes[mes]` | **não** — usar `USERELATIONSHIP` (medida `Registros por mês de internação`) |
| `cnes` | `dim_estabelecimento[cnes]` | sim |
| `municipio_residencia_cod` | `dim_municipio_residencia[...]` | sim |
| `procedimento_cod` | `dim_procedimento[procedimento_cod]` | sim |
| `diagnostico_principal_cod` | `dim_diagnostico[diagnostico_cod]` | sim |
| `especialidade_cod`, `carater_cod`, `complexidade_cod`, `tipo_aih_cod` | dimensões de código | sim |
| `perfil_id` | `dim_perfil_demografico[perfil_id]` | sim |

**Sem ambiguidade de caminhos:** o município do **estabelecimento** é um atributo de
`dim_estabelecimento` (`municipio_estabelecimento_cod`) e **não** se relaciona com
`dim_municipio_residencia`. Assim há um único caminho de filtro para cada dimensão, e residência e
estabelecimento nunca se confundem. A única relação inativa é a segunda data, ativada apenas
dentro de medidas.

Validação automática (`make powerbi`, 122 verificações): chaves únicas e não nulas (14 tabelas);
**0 órfãos** nas 11 relações; cada dimensão tem exatamente as chaves distintas do fato (sem
*fan-out*); *join* com todas as dimensões ativas preserva 73.046 linhas e R$ 125.440.636,13;
cobertura de 100% em cada coluna enriquecida; `fato_registro_aih.csv` byte a byte idêntico à
exportação anterior; medidas equivalentes iguais aos indicadores validados; curva de Lorenz igual
à do relatório de análise.

## AIHs repetidas e longa permanência

- 56 registros excedentes em 50 números de AIH (106 registros); 46 desses números têm registros de
  tipo 1 **e** 5. Não são duplicatas (0 linhas idênticas): são apresentações sucessivas.
- Nada é removido. `aih_ocorrencias` / `aih_repetida` sinalizam; `[AIHs distintas]` conta números.
- Somar valores por registro é correto (cada registro é uma cobrança); contar "internações" por
  registro **não** é.

## Interpretação dos códigos

Cada dimensão de código tem duas descrições: `descricao` (fonte **secundária**, `microdatasus`, ou
conhecimento prévio — coluna `fonte`) e `descricao_oficial` (tabela de conversão do pacote oficial
do SIH/SUS para o TabWin — coluna `fonte_oficial`). **Os visuais usam a oficial**; a secundária é
mantida para rastrear a comparação (`reports/reference/enriquecimento.md`, decisão D-036). `ESPEC`
10, 14 e 87, sem rótulo na fonte secundária, têm rótulo oficial.
