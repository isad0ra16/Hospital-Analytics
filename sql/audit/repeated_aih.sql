-- AIH numbers (N_AIH) occurring in more than one record. Records are flagged, never removed.
with counts as (
    select N_AIH, count(*) as occurrences, string_agg(distinct IDENT, ',' order by IDENT) as idents
    from rd
    group by N_AIH
    having count(*) > 1
)
select
    sum(occurrences - 1) as excess_records,
    count(*) as distinct_numbers,
    sum(occurrences) as records_involved,
    count(*) filter (where occurrences = 2) as numbers_twice,
    count(*) filter (where occurrences = 3) as numbers_three_times,
    count(*) filter (where occurrences >= 4) as numbers_four_or_more,
    count(*) filter (where idents = '5') as numbers_only_ident_5,
    count(*) filter (where idents = '1') as numbers_only_ident_1,
    count(*) filter (where idents = '1,5') as numbers_ident_1_and_5
from counts
