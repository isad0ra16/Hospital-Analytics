-- Month dimension covering every admission and discharge month (full years). Dates are exported
-- at MONTH granularity on purpose (data minimisation: see docs/powerbi/privacidade.md).
-- The competence (2024-01) is a processing month, not a time series: see docs/powerbi/modelo.md.
with bounds as (
    select
        make_date(year(min(least(admission_date, discharge_date))), 1, 1) as m0,
        make_date(year(max(greatest(admission_date, discharge_date))), 12, 1) as m1
    from base
),
months as (
    select unnest(generate_series(m0, m1, interval 1 month))::date as mes from bounds
)
select
    mes,
    year(mes) as ano,
    quarter(mes) as trimestre,
    month(mes) as mes_num,
    strftime(mes, '%Y-%m') as ano_mes,
    year(mes) * 100 + month(mes) as ano_mes_ordem,
    [
        'jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'
    ][month(mes)] as mes_abrev
from months
order by mes
