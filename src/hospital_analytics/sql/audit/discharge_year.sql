-- Records by year of discharge (DT_SAIDA), processed layer.
-- Competence (ANO_CMPT/MES_CMPT) is the processing month, not the discharge month.
select discharge_year, count(*) as records
from rd
group by discharge_year
order by discharge_year
