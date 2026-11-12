# 7. Dashboard Power BI

## Objetivo

Apresentar os indicadores de forma navegável para quem não vai ler código ou relatórios, sem perder as
ressalvas metodológicas: cada página informa a unidade de análise, a fonte e os limites da leitura.

## Situação

O dashboard existe como **projeto Power BI em formato de texto (PBIP)**, em
[`powerbi/HospitalAnalytics.pbip`](../powerbi/HospitalAnalytics.pbip), gerado por
`hospital-analytics pbip`. Ele foi validado fora do Power BI (ver [Verificações](#verificações)), mas
**ainda não foi aberto no Power BI Desktop**, que não estava disponível no ambiente de construção.
Portanto, não há validação visual nem capturas de tela: posição, legibilidade e aparência dos visuais
precisam ser conferidas no aplicativo.

O projeto não contém dados. Ao atualizar o modelo, o Power BI importa os CSV de `data/powerbi/`
indicados pelo parâmetro `PastaDados`.

## Conteúdo

**Modelo semântico** (TMDL), gerado do mesmo esquema que exporta os dados
([`04_modelagem.md`](04_modelagem.md)): 15 tabelas, incluindo a tabela de medidas; 11 relacionamentos,
um deles inativo e usado por `USERELATIONSHIP`; as 31 medidas de
[`medidas.dax`](powerbi/medidas.dax), com formato e pasta; colunas técnicas do fato ocultas; `dim_mes`
marcada como tabela de datas; ordenações de faixa etária, mês e capítulo da CID-10.

**Relatório** (PBIR), com seis páginas e segmentações sincronizadas entre elas (tipo de AIH, caráter,
complexidade, faixa etária e sexo):

| Página | Conteúdo |
| --- | --- |
| 1. Visão geral | seis indicadores-chave, registros por tipo de AIH e por mês de saída (com o aviso de que não é série histórica), valor por complexidade e um guia de leitura |
| 2. Perfil e origem | pirâmide etária dos registros, raça/cor, idade média, residentes de outro município ou estado, dez principais municípios de residência |
| 3. Internações e permanência | especialidade do leito, caráter, permanência geral e na AIH principal, tabela de procedimentos SIGTAP |
| 4. Mortalidade hospitalar | taxa bruta por faixa etária, caráter, capítulo da CID-10 e principais diagnósticos, com aviso fixo sobre a ausência de ajuste de risco |
| 5. Análise financeira | concentração do valor, curva de Lorenz, grupos SIGTAP, dez estabelecimentos de maior valor, esfera jurídica |
| 6. Qualidade e metodologia | reconciliação com o histórico, completude dos 113 campos, AIHs repetidas, fontes e limitações |

O detalhamento de cada visual, com campos, medidas e ordenação, está em
[`paginas.md`](powerbi/paginas.md), gerado do mesmo código que o relatório.

## Verificações

| Verificação | Como |
| --- | --- |
| Todos os arquivos JSON do relatório seguem os esquemas oficiais da Microsoft | `tests/test_pbip.py`, com os esquemas em `tests/fixtures/powerbi_schemas/` (licença MIT) |
| Cada campo e cada medida usados nos visuais existem no modelo | `tests/test_pbip.py` |
| Tabelas, colunas e relacionamentos do TMDL correspondem ao esquema exportado | `tests/test_pbip.py` |
| O projeto versionado é idêntico ao que o gerador produz | `tests/test_pbip.py` |
| Cada medida DAX tem um equivalente em SQL igual aos indicadores reconciliados | `hospital-analytics powerbi`; valores em [`medidas_referencia.json`](../reports/powerbi/medidas_referencia.json) |

O TMDL não tem esquema JSON público; sua sintaxe é validada pelo Power BI Desktop ao abrir o projeto.

## Abrir o projeto no Power BI Desktop

1. Instale uma versão recente do Power BI Desktop. Se os formatos PBIP, PBIR e TMDL ainda aparecerem em
   **Arquivo → Opções → Recursos em versão prévia**, ative os três.
2. Gere os dados com `uv run hospital-analytics powerbi` e abra `powerbi/HospitalAnalytics.pbip`.
3. Em **Transformar dados → Editar parâmetros**, informe em `PastaDados` o caminho completo da pasta
   `data\powerbi\` deste repositório, terminado em `\`. Aplique e clique em **Atualizar**.
4. Confira os cartões com `reports/powerbi/medidas_referencia.json`: 73.046 registros, 72.990 AIHs
   distintas, R$ 125.440.636,13, R$ 1.717,28 por registro, 6,12 dias, mortalidade de 6,39%, idade média
   de 43,85 anos, 57,74% do valor nos 10% maiores registros e 69,27% de urgência. Uma divergência indica
   problema no projeto, não nos dados.
5. Revise cada página. Para manter ajustes visuais, transfira-os para `PAGES` em
   `src/hospital_analytics/pbip.py`: `hospital-analytics pbip` regenera a pasta a partir do código.
6. Salve capturas das seis páginas para a documentação.

Se o Desktop recusar o relatório (por exemplo, por uma versão de esquema mais nova que a instalada), o
modelo continua utilizável: crie um relatório sobre ele e monte as páginas seguindo
[`paginas.md`](powerbi/paginas.md).

## Publicação

Um `.pbix` com dados importados incorpora os registros. Antes de publicá-lo, siga a avaliação de risco
de reidentificação em [`04_modelagem.md`](04_modelagem.md#privacidade-e-risco-de-reidentificação)
(pendência P-013). Arquivos `.pbix` e caches locais do Power BI são ignorados pelo Git.

## Limitações

- Sem validação visual: nenhuma afirmação sobre a aparência do dashboard foi verificada.
- A curva de Lorenz é estática (base completa) e não responde às segmentações.
- As medidas foram conferidas por equivalentes em SQL, não executadas no motor do Power BI.
