-- Distribution of VAL_TOT (exact cents) per scope: quantiles use the discrete definition
-- (an observed value), so results stay exact. Processed layer.
with scoped as (
    select 'full' as scope, val_tot_cents from rd
    union all
    select 'ident_' || IDENT, val_tot_cents from rd
)
select
    scope,
    count(*) as records,
    count(*) filter (where val_tot_cents = 0) as zero_value,
    min(val_tot_cents) as min_cents,
    quantile_disc(val_tot_cents, 0.25) as p25_cents,
    quantile_disc(val_tot_cents, 0.5) as p50_cents,
    quantile_disc(val_tot_cents, 0.75) as p75_cents,
    quantile_disc(val_tot_cents, 0.9) as p90_cents,
    quantile_disc(val_tot_cents, 0.99) as p99_cents,
    max(val_tot_cents) as max_cents
from scoped
group by scope
order by scope
