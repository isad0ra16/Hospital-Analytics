-- Concentration across hospitals (CNES): records and value of the largest establishments.
with h as (
    select CNES, count(*) as records, sum(val_tot_cents) as val_tot_cents from rd group by CNES
),
r as (
    select *, row_number() over (order by val_tot_cents desc, CNES) as rank_value from h
)
select
    count(*) as hospitals,
    sum(records) as records,
    sum(val_tot_cents) as val_tot_cents,
    sum(val_tot_cents) filter (where rank_value <= 10) as top10_hospitals_cents,
    sum(records) filter (where rank_value <= 10) as top10_hospitals_records
from r
