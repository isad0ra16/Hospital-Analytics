-- Date consistency checks (counts only; nothing is corrected). Processed layer.
-- Competence end = last day of the competence month.
with c as (
    select *, last_day(strptime(competence || '-01', '%Y-%m-%d')::date) as competence_end
    from rd
)
select
    count(*) as records,
    count(*) filter (where admission_date is null) as invalid_dt_inter,
    count(*) filter (where discharge_date is null) as invalid_dt_saida,
    count(*) filter (where birth_date is null) as invalid_dt_nasc,
    count(*) filter (where discharge_date < admission_date) as discharge_before_admission,
    count(*) filter (where birth_date > admission_date) as birth_after_admission,
    count(*) filter (where discharge_date > competence_end) as discharge_after_competence,
    count(*) filter (where admission_date > competence_end) as admission_after_competence,
    count(*) filter (where dias_perm_int <> los_days_from_dates) as los_differs_from_dates,
    count(*) filter (where dias_perm_int <> los_days_from_dates and IDENT = '1') as los_differs_ident_1,
    count(*) filter (where dias_perm_int <> los_days_from_dates and IDENT = '5') as los_differs_ident_5,
    min(admission_date) as min_dt_inter,
    max(admission_date) as max_dt_inter,
    min(discharge_date) as min_dt_saida,
    max(discharge_date) as max_dt_saida
from c
