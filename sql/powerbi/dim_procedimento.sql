-- Performed procedures (PROC_REA, SIGTAP code) and their SIGTAP group (first 2 digits).
-- Official names: SIGTAP Tabela Unificada of the same competence (2024-01). SIGTAP code
-- structure: group (2) + subgroup (2) + form of organisation (2) + sequence (3) + check digit.
-- Subgroup and form codes are prefixes of the procedure code (4 and 6 digits), so they are
-- unique across groups; every derived prefix must exist in the official tables (validated).
select
    b.PROC_REA as procedimento_cod,
    b.proc_rea_group as grupo_cod,
    c.label as grupo_descricao,
    c.source_status as grupo_fonte,
    p.nome as procedimento_nome,
    g.nome as grupo_nome_sigtap,
    left(b.PROC_REA, 4) as subgrupo_cod,
    s.nome as subgrupo_nome,
    left(b.PROC_REA, 6) as forma_organizacao_cod,
    f.nome as forma_organizacao_nome,
    case when p.nome is not null then (select label from ref_source where name = 'sigtap') end
        as procedimento_fonte
from (select distinct PROC_REA, proc_rea_group from base) b
left join codebook c on c.field = 'PROC_REA_GROUP' and c.code = b.proc_rea_group
left join ref_procedimento p on p.code = b.PROC_REA
left join ref_grupo g on g.code = b.proc_rea_group
left join ref_subgrupo s on s.code = left(b.PROC_REA, 4)
left join ref_forma f on f.code = left(b.PROC_REA, 6)
order by procedimento_cod
