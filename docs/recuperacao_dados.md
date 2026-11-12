# Estratégia de recuperação dos dados

O projeto original foi perdido junto com o computador. Esta estratégia garante que os dados
possam ser recuperados e **comprovados idênticos** mesmo que o ambiente de execução seja perdido.

## Três camadas de proteção

| Camada | O que guarda | Onde | Protege contra |
|---|---|---|---|
| 1. Código + manifesto | Pipeline, testes, `data/MANIFEST.json` (URLs, datas, tamanhos, SHA-256, impressões digitais) | Git (GitHub) | Perda do ambiente / computador |
| 2. Cópia arquivada do original | `RDRJ2401.dbc` exatamente como baixado | Release `data-rdrj2401` do GitHub (fora do histórico do Git) | Republicação ou indisponibilidade do DATASUS |
| 3. Fonte oficial | Arquivo publicado | FTP do DATASUS | Perda da Release |

Os arquivos derivados (Parquet) **não precisam de backup**: são regenerados pelo pipeline e
comprovados idênticos pela impressão digital do conteúdo registrada no manifesto.

## Procedimento de recuperação (do zero)

```bash
git clone https://github.com/isad0ra16/Hospital-Analytics.git
cd Hospital-Analytics
make install      # ambiente idêntico (uv.lock)
make fetch-data   # baixa o .dbc da Release e confere o SHA-256 com o manifesto
make convert      # regenera o Parquet
make validate     # confirma 73.046 registros, 113 colunas, R$ 125.440.636,13 e a impressão digital
```

Se a Release estiver indisponível, baixar do FTP oficial (`official_url` no manifesto) para
`data/raw/` e executar `make verify`. Se o SHA-256 **não** coincidir, o DATASUS publicou outra
versão do arquivo: ela deve ser registrada como **nova fonte**, nunca substituir a atual, e todos
os indicadores precisam ser reconciliados novamente.

## Arquivos oficiais de referência

Os nomes oficiais das dimensões vêm de arquivos baixados pela autora das fontes oficiais. Cada um está
declarado em `config/params.yaml` (`reference_sources`) com origem, competência, tamanho e SHA-256, e é
conferido **antes** de ser lido (`make verify` lista todos). Para reconstruir
`data/reference/incoming/` (pasta ignorada pelo git):

| Arquivo(s) | Origem oficial | Observação |
|---|---|---|
| `TabelaUnificada_202401_v2402072029.zip` | `ftp2.datasus.gov.br/pub/sistemas/tup/downloads/` | SIGTAP, competência 2024-01; copiar o ZIP |
| `municipios_ibge.json` | `servicodados.ibge.gov.br/api/v1/localidades/municipios` | a API não versiona: outra consulta pode ter outro SHA-256 → registrar como nova versão |
| `STRJ2401.dbc` | `ftp.datasus.gov.br/dissemin/publicos/CNES/200508_/Dados/ST/` | usado só pelo diagnóstico |
| `CADGERRJ.dbf`, `RJ_municip.cnv`, `TP_PFPJ.CNV`, `Estabelecimento.def` | membros `DBF/`, `CNV/` e raiz de `TAB_CNES.zip` (`…/CNES/200508_/Auxiliar/`) | extrair só esses (o ZIP tem 128 MB) |
| `RD2008.DEF` e 10 arquivos `.CNV` (`LEITOS`, `IDENT`, `CARATEND`, `COMPLEX2`, `SEXO`, `RACACOR`, `natjur`, `esferajur`, `GESTAO`, `CID10CAP`) | membros de `TAB_SIH.zip` (`…/SIHSUS/200801_/Auxiliar/`) | extrair só esses; SHA-256 do ZIP também registrado |

Os pacotes auxiliares do DATASUS são atualizados sem versão no nome: um download novo pode trazer
membros diferentes. Se algum SHA-256 divergir, o arquivo **não é lido** — registre a nova versão em
`config/params.yaml` (com data e origem) e reconcilie a cobertura (`make powerbi`).

Recomendação: arquivar estes arquivos como o `.dbc` (Release própria, ex.: `ref-2024-01`) — hoje eles
existem só na cópia local da autora.

## Identificação da versão dos dados

O DATASUS não versiona os arquivos. A versão é identificada por:

1. **SHA-256** do `.dbc`: `a3f0ea9a6ce75099fa8210d81b13736fc4da4ac1acf30e8245c7aa3a0d7dfc9c`;
2. **data de última atualização** gravada no cabeçalho DBF: **2025-02-08**;
3. **data do download**: 2026-11-09.

## Recomendações

- Manter também uma cópia offline pessoal do `.dbc` (por exemplo, em armazenamento em nuvem
  pessoal), com o SHA-256 anotado.
- Não editar nem substituir o asset da Release `data-rdrj2401`. Se precisar de outra versão,
  criar outra Release com outra tag.
- Considerar proteger a tag nas configurações do repositório (*Rules → Tag rulesets*).
