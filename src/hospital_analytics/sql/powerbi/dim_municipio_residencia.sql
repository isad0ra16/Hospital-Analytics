-- Municipality of RESIDENCE of the patient record (MUNIC_RES). The establishment municipality
-- is an attribute of dim_estabelecimento: the two concepts are kept apart on purpose.
select
    MUNIC_RES as municipio_residencia_cod,
    left(MUNIC_RES, 2) as uf_residencia_cod
from base
group by MUNIC_RES
order by MUNIC_RES
