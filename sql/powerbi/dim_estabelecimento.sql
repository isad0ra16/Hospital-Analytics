-- Establishments (CNES). Every attribute below is functionally dependent on CNES in RDRJ2401
-- (verified: 0 CNES with more than one value).
-- Names: trade name (FANTASIA) of the CNES registry CADGERRJ — the same source the official
-- TabWin definition (Estabelecimento.def) uses for "Nome Fantasia". The registry is the one
-- current at download (not 2024-01): see estabelecimento_nome_fonte. Legal name, CNPJ, address
-- and contacts are never loaded. Labels of NAT_JUR and GESTAO: official SIH TabWin tables.
with e as (
    select
        CNES as cnes,
        any_value(MUNIC_MOV) as municipio_estabelecimento_cod,
        left(any_value(MUNIC_MOV), 2) as uf_estabelecimento_cod,
        any_value(NAT_JUR) as natureza_juridica_cod,
        any_value(GESTAO) as gestao_cod
    from base
    group by CNES
)
select
    e.*,
    n.nome as estabelecimento_nome,
    case when n.nome is not null then n.nome || ' (' || e.cnes || ')' end
        as estabelecimento_rotulo,
    m.nome as municipio_estabelecimento_nome,
    m.uf_sigla as uf_estabelecimento_sigla,
    nj.label as natureza_juridica_descricao,
    ej.label as esfera_juridica,
    g.label as gestao_descricao,
    case when n.nome is not null then (select label from ref_source where name = 'cnes') end
        as estabelecimento_nome_fonte
from e
left join ref_estabelecimento n on n.code = e.cnes
left join ref_municipio m on m.code = e.municipio_estabelecimento_cod
left join official_code nj
    on nj.source = 'sih_natureza_juridica' and nj.code = e.natureza_juridica_cod
left join official_code ej
    on ej.source = 'sih_esfera_juridica' and ej.code = e.natureza_juridica_cod
left join official_code g on g.source = 'sih_gestao' and g.code = e.gestao_cod
order by e.cnes
