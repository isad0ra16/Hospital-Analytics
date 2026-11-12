-- Generic small code dimension: every code present in the fact for $source_column, with its
-- codebook label and the source status of that interpretation. Built per dimension in Python.
-- descricao_oficial: TabWin conversion table of the official SIH/SUS package ($official_source),
-- resolved in Python (tables official_code and ref_source); null when the table has no entry.
select
    b.code,
    c.label as descricao,
    coalesce(c.source_status, 'sem rótulo na fonte disponível') as fonte,
    o.label as descricao_oficial,
    case when o.label is not null
        then (select label from ref_source where name = 'tabwin_sih') || ' — ' || o.file
    end as fonte_oficial
from (select distinct "$source_column" as code from base) b
left join codebook c on c.field = $field and c.code = b.code
left join official_code o on o.source = $official_source and o.code = b.code
order by b.code
