-- Principal diagnosis (DIAG_PRINC, CID-10): one row per code present in the fact.
-- Names: SIGTAP tb_cid of the same competence (2024-01); category = first 3 characters, named
-- when tb_cid lists the 3-character code. Chapter: official SIH TabWin table CID10CAP.CNV,
-- which TabWin applies to the first 3 characters of DIAG_PRINC (RD2008.DEF).
select
    b.DIAG_PRINC as diagnostico_cod,
    c.nome as diagnostico_nome,
    case when c.nome is not null then b.DIAG_PRINC || ' · ' || c.nome end as diagnostico_rotulo,
    left(b.DIAG_PRINC, 3) as categoria_cod,
    k.nome as categoria_nome,
    cast(ch.sequence as integer) as capitulo_ordem,
    ch.label as capitulo,
    case when c.nome is not null then (select label from ref_source where name = 'sigtap') end
        as diagnostico_fonte
from (select distinct DIAG_PRINC from base) b
left join ref_cid c on c.code = b.DIAG_PRINC
left join ref_cid k on k.code = left(b.DIAG_PRINC, 3)
left join official_code ch on ch.source = 'sih_cid10_capitulo' and ch.code = b.DIAG_PRINC
order by diagnostico_cod
