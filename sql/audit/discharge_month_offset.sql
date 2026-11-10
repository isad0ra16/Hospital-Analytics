-- Months between discharge and competence (0 = discharge in the competence month).
select
    date_diff('month', date_trunc('month', discharge_date), strptime(competence || '-01', '%Y-%m-%d')::date)
        as months_before_competence,
    IDENT,
    count(*) as records
from rd
group by all
order by months_before_competence, IDENT
