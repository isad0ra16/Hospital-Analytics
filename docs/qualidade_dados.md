# Qualidade dos dados — RDRJ2401 (Fase 3)

Auditoria somente leitura da base recuperada. Números completos e reproduzíveis em
[`reports/audit/audit_rdrj2401.md`](../reports/audit/audit_rdrj2401.md) (gerado por `make audit`;
consultas em `sql/audit/`). Nenhum registro foi removido ou corrigido.

## Resumo

| Dimensão | Resultado | Avaliação |
|---|---|---|
| Registros / colunas | 73.046 / 113 | ✅ conforme histórico |
| Linhas idênticas nas 113 colunas | 0 | ✅ sem duplicatas exatas |
| Datas inválidas (`DT_INTER`, `DT_SAIDA`, `NASC`) | 0 / 0 / 0 | ✅ |
| Saída antes da internação · nascimento após internação | 0 · 0 | ✅ |
| Internação ou saída após o fim da competência | 0 · 0 | ✅ |
| `VAL_TOT` vazio / negativo / malformado | 0 / 0 / 0 | ✅ |
| `VAL_TOT` = 0 | 241 registros | ℹ️ a investigar (Fase 5) |
| Valor com precisão reduzida pela largura do campo | 1 (`VAL_UTI`) | ℹ️ documentado (D-022) |
| `MORTE` × `COBRANCA` 4x (óbito) | coincidem nos 4.664 registros | ✅ consistência entre campos |
| Colunas 100% vazias | `NUM_PROC`, `CPF_AUT`, `GESTOR_DT`, `INFEHOSP`, `DIAGSEC8`, `DIAGSEC9` | ℹ️ `DIAGSEC9`/`INFEHOSP` coincidem com o histórico |
| Códigos fora do dicionário | `ESPEC` 10, 14, 87 (364 registros) | ⏳ pendente de fonte |

## Competência × internação × saída

Todos os registros têm competência **2024-01**, mas as datas de ocorrência são anteriores:

- **Saídas:** 29.279 em 2023 e 43.767 em 2024 (reproduz o histórico), entre 2023-08-01 e
  2024-01-31 — até 5 meses antes da competência (apresentação tardia de AIHs).
- **Internações:** desde 2012-01-02 (AIHs de longa permanência).

Consequência: a competência **não** é o período de ocorrência; análises temporais devem declarar
qual data usam (D-005).

## AIHs com número repetido

| Medida | Valor |
|---|---:|
| Registros excedentes | 56 |
| Números de AIH distintos | 50 |
| Registros envolvidos | 106 |
| Números com 2 / 3 / 4 registros | 45 / 4 / 1 |
| Números com registros de tipo 1 **e** 5 | 46 |
| Números só com tipo 5 | 4 |
| Números só com tipo 1 | 0 |

Colunas que variam dentro desses grupos: `DT_SAIDA` e `SEQUENCIA` (50 de 50 grupos), valores
(`VAL_SH`, `VAL_TOT`: 49), `IDENT` (46), `COBRANCA`/`DIAS_PERM` (45). Os registros **não são
duplicatas**: mesma AIH, períodos/apresentações diferentes, majoritariamente envolvendo longa
permanência. **Hipótese** (pendente da fonte primária): registros sucessivos de uma mesma
internação de longa permanência. Por isso nada é removido; a coluna `aih_repeated` apenas sinaliza.

## Permanência: `DIAS_PERM` × datas

`DIAS_PERM` difere de `DT_SAIDA − DT_INTER` em **660 registros, todos `IDENT` = 5**; para os
72.383 registros de tipo 1 os dois coincidem. Nas AIHs de longa permanência, `DIAS_PERM` mede o
período coberto pela AIH, não o tempo desde a internação (média por datas: 967 dias). O
indicador histórico usa `DIAS_PERM`.

## Idade: unidades de `COD_IDADE`

| `COD_IDADE` | Unidade (fonte secundária) | Registros | `IDADE` mín–máx |
|---|---|---:|---|
| 2 | dias | 2.126 | 0–30 |
| 3 | meses | 1.112 | 1–11 |
| 4 | anos | 69.776 | 1–99 |
| 5 | 100 + `IDADE` | 32 | 0–23 |

Os intervalos são coerentes com as unidades. Média de `IDADE` **sem** considerar a unidade = 43,96
(valor histórico) — critério incorreto; média convertida para anos = 43,85 (ver `indicadores.md`).

## Valores monetários

`VAL_TOT` = `VAL_SH + VAL_SP` em 72.704 registros (342 diferem). A soma dos 11 componentes
`VAL_SH … VAL_PED1AC` coincide com `VAL_TOT` exatamente nos mesmos 72.704 registros. A composição
de `VAL_TOT` nos 342 restantes não é interpretada sem a fonte primária.

## Completude

Campos com mais de 50% de vazios (não usados nos indicadores): `CID_NOTIF` 95,9%, `FAEC_TP` 90,9%,
`AUD_JUST`/`SIS_JUST` 98,9%, `DIAGSEC1` 79,2%, `DIAGSEC2`–`DIAGSEC7` > 96%.

## Limitações

- Interpretação dos códigos por **fonte secundária** (`microdatasus`); a fonte primária não pôde ser
  consultada deste ambiente (D-011, D-020).
- Unidade de análise = registro de AIH; não há identificador de paciente.
- Os relatórios omitem valores de colunas identificadoras ou de texto livre (D-026).
