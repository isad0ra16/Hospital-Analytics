-- Auxiliary table (no relationship) for the Lorenz curve of VAL_TOT on the FULL base: share of
-- the value held by the p% of records with the lowest value, p = 0..100. Same definition as
-- sql/analysis/lorenz.sql (ascending by value, ties by N_AIH and SEQUENCIA, cut at
-- floor(n * p / 100)); the export checks both agree. Static: it does not respond to slicers.
with ranked as (
    select
        val_tot_cents,
        row_number() over (order by val_tot_cents, N_AIH, SEQUENCIA) as rn,
        count(*) over () as n,
        sum(val_tot_cents) over () as total
    from base
),
cum as (
    select rn, n, total, sum(val_tot_cents) over (order by rn) as cum_cents from ranked
),
points as (select unnest(range(0, 101)) as p),
cuts as (
    select p, cast(floor(any_value(n) * p / 100.0) as bigint) as m, any_value(total) as total
    from points, (select n, total from ranked limit 1)
    group by p
)
select
    cast(c.p as integer) as percentil,
    cast(c.p / 100.0 as decimal(9, 6)) as pct_registros,
    cast(coalesce((select max(cum_cents) from cum where rn <= c.m), 0) / c.total
        as decimal(9, 6)) as pct_valor,
    cast(c.p / 100.0 as decimal(9, 6)) as igualdade
from cuts c
order by percentil
