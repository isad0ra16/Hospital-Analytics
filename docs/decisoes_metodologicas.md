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

---

## Decisões pendentes

| ID | Tema | Depende de |
|---|---|---|
| P-001 | Interpretação de `IDENT`, `COD_IDADE`, `DIAS_PERM`, `MORTE`, `CAR_INT` | Documentação oficial (início da Fase 3) |
| P-002 | Campo de permanência usado nos indicadores | P-001 + testes na Fase 4 |
| P-003 | Conversão de idade (`COD_IDADE`) | P-001 + testes na Fase 4 |
| P-004 | Critério de concentração de gastos (top 10%) | Fase 4 |
| P-005 | Campo de classificação clínico/cirúrgico | Fase 4 |
| P-006 | Papel de cada arquivo Parquet. **Parcial:** `data/raw/RDRJ2401.parquet` = conversão direta sem tratamento (D-012). Pendentes: `processed/sih_rj_2024_01*.parquet` | Fase 3 |
| P-007 | Licença do projeto | Antes da Fase 6 |
| P-008 | **Encoding: Latin-1 ou CP850.** O cabeçalho DBF declara *language driver* `0x02` = CP850. Em `AUD_JUST`, 23 valores têm bytes `0x90`/`0xA0`: em CP850 viram `É`/`á` (plausível); em Latin-1, caracteres de controle. Nenhum outro campo tem bytes não ASCII. Ambos os encodings são reversíveis (nenhum byte foi perdido), mas a exibição atual desses 23 valores está incorreta. **Recomendação:** adotar CP850, conforme declarado no arquivo, e regenerar a camada bruta. Não afeta contagens nem `VAL_TOT` | Aprovação da autora |
