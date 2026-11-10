# Dicionário de variáveis — SIH/SUS RD

> **Situação das fontes.** A fonte primária (DATASUS, *Informe Técnico SIH/SUS*) não pôde ser
> consultada deste ambiente (D-011). As interpretações abaixo vêm da **fonte secundária**
> `microdatasus` (Saldanha, Bastos & Barcellos; `R/process_sih.R`, commit `7109ec2`, 2026-07-29),
> que decodifica o SIH a partir da documentação oficial, e foram **corroboradas pelos dados** quando
> indicado. Nenhuma está marcada como confirmada pela fonte primária (pendência P-009).
> Fonte de verdade no código: `src/hospital_analytics/dictionary.py`.

Status: 🟦 fonte secundária + corroboração nos dados · 🟨 fonte secundária · ⬜ conhecimento prévio
(não verificado) · ⏳ sem fonte.

| Campo | Interpretação | Status | Evidência nos dados (RDRJ2401) |
|---|---|---|---|
| `IDENT` | 1 = principal · 3 = continuação · 5 = **longa permanência** | 🟦 | só 1 (72.383) e 5 (663) = contagens históricas |
| `COD_IDADE` | 0 ignorado · 2 dias · 3 meses · 4 anos · 5 centena de anos (100 + `IDADE`) | 🟦 | faixas de `IDADE` coerentes: 2→0–30, 3→1–11, 4→1–99, 5→0–23 |
| `IDADE` | idade na unidade de `COD_IDADE` | 🟦 | idem |
| `MORTE` | 0 não · 1 sim | 🟦 | `MORTE`=1 ⇔ `COBRANCA` 41–43 (óbito) nos 4.664 registros |
| `COBRANCA` | motivo de saída/permanência; 41–43 = óbito (lista parcial) | 🟦 | idem |
| `DIAS_PERM` | dias de permanência (na AIH) | 🟦 | = `DT_SAIDA − DT_INTER` em todo tipo 1; difere em 660 de tipo 5 |
| `CAR_INT` | 01 eletivo · 02 urgência · 03–06 acidentes/lesões | 🟨 | 01, 02, 05, 06 presentes |
| `ESPEC` | 01 cirúrgico · 02 obstétricos · 03 clínicos · 04 crônicos · 05 psiquiatria · 06 tisiologia · 07 pediátricos · 08 reabilitação · 09 leito dia/cirúrgicos | 🟨 | 10, 14, 87 sem decodificação (P-010) |
| `SEXO` | 1 masculino · 2/3 feminino | 🟨 | só 1 e 3 |
| `RACA_COR` | 01 branca · 02 preta · 03 parda · 04 amarela · 05 indígena · 99 sem informação | 🟨 | — |
| `COMPLEX` | 01 atenção básica · 02 média · 03 alta complexidade | 🟨 | só 02 e 03 |
| `PROC_REA` (grupo) | 2 primeiros dígitos = grupo SIGTAP: 02 diagnóstico · 03 clínicos · 04 cirúrgicos · 05 transplantes | ⬜ | usar 04/03 reproduz 51,57%/44,38% |
| `VAL_TOT` | valor total da AIH (R$) | 🟨 | soma = R$ 125.440.636,13 |
| `ANO_CMPT`, `MES_CMPT` | competência (processamento) | 🟦 | todos 2024/01; saídas desde 2023-08 |
| `DT_INTER`, `DT_SAIDA`, `NASC` | datas `AAAAMMDD` | 🟦 | 0 inválidas |
| `N_AIH` | número da AIH | 🟨 | 50 números em 106 registros (não são duplicatas exatas) |
| `SEQUENCIA` | sequencial do registro | ⏳ | varia em todos os grupos de AIH repetida |
| `DIAGSEC9`, `INFEHOSP` | sem preenchimento | — | 100% vazios (como no histórico) |

Para confirmar na fonte primária (P-009): baixar o *Informe Técnico SIH/SUS* da área de
documentação do SIHSUS no DATASUS (provavelmente a pasta `Doc` ao lado de `Dados` no FTP — caminho
não verificado deste ambiente) e comparar com esta tabela.
