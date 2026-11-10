# Plano operacional de enriquecimento — fontes oficiais de referência

> **Status:** plano para aprovação (revisão 2). Nada foi integrado ao modelo. Dados originais,
> camadas, fato, identificadores técnicos e testes permanecem intactos.

## Classes de evidência

| Classe | Significado |
|---|---|
| **A — acessado diretamente** | o projeto obteve um arquivo oficial deste endereço e conferiu o SHA-256 |
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
| Pasta de dados `ftp://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/200801_/Dados/` | download do `RDRJ2401.dbc` (SHA-256 conferido) | **A** |
| Pacote auxiliar `ftp://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/200801_/Auxiliar/TAB_SIH.zip` | citado em página da SES-RJ ("Versão do Aplicativo TabWin SIHSUS") e em fórum (dadosabertos.social); descrito como atualizado mensalmente; não aparece em código | **D** |
| Página "Manuais do SIH" `http://www2.datasus.gov.br/SIHD/manuais` (Dicionário de Dados, layout da AIH Reduzida, Informes Técnicos) | resultado de busca | **D** |
| Página "Reduzida do AIH" `http://www2.datasus.gov.br/SIHD/reduzida` | resultado de busca | **D** |
| Nomes exatos dos documentos (PDF) | — | **E** |

- **Versão:** `TAB_SIH.zip` vigente no download (registrar data e SHA-256); documentação cuja
  vigência cubra a competência 2024-01.
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
| `https://servicodados.ibge.gov.br/api/v1/localidades/municipios` (todos) e `…/api/v1/localidades/estados/{UF}/municipios` | código do pacote PyPI `ibge` 0.0.5 + documentação indexada | **C** |
| Identificador do município com 7 dígitos | conhecimento prévio | **E** (verificar no JSON) |

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
| `ftp://ftp.datasus.gov.br/dissemin/publicos/CNES/200508_/Dados/` | código do `microdatasus` e do `PySUS` | **C** |
| Grupo `ST` = "Estabelecimentos" (nome do arquivo por grupo + UF + ano + mês) | código do `PySUS` | **C** |
| Subpasta e nome exato do arquivo RJ 2024-01 | — | **E** (listar) |
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
