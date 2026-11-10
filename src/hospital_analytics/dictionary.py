"""Codebook of SIH/SUS RD fields used by the project, with the source of every interpretation.

The primary source (DATASUS "Informe Técnico SIH/SUS", published in the ``Doc`` folder of the
DATASUS FTP) could not be reached from the execution environment (decision D-011). Until it is
consulted, interpretations come from a secondary source and are marked as such:

* ``secondary``: taken from the ``microdatasus`` R package (Saldanha, Bastos & Barcellos), which
  decodes SIH files from the official documentation; corroborated by the real data where noted.
* ``prior_knowledge``: general knowledge not yet verified in any source during this project.

No interpretation here is labelled as confirmed by the primary source.
"""

from __future__ import annotations

from dataclasses import dataclass

SECONDARY_SOURCE = (
    "microdatasus (Saldanha, Bastos & Barcellos), R/process_sih.R, "
    "github.com/rfsaldanha/microdatasus commit 7109ec2 (2026-07-29)"
)
PRIMARY_SOURCE_PENDING = "DATASUS Informe Técnico SIH/SUS (not yet consulted)"


@dataclass(frozen=True)
class FieldCodes:
    field: str
    description: str
    codes: dict[str, str]
    source: str
    status: str  # "secondary" | "prior_knowledge"
    evidence: str = ""
    complete: bool = True  # False when only some codes are listed on purpose


CODEBOOK: dict[str, FieldCodes] = {
    "IDENT": FieldCodes(
        "IDENT",
        "Identificação do tipo da AIH",
        {"1": "Principal", "3": "Continuação", "5": "Longa permanência"},
        SECONDARY_SOURCE,
        "secondary",
        "RDRJ2401 has only codes 1 (72,383) and 5 (663), matching the historical counts. "
        "The historical label 'continuidade' for code 5 does not match the source "
        "('Longa permanência'); 'Continuação' is code 3, absent from this file.",
    ),
    "COD_IDADE": FieldCodes(
        "COD_IDADE",
        "Unidade de medida do campo IDADE",
        {
            "0": "Ignorado",
            "2": "Dias",
            "3": "Meses",
            "4": "Anos",
            "5": "Centena de anos (idade = 100 + IDADE)",
        },
        SECONDARY_SOURCE,
        "secondary",
        "Code 5 occurs with IDADE between 0 and 23, consistent with '100 + IDADE'.",
    ),
    "MORTE": FieldCodes(
        "MORTE",
        "Indicador de óbito",
        {"0": "Não", "1": "Sim"},
        SECONDARY_SOURCE,
        "secondary",
        "MORTE = 1 for exactly the 4,664 records whose COBRANCA starts with 4 (deaths).",
    ),
    "COBRANCA": FieldCodes(
        "COBRANCA",
        "Motivo de saída/permanência",
        {
            "41": "Óbito com DO fornecida pelo médico assistente",
            "42": "Óbito com DO fornecida pelo IML",
            "43": "Óbito com DO fornecida pelo SVO",
        },
        SECONDARY_SOURCE,
        "secondary",
        "Only the death codes are listed; used as an independent cross-check of MORTE.",
        complete=False,
    ),
    "CAR_INT": FieldCodes(
        "CAR_INT",
        "Caráter da internação",
        {
            "01": "Eletivo",
            "02": "Urgência",
            "03": "Acidente no local de trabalho ou a serviço da empresa",
            "04": "Acidente no trajeto para o trabalho",
            "05": "Outros tipos de acidente de trânsito",
            "06": "Outros tipos de lesões e envenenamentos por agentes químicos ou físicos",
        },
        SECONDARY_SOURCE,
        "secondary",
        "Stored with two digits in RDRJ2401 (the source lists them without the leading zero).",
    ),
    "ESPEC": FieldCodes(
        "ESPEC",
        "Especialidade do leito",
        {
            "01": "Cirúrgico",
            "02": "Obstétricos",
            "03": "Clínicos",
            "04": "Crônicos",
            "05": "Psiquiatria",
            "06": "Pneumologia sanitária (tisiologia)",
            "07": "Pediátricos",
            "08": "Reabilitação",
            "09": "Leito dia / cirúrgicos",
        },
        SECONDARY_SOURCE,
        "secondary",
        "Codes 10, 14 and 87 occur in RDRJ2401 and are not decoded here (pending).",
    ),
    "SEXO": FieldCodes(
        "SEXO",
        "Sexo do paciente",
        {"1": "Masculino", "2": "Feminino", "3": "Feminino"},
        SECONDARY_SOURCE,
        "secondary",
        "RDRJ2401 uses only 1 and 3.",
    ),
    "RACA_COR": FieldCodes(
        "RACA_COR",
        "Raça/cor",
        {
            "01": "Branca",
            "02": "Preta",
            "03": "Parda",
            "04": "Amarela",
            "05": "Indígena",
            "99": "Sem informação",
        },
        SECONDARY_SOURCE,
        "secondary",
    ),
    "COMPLEX": FieldCodes(
        "COMPLEX",
        "Complexidade",
        {"01": "Atenção básica", "02": "Média complexidade", "03": "Alta complexidade"},
        SECONDARY_SOURCE,
        "secondary",
    ),
    "PROC_REA_GROUP": FieldCodes(
        "PROC_REA_GROUP",
        "Grupo da Tabela SIGTAP do procedimento realizado (2 primeiros dígitos de PROC_REA)",
        {
            "02": "Procedimentos com finalidade diagnóstica",
            "03": "Procedimentos clínicos",
            "04": "Procedimentos cirúrgicos",
            "05": "Transplantes de órgãos, tecidos e células",
        },
        "SIGTAP table structure (prior knowledge; not yet verified in a source)",
        "prior_knowledge",
        "Using groups 04/03 as surgical/clinical reproduces the historical 51.57%/44.38% "
        "exactly (share of VAL_TOT, IDENT 1), so the original project used this grouping.",
    ),
}


def label(field_name: str, code: str) -> str | None:
    """Decoded label for a code, or None when the code is not in the codebook."""
    return CODEBOOK[field_name].codes.get(code)
