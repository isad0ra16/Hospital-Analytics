-- Records, deaths, length of stay and value by age group (corrected age in years) and sex.
-- Age groups follow common epidemiological bands. Processed layer.
with g as (
    select *,
        case
            when age_years is null then 'sem informação'
            when age_years < 1 then '00 <1'
            when age_years < 5 then '01 1-4'
            when age_years < 15 then '02 5-14'
            when age_years < 30 then '03 15-29'
            when age_years < 45 then '04 30-44'
            when age_years < 60 then '05 45-59'
            when age_years < 75 then '06 60-74'
            else '07 75+'
        end as age_group
    from rd
)
select
    age_group,
    SEXO as sex_code,
    count(*) as records,
    count(*) filter (where died) as deaths,
    sum(dias_perm_int) as dias_perm_sum,
    sum(val_tot_cents) as val_tot_cents
from g
group by all
order by age_group, sex_code
