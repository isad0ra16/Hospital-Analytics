-- Length of stay (DIAS_PERM) distribution per AIH type, with Tukey fences (Q3 + 1.5 IQR).
-- Outliers are counted, never removed. Processed layer.
with q as (
    select IDENT,
           quantile_disc(dias_perm_int, 0.25) as p25,
           quantile_disc(dias_perm_int, 0.5) as p50,
           quantile_disc(dias_perm_int, 0.75) as p75,
           quantile_disc(dias_perm_int, 0.9) as p90,
           quantile_disc(dias_perm_int, 0.99) as p99,
           min(dias_perm_int) as min_days,
           max(dias_perm_int) as max_days,
           count(*) as records,
           count(*) filter (where dias_perm_int = 0) as zero_days
    from rd
    group by IDENT
)
select q.*,
       p75 + 1.5 * (p75 - p25) as upper_fence,
       (select count(*) from rd where rd.IDENT = q.IDENT and dias_perm_int > p75 + 1.5 * (p75 - p25))
           as above_upper_fence
from q
order by IDENT
