-- Generic small code dimension: every code present in the fact for $source_column, with its
-- codebook label and the source status of that interpretation. Built per dimension in Python.
select
    b.code,
    c.label as descricao,
    coalesce(c.source_status, 'sem rótulo na fonte disponível') as fonte
from (select distinct "$source_column" as code from base) b
left join codebook c on c.field = $field and c.code = b.code
order by b.code
