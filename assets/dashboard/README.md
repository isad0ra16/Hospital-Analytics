# Capturas do dashboard

Esta pasta recebe as capturas **reais** das seis páginas da versão final do dashboard, exportadas do
Power BI Desktop. Nenhuma imagem simulada ou de versão antiga deve ser colocada aqui.

| Arquivo | Página |
| --- | --- |
| `01-visao-geral.png` | 1. Visão geral |
| `02-perfil-e-origem.png` | 2. Perfil e origem |
| `03-internacoes-e-permanencia.png` | 3. Internações e permanência |
| `04-mortalidade.png` | 4. Mortalidade hospitalar |
| `05-analise-financeira.png` | 5. Análise financeira |
| `06-qualidade-e-metodologia.png` | 6. Qualidade e metodologia |

## Como exportar

1. Abra a versão final do relatório no Power BI Desktop, com os dados atualizados e **sem filtros ou
   segmentações aplicados**, para que os cartões mostrem a base completa.
2. Antes de capturar, confira os cartões da página 1 com
   [`reports/powerbi/medidas_referencia.json`](../../reports/powerbi/medidas_referencia.json): 73.046
   registros, 72.990 AIHs distintas, R$ 125.440.636,13, R$ 1.717,28, 6,12 dias e 6,39%.
3. Exporte cada página em PNG na resolução da página (1280×720) ou maior, mantendo a proporção 16:9.
   Uma opção é **Arquivo → Exportar → Exportar para PDF** e converter cada página em PNG; outra é a
   captura de tela da página em tela cheia (**Exibir → Ajustar à página**).
4. Salve com os nomes da tabela acima. Use também `01-visao-geral.png` como imagem de prévia do README e
   como base da imagem de compartilhamento social do repositório.
