-- Records, deaths, length of stay and value by category, for several dimensions at once.
-- Codes are decoded in Python with the codebook (dictionary.py). Processed layer.
select 'IDENT' as dimension, IDENT as code, count(*) as records, count(*) filter (where died) as deaths,
       sum(dias_perm_int) as dias_perm_sum, sum(val_tot_cents) as val_tot_cents from rd group by all
union all
select 'ESPEC', ESPEC, count(*), count(*) filter (where died), sum(dias_perm_int), sum(val_tot_cents) from rd group by all
union all
select 'CAR_INT', CAR_INT, count(*), count(*) filter (where died), sum(dias_perm_int), sum(val_tot_cents) from rd group by all
union all
select 'COMPLEX', COMPLEX, count(*), count(*) filter (where died), sum(dias_perm_int), sum(val_tot_cents) from rd group by all
union all
select 'PROC_REA_GROUP', proc_rea_group, count(*), count(*) filter (where died), sum(dias_perm_int), sum(val_tot_cents) from rd group by all
union all
select 'SEXO', SEXO, count(*), count(*) filter (where died), sum(dias_perm_int), sum(val_tot_cents) from rd group by all
union all
select 'RACA_COR', RACA_COR, count(*), count(*) filter (where died), sum(dias_perm_int), sum(val_tot_cents) from rd group by all
order by dimension, code
