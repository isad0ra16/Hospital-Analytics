-- Records identical in all 113 original columns (raw layer). Nothing is removed.
select
    count(*) as records,
    count(*) - (select count(*) from (select distinct * from raw_rd)) as identical_duplicate_records
from raw_rd
