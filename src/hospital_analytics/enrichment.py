"""Official reference data used to enrich the Power BI dimensions (names and descriptions).

Every file is checked (size and SHA-256 against ``config/params.yaml``) BEFORE it is read; a
missing or divergent file stops the export. Only the columns needed for the model are kept:
from the CNES registry, the CNES code and the trade name (``FANTASIA``) — never the legal
name, CPF/CNPJ, address, phone or e-mail.

Joins are by exact code only (never by name or approximate match). Reference keys must be
unique: a duplicated key would multiply dimension rows and is reported as an error.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hospital_analytics.dbf import decode_value, inspect_dbf, iter_raw_rows
from hospital_analytics.integrity import check_declared
from hospital_analytics.reference import (
    CnvTable,
    ReferenceFormatError,
    clean_label,
    read_cnv_table,
    read_ibge_municipios,
    read_sigtap_table,
)

REQUIRED_SOURCES = (
    "sigtap",
    "ibge_municipios",
    "cnes_cadger",
    "sih_leitos",
    "sih_ident",
    "sih_carater",
    "sih_complexidade",
    "sih_sexo",
    "sih_raca_cor",
    "sih_natureza_juridica",
    "sih_esfera_juridica",
    "sih_gestao",
    "sih_cid10_capitulo",
)


class ReferenceIntegrityError(Exception):
    """A reference file is missing or differs from its declared size or SHA-256."""


@dataclass
class References:
    """Lookups built from the official files (all keys and values are text)."""

    procedimento: dict[str, str]  # CO_PROCEDIMENTO -> NO_PROCEDIMENTO
    grupo: dict[str, str]  # CO_GRUPO -> NO_GRUPO
    subgrupo: dict[str, str]  # CO_GRUPO + CO_SUB_GRUPO (4) -> NO_SUB_GRUPO
    forma: dict[str, str]  # grupo + subgrupo + forma (6) -> NO_FORMA_ORGANIZACAO
    cid: dict[str, str]  # CO_CID (3 or 4 characters) -> NO_CID
    municipio: dict[str, dict[str, str]]  # 6-digit prefix of the IBGE id -> id, nome, uf_sigla
    estabelecimento: dict[str, str]  # CNES -> FANTASIA
    cnv: dict[str, CnvTable]  # source name -> TabWin table
    cnv_start: dict[str, int]  # source name -> start position in the RD field (RD2008.DEF)
    sources: dict[str, str] = field(default_factory=dict)  # source name -> provenance label
    provenance: dict[str, dict[str, Any]] = field(default_factory=dict)


def verify(path: Path, spec: dict[str, Any]) -> dict[str, Any]:
    """Size and SHA-256 of ``path`` against ``spec``; raise on any difference."""
    result = check_declared(path, {"size_bytes": spec["size_bytes"], "sha256": spec["sha256"]})
    if not result["present"]:
        raise ReferenceIntegrityError(
            f"{path.name}: reference file not found in {path.parent} "
            "(copy it there; see docs/01_fontes_de_dados.md)"
        )
    if not result["integrity_ok"]:
        raise ReferenceIntegrityError(
            f"{path.name}: size/SHA-256 {result['size_bytes']}/{result['sha256']} differ from the "
            f"declared {spec['size_bytes']}/{spec['sha256']} — the file is not read"
        )
    return {k: result[k] for k in ("file", "size_bytes", "sha256")}


def _unique(pairs: list[tuple[str, str]], what: str) -> dict[str, str]:
    """Key -> value; a duplicated or blank key is an error (it would multiply rows)."""
    out: dict[str, str] = {}
    duplicated: set[str] = set()
    for key, value in pairs:
        if key in out:
            duplicated.add(key)
        out[key] = value
    if duplicated:
        raise ReferenceFormatError(
            f"{what}: duplicated keys {sorted(duplicated)[:5]} (join fan-out)"
        )
    if "" in out:
        raise ReferenceFormatError(f"{what}: blank key")
    return out


def load_references(incoming: Path, sources: dict[str, Any]) -> References:
    """Verify and read every official reference file needed by the model."""
    incoming = Path(incoming)
    missing = [s for s in REQUIRED_SOURCES if s not in sources]
    if missing:
        raise ReferenceIntegrityError(f"reference sources not declared in params: {missing}")
    provenance = {
        name: verify(incoming / sources[name]["filename"], sources[name])
        for name in REQUIRED_SOURCES
    }

    sigtap = incoming / sources["sigtap"]["filename"]

    def sigtap_lookup(table: str, key_columns: tuple[str, ...], name_column: str) -> dict:
        rows = read_sigtap_table(sigtap, table)
        pairs = [("".join(r[c] for c in key_columns), r[name_column]) for r in rows]
        return _unique(pairs, f"SIGTAP {table}")

    procedimento = sigtap_lookup("tb_procedimento", ("CO_PROCEDIMENTO",), "NO_PROCEDIMENTO")
    grupo = sigtap_lookup("tb_grupo", ("CO_GRUPO",), "NO_GRUPO")
    subgrupo = sigtap_lookup("tb_sub_grupo", ("CO_GRUPO", "CO_SUB_GRUPO"), "NO_SUB_GRUPO")
    forma = sigtap_lookup(
        "tb_forma_organizacao",
        ("CO_GRUPO", "CO_SUB_GRUPO", "CO_FORMA_ORGANIZACAO"),
        "NO_FORMA_ORGANIZACAO",
    )
    cid = sigtap_lookup("tb_cid", ("CO_CID",), "NO_CID")

    ibge_rows = read_ibge_municipios(incoming / sources["ibge_municipios"]["filename"])
    _unique([(r["id"][:6], r["nome"]) for r in ibge_rows], "IBGE municipalities (6-digit prefix)")
    municipio = {
        r["id"][:6]: {"id": r["id"], "nome": r["nome"], "uf_sigla": r["uf_sigla"]}
        for r in ibge_rows
    }

    cadger = sources["cnes_cadger"]
    path, enc = incoming / cadger["filename"], cadger["encoding"]
    info = inspect_dbf(path, enc)
    names = info.field_names
    key_i, name_i = names.index(cadger["key_column"]), names.index(cadger["name_column"])
    # Only the key and the trade name leave the DBF: no legal name, CNPJ, address or contacts.
    estabelecimento = _unique(
        [
            (decode_value(r[key_i], enc), decode_value(r[name_i], enc))
            for r in iter_raw_rows(path, enc)
        ],
        "CNES CADGER",
    )

    cnv_names = [s for s in REQUIRED_SOURCES if sources[s].get("kind") == "cnv"]
    cnv = {s: read_cnv_table(incoming / sources[s]["filename"]) for s in cnv_names}
    cnv_start = {s: int(sources[s]["start"]) for s in cnv_names}

    def package(name: str) -> str:
        return sources[name]["official_package"].split(" (")[0]

    return References(
        procedimento=procedimento,
        grupo=grupo,
        subgrupo=subgrupo,
        forma=forma,
        cid=cid,
        municipio=municipio,
        estabelecimento=estabelecimento,
        cnv=cnv,
        cnv_start=cnv_start,
        sources={
            "sigtap": f"SIGTAP {sources['sigtap']['competence']} ({sigtap.stem})",
            "ibge": "IBGE API de Localidades (arquivo de "
            f"{sources['ibge_municipios']['file_timestamp'][:10]})",
            "cnes": f"CNES {cadger['filename']} (cadastro atualizado em {info.last_update})",
            "tabwin_sih": f"TabWin SIH/SUS ({package('sih_leitos')})",
        },
        provenance=provenance,
    )


# ---------------------------------------------------------------------------
# Official labels of RD codes (TabWin conversion tables)
# ---------------------------------------------------------------------------
CID_CHAPTER = re.compile(r"^([IVXL]+\.)\s*")


def official_label(refs: References, source: str, code: str) -> tuple[str | None, str | None]:
    """(label, category sequence) of ``code`` in a TabWin table, or (None, None)."""
    table = refs.cnv[source]
    entry = table.resolve(code, refs.cnv_start[source])
    if entry is None:
        return None, None
    if source == "sih_esfera_juridica":
        label = table.full_label(entry)
    elif source == "sih_cid10_capitulo":
        label = CID_CHAPTER.sub(r"\1 ", " ".join(entry.label.split()))
    else:
        label = clean_label(" ".join(entry.label.split()), code)
    return label, entry.sequence


def official_code_rows(refs: References, codes: dict[str, list[str]]) -> list[tuple]:
    """Rows (source, code, label, sequence) for every distinct code of each TabWin source."""
    return [
        (source, code, *official_label(refs, source, code))
        for source, values in codes.items()
        for code in sorted(set(values))
    ]
