-- Performed procedures (PROC_REA, SIGTAP code) and their SIGTAP group (first 2 digits).
select
    b.PROC_REA as procedimento_cod,
    b.proc_rea_group as grupo_cod,
    c.label as grupo_descricao,
    c.source_status as grupo_fonte
from (select distinct PROC_REA, proc_rea_group from base) b
left join codebook c on c.field = 'PROC_REA_GROUP' and c.code = b.proc_rea_group
order by procedimento_cod
