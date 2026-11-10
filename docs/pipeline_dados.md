# Pipeline de dados — camada bruta (Fase 2)

Conversão **sem tratamento** do arquivo oficial do DATASUS para Parquet.
Código: `src/hospital_analytics/` · Testes: `tests/` · Decisões: D-011 a D-018 em
[`decisoes_metodologicas.md`](decisoes_metodologicas.md).

## Fluxo

```text
data/raw/RDRJ2401.dbc            (original, somente leitura, registrado no manifesto)
   │  1. dbc.py  — pyreaddbc.dbc2dbf (descompressão PKWare DCL "implode")
   ▼                verificação: tamanho = cabeçalho + nº registros × tamanho do registro
RDRJ2401.dbf                     (temporário; SHA-256 registrado e descartado)
   │  2. dbf.py  — dbfread em modo bruto (bytes), sem interpretar valores
   ▼                verificação: ativos + excluídos = registros declarados no cabeçalho
linhas de texto                  (bytes decodificados; somente o preenchimento de espaços removido)
   │  3. convert.py — tabela Apache Arrow com esquema explícito: 113 colunas `string`, não nulas
   ▼                escrita em .partial → releitura → impressão digital comparada → renomeação
data/raw/RDRJ2401.parquet        (somente leitura, registrado no manifesto)
   │  4. validate.py — registros, colunas, tipos, VAL_TOT exato, preservação
   ▼
relatório PASS/FAIL              (código de saída 1 em qualquer divergência)
```

## Como executar

```bash
make fetch-data   # baixa o .dbc da Release do GitHub e verifica o SHA-256
make convert      # .dbc -> Parquet (camada bruta)
make validate     # compara com as referências históricas e o manifesto
make verify       # confere todos os arquivos do manifesto
```

## Diferenças entre o DBF e o Parquet (o que muda e o que não muda)

| Aspecto | No DBF | No Parquet (camada bruta) | Justificativa |
|---|---|---|---|
| Valores | Texto de largura fixa | Mesmo texto, sem espaços de preenchimento | Preenchimento é formato, não dado |
| Tipos | `C` (caractere) e `N` (numérico) | **Todas** as colunas `string` | Nenhuma inferência de tipo; zeros à esquerda e casas decimais preservados. O tipo DBF original de cada campo fica nos metadados do Parquet |
| Nulos | Não existem: campo vazio = espaços | Campo vazio = `""`; colunas declaradas não anuláveis | Converter vazio em nulo é tratamento (Fase 3) |
| Encoding | Bytes | Decodificados como Latin-1 (reversível) | Ver pendência P-008 sobre CP850 |
| Ordem | Ordem física dos registros | Mesma ordem | A impressão digital do conteúdo depende da ordem |
| Registros excluídos (`*`) | Podem existir | Conversão é **interrompida** se houver | Exige decisão explícita; RDRJ2401 tem 0 |

Metadados gravados no Parquet (`hospital_analytics.raw_conversion`): SHA-256 da fonte, encoding,
especificação de cada campo DBF (tipo, tamanho, casas decimais) e a declaração de que nenhum
tratamento foi aplicado.

## Salvaguardas contra falhas silenciosas

As ferramentas de baixo nível não sinalizam alguns erros, então cada etapa tem verificação própria:

| Ferramenta | Falha silenciosa | Salvaguarda |
|---|---|---|
| `pyreaddbc.dbc2dbf` (C) | Em erro, apenas imprime mensagem; pode deixar `.dbf` vazio ou truncado | `check_dbf_size`: tamanho exato exigido pelo cabeçalho |
| `dbfread` | Pula registros com marcador desconhecido; não confere a contagem | `inspect_dbf`: ativos + excluídos = cabeçalho |
| Escrita do Parquet | Arquivo parcial em caso de interrupção | Escrita em `.partial`, verificação, `os.replace` atômico |
| Arquivos em disco | Alteração acidental | `chmod 444` + SHA-256 no manifesto + `make verify` |

## Impressão digital do conteúdo × SHA-256 do arquivo

- **SHA-256 do arquivo**: identidade byte a byte. Ideal para o `.dbc` oficial.
- **Impressão digital do conteúdo** (`ContentFingerprint`): SHA-256 sobre nomes de colunas e valores,
  na ordem, com prefixo de comprimento em cada valor. Prova que o Parquet contém exatamente os
  valores do DBF. Não depende de compressão nem da versão da biblioteca que escreveu o Parquet.

## Testes com dados sintéticos

Os testes usam arquivos **sintéticos** gerados em diretórios temporários (`tests/synthetic_data.py`),
com valores fictícios. Nenhum resultado sintético representa o Hospital Analytics. Para gerar
`.dbc` sintéticos, foi implementado um compressor mínimo PKWare DCL (apenas literais), derivado
do decodificador `blast.c` usado pela `pyreaddbc`; o teste `test_roundtrip_is_byte_identical`
comprova que o `dbc2dbf` real reconstrói o DBF original byte a byte.
