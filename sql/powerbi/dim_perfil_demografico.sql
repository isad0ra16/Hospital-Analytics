-- Demographic PROFILE of the record (age band x sex x race/colour). This is NOT a patient
-- dimension: the SIH RD file has no patient identifier.
-- *_oficial: labels from the official SIH/SUS TabWin tables (SEXO.CNV, RACACOR.CNV).
select distinct
    b.perfil_id,
    b.faixa_etaria_ordem,
    case b.faixa_etaria_ordem
        when 0 then '< 1 ano' when 1 then '1–4' when 2 then '5–14' when 3 then '15–29'
        when 4 then '30–44' when 5 then '45–59' when 6 then '60–74' when 7 then '75+'
        else 'sem informação'
    end as faixa_etaria,
    b.SEXO as sexo_cod,
    s.label as sexo_descricao,
    b.RACA_COR as raca_cor_cod,
    r.label as raca_cor_descricao,
    os.label as sexo_descricao_oficial,
    orc.label as raca_cor_descricao_oficial
from base b
left join codebook s on s.field = 'SEXO' and s.code = b.SEXO
left join codebook r on r.field = 'RACA_COR' and r.code = b.RACA_COR
left join official_code os on os.source = 'sih_sexo' and os.code = b.SEXO
left join official_code orc on orc.source = 'sih_raca_cor' and orc.code = b.RACA_COR
order by b.perfil_id
