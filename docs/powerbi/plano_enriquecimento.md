# Plano operacional de enriquecimento — fontes oficiais de referência

> **Revisão 6 (2026-11-11): integração concluída e autorizada.** Colunas oficiais acrescentadas às
> dimensões, nova `dim_diagnostico`, rótulos do dicionário TabWin do SIH (`TAB_SIH.zip`); os 7
> testes de aceitação abaixo são verificados a cada `make powerbi` (D-035 a D-040).
>
> **Revisão 5:** diagnóstico concluído para todas as fontes (inclui CADGERRJ, TP_PFPJ.CNV,
> RJ_municip.cnv e Estabelecimento.def; 7/7 arquivos A1). Resultados, riscos e colunas propostas em
> [`diagnostico_referencias.md`](diagnostico_referencias.md). Integração aguarda aprovação.
>
> **Status:** plano para aprovação (revisão 4 — arquivos obtidos pela autora; leitores e diagnóstico
> preparados, **sem integração**). Nada foi integrado ao modelo. Dados originais,
> camadas, fato, identificadores técnicos e testes permanecem intactos.

## Classes de evidência

| Classe | Significado |
|---|---|
| **A1 — confirmado com integridade** | arquivo oficial obtido diretamente, com SHA-256 registrado |
| **A2 — acesso direto pela autora** | o endereço respondeu, ou o arquivo aparece na **listagem oficial** do diretório, consultada pela autora no Windows; SHA-256 ainda não registrado (passa a A1 quando registrado) |
| **B — corroborado por automação pública ativa** | código público que baixa deste endereço **em execução recorrente com sucesso** (commits automáticos verificados em 2026-11-10) |
| **C — corroborado por código público** | o endereço/nome aparece no código-fonte de ferramentas públicas que usam a fonte oficial |
| **D — indexado por busca** | página oficial encontrada por mecanismo de busca, **não aberta** por este projeto |
| **E — não confirmado** | nome exato ou existência ainda desconhecidos → confirmar por listagem/página oficial |

**Limitação do ambiente:** nenhum site oficial abre daqui. O contêiner e a ferramenta de leitura web
seguem a mesma política de rede (falha de resolução de nome para `www2.datasus.gov.br`,
`wiki.datasus.gov.br`, `servicodados.ibge.gov.br`, `opendatasus.saude.gov.br`,
`www.saude.rj.gov.br`; 403 para os demais testados). Ferramentas de terceiros foram usadas **apenas
para localizar endereços e formatos** — nenhum dado delas é incorporado.

**Achado relevante:** dois repositórios públicos baixam diariamente do FTP do DATASUS a partir do
GitHub Actions (último sucesso: 2026-11-10 16:21 UTC). O DATASUS **não** bloqueia acesso a partir do
exterior; o bloqueio é do ambiente de execução deste projeto (revisa a hipótese da D-011).

## 1. Dicionário oficial SIH/SUS e auxiliares do TabWin — prioridade 1

| Item | Evidência | Classe |
|---|---|---|
| Pasta de dados `ftp://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/200801_/Dados/` | download do `RDRJ2401.dbc` (SHA-256 conferido) | **A1** |
| Pasta `ftp://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/200801_/Auxiliar/` | listagem oficial pela autora: `TAB_SIH.zip`, `TAB_SIH_199201-199712.zip`, `TAB_SIH_199801-200307.zip`, `TAB_SIH_200308-200712.zip` | **A2** |
| Pacote auxiliar `…/SIHSUS/200801_/Auxiliar/TAB_SIH.zip` | presente na listagem oficial; os demais pacotes têm períodos no nome (até 2007-12), logo `TAB_SIH.zip` é o pacote **sem período**, a usar para a competência 2024-01 (a confirmar pelo conteúdo) | **A2** |
| Página "Manuais do SIH" `http://www2.datasus.gov.br/SIHD/manuais` (Dicionário de Dados, layout da AIH Reduzida, Informes Técnicos) | resultado de busca | **D** |
| Página "Reduzida do AIH" `http://www2.datasus.gov.br/SIHD/reduzida` | resultado de busca | **D** |
| Nomes exatos dos documentos (PDF) | — | **E** |

- **Versão:** `TAB_SIH.zip` (o único sem período no nome) vigente no download — registrar data e
  SHA-256; os pacotes com período (1992–2007) **não** se aplicam a 2024-01. Documentação cuja
  vigência cubra a competência 2024-01 (página de manuais ainda **D**).
- **Relacionamento:** códigos do RD (`ESPEC`, `CAR_INT`, `COBRANCA`, `NAT_JUR`, `GESTAO`, `IDENT`,
  `COD_IDADE`, `MARCA_UTI`, `MUNIC_RES`/`MUNIC_MOV`, `PROC_REA`, `DIAG_PRINC`) ↔ tabelas de conversão.
- **Uso:** confirmar/corrigir o dicionário secundário (P-001, P-009), rotular `ESPEC` 10/14/87
  (P-010), `NAT_JUR` e `GESTAO`.
- **Riscos:** formato próprio do TabWin (`.cnv`/`.def`, a documentar após o download); rótulos
  abreviados ou agrupados; pacote atualizado mensalmente (o conteúdo de hoje pode diferir do de
  jan/2024 — registrar a data).

## 2. IBGE — municípios e UF — prioridade 2

| Item | Evidência | Classe |
|---|---|---|
| Documentação `https://servicodados.ibge.gov.br/api/docs/localidades` | resultado de busca (página oficial) | **D** |
| `https://servicodados.ibge.gov.br/api/v1/localidades/municipios` (todos) | resposta obtida pela autora: `municipios_ibge.json`, ≈ 2,35 MB (SHA-256 pendente); também no código do pacote `ibge` 0.0.5 | **A2** |
| `…/api/v1/localidades/estados/{UF}/municipios` | código do pacote PyPI `ibge` 0.0.5 + documentação indexada | **C** |
| Identificador do município com 7 dígitos | conhecimento prévio | **E** (verificar no JSON recebido) |

- **Versão:** a API não é versionada por data — registrar a data da consulta. Alternativa
  versionada (DTB anual do IBGE): **E**, endereço não corroborado.
- **Relacionamento:** `dim_municipio_residencia.municipio_residencia_cod` e
  `dim_estabelecimento.municipio_estabelecimento_cod` (6 dígitos) ↔ 6 primeiros dígitos do `id`
  do IBGE; `uf_*_cod` ↔ `id` da UF.
- **Riscos:** o prefixo de 6 dígitos precisa ser **único** (teste); códigos do RD fora da lista
  (municípios de outras UFs ou códigos especiais) → cobertura reportada; termos de uso **não
  verificados**. Comparar com a tabela de municípios do `TAB_SIH.zip`, se existir.

## 3. CNES — estabelecimentos, competência 2024-01 — prioridade 3

| Item | Evidência | Classe |
|---|---|---|
| `ftp://ftp.datasus.gov.br/dissemin/publicos/CNES/200508_/Dados/` | listagem oficial pela autora (também no código do `microdatasus` e do `PySUS`) | **A2** |
| Subpasta `…/CNES/200508_/Dados/ST/` | presente na listagem oficial | **A2** |
| `ST` = "Estabelecimentos" (arquivo por grupo + UF + ano + mês) | código do `PySUS` | **C** |
| Nome exato do arquivo RJ 2024-01 dentro de `ST/` | — | **E** (aguarda listagem de `ST/`) |
| `ftp://ftp.datasus.gov.br/dissemin/publicos/CNES/200508_/Auxiliar/TAB_CNES.zip` | código do `microdatasus` | **C** |
| Extração por competência `http://cnes.datasus.gov.br/pages/estabelecimentos/extracao.jsp` | resultado de busca | **D** |
| OpenDataSUS `https://opendatasus.saude.gov.br/dataset/cnes-cadastro-nacional-de-estabelecimentos-de-saude` | resultado de busca (indica atualização diária — provavelmente **não** é a fotografia de jan/2024) | **D** |

- **Versão:** competência **2024-01**, UF RJ.
- **Relacionamento:** `dim_estabelecimento.cnes` (7 dígitos, texto) ↔ código CNES.
- **Riscos:** o arquivo `ST` pode não conter o **nome** do estabelecimento (verificar colunas);
  nesse caso, o nome viria do `TAB_CNES.zip` ou da extração por competência; renomeações e
  desativações; unicidade por CNES a testar.

## 4. SIGTAP — procedimentos, competência 2024-01 — prioridade 4

| Item | Evidência | Classe |
|---|---|---|
| `ftp://ftp2.datasus.gov.br/pub/sistemas/tup/downloads/` | repositórios `btran12/SIGTAP` e `RenatoKR/SIGTAP` sincronizam daqui diariamente (sucesso em 2026-11-10) | **B** |
| Padrão `TabelaUnificada_AAAAMM_vAAMMDDHHMM.zip` | arquivos baixados por essas automações (ex.: `TabelaUnificada_202601_v2601221740.zip`) | **B** |
| Existência da competência 202401 no FTP | as automações listam o diretório e pegam só os 6 últimos → o diretório guarda mais competências | inferência — **E** |
| Nome exato do arquivo 202401 (sufixo `v…` não dedutível) | — | **E** (listar) |
| Página de download `https://wiki.datasus.gov.br/sigtap/index.php/Download` | resultado de busca (arquivos .txt por competência + notas técnicas) | **D** |

- **Relacionamento:** `dim_procedimento.procedimento_cod` (10 dígitos) ↔ código do procedimento;
  `grupo_cod` ↔ código do grupo (confirma P-011).
- **Riscos:** procedimentos de AIHs de longa permanência iniciadas antes de 2024 podem não existir
  em 202401 → cobertura reportada e, se preciso, competência anterior **documentada**; o pacote tem
  várias tabelas e layout próprio (descrito no pacote). Licença: um espelho afirma "domínio
  público" — **afirmação de terceiro, não verificada**.

## 5. CID-10 — diagnósticos — prioridade 5

| Item | Evidência | Classe |
|---|---|---|
| Página "Tabelas da CID-10" `http://www2.datasus.gov.br/cid10/V2008/download.htm` e página dos CSV `http://www2.datasus.gov.br/cid10/V2008/descrcsv.htm` | resultado de busca | **D** |
| Arquivos `CID-10-CAPITULOS.CSV`, `CID-10-GRUPOS.CSV`, `CID-10-CATEGORIAS.CSV`, `CID-10-SUBCATEGORIAS.CSV` | presentes, com esses nomes, no pacote público `com.github.kyriosdata.cid10:cid10-dados:2008.1.0` (Maven Central, código-fonte) | **C** |
| Formato | ISO-8859-1, separador `;`, cabeçalho; chaves `SUBCAT` (4) e `CAT` (3) **sem ponto** | **C** |
| Arquivo zip/nome do download na página oficial | — | **E** |

- **Viabilidade medida (cópia de terceiro, não incorporada):** chaves únicas; dos 3.759 códigos do
  RD, 3.349 casam com `SUBCAT` e 410 com `CAT`; **0 sem correspondência**. Regra de junção:
  subcategoria e, na falta, categoria.
- **Riscos:** versão "V2008" × atualizações posteriores da CID-10 — refazer a cobertura com o
  arquivo oficial; termos de uso não verificados.

## Arquivos obtidos pela autora (revisão 4)

Baixados das fontes oficiais pela autora no Windows; tamanho e SHA-256 informados por ela; ZIPs
aprovados no teste de CRC. **Ainda não estão no ambiente de execução** (verificado: ausentes do
sistema de arquivos, das Releases e dos branches). Classe **A2** até serem conferidos aqui pelo
diagnóstico; depois, **A1**. Declarados em `config/params.yaml` → `reference_sources`.

| Arquivo | Origem oficial | Competência | Tamanho (bytes) | SHA-256 |
|---|---|---|---:|---|
| `STRJ2401.dbc` | `…/CNES/200508_/Dados/ST/` | 2024-01, RJ | 1.416.490 | `13f364d6f4e41f610717cc087d66e3ecb88ac63d834099b00b6f20f622ae7aa1` |
| `TAB_CNES.zip` | `…/CNES/200508_/Auxiliar/` | pacote vigente no download | 127.950.292 | `11c8876331f4255efa18a12daaee7ed3183db71376e57b8dc9de13196fb9b559` |
| `TabelaUnificada_202401_v2402072029.zip` | `ftp://ftp2.datasus.gov.br/pub/sistemas/tup/downloads/` | 2024-01 | 2.031.390 | `ea520664ab2f2e5fddf0aaa2ec5b82a1861d2ac9bc75c6194b906a9b0f13a367` |
| `municipios_ibge.json` | API IBGE `…/localidades/municipios` | data da consulta (a registrar) | ≈ 2,35 MB | **pendente** |
| `TAB_SIH.zip` | `…/SIHSUS/200801_/Auxiliar/` | pacote vigente no download | pendente | **pendente** |

Conteúdo informado pela autora: o SIGTAP contém `tb_procedimento.txt`/`tb_procedimento_layout.txt`
e `tb_cid.txt`/`tb_cid_layout.txt` (posições fixas conforme os layouts); o `TAB_CNES.zip` contém
`Estabelecimento.def` e tabelas auxiliares.

**Consequência para a CID-10:** o `tb_cid` do SIGTAP é tabela **oficial da mesma competência
(2024-01)**. Ele pode fornecer as descrições de diagnóstico, sem depender da publicação "V2008"
(a confirmar pela cobertura dos 3.759 códigos do RD).

## Preparação técnica (pronta, não executada sobre os arquivos reais)

| Componente | Função |
|---|---|
| `reference.parse_layout` / `read_sigtap_table` | lê o layout publicado **dentro do próprio ZIP** e recorta cada linha pelas posições oficiais; exige cabeçalho `Coluna,Tamanho,Inicio,Fim,Tipo`, tamanho = fim − início + 1, colunas contíguas e largura exata em todas as linhas; tudo como texto; só codificações de 1 byte (posição em bytes = posição em caracteres). Formato do layout corroborado por leitor público (`btran12/SIGTAP`); codificação Latin-1 **a confirmar** no arquivo real |
| leitura do `STRJ2401.dbc` | mesmo pipeline validado do RD (`convert_dbc_to_parquet`): tamanho do DBF, contagem do cabeçalho, encoding declarado — em diretório temporário, sem tocar `data/` |
| `reference.read_ibge_municipios` | `id` como texto, nome e UF a partir da hierarquia; falha se faltar a UF |
| `reference.key_report` / `coverage` | unicidade, vazios, comprimentos e não dígitos da chave; cobertura **a partir da dimensão**, com códigos não encontrados e **ambíguos** (chave repetida na referência = risco de multiplicação) |
| `reference.enrichment_guard` | reprova qualquer enriquecimento que mude nº de linhas, conjunto de chaves, duplique chaves ou altere colunas originais |
| `reference.fact_unchanged` | o fato tem de continuar byte a byte igual ao registrado em `reports/powerbi/export_summary.json` |
| `hospital-analytics reference-diagnose` | confere tamanho e SHA-256 **antes** de ler; arquivo divergente não é lido; gera `reports/reference/diagnostico_referencias.json` (estrutura, colunas reais, chaves, cobertura) |
| `tests/test_reference.py` | 22 testes com dados sintéticos (layout inconsistente, largura errada, chave duplicada, hash divergente, guarda de cardinalidade, fato inalterado) |

Nomes de coluna-chave esperados (`CNES`, `CO_PROCEDIMENTO`, `CO_CID`) são **hipóteses** em
`reference_sources`; o diagnóstico lista as colunas reais e marca a hipótese como não encontrada,
se for o caso.

## Transferência para o ambiente de execução

Mesmo método do `.dbc` do RD: uma **Release criada pela autora** (ex.: tag `ref-2024-01`) com os
arquivos como *assets*; o diagnóstico baixa pela API e confere os hashes. Para o `TAB_CNES.zip`
(128 MB), primeiro identificar **qual arquivo interno** contém os nomes dos estabelecimentos —
pode bastar transferir esse arquivo e o `Estabelecimento.def` (registrando o SHA-256 do ZIP de
origem e do arquivo extraído).

## Quadro de situação (revisão 3 — mantido como histórico)

| Fonte | Confirmado diretamente | Ainda pendente |
|---|---|---|
| SIH — dados | `…/SIHSUS/200801_/Dados/RDRJ2401.dbc` (**A1**) | — |
| SIH — auxiliares TabWin | pasta `…/200801_/Auxiliar/` e `TAB_SIH.zip` na listagem (**A2**) | download + SHA-256 de `TAB_SIH.zip`; documentação da AIH Reduzida (**D**) |
| IBGE | API `…/localidades/municipios` respondeu (**A2**) | SHA-256 e data/hora da consulta de `municipios_ibge.json`; termos de uso |
| CNES | pasta `…/CNES/200508_/Dados/` e subpasta `ST/` (**A2**) | listagem de `ST/` → nome exato do arquivo RJ 2024-01 + SHA-256; `TAB_CNES.zip` (**C**, pasta `Auxiliar/` do CNES ainda não listada) |
| SIGTAP | — | listagem de `ftp2…/tup/downloads/` (**B**) → nome exato `TabelaUnificada_202401_v….zip` + SHA-256 |
| CID-10 | — | página oficial (**D**) e arquivos CSV (**C**) + SHA-256 |

## Testes de aceitação (obrigatórios antes de qualquer integração)

1. **Fato intocado:** `fato_registro_aih.csv` byte a byte idêntico (SHA-256 em
   `reports/powerbi/export_summary.json`) → 73.046 registros e R$ 125.440.636,13 por construção;
   `registro_id` e `aih_id` inalterados.
2. **Dimensões:** mesmo número de linhas e mesmo conjunto de chaves; junção a partir da dimensão;
   chave da referência **única** (falha se duplicada); nenhuma nova relação no modelo.
3. **Integridade atual:** as 64 verificações de `make powerbi` e `make verify` continuam passando.
4. **Cobertura reportada, nunca forçada:** % de códigos com nome oficial por dimensão + lista dos
   não encontrados; sem correspondência aproximada.
5. **Proveniência:** cada arquivo de referência registrado em `data/MANIFEST.json` (URL, data,
   versão/competência, SHA-256, termos de uso) e conferido antes do uso.
6. **Secundária × oficial:** tabela comparativa dos rótulos atuais com os oficiais; divergências
   decididas explicitamente.
7. **Reprodutibilidade:** duas exportações seguidas com SHA-256 idênticos.

## Como obter os arquivos

**Opção B (escolhida) — download manual no Windows (PowerShell; use `curl.exe` com `.exe`).**
Primeiro **listar** (os nomes exatos saem da listagem), depois baixar e registrar o SHA-256 com
`Get-FileHash .\<arquivo> -Algorithm SHA256`. Para páginas web, anotar URL da página e do arquivo,
data, versão/competência e termos de uso.

**Alternativa a considerar — GitHub Actions no próprio repositório.** Como o FTP do DATASUS
responde ao GitHub Actions, um workflow manual (`workflow_dispatch`) poderia listar os diretórios e
baixar os arquivos com registro automático de SHA-256 — acesso direto, reproduzível e auditável.
Requer sua autorização (criação de workflow e decisão sobre onde guardar os arquivos).
