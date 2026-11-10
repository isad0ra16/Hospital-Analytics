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
 dim_especialidade ─────────────▶ │  1 linha = 1 registro│ ◀─ tipo_aih_cod ── dim_tipo_aih
 dim_carater ───────────────────▶ │  de AIH (73.046)     │ ◀─ complexidade_cod ── dim_complexidade
                                  └──────────────────────┘

 Tabelas auxiliares, sem relacionamento: ref_indicadores_validados · qualidade_campos
```

| Tabela | Granularidade | Linhas | Chave |
|---|---|---:|---|
| `fato_registro_aih` | registro de AIH | 73.046 | `registro_id` |
| `dim_mes` | mês (anos 2012–2024 completos) | 156 | `mes` |
| `dim_estabelecimento` | CNES | 240 | `cnes` |
| `dim_municipio_residencia` | município de residência | 262 | `municipio_residencia_cod` |
| `dim_procedimento` | procedimento SIGTAP realizado | 1.094 | `procedimento_cod` |
| `dim_especialidade` · `dim_carater` · `dim_complexidade` · `dim_tipo_aih` | código | 12 · 4 · 2 · 2 | `*_cod` |
| `dim_perfil_demografico` | faixa etária × sexo × raça/cor | 78 | `perfil_id` |
| `ref_indicadores_validados` | indicador reconciliado | 26 | `indicador_id` |
| `qualidade_campos` | campo original do RD | 113 | `campo` |

## Relacionamentos

Todos **muitos-para-um**, direção de filtro **única** (dimensão → fato), sem relação bidirecional.

| Fato | Dimensão | Ativo |
|---|---|---|
| `mes_saida` | `dim_mes[mes]` | sim |
| `mes_internacao` | `dim_mes[mes]` | **não** — usar `USERELATIONSHIP` (medida `Registros por mês de internação`) |
| `cnes` | `dim_estabelecimento[cnes]` | sim |
| `municipio_residencia_cod` | `dim_municipio_residencia[...]` | sim |
| `procedimento_cod` | `dim_procedimento[procedimento_cod]` | sim |
| `especialidade_cod`, `carater_cod`, `complexidade_cod`, `tipo_aih_cod` | dimensões de código | sim |
| `perfil_id` | `dim_perfil_demografico[perfil_id]` | sim |

**Sem ambiguidade de caminhos:** o município do **estabelecimento** é um atributo de
`dim_estabelecimento` (`municipio_estabelecimento_cod`) e **não** se relaciona com
`dim_municipio_residencia`. Assim há um único caminho de filtro para cada dimensão, e residência e
estabelecimento nunca se confundem. A única relação inativa é a segunda data, ativada apenas
dentro de medidas.

Validação automática (`make powerbi`, 64 verificações): chaves únicas e não nulas; **0 órfãos** nas
10 relações; *join* com todas as dimensões ativas preserva 73.046 linhas e R$ 125.440.636,13;
medidas equivalentes recalculadas sobre os CSV iguais aos indicadores validados.

## AIHs repetidas e longa permanência

- 56 registros excedentes em 50 números de AIH (106 registros); 46 desses números têm registros de
  tipo 1 **e** 5. Não são duplicatas (0 linhas idênticas): são apresentações sucessivas.
- Nada é removido. `aih_ocorrencias` / `aih_repetida` sinalizam; `[AIHs distintas]` conta números.
- Somar valores por registro é correto (cada registro é uma cobrança); contar "internações" por
  registro **não** é.

## Interpretação dos códigos

Rótulos das dimensões de código vêm de fonte **secundária** (`microdatasus`) ou de conhecimento
prévio não verificado — a coluna `fonte` de cada dimensão declara qual. Códigos sem rótulo
(`ESPEC` 10, 14, 87) aparecem com descrição vazia e `fonte = "sem rótulo na fonte disponível"`.
Nomes de municípios, estabelecimentos, procedimentos e diagnósticos dependem de tabelas oficiais
ainda não integradas (ver [`fontes_referencia.md`](fontes_referencia.md)).
