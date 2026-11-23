-- Lorenz curve of VAL_TOT: cumulative share of value held by the poorest p% of records,
-- at every 5% of records (records sorted ascending by value). Processed layer.
with ranked as (
    select val_tot_cents,
           row_number() over (order by val_tot_cents, N_AIH, SEQUENCIA) as rn,
           count(*) over () as n,
           sum(val_tot_cents) over () as total
    from rd
),
cum as (
    select rn, n, total, sum(val_tot_cents) over (order by rn) as cum_cents from ranked
),
points as (select unnest(range(0, 101, 5)) as pct)
select
    pct,
    coalesce((select max(cum_cents) from cum where rn <= floor(n * pct / 100.0)), 0) as cum_cents,
    (select any_value(total) from cum) as total_cents
from points, (select any_value(n) as n from ranked)
order by pct
