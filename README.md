# Hospital Analytics

Análise das internações hospitalares do SUS no estado do Rio de Janeiro a partir dos microdados públicos
do SIH/SUS. O projeto cobre o caminho completo: download e conferência do arquivo oficial, conversão sem
perda, tratamento, auditoria de qualidade, reconciliação com indicadores históricos, enriquecimento com
tabelas oficiais, modelo dimensional e um dashboard Power BI.

O foco é a confiabilidade: cada número pode ser reproduzido a partir do arquivo público, e cada
interpretação indica a fonte que a sustenta.

## Problema e objetivos

O projeto original, com notebook, scripts e dados tratados, foi perdido junto com o computador em que
estava. Restaram apenas os valores dos indicadores calculados na época. Os objetivos desta reconstrução
são:

1. recuperar a base exata e provar que ela não foi alterada em nenhuma etapa;
2. reproduzir os indicadores históricos e explicar cada divergência, sem ajustar dados para obter os
   valores esperados;
3. descrever o perfil das internações com indicadores bem definidos e unidades de análise explícitas;
4. entregar um modelo analítico e um dashboard que preservem as ressalvas metodológicas.

## Dados

| Item | Descrição |
| --- | --- |
| Fonte | SIH/SUS (DATASUS), arquivo RD — *AIH Reduzida* |
| Recorte | Rio de Janeiro, competência janeiro de 2024 (`RDRJ2401.dbc`) |
| Volume | 73.046 registros de AIH, 113 campos, R$ 125.440.636,13 aprovados |
| Período das saídas | agosto de 2023 a janeiro de 2024 |
| Referências oficiais | SIGTAP 2024-01, IBGE (municípios), CNES (estabelecimentos), tabelas do SIH para o TabWin |

A competência é o mês de **processamento**, não o de ocorrência: 40% das saídas são de 2023. A versão
usada é identificada pelo SHA-256 `a3f0ea9a…0d7dfc9c`. Origem e conferência de cada arquivo:
[`docs/01_fontes_de_dados.md`](docs/01_fontes_de_dados.md).

## Metodologia

- **Dados brutos imutáveis.** O arquivo oficial é convertido para Parquet como texto, sem tratamento, e
  impressões digitais comprovam que nenhum valor ou byte mudou.
- **Nada é removido.** AIHs com número repetido (56 registros excedentes) são sinalizadas, não excluídas;
  filtros são explícitos em cada indicador.
- **Valores exatos.** Dinheiro em centavos inteiros e `Decimal`; Pandas e DuckDB calculam os mesmos
  agregados de forma independente e precisam concordar.
- **Interpretação com fonte declarada.** Cada código traz a origem do seu rótulo; o modelo usa os rótulos
  oficiais do SIH e mantém a fonte secundária ao lado para comparação.
- **Enriquecimento por código exato.** Tabelas oficiais conferidas por SHA-256 antes da leitura, chaves
  únicas e cobertura verificada; as dimensões só ganham colunas, e a tabela fato permanece idêntica byte
  a byte.
- **Unidade de análise explícita.** Todas as taxas são por registro de AIH: a base não identifica
  pacientes e não permite reconstruir internações.

As decisões estão registradas, com contexto e alternativas, em
[`docs/decisoes_metodologicas.md`](docs/decisoes_metodologicas.md).

## Arquitetura

```text
RDRJ2401.dbc (DATASUS)
  │ convert            .dbc → .dbf → Parquet, 113 colunas de texto, CP850
  ▼
data/raw/RDRJ2401.parquet                 validate: contagens, VAL_TOT, impressões digitais
  │ build-processed    originais intactos + 50 colunas derivadas reversíveis
  ▼
data/processed/sih_rj_2024_01_tratado.parquet
  ├─ audit             → reports/audit/        qualidade dos dados
  ├─ indicators        → reports/indicators/   reconciliação, Pandas × DuckDB
  ├─ analysis          → reports/analysis/     análise exploratória e gráficos
  └─ powerbi           → data/powerbi/         esquema estrela + nomes oficiais (SIGTAP, IBGE, CNES, TabWin)
                           └─ pbip → powerbi/HospitalAnalytics.pbip
```

| Pasta | Conteúdo |
| --- | --- |
| `src/hospital_analytics/` | pacote Python com o pipeline e a CLI `hospital-analytics` |
| `sql/` | consultas DuckDB versionadas (auditoria, indicadores, análises, modelo) |
| `config/params.yaml` | parâmetros, valores históricos e proveniência das referências oficiais |
| `reports/` | relatórios gerados (JSON e Markdown) e gráficos |
| `powerbi/` | projeto Power BI gerado (modelo TMDL e relatório PBIR) |
| `docs/` | documentação por etapa |
| `tests/` | testes automatizados com dados sintéticos |
| `data/` | dados locais, fora do Git ([`data/README.md`](data/README.md)) |

## Tecnologias

Python 3.13 · pandas · PyArrow e Parquet · DuckDB · pyreaddbc e dbfread (leitura do formato DATASUS) ·
matplotlib · Power BI (TMDL, PBIR, DAX, Power Query M) · pytest · ruff · uv.

## Resultados validados

Indicadores da base completa, conferidos contra o histórico e entre duas implementações independentes:

| Indicador | Valor | Situação |
| --- | ---: | --- |
| Registros de AIH | 73.046 | igual ao histórico |
| Valor total aprovado | R$ 125.440.636,13 | igual ao histórico, ao centavo |
| Valor médio por registro | R$ 1.717,28 | igual ao histórico |
| Permanência média (`DIAS_PERM`) | 6,12 dias (tipo 1: 5,93; tipo 5: 27,90) | igual; critério identificado |
| Óbitos | 4.664 | igual; critério identificado |
| Mortalidade hospitalar bruta | 6,39% | histórico registrava 6,38%, explicável só por truncamento |
| Idade média | 43,85 anos | o histórico (43,96) ignorava a unidade da idade |
| Valor dos 10% maiores registros | 57,74% | histórico de 58,20% não reproduzido |

Das 24 referências históricas comparadas, 22 foram reproduzidas exatamente. A reconciliação completa e
os achados estão em [`docs/05_validacao.md`](docs/05_validacao.md).

Destaques descritivos do modelo enriquecido:

- Gravidez, parto e puerpério é o capítulo da CID-10 mais frequente, com 16,5% dos registros; o
  procedimento mais registrado é o parto normal (4.250 registros).
- 69,3% dos registros são de urgência, e em 22,4% o paciente reside em município diferente do
  estabelecimento.
- Hospitais da administração pública municipal concentram 38,9% do valor; os 10 estabelecimentos de
  maior valor somam 30,9% do total.
- A mortalidade bruta é maior nas doenças infecciosas (20,8%) e respiratórias (16,4%). São taxas sem
  ajuste de risco, que refletem o perfil dos casos e não a qualidade do cuidado.

![Registros por faixa etária e sexo](reports/analysis/figures/age_pyramid.png)

A análise exploratória completa, com perfil demográfico, hospitalar, mortalidade, valores e permanência,
está em [`docs/06_analise_exploratoria.md`](docs/06_analise_exploratoria.md).

## Dashboard Power BI

O projeto em [`powerbi/`](powerbi/) tem seis páginas: visão geral, perfil e origem, internações e
permanência, mortalidade hospitalar, análise financeira e qualidade e metodologia. O modelo semântico
traz 15 tabelas, 11 relacionamentos e 31 medidas DAX documentadas.

Os arquivos do relatório foram validados contra os esquemas oficiais da Microsoft, e cada medida tem um
equivalente em SQL conferido sobre os dados exportados. O projeto **ainda não foi aberto no Power BI
Desktop**, portanto não há validação visual nem capturas de tela. Conteúdo das páginas e passos para
abrir e conferir: [`docs/07_dashboard.md`](docs/07_dashboard.md).

## Qualidade e validação

- 0 registros duplicados, 0 datas inválidas e 0 valores monetários malformados nos 73.046 registros.
- 122 verificações do modelo analítico: chaves únicas, nenhum registro órfão nos 11 relacionamentos,
  totais preservados, 100% de cobertura dos nomes oficiais e tabela fato idêntica à exportação anterior.
- O pipeline executado a partir de um *checkout* limpo no Windows gerou Parquets, relatórios e CSV
  idênticos, byte a byte, aos produzidos no Linux.
- A suíte de testes usa apenas dados sintéticos e cobre leitura do formato DATASUS, conversão,
  indicadores, enriquecimento, projeto Power BI, higiene do repositório e links da documentação.

## Limitações

- A unidade é o registro de AIH: não há como contar pacientes nem internações completas.
- Uma única competência não forma série histórica.
- As taxas são brutas e não permitem comparar o desempenho de hospitais ou grupos.
- Os nomes dos estabelecimentos vêm do cadastro CNES de 2026-10, não de 2024-01.

Lista completa: [`docs/08_limitacoes.md`](docs/08_limitacoes.md).

## Como executar

Requisitos: [uv](https://docs.astral.sh/uv/), que instala o Python 3.13 e as dependências fixadas no
`uv.lock`. Os comandos abaixo funcionam no Windows (PowerShell) e no Linux.

```bash
uv sync --locked
```

Coloque os arquivos de entrada nas pastas indicadas em [`data/README.md`](data/README.md): o
`RDRJ2401.dbc`, disponível na Release `data-rdrj2401` deste repositório, em `data/raw/`; as tabelas
oficiais de referência em `data/reference/incoming/`. Depois confira a integridade:

```bash
uv run hospital-analytics verify
```

Execute o pipeline na ordem:

```bash
uv run hospital-analytics convert
uv run hospital-analytics validate
uv run hospital-analytics build-processed
uv run hospital-analytics audit
uv run hospital-analytics indicators
uv run hospital-analytics analysis
uv run hospital-analytics powerbi
uv run hospital-analytics pbip
```

Testes e verificação de estilo:

```bash
uv run pytest
uv run ruff check .
```

Em sistemas com `make`, o [`Makefile`](Makefile) oferece os mesmos passos como atalhos (`make pipeline`,
`make check`).

## Documentação

| Etapa | Documento |
| --- | --- |
| 1. Fontes de dados | [`01_fontes_de_dados.md`](docs/01_fontes_de_dados.md) |
| 2. Ingestão | [`02_ingestao.md`](docs/02_ingestao.md) |
| 3. Tratamento e dicionário de variáveis | [`03_tratamento.md`](docs/03_tratamento.md) |
| 4. Modelagem e enriquecimento | [`04_modelagem.md`](docs/04_modelagem.md) |
| 5. Validação | [`05_validacao.md`](docs/05_validacao.md) |
| 6. Análise exploratória | [`06_analise_exploratoria.md`](docs/06_analise_exploratoria.md) |
| 7. Dashboard | [`07_dashboard.md`](docs/07_dashboard.md) |
| 8. Limitações | [`08_limitacoes.md`](docs/08_limitacoes.md) |
| Decisões metodológicas | [`decisoes_metodologicas.md`](docs/decisoes_metodologicas.md) |

Anexos técnicos do modelo, gerados pelo pipeline, em [`docs/powerbi/`](docs/powerbi/): dicionário de
campos, consultas Power Query, medidas DAX e guia das páginas.

## Autoria

Isadora Veiga — projeto de portfólio em engenharia e análise de dados aplicadas à saúde.
