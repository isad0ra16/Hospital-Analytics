-- MORTE versus the first digit of COBRANCA (discharge reason; 4x = death in the codebook).
select MORTE, left(COBRANCA, 1) as cobranca_group, count(*) as records
from rd
group by all
order by MORTE, cobranca_group
