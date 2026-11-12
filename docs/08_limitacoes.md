# 8. Limitações

Este documento reúne o que os resultados **não** permitem afirmar. Cada etapa traz também as limitações
específicas do seu procedimento.

## Unidade de análise

- O arquivo RD registra **AIHs**, não pacientes nem internações. Não há identificador de paciente, e uma
  internação de longa permanência gera vários registros. Reinternações, pacientes distintos e episódios
  completos de cuidado não são mensuráveis com esta base.
- Todas as taxas usam o registro de AIH como denominador.

## Período

- Há uma única competência, 2024-01, que é o mês de **processamento**. As saídas vão de 2023-08 a 2024-01
  e cada mês contém apenas o que foi apresentado nessa competência: a contagem por mês não é série
  histórica nem produção mensal.
- O DATASUS pode republicar o arquivo. Os resultados valem para a versão com SHA-256
  `a3f0ea9a…0d7dfc9c`, com cabeçalho atualizado em 2025-02-08.

## Interpretação

- Mortalidade e demais taxas são **brutas**, sem ajuste por idade, gravidade ou perfil de casos.
  Diferenças entre grupos ou estabelecimentos refletem a composição dos atendimentos e não medem
  qualidade assistencial. Nenhuma relação causal é sugerida.
- Na longa permanência, `DIAS_PERM` mede o período coberto pelo registro, não a duração da internação:
  a permanência deve ser lida por tipo de AIH.
- A semântica de alguns campos não tem documento primário: `DIAS_PERM` na longa permanência e a
  composição de `VAL_TOT` em 342 registros (P-009, parcial). Os rótulos dos códigos foram confirmados
  pelas tabelas oficiais do TabWin.

## Reconstrução do histórico

- O código original foi perdido. Dois indicadores históricos não foram reproduzidos: a mortalidade de
  6,38% (o valor correto é 6,39%) e a concentração de 58,20% nos 10% maiores registros, cujo critério
  não foi recuperado (P-004). Não use 58,20%.
- A idade média histórica de 43,96 anos usa um critério incorreto; a corrigida é 43,85.

## Referências oficiais

- O nome dos estabelecimentos vem do cadastro CNES de 2026-10, não de 2024-01, e pode ter mudado desde a
  competência. Três nomes ocupam todo o campo de 60 caracteres e podem estar truncados.
- A data da consulta ao IBGE é o carimbo do arquivo salvo. Municípios fora do RJ (170) têm apenas o IBGE
  como fonte de nome.
- Textos oficiais são reproduzidos literalmente, com abreviações e grafias originais.

## Dashboard e publicação

- O projeto Power BI ainda não foi aberto no Power BI Desktop: não há validação visual.
- Os dados permitem identificar combinações raras de atributos. Um `.pbix` com dados importados não deve
  ser publicado sem a avaliação de privacidade de [`04_modelagem.md`](04_modelagem.md) (P-013).
- A licença do projeto ainda não foi definida; a dependência `pyreaddbc` é AGPL-3.0 (P-007).
