-- Records by discharge month (DT_SAIDA), per AIH type. Competence is 2024-01 for all.
select strftime(discharge_date, '%Y-%m') as discharge_month, IDENT, count(*) as records
from rd
group by all
order by discharge_month, IDENT
