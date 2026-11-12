# 3. Tratamento: camada tratada e dicionário de variáveis

## Objetivo

Tornar os campos utilizáveis (números, datas, idade em anos, sinalizações) **sem alterar nem remover
nada** do arquivo original, com cada interpretação de código ligada à fonte que a justifica.

Arquivo: `data/processed/sih_rj_2024_01_tratado.parquet` · Código: `processed.py`, `dictionary.py` ·
Comando: `hospital-analytics build-processed` · Decisões: D-004, D-020 a D-023, D-025, D-027.

## Procedimento

**Convenção:** colunas em `MAIÚSCULAS` são os 113 campos originais, copiados sem alteração; colunas em
`minúsculas` são derivadas (50). A impressão digital das colunas originais é recalculada e registrada
no manifesto: idêntica à da camada bruta (`b3dfcaba…`). Nenhum registro é removido, filtrado ou
reordenado (D-004, D-021). Nomes derivados não podem coincidir com originais **ignorando maiúsculas**,
porque o DuckDB resolve nomes sem distinguir caixa — um defeito real encontrado na auditoria (D-023).

### Conversões de formato (reversíveis, verificadas linha a linha)

| Coluna | Tipo | Origem | Regra |
| --- | --- | --- | --- |
| `<campo>_cents` | int64 | cada campo `N` com 2 decimais (ex.: `val_tot_cents`) | texto → centavos inteiros; a reconversão deve reproduzir o texto |
| `<campo>_int` | int64 | cada campo `N` sem decimais (ex.: `dias_perm_int`, `idade_int`) | texto → inteiro; idem |
| `competence` | string | `ANO_CMPT`, `MES_CMPT` | `AAAA-MM` |
| `admission_date`, `discharge_date`, `birth_date` | date | `DT_INTER`, `DT_SAIDA`, `NASC` | `AAAAMMDD` → data; inválida → nula e contada |
| `discharge_year` | int16 | `DT_SAIDA` | ano da saída |

**Precisão reduzida pela largura do campo (D-022).** Em `VAL_UTI` (`N8.2`), `166200.00` não cabe em 8
caracteres e a origem gravou `166200.0`. Esse caso só é aceito quando a forma completa excede a largura
e difere apenas por zeros finais; é contado no manifesto (`reduced_precision_values`: 1). Qualquer
outro formato interrompe o build. Uma eventual segunda casa decimal perdida na origem vale no máximo
R$ 0,09 e não afeta `VAL_TOT`.

### Colunas estruturais (sem interpretação de códigos)

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `los_days_from_dates` | int32 | `discharge_date − admission_date` em dias |
| `proc_rea_group` | string | 2 primeiros caracteres de `PROC_REA` (grupo SIGTAP) |
| `aih_occurrences` | int32 | nº de registros com o mesmo `N_AIH` |
| `aih_repeated` | bool | `aih_occurrences > 1` — **apenas sinaliza; nada é removido** |

### Interpretações de códigos

| Coluna | Origem | Regra | Fonte |
| --- | --- | --- | --- |
| `age_unit` | `COD_IDADE` | rótulo do código | secundária |
| `age_years` | `COD_IDADE`, `IDADE` | 2: `IDADE/365,25` · 3: `IDADE/12` · 4: `IDADE` · 5: `100 + IDADE` · outros: nulo | secundária |
| `died` | `MORTE` | `MORTE = '1'` | secundária |
| `ident_label` | `IDENT` | rótulo do código | secundária |
| `proc_rea_group_label` | `PROC_REA` | rótulo do grupo SIGTAP | conhecimento prévio, confirmado depois pelo SIGTAP oficial |

## Dicionário de variáveis

As interpretações foram feitas primeiro com uma **fonte secundária pública e citável**, o pacote
`microdatasus` (Saldanha, Bastos & Barcellos; `R/process_sih.R`, commit `7109ec2`), que decodifica o
SIH a partir da documentação oficial, sempre **corroborada pelos dados** quando possível (D-020). Cada
código em `dictionary.py` declara fonte e status. Depois, os rótulos dos códigos foram confrontados
com o **dicionário oficial do SIH para o TabWin** (`TAB_SIH.zip`, D-036); o modelo analítico usa os
rótulos oficiais e mantém os secundários ao lado ([`04_modelagem.md`](04_modelagem.md)).

| Campo | Interpretação | Evidência nos dados (`RDRJ2401`) | Fonte oficial (TabWin) |
| --- | --- | --- | --- |
| `IDENT` | 1 = AIH normal (principal) · 5 = longa permanência | só 1 (72.383) e 5 (663) = contagens históricas | `IDENT.CNV`: 1 "Normal", 5 "Longa permanência" |
| `COD_IDADE` / `IDADE` | 2 dias · 3 meses · 4 anos · 5 = 100 + `IDADE` | faixas coerentes: 2→0–30, 3→1–11, 4→1–99, 5→0–23 | — |
| `MORTE` / `COBRANCA` | `MORTE` 1 = óbito; `COBRANCA` 41–43 = saída por óbito | `MORTE` = 1 ⇔ `COBRANCA` 4x nos 4.664 registros | — |
| `DIAS_PERM` | dias de permanência da AIH | = `DT_SAIDA − DT_INTER` em todo o tipo 1; difere em 660 registros de tipo 5 | — |
| `CAR_INT` | 01 eletivo · 02 urgência · 05/06 acidentes e lesões | 01, 02, 05, 06 presentes | `CARATEND.CNV` (textos abreviados em 05/06) |
| `ESPEC` | especialidade do leito | 12 códigos; 10, 14 e 87 sem rótulo na fonte secundária | `LEITOS.CNV`: 10 "Leito Dia / Aids", 14 "Leito Dia / Saúde Mental", 87 "Saúde Mental (Clínico)" |
| `SEXO` | 1 masculino · 2/3 feminino | só 1 e 3 | `SEXO.CNV`: 1 Masculino; 2,3 Feminino |
| `RACA_COR` | 01 branca · 02 preta · 03 parda · 04 amarela · 05 indígena · 99 sem informação | — | `RACACOR.CNV` (iguais) |
| `COMPLEX` | 02 média · 03 alta complexidade | só 02 e 03 | `COMPLEX2.CNV` (iguais) |
| `PROC_REA` (grupo) | 02 diagnóstico · 03 clínicos · 04 cirúrgicos · 05 transplantes | usar 04/03 reproduz 51,57%/44,38% | SIGTAP `tb_grupo` 2024-01 (iguais; grafia oficial "orgãos") |
| `NAT_JUR`, `GESTAO` | natureza jurídica e tipo de gestão do estabelecimento | 16 naturezas; gestão 1 e 2 | `natjur.cnv`, `esferajur.cnv`, `GESTAO.CNV` |
| `DIAG_PRINC` | diagnóstico principal, CID-10 sem ponto | 3.759 códigos | SIGTAP `tb_cid` 2024-01; capítulo por `CID10CAP.CNV` |
| `N_AIH` | número da AIH | 50 números em 106 registros (não são duplicatas exatas) | — |
| `SEQUENCIA` | sequencial do registro | varia em todos os grupos de AIH repetida | — |

**Idade (D-025).** A média histórica de 43,96 só é reproduzida somando `IDADE` sem considerar a unidade
(um recém-nascido de 15 dias conta como 15 anos). A idade em anos corrigida é **43,85**; ambas são
publicadas, e só a corrigida deve ser usada em conclusões.

**Tipos de AIH (D-027).** O rótulo histórico "continuidade" para o tipo 5 é citado apenas como
referência; o tipo 5 é longa permanência segundo a fonte secundária, os dados e a tabela oficial.

## Verificações

- Impressão digital das 113 colunas originais idêntica à da camada bruta.
- Conversões de formato reversíveis linha a linha; 0 datas inválidas em `DT_INTER`, `DT_SAIDA`, `NASC`.
- 73.046 registros na entrada e na saída; colisão de nomes ignorando caixa recusada por teste.
- SHA-256 do Parquet tratado `cdab78f8…` — idêntico no Linux e no Windows.

## Limitações

- A semântica de alguns campos não tem documento primário: o significado de `DIAS_PERM` na longa
  permanência e a composição de `VAL_TOT` em 342 registros (P-009, parcial).
- `proc_rea_group_label` e os rótulos de `dictionary.py` permanecem secundários na camada tratada; os
  rótulos oficiais são aplicados no modelo analítico.
