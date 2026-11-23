-- Base for every Power BI table: one row per AIH record of the processed layer, with the
-- deterministic keys computed once (record id, pseudonymous AIH id, demographic profile).
-- Requires: view rd_file (processed layer read with file_row_number = true), table codebook.
create or replace temp table base as
with src as (
    select
        file_row_number + 1 as registro_id,
        dense_rank() over (order by N_AIH) as aih_id,
        *,
        case
            when age_years is null then 99
            when age_years < 1 then 0
            when age_years < 5 then 1
            when age_years < 15 then 2
            when age_years < 30 then 3
            when age_years < 45 then 4
            when age_years < 60 then 5
            when age_years < 75 then 6
            else 7
        end as faixa_etaria_ordem
    from rd_file
)
select
    *,
    dense_rank() over (order by faixa_etaria_ordem, SEXO, RACA_COR) as perfil_id
from src
