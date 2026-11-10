-- Share of VAL_TOT held by the top k records by VAL_TOT, k = floor(n * $fraction).
-- $ident: NULL for the full base, or an IDENT code. Ties at the cut are broken by N_AIH, SEQUENCIA.
with base as (
    select val_tot_cents, N_AIH, SEQUENCIA from rd where $ident::varchar is null or IDENT = $ident::varchar
),
ranked as (
    select val_tot_cents,
           row_number() over (order by val_tot_cents desc, N_AIH, SEQUENCIA) as rn,
           count(*) over () as n
    from base
)
select
    any_value(n) as records,
    floor(any_value(n) * $fraction::decimal(10, 4))::bigint as top_records,
    sum(val_tot_cents) filter (where rn <= floor(n * $fraction::decimal(10, 4))) as top_cents,
    sum(val_tot_cents) as total_cents
from ranked
