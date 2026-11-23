-- Most frequent performed procedures (PROC_REA, SIGTAP code) and their value. Processed layer.
-- Procedure names are not available offline; codes only (see docs: pending SIGTAP table).
select PROC_REA as procedure, count(*) as records, count(*) filter (where died) as deaths,
       sum(dias_perm_int) as dias_perm_sum,
       sum(val_tot_cents) as val_tot_cents
from rd
group by all
order by records desc, procedure
limit $limit
