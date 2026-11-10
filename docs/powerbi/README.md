# Camada analítica para Power BI

| Documento | Conteúdo |
|---|---|
| [`modelo.md`](modelo.md) | conceitos (registro × AIH × internação × paciente), esquema estrela, granularidade, relacionamentos |
| [`dicionario_campos.md`](dicionario_campos.md) | todos os campos, tipos, origem e nulos (gerado) |
| [`medidas.dax`](medidas.dax) | medidas DAX com denominadores, filtros, formato e limitações |
| [`consultas_power_query.pq`](consultas_power_query.pq) | consultas M com tipos explícitos (gerado) |
| [`paginas.md`](paginas.md) | plano das páginas do dashboard |
| [`privacidade.md`](privacidade.md) | exclusões e avaliação de risco de reidentificação |
| [`fontes_referencia.md`](fontes_referencia.md) | fontes oficiais para nomes (IBGE, CNES, SIGTAP, CID-10) |

## Gerar os arquivos

```bash
make powerbi          # data/powerbi/*.csv + validação (64 verificações)
```
```bash
uv run hospital-analytics powerbi --parquet   # também gera .parquet
```

Pré-requisito: camada tratada gerada (`make fetch-data && make pipeline`). Resumo reproduzível
(linhas e SHA-256 de cada CSV): `reports/powerbi/export_summary.json`.

**Formato dos CSV:** UTF-8, separador `,`, cabeçalho na 1ª linha, decimal com **ponto**, datas ISO
`AAAA-MM-DD` (mês = 1º dia do mês), nulo = campo vazio, booleanos como `0`/`1`. Códigos (`01`,
`0408060352`) são **texto** — preservam zeros à esquerda.

## Importar no Power BI Desktop

1. **Página Inicial → Transformar dados → Gerenciar parâmetros → Novo parâmetro:** `PastaDados`,
   tipo Texto, valor = caminho completo da pasta `data/powerbi\` (com a barra final).
2. Para cada tabela: **Nova fonte → Consulta em branco → Editor avançado**, cole o bloco
   correspondente de [`consultas_power_query.pq`](consultas_power_query.pq) e nomeie a consulta com o
   nome da tabela. Os blocos já declaram `Encoding = 65001` (UTF-8), os tipos de cada coluna e a
   cultura `en-US` (ponto decimal). **Não** use a detecção automática de tipos: ela converteria
   códigos em números e apagaria zeros à esquerda.
3. **Fechar e aplicar.** Em **Modelo**, crie os relacionamentos da tabela em
   [`modelo.md`](modelo.md#relacionamentos): todos *muitos-para-um*, filtro em **direção única**;
   `mes_internacao → dim_mes[mes]` **inativo**. Desative a "Detecção automática de relações" se ela
   criar ligações extras.
4. Marque `dim_mes` como **tabela de datas** (coluna `mes`).
5. Crie uma tabela `_Medidas` (Inserir dados → tabela vazia) e cole as medidas de
   [`medidas.dax`](medidas.dax). Formatos: moeda para valores; **porcentagem** para
   `Mortalidade hospitalar (razão)`, `% dos registros`, `% do valor` e a concentração.
6. Ordene `dim_perfil_demografico[faixa_etaria]` por `faixa_etaria_ordem` e `dim_mes[ano_mes]` por
   `ano_mes_ordem`.
7. **Conferência:** um cartão com cada medida na base completa deve mostrar os valores de
   referência listados no topo de `medidas.dax` (também em `ref_indicadores_validados`).

## Validação automatizada

`make powerbi` termina com `RESULT: ALL CHECKS PASSED (64 checks)` quando: chaves únicas e não
nulas (12 tabelas); 0 órfãos nos 10 relacionamentos; join preserva linhas e valor; centavos e
decimais concordam linha a linha; contagens e somas iguais ao pipeline; medidas equivalentes iguais
aos indicadores validados. Testes unitários (dados sintéticos): `tests/test_powerbi.py`.
