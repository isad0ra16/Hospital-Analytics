-- Establishments (CNES). Every attribute below is functionally dependent on CNES in RDRJ2401
-- (verified: 0 CNES with more than one value). Names require the official CNES registry.
select
    CNES as cnes,
    any_value(MUNIC_MOV) as municipio_estabelecimento_cod,
    left(any_value(MUNIC_MOV), 2) as uf_estabelecimento_cod,
    any_value(NAT_JUR) as natureza_juridica_cod,
    any_value(GESTAO) as gestao_cod
from base
group by CNES
order by CNES
