-- Fact table: 1 row = 1 AIH record (not a patient, not necessarily a distinct admission).
-- Identifying fields (N_AIH, NASC, CEP, CPF fields, free text) are NOT exported.
select
    registro_id,
    aih_id,
    competence as competencia,
    date_trunc('month', discharge_date)::date as mes_saida,
    date_trunc('month', admission_date)::date as mes_internacao,
    CNES as cnes,
    MUNIC_RES as municipio_residencia_cod,
    PROC_REA as procedimento_cod,
    DIAG_PRINC as diagnostico_principal_cod,
    ESPEC as especialidade_cod,
    CAR_INT as carater_cod,
    COMPLEX as complexidade_cod,
    IDENT as tipo_aih_cod,
    perfil_id,
    cast(VAL_TOT as decimal(18, 2)) as valor_total,
    val_tot_cents as valor_total_centavos,
    dias_perm_int as dias_permanencia,
    los_days_from_dates as dias_entre_datas,
    cast(age_years as decimal(12, 6)) as idade_anos,
    cast(died as integer) as obito,
    aih_occurrences as aih_ocorrencias,
    cast(aih_repeated as integer) as aih_repetida
from base
order by registro_id
