-- Municipality of RESIDENCE of the patient record (MUNIC_RES). The establishment municipality
-- is an attribute of dim_estabelecimento: the two concepts are kept apart on purpose.
-- Names: IBGE API de Localidades. The 6-digit SIH code is the IBGE code without its check digit
-- (verified: unique 6-digit prefix in the IBGE list; RJ names equal to the DATASUS RJ_municip.cnv).
select
    b.MUNIC_RES as municipio_residencia_cod,
    left(b.MUNIC_RES, 2) as uf_residencia_cod,
    m.ibge_id as municipio_residencia_ibge,
    m.nome as municipio_residencia_nome,
    m.uf_sigla as uf_residencia_sigla,
    case when m.nome is not null then m.nome || ' (' || m.uf_sigla || ')' end
        as municipio_residencia_rotulo,
    case when m.nome is not null then (select label from ref_source where name = 'ibge') end
        as municipio_residencia_fonte
from (select distinct MUNIC_RES from base) b
left join ref_municipio m on m.code = b.MUNIC_RES
order by municipio_residencia_cod
