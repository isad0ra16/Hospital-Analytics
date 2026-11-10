# Dicionário de variáveis — SIH/SUS RD

> ⚠️ **Nenhuma interpretação abaixo está confirmada.** As descrições na coluna "Hipótese atual"
> vêm de conhecimento prévio e precisam ser verificadas contra a documentação oficial do DATASUS
> (dicionário de dados / informe técnico do SIH) no início da Fase 3, antes de virarem regras.
> Ao confirmar, registrar a fonte (documento, versão, página/URL) e mudar o status.

Status: ⏳ não confirmado · ✅ confirmado (com fonte) · ⚠️ divergente da hipótese.

## Campos críticos para a reconciliação

| Campo | Hipótese atual (a confirmar) | Usado em | Status | Fonte oficial |
|---|---|---|---|---|
| `IDENT` | Identificação da AIH: 1 = principal/normal; 3 = continuação; 5 = longa permanência | Indicadores por tipo | ⏳ | — |
| `COD_IDADE` | Unidade de `IDADE` (ex.: dias, meses, anos, centenas de anos) | Idade média | ⏳ | — |
| `IDADE` | Idade na unidade indicada por `COD_IDADE` | Idade média | ⏳ | — |
| `DIAS_PERM` | Dias de permanência | Permanência média | ⏳ | — |
| `QT_DIARIAS` | Quantidade de diárias (alternativa para permanência) | Permanência média | ⏳ | — |
| `MORTE` | Indicador de óbito (0/1) | Óbitos, mortalidade | ⏳ | — |
| `CAR_INT` | Caráter da internação (ex.: eletivo, urgência, acidentes) — **não** clínico/cirúrgico | Classificação | ⏳ | — |
| `ESPEC` | Especialidade do leito (candidato à classificação clínico/cirúrgico) | Classificação | ⏳ | — |
| `PROC_REA` | Procedimento realizado (SIGTAP); grupo = 2 primeiros dígitos (candidato) | Classificação | ⏳ | — |
| `N_AIH` | Número da AIH | Repetições | ⏳ | — |
| `VAL_TOT` | Valor total da AIH (R$) | Financeiro | ⏳ | — |
| `ANO_CMPT`, `MES_CMPT` | Competência (ano/mês de processamento) | Recorte | ⏳ | — |
| `DT_INTER`, `DT_SAIDA` | Datas de internação e saída (AAAAMMDD) | Datas, permanência | ⏳ | — |
| `COBRANCA` | Motivo de saída/permanência (alternativa para óbito) | Óbitos | ⏳ | — |
| `DIAGSEC9`, `INFEHOSP` | Campos identificados como sem preenchimento no histórico | Qualidade | ⏳ | — |
