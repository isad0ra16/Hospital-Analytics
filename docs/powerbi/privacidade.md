# Privacidade e risco de reidentificação

Os microdados RD do SIH/SUS são públicos e não contêm nomes. Ainda assim, combinações de atributos
(quasi-identificadores) podem tornar um registro único. Esta avaliação orientou o que é exportado
para o Power BI. A decisão sobre publicar o `.pbix` (que **incorpora os dados**) é posterior.

## O que não é exportado

`N_AIH` (substituído por `aih_id`), `NASC`, `CEP`, `CPF_AUT`, `GESTOR_CPF`, `INSC_PN`, textos livres
`AUD_JUST`/`SIS_JUST`, CNPJs (desnecessários) e as **datas por dia** (exportadas só como mês).
Lista completa em [`dicionario_campos.md`](dicionario_campos.md).

**`aih_id`** = posto denso do `N_AIH` ordenado: determinístico e adequado a contagens distintas.
**Não é anonimização:** quem tiver o arquivo público original pode reconstruir a correspondência.
Serve para não expor o número da AIH em visuais e arquivos derivados.

## Nomes oficiais acrescentados (enriquecimento)

Do cadastro CNES (CADGERRJ) só são lidos o código CNES e o **nome fantasia** dos estabelecimentos
presentes no fato — todos pessoas jurídicas (CNPJ de 14 dígitos nos 240; nenhum nome com sequência
de 11+ dígitos ou título pessoal, ver `diagnostico_referencias.md`). Razão social, CNPJ, endereço,
telefone e e-mail **nunca** são carregados (teste em `tests/test_enrichment.py`). Nomes de municípios
(IBGE), procedimentos e diagnósticos (SIGTAP) são tabelas públicas de códigos e não aumentam o risco
de reidentificação além do que os códigos já permitiam.

## Medição (k-anonimato) — registros únicos na base de 73.046

| Quasi-identificadores | Únicos (k = 1) | k < 5 |
|---|---:|---:|
| faixa etária + sexo + raça/cor | 0,0% | 0,0% |
| + município de residência | 1,4% | 5,3% |
| + município + estabelecimento | 9,9% | 24,4% |
| idade exata + sexo + município + **datas por dia** (internação e saída) | **89,4%** | 99,5% |
| idade exata + sexo + município + **meses** (exportação adotada) | **19,9%** | 45,1% |
| faixa + sexo + raça + município + meses | 7,3% | 19,3% |

164 municípios de residência têm menos de 5 registros.

## Conclusões

1. Reduzir as datas para **mês** derruba a proporção de registros únicos de 89,4% para 19,9% sem
   perder nenhuma análise planejada (a permanência continua exata em dias). Adotado (D-030).
2. O nível de **registro** mantém risco residual relevante. Antes de publicar um `.pbix` com dados
   importados, avaliar uma versão **agregada** (ex.: faixa etária em vez de idade exata, supressão
   de células com menos de 5 registros, municípios pequenos agrupados).
3. Os arquivos de `data/powerbi/` não são versionados (`.gitignore`) e são regenerados por
   `make powerbi`.
