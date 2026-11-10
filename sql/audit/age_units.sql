-- IDADE range by unit code COD_IDADE (interpretation of units: codebook, secondary source).
select COD_IDADE, age_unit, count(*) as records, min(idade_int) as min_idade, max(idade_int) as max_idade
from rd
group by all
order by COD_IDADE
