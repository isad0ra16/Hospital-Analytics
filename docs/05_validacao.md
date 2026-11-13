# 5. Validação: qualidade, reconciliação e reprodutibilidade

## Objetivo

Demonstrar, com verificações automatizadas, que (1) a base recuperada é íntegra, (2) os indicadores
históricos são reproduzidos — ou que cada divergência é explicada — e (3) o pipeline gera os mesmos
arquivos em qualquer máquina.

Código: `audit.py`, `indicators.py`, `powerbi.py`, `validate.py` · Comandos: `hospital-analytics audit`,
`indicators`, `powerbi` e `verify`; testes com `uv run pytest` · Decisões: D-003, D-024 a D-026.

## Qualidade dos dados (auditoria)

Auditoria somente leitura; números completos em
[`reports/audit/audit_rdrj2401.md`](../reports/audit/audit_rdrj2401.md) (SQL em `sql/audit/`). Nenhum
registro foi removido ou corrigido.

| Dimensão | Resultado |
| --- | --- |
| Registros / colunas | 73.046 / 113 |
| Linhas idênticas nas 113 colunas | 0 — sem duplicatas exatas |
| Datas inválidas (`DT_INTER`, `DT_SAIDA`, `NASC`) | 0 / 0 / 0 |
| Saída antes da internação · nascimento após a internação | 0 · 0 |
| Internação ou saída após o fim da competência | 0 · 0 |
| `VAL_TOT` vazio / negativo / malformado | 0 / 0 / 0 |
| `VAL_TOT` = 0 | 241 registros — **exatamente** os 241 com `ESPEC` 87 ("Saúde Mental (Clínico)") |
| Valor com precisão reduzida pela largura do campo | 1 (`VAL_UTI`, D-022) |
| `MORTE` × `COBRANCA` 4x (óbito) | coincidem nos 4.664 registros |
| Colunas 100% vazias | `NUM_PROC`, `CPF_AUT`, `GESTOR_DT`, `INFEHOSP`, `DIAGSEC8`, `DIAGSEC9` (as duas últimas coincidem com o histórico) |

### Competência, internação e saída

Todos os registros têm competência **2024-01**, mas as saídas se distribuem entre 2023-08-01 e
2024-01-31 (29.279 em 2023 e 43.767 em 2024 — reproduz o histórico), até 5 meses antes da competência,
e as internações começam em 2012-01-02 (longa permanência). A competência não é o período de
ocorrência; toda análise temporal declara a data que usa (D-005).

### AIHs com número repetido

| Medida | Valor |
| --- | ---: |
| Registros excedentes | 56 |
| Números de AIH distintos | 50 |
| Registros envolvidos | 106 |
| Números com 2 / 3 / 4 registros | 45 / 4 / 1 |
| Números com registros de tipo 1 **e** 5 · só tipo 5 · só tipo 1 | 46 · 4 · 0 |

Dentro desses grupos variam `DT_SAIDA` e `SEQUENCIA` (50 de 50), valores (`VAL_SH`, `VAL_TOT`: 49),
`IDENT` (46), `COBRANCA` e `DIAS_PERM` (45). Não são duplicatas: são apresentações sucessivas, na maioria
envolvendo longa permanência. Nada é removido; `aih_repeated` apenas sinaliza (D-004).

### Permanência, idade e valores

- `DIAS_PERM` difere de `DT_SAIDA − DT_INTER` em **660 registros, todos `IDENT` 5**; nos 72.383 de tipo
  1 os dois coincidem. Na longa permanência, a média por datas é de 967 dias.
- `COD_IDADE`: 2 (dias) 2.126 registros, `IDADE` 0–30 · 3 (meses) 1.112, 1–11 · 4 (anos) 69.776, 1–99 ·
  5 (100 + `IDADE`) 32, 0–23 — intervalos coerentes com as unidades.
- `VAL_TOT` = `VAL_SH + VAL_SP` (e = soma dos 11 componentes) em 72.704 registros; a composição dos 342
  restantes não é interpretada sem a fonte primária.
- Completude: `CID_NOTIF` 95,9% vazio, `FAEC_TP` 90,9%, `AUD_JUST`/`SIS_JUST` 98,9%, `DIAGSEC1` 79,2%,
  `DIAGSEC2`–`DIAGSEC7` > 96% — campos não usados nos indicadores.

## Reconciliação com o histórico

Os valores históricos são lidos de `config/params.yaml`. Pandas e DuckDB calculam os mesmos agregados
exatos (somas inteiras em centavos e dias, contagens) e **concordam em todos**; médias e percentuais
são calculados em `Decimal`, arredondados *half-up* na precisão do histórico, com o valor exato também
publicado. O status é atribuído por regra fixa, nunca manualmente (D-024). Critério de aceite:
contagens e somas monetárias **exatas** ao centavo; médias e percentuais iguais com 2 casas.

Situação: **reproduzido** (critério documentado no histórico) · **critério identificado** (valor
reproduzido; o critério foi descoberto nesta reconstrução) · **divergente, explicado** ·
**divergente**.

| # | Indicador | Base | Histórico | Reproduzido | Critério | Situação |
| --- | --- | --- | ---: | ---: | --- | --- |
| 1 | Registros | completa | 73.046 | 73.046 | linhas = registros do cabeçalho DBF | reproduzido |
| 2 | Colunas | completa | 113 | 113 | campos do DBF | reproduzido |
| 3 | Soma `VAL_TOT` | completa | R$ 125.440.636,13 | R$ 125.440.636,13 | soma exata | reproduzido |
| 4–5 | Saídas em 2023 · 2024 | completa | 29.279 · 43.767 | 29.279 · 43.767 | ano de `DT_SAIDA` | reproduzido |
| 6 | Permanência média | completa | 6,12 | 6,12 (6,1249) | média de `DIAS_PERM` | critério identificado |
| 7 | Idade média | completa | 43,96 | 43,96 (43,9613) | `IDADE` **sem** `COD_IDADE` — critério incorreto; a idade corrigida, 43,85, é publicada ao lado | critério identificado |
| 8 | Valor médio | completa | R$ 1.717,28 | R$ 1.717,28 | `VAL_TOT` / registros | reproduzido |
| 9 | Óbitos | completa | 4.664 | 4.664 | `MORTE` = 1 | critério identificado |
| 10 | Mortalidade bruta | completa | 6,38% | 6,39% (6,3850) | óbitos / registros | divergente, explicado |
| 11–13 | Registros · `VAL_TOT` · valor médio | AIH tipo 1 | 72.383 · R$ 123.858.470,15 · R$ 1.711,15 | idem | `IDENT` = 1 | reproduzido |
| 14–15 | Permanência · óbitos | AIH tipo 1 | 5,93 · 4.656 | 5,93 (5,9255) · 4.656 | `DIAS_PERM`, `MORTE` | critério identificado |
| 16–18 | Registros · `VAL_TOT` · valor médio | AIH tipo 5 | 663 · R$ 1.582.165,98 · R$ 2.386,37 | idem | `IDENT` = 5 | reproduzido |
| 19–20 | Permanência · óbitos | AIH tipo 5 | 27,90 · 8 | 27,90 (27,8989) · 8 | `DIAS_PERM`, `MORTE` | critério identificado |
| 21 | AIHs repetidas (ocorrências) | completa | 56 | 56 | registros excedentes | critério identificado |
| 22 | AIHs repetidas (números) | completa | 50 | 50 | | reproduzido |
| 23 | Concentração top 10% | ? | 58,20% | 57,74% (completa) · 58,27% (tipo 1) | critério não recuperado | divergente |
| 24–25 | Cirúrgicos · clínicos | AIH tipo 1 | 51,57% · 44,38% | 51,57% · 44,38% | participação no **valor**, grupos SIGTAP 04 e 03 | critério identificado |
| 26 | Grupos com diferenças (preservação) | — | 0 | 0 | impressão digital das colunas originais idêntica em bruto e tratado | critério identificado |

**24 das 26 referências da tabela foram reproduzidas exatamente** (13 com situação **reproduzido** e 11
com **critério identificado**); as duas restantes são a mortalidade e a concentração. O relatório gerado
pela etapa `indicators` cobre 24 dessas referências e reproduz 22 (12 e 10): a linha 2 (colunas) é
conferida pela etapa `validate`, a linha 26 (preservação dos campos) pela etapa `build-processed`, e a
concentração aparece em duas linhas (base completa e AIH tipo 1), comparadas ao mesmo valor histórico.
Tabela gerada com valores exatos:
[`reports/indicators/reconciliation.md`](../reports/indicators/reconciliation.md).

**Consistência interna do histórico** (automatizada em `tests/test_historical_reference.py`):
29.279 + 43.767 = 73.046; 72.383 + 663 = 73.046; R$ 123.858.470,15 + R$ 1.582.165,98 = total exato;
4.656 + 8 = 4.664; valores médios = soma ÷ registros; permanência geral compatível com a média
ponderada dos tipos (6,124–6,134).

### Achados da reconciliação

1. **Idade média:** 43,96 só é reproduzido somando `IDADE` em dias, meses e anos como se fossem anos.
   A idade em anos é **43,85**; ambas são publicadas e só a corrigida deve ser usada (D-025).
2. **"Cirúrgicos 51,57% / clínicos 44,38%" mede valor, não internações:** é a participação no `VAL_TOT`
   dos grupos SIGTAP 04 e 03 do procedimento realizado, apenas AIH tipo 1. Por contagem de registros, as
   proporções se invertem: 44,97% cirúrgicos e 54,25% clínicos.
3. **Mortalidade 6,38% × 6,39%:** 4.664 / 73.046 = 6,38501…%; arredondamento (half-up ou bancário) dá
   6,39% e só truncamento dá 6,38%. Nenhum numerador ou denominador alternativo testado (tipo 1, números
   de AIH únicos) produz 6,38%. O valor correto é **6,39%**, em óbitos por 100 registros de AIH.
4. **Concentração não reproduzida:** definição adotada = participação no `VAL_TOT` dos k = ⌊0,1·n⌋
   registros de maior valor: **57,74%**. Variantes testadas, em número limitado para não procurar um
   número: ⌈⌉ 57,75; AIH tipo 1 58,27; `VAL_SH` 58,96; `VAL_SH+VAL_SP` 57,81; sem zeros 57,67; por número
   de AIH 57,74; por hospital 50,32. Nenhuma dá 58,20%, e o histórico dizia "aproximadamente".
   **Não usar 58,20%** (P-004).
5. **Permanência usa `DIAS_PERM`:** reproduz 6,12 / 5,93 / 27,90; `QT_DIARIAS` (5,44) e a diferença de
   datas (14,65) não.
6. **"Tipo 5" é longa permanência**, não "continuidade" (D-027).

## Modelo analítico

`hospital-analytics powerbi` termina com `RESULT: ALL CHECKS PASSED (122 checks)` quando:

- chaves únicas e não nulas nas 14 tabelas; colunas iguais ao esquema;
- **0 órfãos** nos 11 relacionamentos; cada dimensão tem exatamente as chaves distintas do fato
  (sem *fan-out*, sem linhas extras);
- *join* com todas as dimensões ativas preserva 73.046 linhas e R$ 125.440.636,13; centavos e decimais
  concordam linha a linha; óbitos, soma de permanência e idades não nulas iguais ao pipeline;
- cobertura de 100% em cada coluna com nome oficial;
- `fato_registro_aih.csv` **byte a byte idêntico** à exportação anterior
  (SHA-256 `1d1e038b17471d94ad19bf8a1a6dccf5f4af070b8c31862ff1cf2f6dec2b6518`);
- equivalentes SQL das medidas DAX iguais aos indicadores reconciliados; AIHs distintas = registros −
  excedentes; os 21 pontos da curva de Lorenz iguais aos do relatório de análise.

O projeto Power BI tem verificações próprias ([`07_dashboard.md`](07_dashboard.md#verificações)).

## Reprodutibilidade

- **Relatórios determinísticos:** sem carimbo de hora e sem valores de colunas identificadoras ou de
  texto livre — mesmos dados e mesmo código geram arquivos idênticos (D-026).
- **Linux × Windows:** a partir de um *checkout* limpo, com ambiente criado pelo `uv.lock`, o pipeline
  completo gerou os Parquets bruto e tratado, todos os relatórios JSON e Markdown e as 13 CSVs do modelo
  **byte a byte idênticos** aos gerados originalmente no Linux. Duas exportações seguidas dão os mesmos
  SHA-256. Exceção: as figuras PNG diferem em 2–3% dos pixels por rasterização de texto; o conteúdo é o
  mesmo e as versionadas não são substituídas (D-040).
- **Proveniência conferida:** `hospital-analytics verify` confere o `.dbc`, os dois Parquets e os arquivos de
  referência declarados (tamanho e SHA-256).

## Testes automatizados

`uv run pytest` executa a suíte com **dados sintéticos apenas**: leitura de `.dbc`/`.dbf`
(incluindo arquivos truncados e inválidos), conversão e manifesto, camada tratada, auditoria,
indicadores com oráculo independente, análises, modelo Power BI, enriquecimento (hash divergente, chave
duplicada, cobertura incompleta, campos pessoais do cadastro CNES), leitores das referências oficiais,
projeto PBIP contra os esquemas oficiais da Microsoft, higiene do repositório (dados nunca versionados),
portabilidade (I/O sem depender da codificação do sistema) e links internos da documentação.

## Limitações

- A validação é contra o histórico recuperado e contra a consistência interna; não há uma segunda base
  independente do mesmo período.
- Medidas DAX são verificadas por equivalentes em SQL; a execução no motor do Power BI depende de abrir
  o projeto no Desktop.
