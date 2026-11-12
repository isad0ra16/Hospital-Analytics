# Camada analítica e dashboard Power BI

| Documento | Conteúdo |
|---|---|
| [`modelo.md`](modelo.md) | conceitos (registro × AIH × internação × paciente), esquema estrela, nomes oficiais, relacionamentos |
| [`dicionario_campos.md`](dicionario_campos.md) | todos os campos, tipos, origem e nulos (gerado) |
| [`medidas.dax`](medidas.dax) | medidas DAX com denominadores, filtros, formato e limitações (fonte das medidas do projeto) |
| [`consultas_power_query.pq`](consultas_power_query.pq) | consultas M com tipos explícitos (gerado) |
| [`paginas.md`](paginas.md) | as 6 páginas do dashboard: conteúdo, leitura e conferência |
| [`privacidade.md`](privacidade.md) | exclusões e avaliação de risco de reidentificação |
| [`fontes_referencia.md`](fontes_referencia.md) · [`diagnostico_referencias.md`](diagnostico_referencias.md) | fontes oficiais e diagnóstico antes da integração |
| [`../../powerbi/`](../../powerbi/) | **projeto Power BI (PBIP)**: modelo TMDL + relatório PBIR (gerado) |

## Gerar os arquivos

```bash
make powerbi   # data/powerbi/*.csv + validação (122 verificações) + relatórios de enriquecimento
```

```bash
make pbip      # powerbi/HospitalAnalytics.pbip (modelo TMDL + 6 páginas PBIR)
```

Pré-requisitos: camada tratada (`make fetch-data && make pipeline`) e os arquivos oficiais de referência
em `data/reference/incoming/` (conferidos por tamanho e SHA-256 antes da leitura). Resumo reproduzível:
`reports/powerbi/export_summary.json`; valores exatos das medidas: `reports/powerbi/medidas_referencia.json`.

**Formato dos CSV:** UTF-8, separador `,`, cabeçalho, decimal com **ponto**, datas ISO `AAAA-MM-DD`
(mês = 1º dia do mês), nulo = campo vazio, booleanos `0`/`1`. Códigos (`01`, `0408060352`) são **texto**.

## Abrir o projeto no Power BI Desktop

> **Estado:** o projeto foi gerado e validado fora do Power BI (esquemas JSON oficiais da Microsoft,
> referências de campos, equivalência das medidas em SQL). **Ainda não foi aberto no Power BI Desktop**,
> que não estava disponível no ambiente de construção. Os passos abaixo concluem e conferem o dashboard.

1. Instale o **Power BI Desktop** (versão recente; o projeto usa os formatos PBIR e TMDL).
   Em **Arquivo → Opções → Recursos em versão prévia**, ative *Formato de projeto do Power BI (.pbip)*,
   *Armazenar relatórios usando o formato PBIR* e *Formato TMDL do modelo semântico*, se ainda aparecerem
   como versão prévia.
2. Gere os dados (`make powerbi`) e abra `powerbi/HospitalAnalytics.pbip`.
3. **Transformar dados → Editar parâmetros → `PastaDados`:** informe o caminho completo da pasta
   `data/powerbi\` deste repositório (terminado em `\`). Aplique e clique em **Atualizar**.
4. **Conferência obrigatória** (página 1 e cartões das demais): os valores devem ser iguais aos de
   `reports/powerbi/medidas_referencia.json` — 73.046 registros, 72.990 AIHs distintas,
   R$ 125.440.636,13, R$ 1.717,28, 6,12 dias, 6,39%, 43,85 anos, 57,74%, 69,27% de urgência.
   Divergência = problema no projeto, não nos dados: não ajuste valores.
5. Revise cada página (posição, rótulos, cores). Ajustes visuais feitos no Desktop ficam em
   `powerbi/HospitalAnalytics.Report/` — para mantê-los, transfira-os para `PAGES` em
   `src/hospital_analytics/pbip.py` (o comando `make pbip` regenera a pasta a partir do código).
6. Salve capturas das 6 páginas em `docs/powerbi/capturas/` para o README.

**Se o Desktop recusar o relatório** (ex.: versão de esquema mais nova que a instalada), o modelo
continua utilizável: abra o `.pbip`, ou crie um relatório novo conectado ao modelo, e monte as páginas
de [`paginas.md`](paginas.md), que descreve cada visual com os mesmos campos e medidas. Relate o erro
exibido para corrigir o gerador.

**Publicação:** o `.pbix`/`.pbip` com dados importados **incorpora os registros**. Antes de publicar,
siga a avaliação de [`privacidade.md`](privacidade.md) (P-013).

## Validação automatizada

`make powerbi` termina com `RESULT: ALL CHECKS PASSED (122 checks)` quando: chaves únicas e não nulas
(14 tabelas); 0 órfãos nos 11 relacionamentos; cada dimensão tem exatamente as chaves distintas do fato;
*join* preserva linhas e valor; centavos e decimais concordam linha a linha; contagens e somas iguais ao
pipeline; cobertura de 100% das colunas com nomes oficiais; fato byte a byte idêntico à exportação
anterior; medidas equivalentes iguais aos indicadores validados; curva de Lorenz igual à do relatório de
análise. Testes (dados sintéticos): `tests/test_powerbi.py`, `tests/test_enrichment.py`,
`tests/test_pbip.py` (esquemas oficiais em `tests/fixtures/powerbi_schemas/`, licença MIT).

### Validação opcional do TMDL com a biblioteca oficial

O TMDL não tem esquema JSON. A biblioteca TOM da Microsoft (`Microsoft.AnalysisServices.retail.amd64`,
NuGet) desserializa a pasta e acusa qualquer erro de sintaxe ou de objeto. No Windows PowerShell, após
extrair o pacote em uma pasta `tom`:

```powershell
Add-Type -Path tom\lib\net45\Microsoft.AnalysisServices.Core.dll, tom\lib\net45\Microsoft.AnalysisServices.Tabular.Json.dll, tom\lib\net45\Microsoft.AnalysisServices.Tabular.dll
[Microsoft.AnalysisServices.Tabular.TmdlSerializer]::DeserializeDatabaseFromFolder("$PWD\powerbi\HospitalAnalytics.SemanticModel\definition").Model.Tables.Count   # esperado: 15
```

Esta verificação **não foi executada** na construção (execução de bibliotecas externas não autorizada no
ambiente); o Power BI Desktop faz a mesma desserialização ao abrir o projeto.
