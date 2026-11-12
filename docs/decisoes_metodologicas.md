# Decisões metodológicas e técnicas

Registro no estilo ADR (*Architecture Decision Record*). Cada decisão tem identificador estável;
decisões não são apagadas — quando mudam, recebem status **Substituída** e apontam para a nova.

Status: **Adotada** · **Pendente** (aguarda verificação) · **Substituída**.

---

## D-001 — Dados brutos imutáveis e camadas separadas
**Status:** Adotada (Fase 1)
**Contexto:** o projeto original separava camada bruta e processada.
**Decisão:** `data/raw/` contém o `.dbc` oficial e sua conversão direta, nunca alterados após
gravados; transformações geram novos arquivos em `data/processed/`.
**Motivo:** permite refazer qualquer etapa e auditar cada transformação a partir da origem.

## D-002 — Dados fora do Git
**Status:** Adotada (Fase 1)
**Decisão:** nada em `data/` é versionado, exceto `.gitkeep`, `README.md` e um manifesto
(`MANIFEST.json`, Fase 2) com URL, data de download e SHA-256. O `.gitignore` usa lista de
permissão e há testes (`tests/test_repository_hygiene.py`) que verificam o comportamento real do Git.
**Motivo:** dados públicos são reobtidos da fonte oficial; o manifesto garante que saberemos se o
arquivo baixado mudou.

## D-003 — Indicadores históricos são referências de reconciliação
**Status:** Adotada (Fase 1)
**Decisão:** os valores recuperados ficam em `config/params.yaml` (`historical_reference`), cada um
com status (`recorded`, `needs_verification`, `criterion_unknown`). Resultados reproduzidos são
comparados a eles, **nunca ajustados** para coincidir. Divergências são documentadas em
[`reconciliacao.md`](reconciliacao.md).

## D-004 — Nenhum registro é excluído
**Status:** Adotada (Fase 1)
**Decisão:** AIHs com número repetido são investigadas e marcadas (colunas derivadas), não
removidas. Filtros de análise são explícitos e documentados por indicador.

## D-005 — Competência ≠ datas de ocorrência
**Status:** Adotada (Fase 1)
**Decisão:** `ANO_CMPT`/`MES_CMPT` (competência), `DT_INTER` (internação) e `DT_SAIDA` (saída) são
tratados como dimensões distintas. Todo indicador declara qual delas usa.

## D-006 — Valores monetários exatos
**Status:** Adotada (Fase 1)
**Decisão:** valores de referência são armazenados como texto e lidos como `decimal.Decimal`
(`hospital_analytics.config.to_money`, que rejeita `float`). Comparações de somas monetárias são
exatas ao centavo.
**Motivo:** `float` não representa centavos exatamente; somas de 73 mil valores podem divergir.

## D-007 — Ambiente: Python 3.13, uv e lockfile
**Status:** Adotada (Fase 1)
**Decisão:** Python 3.13 (`.python-version`), dependências declaradas no `pyproject.toml` com
versões mínimas e fixadas exatamente no `uv.lock`. Instalação com `uv sync --locked`.
**Evidência:** `pyreaddbc 2.0.4` possui binário compilado para CPython 3.13 e foi testada em
ambiente descartável antes da adoção.
**Observação:** versões resolvidas incluem pandas 3.1 e DuckDB 2.0, provavelmente mais novas que as
do projeto original (não registradas). Mudanças de comportamento do pandas 3 (tipo `string` padrão,
*copy-on-write*) são uma possível fonte de divergência e serão consideradas na reconciliação.

## D-008 — Leitura do `.dbc`: pyreaddbc + dbfread
**Status:** Adotada (Fase 1) — validação final na Fase 2
**Decisão:** `pyreaddbc.dbc2dbf` descompacta `.dbc` → `.dbf`; `dbfread` lê o `.dbf`. Encoding e
tipos serão definidos na Fase 2 com base no arquivo real.
**Licença:** `pyreaddbc` é AGPL-3.0. Uso como dependência para análise é compatível; a escolha
da licença deste projeto deve considerar isso (pendente).

## D-009 — Lógica em `src/`, notebook para apresentação
**Status:** Adotada (Fase 1)
**Decisão:** funções do pipeline ficam no pacote `hospital_analytics` (layout `src/`) e são
testadas; o notebook importa e apresenta resultados.
**Motivo:** código em notebook é difícil de testar e de revisar em diffs.

## D-010 — Autoria dos commits
**Status:** Adotada (Fase 1)
**Decisão:** `user.name`/`user.email` configurados **apenas neste repositório** (`git config` local),
com endereço noreply do GitHub, sem expor e-mail pessoal no histórico público.

## D-011 — Obtenção do arquivo original fora do ambiente de execução
**Status:** Adotada (Fase 2)
**Contexto:** o ambiente em nuvem não alcança o DATASUS: mesmo com o host liberado no proxy, o
servidor não responde nas portas 21 (FTP), 80 e 443 a partir da infraestrutura de saída.
**Decisão:** a autora baixou o `.dbc` do FTP oficial em conexão brasileira, publicou-o sem
modificação como asset da Release `data-rdrj2401` e o ambiente o obteve pela API REST do GitHub.
**Evidência de integridade:** SHA-256 idêntico calculado de forma independente pela autora, pelo
GitHub (digest do asset) e neste ambiente.

## D-012 — Camada bruta 100% texto, sem inferência de tipos
**Status:** Adotada (Fase 2)
**Decisão:** todas as 113 colunas são gravadas como `string` não anulável, com o valor exatamente
como no DBF, apenas sem os espaços de preenchimento da largura fixa. Campos vazios são `""`.
O tipo DBF original de cada campo é preservado nos metadados do Parquet.
**Motivo:** inferir tipos apagaria zeros à esquerda de códigos e introduziria `float` em valores
monetários; interpretar campos é tratamento e depende do dicionário oficial (Fase 3).

## D-013 — Arrow como etapa "DataFrame" da conversão
**Status:** Adotada (Fase 2)
**Decisão:** a tabela em memória é construída diretamente em Apache Arrow com esquema explícito,
em lotes de 10.000 registros; o pandas é usado para leitura (`read_raw_dataframe`).
**Motivo:** o pandas infere tipos ao construir DataFrames; o Arrow permite declarar o esquema.

## D-014 — Verificação independente de cada ferramenta de baixo nível
**Status:** Adotada (Fase 2)
**Contexto:** a leitura do código-fonte mostrou que `pyreaddbc.dbc2dbf` apenas imprime erros
(pode deixar `.dbf` vazio ou truncado) e que o `dbfread` pula em silêncio registros com marcador
desconhecido.
**Decisão:** tamanho exato do `.dbf` conferido com o cabeçalho; ativos + excluídos conferidos com a
contagem declarada; Parquet relido e comparado pela impressão digital do conteúdo.

## D-015 — Impressão digital do conteúdo como prova de preservação
**Status:** Adotada (Fase 2)
**Decisão:** SHA-256 sobre colunas e valores (com prefixo de comprimento), calculado durante a
leitura do DBF e recalculado sobre o Parquet; ambos registrados e comparados.
**Motivo:** o SHA-256 do arquivo Parquet depende da biblioteca e da compressão; a impressão
digital depende apenas dos dados.

## D-016 — Imutabilidade e escrita segura
**Status:** Adotada (Fase 2)
**Decisão:** arquivos nunca são sobrescritos (o pipeline recusa destinos existentes); saídas são
escritas em `.partial` e renomeadas atomicamente após verificação; fonte e Parquet ficam com
permissão somente leitura; uma fonte registrada no manifesto não pode ser substituída por outro
conteúdo com o mesmo caminho.

## D-017 — Registros marcados como excluídos interrompem a conversão
**Status:** Adotada (Fase 2)
**Decisão:** se o DBF tiver registros com marcador `*`, a conversão para e exige decisão explícita.
**Situação real:** `RDRJ2401` tem 0 registros excluídos (73.046 ativos = 73.046 declarados).

## D-018 — Manifesto e recuperação dos dados
**Status:** Adotada (Fase 2)
**Decisão:** `data/MANIFEST.json` (versionado) registra fonte, cópia arquivada, datas, tamanhos,
SHA-256, versão dos dados (data de atualização do cabeçalho DBF: 2025-02-08), ferramentas e
impressões digitais. Recuperação: `make fetch-data` (Release → verificação). Ver
[`recuperacao_dados.md`](recuperacao_dados.md).

## D-019 — Encoding CP850, declarado pelo cabeçalho do DBF
**Status:** Adotada (Fase 2) — resolve P-008 · aprovada pela autora
**Contexto:** a camada bruta foi gerada inicialmente com Latin-1 (D-012). O cabeçalho do DBF declara
*language driver* `0x02` = CP850. Em `AUD_JUST`, 23 valores continham os bytes `0x90`/`0xA0`,
exibidos em Latin-1 como caracteres de controle.
**Alternativas:** (a) manter Latin-1 — reversível, mas exibição incorreta e contrária ao que o
arquivo declara; (b) guardar bytes brutos em vez de texto — fiel, mas pouco prático para análise;
(c) **CP850** — o que o arquivo declara, também reversível para os 256 bytes.
**Decisão:** CP850. A conversão passa a **recusar** um encoding que contradiga o cabeçalho.
**Prova de que nenhum valor bruto mudou:** nova impressão digital sobre os **bytes** de cada campo
(independente de encoding): idêntica antes (Latin-1) e depois (CP850) —
`6ea7c886bbc44d009278a3761ab5a3a90cd7e63ba29cb54f175582bfb4ee607e`. Comparação célula a célula:
somente 23 células de `AUD_JUST` mudaram de texto (`RECÉM` ×13, `USUáRIO` ×10 — o "á" minúsculo
está no dado de origem). Caracteres de controle na base: 13 → 0.
**Consequências:** a impressão digital do texto mudou (`e9fcf1b8…` → `b3dfcaba…`); a entrada
anterior foi mantida em `history` no manifesto (substituição explícita com motivo, via
`convert --supersede`). Registros, colunas e `VAL_TOT` inalterados.

## D-020 — Dicionário por fonte secundária, com status explícito
**Status:** Adotada (Fase 3)
**Contexto:** a fonte primária (Informe Técnico SIH/SUS, pasta `Doc` do FTP do DATASUS) não é
alcançável deste ambiente (D-011).
**Alternativas:** (a) aguardar a fonte primária — bloquearia a Fase 3; (b) usar conhecimento prévio
sem fonte — viola "não inventar interpretações"; (c) **fonte secundária pública e citável**
(`microdatasus`, que decodifica o SIH a partir da documentação oficial), corroborada pelos dados.
**Decisão:** (c). Cada interpretação em `dictionary.py` declara fonte e status (`secondary` ou
`prior_knowledge`); nada é rotulado como confirmado pela fonte primária.
**Corroboração nos dados:** `IDENT` só 1 e 5 (contagens históricas); `MORTE`=1 ⇔ `COBRANCA` 4x;
`COD_IDADE`=5 com `IDADE` 0–23.
**Consequência:** pendência P-009 (confirmar na fonte primária).

## D-021 — Camada tratada: originais intactos + derivadas em minúsculas
**Status:** Adotada (Fase 3)
**Decisão:** `sih_rj_2024_01_tratado.parquet` contém os 113 campos originais (arrays Arrow copiados
sem alteração) e 50 colunas derivadas. A impressão digital das colunas originais deve ser idêntica à
da camada bruta (verificado e registrado no manifesto). Conversões de formato (centavos, inteiros,
datas) são verificadas como reversíveis linha a linha; interpretações de códigos ficam em colunas
próprias, com status da fonte.
**Alternativa descartada:** substituir os campos por versões tipadas — perderia a rastreabilidade.

## D-022 — Precisão reduzida pela largura do campo
**Status:** Adotada (Fase 3)
**Contexto:** `VAL_UTI` (`N8.2`) contém `166200.0`: `166200.00` não cabe em 8 caracteres.
**Decisão:** aceitar menos casas decimais **somente** quando a forma completa excede a largura e
difere apenas por zeros finais; ler o valor como escrito (16.620.000 centavos); contar no manifesto.
Qualquer outro formato interrompe o build.
**Consequência:** uma eventual segunda casa decimal pode ter sido perdida na origem (≤ R$ 0,09);
não afeta `VAL_TOT`.

## D-023 — Nomes derivados distintos ignorando maiúsculas
**Status:** Adotada (Fase 3)
**Contexto:** a primeira versão usava `dt_inter`; o DuckDB resolve nomes sem distinguir caixa e
leu a coluna original `DT_INTER` (texto) — defeito encontrado ao executar a auditoria.
**Decisão:** datas derivadas renomeadas (`admission_date`, `discharge_date`, `birth_date`); o build
recusa qualquer colisão de nomes ignorando caixa (teste dedicado).

## D-024 — Indicadores: duas engines, agregados exatos e status por regra
**Status:** Adotada (Fase 4)
**Decisão:** Pandas e DuckDB calculam os mesmos agregados inteiros; médias/percentuais em `Decimal`,
arredondamento half-up na precisão histórica; status definido por regra (`indicators.status_for`),
nunca escolhido manualmente. Valores históricos lidos somente de `config/params.yaml`.

## D-025 — Idade: indicador histórico mantido, corrigido publicado ao lado
**Status:** Adotada (Fase 4)
**Contexto:** 43,96 só é reproduzido ignorando a unidade `COD_IDADE` (critério incorreto).
**Decisão:** publicar ambos: "critério histórico" (para reconciliação) e "em anos — corrigida"
(43,85), com aviso para usar o corrigido em conclusões. O histórico não é alterado nem escondido.

## D-026 — Relatórios determinísticos e sem valores sensíveis
**Status:** Adotada (Fase 3)
**Decisão:** relatórios gerados (`reports/`) não têm carimbo de hora (mesmos dados + mesmo código =
arquivos idênticos; a proveniência vem do git) e nunca contêm valores de colunas identificadoras
ou de texto livre (`N_AIH`, `CEP`, `NASC`, `CPF_AUT`, `GESTOR_CPF`, `AUD_JUST`, `SIS_JUST`,
`INSC_PN`) — apenas estatísticas agregadas. Testes verificam ambas as propriedades.

## D-027 — Nomenclatura dos tipos de AIH
**Status:** Adotada (Fase 4)
**Decisão:** documentação e relatórios usam "AIH tipo 1 (principal)" e "AIH tipo 5 (longa
permanência)"; o rótulo histórico "continuidade" é citado apenas como referência histórica.

## D-028 — Granularidade do fato: registro de AIH
**Status:** Adotada (Fase 6)
**Decisão:** `fato_registro_aih` tem 1 linha por registro do RD (73.046), chave técnica
`registro_id` (posição no arquivo). `N_AIH` é substituído por `aih_id` (posto denso, determinístico)
para contagens distintas. Não existem medidas de "internações" nem de "pacientes": a base não tem
identificador de paciente e a longa permanência gera vários registros por AIH.
**Alternativa descartada:** consolidar registros por AIH — perderia valores cobrados por período e
exigiria regras de consolidação não documentadas pela fonte.

## D-029 — Esquema estrela sem caminhos ambíguos
**Status:** Adotada (Fase 6)
**Decisão:** relações muitos-para-um, direção única. O município do **estabelecimento** é atributo
de `dim_estabelecimento` (todos os atributos dependem do CNES: verificado), separado de
`dim_municipio_residencia`. A segunda data (internação) é relação **inativa**, usada via
`USERELATIONSHIP`. "Características do paciente" viram `dim_perfil_demografico` (perfil do
registro), não uma dimensão de pacientes.

## D-030 — Minimização: datas exportadas por mês
**Status:** Adotada (Fase 6)
**Contexto:** idade exata + sexo + município + datas por dia tornam 89,4% dos registros únicos.
**Decisão:** exportar `mes_saida`/`mes_internacao` (1º dia do mês) e `dim_mes`; permanência exata
em dias preservada. Registros únicos na combinação equivalente: 19,9%. Identificadores pessoais,
CEP, textos livres e CNPJs não são exportados. Ver `docs/powerbi/privacidade.md`.

## D-031 — Formato de exportação e esquema único
**Status:** Adotada (Fase 6)
**Decisão:** CSV UTF-8 (ponto decimal, datas ISO, nulo = vazio, booleanos 0/1) como formato
principal; Parquet opcional (`--parquet`). Um único esquema em Python (`powerbi.TABLES`) gera a
exportação, o dicionário de campos, as consultas Power Query com tipos explícitos e os testes;
saídas determinísticas (SHA-256 em `reports/powerbi/export_summary.json`).

## D-032 — Convenções das medidas DAX
**Status:** Adotada (Fase 6)
**Decisão:** razões retornam a fração e são **formatadas** como porcentagem (sem ×100); divisões
com `DIVIDE`; concentração top 10% com `TOPN` desempatado por `registro_id` (exatamente k
registros); permanência sempre interpretável por tipo de AIH. As medidas são verificadas por
equivalentes em SQL sobre os CSV (a execução de DAX não é possível no ambiente de construção).

## D-033 — Enriquecimento somente com fonte oficial verificada
**Status:** Adotada (Fase 6) — enriquecimento **pendente**
**Decisão:** nomes de municípios, estabelecimentos, procedimentos e diagnósticos só entram a partir
de fontes oficiais verificadas (URL, versão/competência, licença, SHA-256), por junção de código
exato, com testes de cobertura. Do ambiente de execução, todos os hosts oficiais candidatos foram
recusados pela política de rede; as dimensões mantêm os códigos até a obtenção dos arquivos
(`docs/powerbi/fontes_referencia.md`).

## D-034 — Codificação das referências: CP1252
**Status:** Adotada (diagnóstico de referências)
**Evidência:** no SIGTAP 2024-01, 12 nomes usam os bytes 0x93/0x94/0x96 (aspas tipográficas e
travessão), que só CP1252 decodifica corretamente (Latin-1 produz caracteres de controle); no
CADGERRJ, os bytes acentuados decodificam como `ÃÇÉÓÚ` em CP1252 e como desenho de caixa em CP850.
**Decisão:** leitor do SIGTAP com padrão CP1252 (posição em bytes = posição em caracteres
preservada); CADGERRJ lido em CP1252. Diagnóstico em `docs/powerbi/diagnostico_referencias.md`.

## D-035 — Integração das referências oficiais às dimensões
**Status:** Adotada (etapa de enriquecimento, autorizada pela autora em 2026-11-11)
**Decisão:** as dimensões recebem **somente colunas novas**, preenchidas por junção exata de código
a partir da dimensão: SIGTAP 2024-01 (procedimento, grupo, subgrupo, forma de organização, CID-10),
IBGE (município pelos 6 primeiros dígitos, prefixo único), CNES CADGERRJ (`FANTASIA`) e tabelas
TabWin do SIH (D-036). Nova `dim_diagnostico` (3.759 códigos) ligada ao fato por
`diagnostico_principal_cod`. Colunas existentes não mudam; o `fato_registro_aih.csv` permanece byte
a byte idêntico (SHA-256 `1d1e038b…`, verificado a cada exportação).
**Salvaguardas:** tamanho e SHA-256 de cada arquivo conferidos **antes** da leitura; chave de
referência duplicada é erro; cada dimensão tem exatamente as chaves distintas do fato (sem
*fan-out*); cobertura por coluna verificada (100% em todas) e nunca forçada — código sem
correspondência fica vazio e reprova a verificação; do cadastro CNES só saem CNES e nome fantasia.

## D-036 — Dicionário oficial do RD: tabelas TabWin do `TAB_SIH.zip`
**Status:** Adotada
**Evidência:** o `RD2008.DEF` do pacote oficial do SIH/SUS declara, para cada campo do RD, a tabela
de conversão e a posição inicial (`ESPEC → LEITOS.CNV`, `IDENT → IDENT.CNV`, `CAR_INT →
CARATEND.CNV`, `COMPLEX → COMPLEX2.CNV`, `SEXO`, `RACA_COR`, `NAT_JUR → natjur.cnv/esferajur.cnv`,
`GESTAO`, `DIAG_PRINC → CID10CAP.CNV`, todas na posição 1).
**Decisão:** somente os 11 arquivos necessários foram extraídos do pacote (o ZIP não é copiado), cada
um com SHA-256 próprio em `config/params.yaml`. Os rótulos oficiais vão para colunas
`*_oficial`/`descricao_oficial`, usadas nos visuais; a fonte secundária é mantida ao lado. A
comparação está em `reports/reference/enriquecimento.md`: 3 divergências (especialidade 03
"Clínico", tipo de AIH 1 "Normal", textos abreviados de caráter 05/06) — adotado o oficial.
Resolve P-010 (`ESPEC` 10 "Leito Dia / Aids", 14 "Leito Dia / Saúde Mental", 87 "Saúde Mental
(Clínico)").

## D-037 — Precedência nas tabelas TabWin: duas regras que precisam concordar
**Status:** Adotada
**Contexto:** códigos aparecem em mais de uma categoria (faixa "pega-tudo" listada antes de códigos
específicos, hierarquias pai/filho); a regra de precedência do formato não está documentada nos
arquivos.
**Decisão:** o leitor aplica "o item mais específico vence" (código exato, depois a faixa numérica
mais estreita) e "o último listado vence"; se divergirem, ou houver empate, é erro — o rótulo nunca
é adivinhado. Nos 12 arquivos reais, as duas regras concordam para todos os códigos do modelo. A
chave de busca é o trecho do campo a partir da posição do `.DEF` com a largura do cabeçalho (ex.: 3
primeiros caracteres da CID para o capítulo).

## D-038 — Nomes de estabelecimentos: cadastro vigente, não o de 2024-01
**Status:** Adotada, com limitação declarada
**Decisão:** `estabelecimento_nome` vem do CADGERRJ atualizado em 2026-10-15 (o CNES não publica o
nome no arquivo `ST` da competência). A fonte e a data acompanham cada linha
(`estabelecimento_nome_fonte`). Dois nomes fantasia são compartilhados por 4 estabelecimentos:
os visuais usam `estabelecimento_rotulo` = `nome (CNES)`, único.

## D-039 — Data da consulta ao IBGE
**Status:** Adotada, com limitação declarada
**Decisão:** a hora da consulta à API não foi registrada; o carimbo de modificação do arquivo salvo
pela autora (2026-11-10 19:19, UTC−03:00) é a evidência mais próxima e é registrado como tal
(`file_timestamp`), não como data de consulta confirmada.

## D-040 — Portabilidade Windows/Linux
**Status:** Adotada
**Decisão:** o decodificador C do `.dbc` roda em processo filho isolado (o código C não fecha o
arquivo de saída quando rejeita a entrada; no Windows o arquivo ficava bloqueado e a limpeza
falhava); todo I/O de texto declara `encoding` (teste estático impede regressão); o console nunca
derruba um comando por não codificar um símbolo. Reprodução a partir de um *checkout* limpo no
Windows, com ambiente criado pelo `uv.lock`, gerou Parquets, relatórios JSON/Markdown e as 13 CSVs
**byte a byte idênticos** aos gerados no Linux. Exceção: as figuras PNG diferem em ~2–3% dos pixels
(rasterização de texto); o conteúdo é o mesmo e as versionadas não são substituídas.

---

## Decisões pendentes

| ID | Tema | Situação |
|---|---|---|
| P-001 | Interpretação de `IDENT`, `COD_IDADE`, `DIAS_PERM`, `MORTE`, `CAR_INT` | **Parcial:** fonte secundária + corroboração nos dados (D-020); confirmação primária em P-009 |
| ~~P-002~~ | Campo de permanência | **Resolvida:** `DIAS_PERM` (reproduz os 3 valores) |
| ~~P-003~~ | Conversão de idade | **Resolvida:** histórico ignora `COD_IDADE`; corrigido publicado (D-025) |
| P-004 | Critério da concentração top 10% (58,20%) | **Aberta:** não reproduzida; variantes documentadas em `indicadores.md` |
| ~~P-005~~ | Classificação clínico/cirúrgico | **Resolvida:** participação no `VAL_TOT` por grupo SIGTAP, AIH tipo 1 |
| ~~P-006~~ | Papel dos arquivos Parquet | **Resolvida:** `raw/RDRJ2401.parquet` (bruto) e `processed/sih_rj_2024_01_tratado.parquet` (D-021). O intermediário histórico `sih_rj_2024_01.parquet` não foi reconstruído (função desconhecida; não necessário) |
| P-007 | Licença do projeto | Antes da Fase 6 |
| ~~P-008~~ | Encoding | **Resolvida pela D-019** |
| P-009 | Confirmar o dicionário na fonte primária (Informe Técnico SIH/SUS) | **Parcial:** rótulos dos códigos confirmados pelas tabelas oficiais do TabWin (D-036); a semântica de campos como `DIAS_PERM` na longa permanência segue sem documento primário |
| ~~P-010~~ | Códigos de `ESPEC` 10, 14 e 87 (364 registros) | **Resolvida** por `LEITOS.CNV` (D-036) |
| ~~P-011~~ | Grupos SIGTAP 02–05 (rótulos) | **Resolvida:** `tb_grupo` oficial integrada (`grupo_nome_sigtap`) |
| ~~P-012~~ | Enriquecimento oficial (IBGE, CNES, SIGTAP, CID-10) | **Resolvida** (D-035 a D-039) |
| P-013 | Publicação do `.pbix` (incorpora dados) | Decisão da autora após avaliação de privacidade |
