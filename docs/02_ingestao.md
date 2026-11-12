# 2. Ingestão: do `.dbc` à camada bruta

## Objetivo

Converter o arquivo oficial `RDRJ2401.dbc` para Parquet **sem nenhum tratamento**, provando que
nenhum valor nem byte original foi perdido ou alterado.

Código: `dbc.py`, `dbf.py`, `convert.py`, `manifest.py`, `validate.py` · Comandos: `hospital-analytics convert`,
`validate` e `verify` · Decisões: D-008, D-011 a D-019, D-040.

## Procedimento

```text
data/raw/RDRJ2401.dbc            original, somente leitura, registrado no manifesto
   │  1. dbc.py  — pyreaddbc.dbc2dbf (descompressão PKWare DCL "implode"), em processo filho
   ▼                verificação: tamanho = cabeçalho + nº de registros × tamanho do registro
RDRJ2401.dbf                     temporário; SHA-256 registrado e descartado
   │  2. dbf.py  — dbfread em modo bruto (bytes), sem interpretar valores
   ▼                verificação: ativos + excluídos = registros declarados no cabeçalho
linhas de texto                  bytes decodificados em CP850; só o preenchimento de espaços removido
   │  3. convert.py — tabela Apache Arrow com esquema explícito: 113 colunas string, não nulas
   ▼                escrita em .partial → releitura → impressões digitais comparadas → renomeação
data/raw/RDRJ2401.parquet        somente leitura, registrado no manifesto
   │  4. validate.py — registros, colunas, tipos, VAL_TOT exato, preservação
   ▼
relatório PASS/FAIL              código de saída 1 em qualquer divergência
```

## O que muda e o que não muda entre DBF e Parquet

| Aspecto | No DBF | Na camada bruta | Justificativa |
| --- | --- | --- | --- |
| Valores | texto de largura fixa | mesmo texto, sem espaços de preenchimento | preenchimento é formato, não dado |
| Tipos | `C` e `N` | **todas** as colunas `string`; o tipo DBF de cada campo fica nos metadados | inferir tipos apagaria zeros à esquerda e introduziria `float` em valores monetários (D-012) |
| Nulos | não existem (vazio = espaços) | vazio = `""`; colunas não anuláveis | converter vazio em nulo é tratamento |
| Encoding | bytes; o cabeçalho declara CP850 (*language driver* `0x02`) | decodificados em **CP850**, reversível para os 256 bytes | a conversão recusa um encoding que contradiga o cabeçalho (D-019) |
| Ordem | ordem física | mesma ordem | a impressão digital depende da ordem |
| Registros excluídos (`*`) | podem existir | a conversão é **interrompida** | exige decisão explícita; `RDRJ2401` tem 0 (D-017) |

Metadados gravados no Parquet (`hospital_analytics.raw_conversion`): SHA-256 da fonte, encoding,
especificação de cada campo DBF e a declaração de que nenhum tratamento foi aplicado. A tabela em
memória é construída diretamente em Arrow, em lotes de 10.000 registros, porque o pandas inferiria
tipos (D-013).

## Salvaguardas contra falhas silenciosas

A leitura do código-fonte das ferramentas mostrou que algumas não sinalizam erros (D-014):

| Ferramenta | Falha silenciosa | Salvaguarda |
| --- | --- | --- |
| `pyreaddbc.dbc2dbf` (C) | em erro, apenas imprime uma mensagem; pode deixar `.dbf` vazio ou truncado e **não fecha o arquivo de saída** | tamanho exato exigido pelo cabeçalho; execução em processo filho isolado, que libera o arquivo em qualquer sistema e captura a mensagem (D-040) |
| `dbfread` | pula registros com marcador desconhecido; não confere a contagem | ativos + excluídos = cabeçalho |
| Escrita do Parquet | arquivo parcial se interrompida | `.partial`, verificação e `os.replace` atômico (D-016) |
| Arquivos em disco | alteração acidental | somente leitura, SHA-256 no manifesto e `hospital-analytics verify` |

## Duas provas de preservação

- **SHA-256 do arquivo**: identidade byte a byte — usado para o `.dbc` oficial.
- **Impressão digital do conteúdo**: SHA-256 sobre nomes de colunas e valores, na ordem, com prefixo de
  comprimento em cada valor. Prova que o Parquet tem exatamente os valores do DBF e não depende da
  compressão nem da versão da biblioteca (D-015).
- **Impressão digital dos bytes brutos**: o mesmo cálculo sobre os bytes de cada campo antes da
  decodificação. Não depende do encoding e é recalculável a partir do Parquet recodificando o texto
  (o espaço é o único byte que decodifica para `" "`). Prova que reinterpretar o texto nunca alterou
  um dado.

## Resultados

| Verificação | Resultado |
| --- | --- |
| Registros · colunas | 73.046 · 113 (= cabeçalho DBF e = histórico) |
| `VAL_TOT` | soma exata R$ 125.440.636,13; 0 vazios, 0 malformados |
| Registros excluídos | 0 |
| Impressão digital do conteúdo | `b3dfcaba…f0e67c7` |
| Impressão digital dos bytes brutos | `6ea7c886…4ee607e` |
| SHA-256 do Parquet bruto | `de7000cd…59a831` — idêntico no Linux e no Windows |
| Colunas 100% vazias | `NUM_PROC`, `CPF_AUT`, `GESTOR_DT`, `INFEHOSP`, `DIAGSEC8`, `DIAGSEC9` |

**Correção de encoding (D-019).** A primeira conversão usou Latin-1. O cabeçalho declara CP850, e em
23 valores de `AUD_JUST` os bytes `0x90`/`0xA0` apareciam como caracteres de controle. Com CP850,
somente essas 23 células mudaram de texto (`RECÉM` ×13, `USUáRIO` ×10 — o "á" minúsculo está no dado
de origem) e os caracteres de controle na base caíram de 13 para 0. A impressão digital dos bytes
brutos ficou idêntica antes e depois, provando que nenhum valor original mudou. A entrada anterior é
mantida em `history` no manifesto (substituição explícita, `convert --supersede`).

## Testes com dados sintéticos

Os testes usam apenas arquivos **sintéticos**, gerados em diretórios temporários
(`tests/synthetic_data.py`). Para gerar `.dbc`, foi implementado um compressor mínimo PKWare DCL
(apenas literais), derivado do decodificador `blast.c` usado pela `pyreaddbc`; um teste comprova que
o `dbc2dbf` real reconstrói o DBF original byte a byte. Outros cobrem arquivo truncado, lixo,
encoding contraditório, registros excluídos e escrita interrompida.

## Limitações

- A `pyreaddbc` é AGPL-3.0; o uso como dependência é compatível, mas pesa na escolha da licença do
  projeto (P-007).
- O tipo DBF é preservado apenas como metadado: qualquer uso numérico exige a camada tratada.
