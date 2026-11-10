# Plano do dashboard (Power BI)

Status: **planejado** — o `.pbix` e as visualizações ainda não foram construídos.
Todas as páginas trazem no rodapé: *Fonte: SIH/SUS (DATASUS), RD RJ, competência 2024-01. Unidade:
registro de AIH (não paciente). Rótulos de códigos: fonte secundária.*

Filtros globais (painel lateral, sincronizados): tipo de AIH, especialidade, caráter, complexidade,
faixa etária, sexo. Mês de saída como filtro de intervalo, com aviso de que não é série histórica.

## 1. Visão geral
- **Cartões:** Registros de AIH · AIHs distintas · Valor total · Valor médio por registro ·
  Permanência média (dias) · Mortalidade hospitalar (razão, formato %).
- Barras: registros por tipo de AIH (com rótulo "longa permanência" para o tipo 5).
- Colunas: registros por mês de saída (`dim_mes`) + nota "competência 2024-01: não é série histórica".
- Barras: valor por complexidade.

## 2. Perfil dos registros
- Pirâmide (barras divergentes) faixa etária × sexo — `dim_perfil_demografico`.
- Barras: % dos registros por raça/cor (incluindo "sem informação").
- Cartão: idade média (anos) — corrigida.
- Título explícito: "perfil dos **registros**" (não há identificação de pacientes).

## 3. Internações e permanência
- Barras: registros e permanência média por especialidade (`dim_especialidade`, com coluna fonte).
- Barras: caráter (eletivo × urgência) e complexidade.
- Tabela: top 15 procedimentos por registros (código; nome pendente — SIGTAP).
- Histograma de `dias_permanencia` **separado por tipo de AIH** + caixa de texto sobre
  `DIAS_PERM` na longa permanência.

## 4. Mortalidade hospitalar
- Barras: mortalidade (razão, %) por faixa etária, especialidade, caráter e grupo SIGTAP, sempre
  com o número de registros (denominador) no tooltip.
- Nota fixa: taxa **bruta**, sem ajuste de risco; diferenças refletem casemix e não qualidade
  assistencial; sem leitura causal.

## 5. Análise financeira
- Cartão: concentração do valor — top 10% (57,74%), com nota de que a referência histórica (58,20%)
  não foi reproduzida.
- Curva de Lorenz (linha; eixo X = % acumulado de registros) — exige uma tabela auxiliar de
  percentis ou um visual de dispersão sobre o fato ordenado (a definir na construção).
- Barras: % do valor por grupo SIGTAP, complexidade, especialidade; top 10 estabelecimentos (código
  CNES; nome pendente).

## 6. Qualidade dos dados
- Tabela `qualidade_campos`: % de vazios, distintos, exportado/motivo.
- Cartões: registros excedentes de AIH (56), registros de AIH repetida, registros com valor zero
  (241 = `ESPEC` 87).
- Tabela `ref_indicadores_validados`: histórico × reproduzido × status (inclui mortalidade 🟠 e
  concentração 🔴).
- Texto: fonte dos rótulos (secundária) e pendências de enriquecimento.

## Distribuição geográfica
Barras por **código** de município de residência (`dim_municipio_residencia`) e do estabelecimento
(atributo de `dim_estabelecimento`). **Mapa só após** integrar a tabela oficial do IBGE
(ver [`fontes_referencia.md`](fontes_referencia.md)); não geocodificar códigos sem nome verificado.

## Pendências para a construção
1. Enriquecimento oficial (IBGE, CNES, SIGTAP, CID-10) — investigação em andamento.
2. Tabela auxiliar para a curva de Lorenz.
3. Tema visual (cores acessíveis; o mesmo par azul/laranja dos gráficos do pipeline para sexo).
4. Verificar no Power BI os valores das medidas contra `ref_indicadores_validados`.
5. Decisão sobre publicação do `.pbix` (ver `privacidade.md`).
