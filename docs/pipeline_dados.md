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
| Encoding | Bytes (cabeçalho declara CP850, *language driver* `0x02`) | Decodificados em **CP850** (reversível para os 256 bytes) | D-019; conversão recusa encoding que contradiga o cabeçalho |
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
- **Impressão digital dos bytes brutos**: o mesmo cálculo sobre os bytes de cada campo (sem
  preenchimento), antes de decodificar. Não depende do encoding; é recalculável a partir do
  Parquet recodificando o texto (`parquet_fingerprint(..., encode_with="cp850")`), porque o
  espaço é o único byte que decodifica para `" "`. Prova que reinterpretar texto nunca altera dados.

## Testes com dados sintéticos

Os testes usam arquivos **sintéticos** gerados em diretórios temporários (`tests/synthetic_data.py`),
com valores fictícios. Nenhum resultado sintético representa o Hospital Analytics. Para gerar
`.dbc` sintéticos, foi implementado um compressor mínimo PKWare DCL (apenas literais), derivado
do decodificador `blast.c` usado pela `pyreaddbc`; o teste `test_roundtrip_is_byte_identical`
comprova que o `dbc2dbf` real reconstrói o DBF original byte a byte.

---

# Camada tratada (Fase 3)

Arquivo: `data/processed/sih_rj_2024_01_tratado.parquet` · Código: `processed.py` ·
Comando: `make processed` · Decisões: D-020 a D-024.

**Convenção:** colunas em `MAIÚSCULAS` são os 113 campos originais, copiados sem nenhuma alteração
(a impressão digital dessas colunas é verificada e registrada no manifesto: idêntica à da camada
bruta). Colunas em `minúsculas` são derivadas. Nenhum registro é removido, filtrado ou reordenado.
Nomes derivados não podem coincidir com originais **ignorando maiúsculas** (o DuckDB resolve nomes
sem distinguir caixa), o que é verificado no build.

## Conversões de formato (reversíveis, verificadas linha a linha)

| Coluna | Tipo | Origem | Regra |
|---|---|---|---|
| `<campo>_cents` | int64 | cada campo DBF `N` com 2 decimais (ex.: `VAL_TOT` → `val_tot_cents`) | texto → centavos inteiros; reconversão deve reproduzir o texto |
| `<campo>_int` | int64 | cada campo DBF `N` sem decimais (ex.: `DIAS_PERM` → `dias_perm_int`, `IDADE` → `idade_int`) | texto → inteiro; reconversão deve reproduzir o texto |
| `competence` | string | `ANO_CMPT`, `MES_CMPT` | `AAAA-MM` |
| `admission_date` | date | `DT_INTER` | `AAAAMMDD` → data; inválida → nula e contada |
| `discharge_date` | date | `DT_SAIDA` | idem |
| `birth_date` | date | `NASC` | idem |
| `discharge_year` | int16 | `DT_SAIDA` | ano de `discharge_date` |

**Precisão reduzida pela largura do campo:** em `VAL_UTI` (`N8.2`), o valor `166200.00` não cabe em 8
caracteres e o sistema de origem gravou `166200.0`. Esse caso é aceito **somente** quando a forma
completa excede a largura e difere apenas por zeros finais; é contado no manifesto
(`reduced_precision_values`). Qualquer outro formato interrompe o build.

## Colunas estruturais (sem interpretação de códigos)

| Coluna | Tipo | Origem | Regra |
|---|---|---|---|
| `los_days_from_dates` | int32 | `DT_INTER`, `DT_SAIDA` | `discharge_date − admission_date` em dias |
| `proc_rea_group` | string | `PROC_REA` | 2 primeiros caracteres (grupo SIGTAP) |
| `aih_occurrences` | int32 | `N_AIH` | nº de registros com o mesmo número de AIH |
| `aih_repeated` | bool | `N_AIH` | `aih_occurrences > 1` — **apenas sinaliza; nada é removido** |

## Interpretações de códigos (dependem do dicionário — `dictionary.py`)

| Coluna | Tipo | Origem | Regra | Fonte |
|---|---|---|---|---|
| `age_unit` | string | `COD_IDADE` | rótulo do código | secundária |
| `age_years` | float64 | `COD_IDADE`, `IDADE` | 2: `IDADE/365,25` · 3: `IDADE/12` · 4: `IDADE` · 5: `100 + IDADE` · outros: nulo | secundária |
| `died` | bool | `MORTE` | `MORTE = '1'` | secundária |
| `ident_label` | string | `IDENT` | rótulo do código | secundária |
| `proc_rea_group_label` | string | `PROC_REA` | rótulo do grupo SIGTAP | conhecimento prévio |

"Secundária" = pacote `microdatasus`; a fonte primária (Informe Técnico SIH/SUS) não pôde ser
consultada deste ambiente. Ver [`dicionario_variaveis.md`](dicionario_variaveis.md).
