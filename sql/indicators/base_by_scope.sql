-- Base aggregates per scope, as exact integers (means are derived from them afterwards).
-- Scopes: full base, and each AIH type (IDENT). Processed layer.
with scoped as (
    select 'full' as scope, * from rd
    union all
    select 'ident_' || IDENT as scope, * from rd
)
select
    scope,
    count(*) as records,
    sum(val_tot_cents) as val_tot_cents,
    sum(dias_perm_int) as dias_perm_sum,
    count(dias_perm_int) as dias_perm_count,
    sum(idade_int) as idade_raw_sum,
    count(idade_int) as idade_raw_count,
    sum(age_years) as age_years_sum,
    count(age_years) as age_years_count,
    count(*) filter (where died) as deaths
from scoped
group by scope
order by scope
