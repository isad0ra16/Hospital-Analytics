-- Monetary checks on exact integer cents (processed layer).
select
    count(*) filter (where val_tot_cents is null) as val_tot_blank,
    count(*) filter (where val_tot_cents = 0) as val_tot_zero,
    count(*) filter (where val_tot_cents < 0) as val_tot_negative,
    min(val_tot_cents) as val_tot_min_cents,
    max(val_tot_cents) as val_tot_max_cents,
    sum(val_tot_cents) as val_tot_sum_cents,
    count(*) filter (
        where val_tot_cents = val_sh_cents + val_sp_cents + val_sadt_cents + val_rn_cents
            + val_acomp_cents + val_ortp_cents + val_sangue_cents + val_sadtsr_cents
            + val_transp_cents + val_obsang_cents + val_ped1ac_cents
    ) as val_tot_equals_components,
    count(*) filter (where val_tot_cents = val_sh_cents + val_sp_cents) as val_tot_equals_sh_plus_sp
from rd
