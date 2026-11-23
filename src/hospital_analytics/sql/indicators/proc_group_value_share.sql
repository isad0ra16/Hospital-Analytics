-- VAL_TOT and record counts by SIGTAP group of the performed procedure (PROC_REA).
-- $ident: NULL for the full base, or an IDENT code.
select
    proc_rea_group,
    count(*) as records,
    sum(val_tot_cents) as val_tot_cents
from rd
where $ident::varchar is null or IDENT = $ident::varchar
group by proc_rea_group
order by proc_rea_group
