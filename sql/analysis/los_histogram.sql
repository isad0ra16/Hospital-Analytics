-- Records per DIAS_PERM value for AIH type 1 (values above $cap are grouped in the last bin).
select least(dias_perm_int, $cap) as days, count(*) as records
from rd
where IDENT = '1'
group by all
order by days
