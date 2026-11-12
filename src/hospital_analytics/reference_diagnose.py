"""Diagnostic of the official reference files before any enrichment (read-only).

Looks for the files declared in ``config/params.yaml`` (``reference_sources``) in an incoming
directory, verifies size and SHA-256 BEFORE reading, then reports structure, key quality and
coverage against the current Power BI dimensions. It never modifies the model or the data layers.
"""

from __future__ import annotations

import csv
import json
import tempfile
import zipfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from hospital_analytics.config import load_params
from hospital_analytics.convert import convert_dbc_to_parquet
from hospital_analytics.dbf import decode_value, inspect_dbf, iter_raw_rows
from hospital_analytics.integrity import check_declared
from hospital_analytics.reference import (
    ReferenceFormatError,
    coverage,
    key_report,
    read_cnv_table,
    read_ibge_municipios,
    read_sigtap_table,
)


def _dimension_keys(powerbi_dir: Path, table: str, column: str) -> list[str]:
    path = powerbi_dir / f"{table}.csv"
    with path.open(encoding="utf-8", newline="") as fh:
        return [row[column] for row in csv.DictReader(fh)]


def diagnose_cnes_st(path: Path, spec: dict, powerbi_dir: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        report = convert_dbc_to_parquet(
            path, Path(tmp) / "st.parquet", expected_source_sha256=spec["sha256"]
        )
        table = pq.read_table(Path(tmp) / "st.parquet")
    out: dict[str, Any] = {
        "records": report.records,
        "columns": [f["name"] for f in report.dbf_fields],
        "dbf_declared_encoding": report.dbf_declared_encoding,
        "dbf_last_update": report.dbf_last_update,
    }
    key = spec["key_column"]
    if key not in table.column_names:
        out["key_column_found"] = False
        return out
    keys = table.column(key).to_pylist()
    out["key_column_found"] = True
    out["key"] = asdict(key_report(key, keys))
    dim = _dimension_keys(powerbi_dir, "dim_estabelecimento", "cnes")
    out["coverage"] = asdict(coverage("dim_estabelecimento", dim, path.name, keys))
    return out


def diagnose_sigtap(path: Path, spec: dict, powerbi_dir: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as zf:
        out: dict[str, Any] = {"members": sorted(zf.namelist()), "crc_ok": zf.testzip() is None}
    for table, tspec in spec["tables"].items():
        entry: dict[str, Any] = {}
        try:
            rows = read_sigtap_table(path, table)
        except ReferenceFormatError as exc:
            out[table] = {"error": str(exc)}
            continue
        entry["rows"] = len(rows)
        entry["columns"] = list(rows[0]) if rows else []
        key = tspec["key_column"]
        if not rows or key not in rows[0]:
            entry["key_column_found"] = False
            out[table] = entry
            continue
        keys = [r[key] for r in rows]
        entry["key_column_found"] = True
        entry["key"] = asdict(key_report(key, keys))
        dim_table, dim_column = tspec["dimension"].split(".")
        dim = _dimension_keys(powerbi_dir, dim_table, dim_column)
        entry["coverage"] = asdict(coverage(dim_table, dim, f"{path.name}:{table}", keys))
        out[table] = entry
    return out


def diagnose_tab_cnes(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as zf:
        infos = zf.infolist()
        return {
            "crc_ok": zf.testzip() is None,
            "members": len(infos),
            "by_extension": _count_ext(i.filename for i in infos),
            "def_files": sorted(i.filename for i in infos if i.filename.lower().endswith(".def")),
        }


def _count_ext(names) -> dict[str, int]:
    counts: dict[str, int] = {}
    for n in names:
        ext = Path(n).suffix.lower() or "(sem extensão)"
        counts[ext] = counts.get(ext, 0) + 1
    return dict(sorted(counts.items()))


def diagnose_ibge(path: Path, powerbi_dir: Path) -> dict[str, Any]:
    rows = read_ibge_municipios(path)
    ids = [r["id"] for r in rows]
    prefixes = [i[:6] for i in ids]
    out = {
        "records": len(rows),
        "id_key": asdict(key_report("id", ids)),
        "prefix6_key": asdict(key_report("id[:6]", prefixes)),
    }
    res = _dimension_keys(powerbi_dir, "dim_municipio_residencia", "municipio_residencia_cod")
    est = _dimension_keys(powerbi_dir, "dim_estabelecimento", "municipio_estabelecimento_cod")
    out["coverage_residencia"] = asdict(
        coverage("dim_municipio_residencia", res, path.name, ids, transform=lambda i: i[:6])
    )
    out["coverage_estabelecimento"] = asdict(
        coverage("dim_estabelecimento.municipio", est, path.name, ids, transform=lambda i: i[:6])
    )
    return out


def diagnose_cadger(path: Path, spec: dict, powerbi_dir: Path) -> dict[str, Any]:
    """Aggregates only: never returns names, CPF/CNPJ, addresses, phones or e-mails."""
    enc = spec["encoding"]
    info = inspect_dbf(path, enc)
    names = info.field_names
    by: dict[str, dict[str, str]] = {}
    keys = []
    for raw in iter_raw_rows(path, enc):
        row = {k: decode_value(v, enc) for k, v in zip(names, raw, strict=True)}
        keys.append(row["CNES"])
        by[row["CNES"]] = row
    dim = {
        r["cnes"]: r
        for r in csv.DictReader((powerbi_dir / "dim_estabelecimento.csv").open(encoding="utf-8"))
    }
    sel = [by[c] for c in dim if c in by]
    fantasia = [r[spec["name_column"]] for r in sel]
    counts: dict[str, int] = {}
    for n in fantasia:
        counts[n] = counts.get(n, 0) + 1
    width = next(f.length for f in info.fields if f.name == spec["name_column"])
    return {
        "records": info.numrecords,
        "deleted_records": info.deleted_records,
        "dbf_last_update": info.last_update,
        "language_driver": f"0x{info.language_driver:02x}",
        "fields": names,
        "key": asdict(key_report("CNES", keys)),
        "coverage": asdict(coverage("dim_estabelecimento", list(dim), path.name, keys)),
        "among_model_establishments": {
            "name_blank": sum(1 for n in fantasia if not n),
            "distinct_names": len(counts),
            "repeated_name_groups": sum(1 for c in counts.values() if c > 1),
            "establishments_with_repeated_name": sum(c for c in counts.values() if c > 1),
            "names_at_field_width": sum(1 for n in fantasia if len(n) == width),
            "excluded_flag": dict(sorted(_count(r["EXCLUIDO"] for r in sel).items())),
            "cpf_cnpj_length": dict(sorted(_count(str(len(r["CPF_CNPJ"])) for r in sel).items())),
            "municipality_equals_rd": sum(
                1
                for c, d in dim.items()
                if c in by and by[c]["CODUFMUN"] == d["municipio_estabelecimento_cod"]
            ),
        },
    }


def _count(values) -> dict[str, int]:
    out: dict[str, int] = {}
    for v in values:
        out[v] = out.get(v, 0) + 1
    return out


def diagnose_cnv(path: Path, lookup_codes: list[str] | None = None) -> dict[str, Any]:
    table = read_cnv_table(path)
    out: dict[str, Any] = {"header": list(table.header), "categories": len(table.entries)}
    if lookup_codes is not None:
        out["lookup"] = {c: [k.label for k in table.matches(c)] for c in lookup_codes}
    return out


def diagnose_def(path: Path) -> dict[str, Any]:
    text = path.read_bytes().decode("cp1252")
    lines = [ln.strip() for ln in text.splitlines() if "CADGERRJ" in ln.upper()]
    return {"lines_referencing_CADGERRJ": lines}


def diagnose_rj_municip(path: Path, powerbi_dir: Path, incoming: Path) -> dict[str, Any]:
    table = read_cnv_table(path)
    cats = table.entries
    res = _dimension_keys(powerbi_dir, "dim_municipio_residencia", "municipio_residencia_cod")
    est = _dimension_keys(powerbi_dir, "dim_estabelecimento", "municipio_estabelecimento_cod")
    rj = sorted({c for c in res + est if c.startswith("33")})
    found = {c: table.matches(c) for c in rj}
    out: dict[str, Any] = {
        "categories": len(cats),
        "rj_codes_in_model": len(rj),
        "found_in_cnv": sum(1 for v in found.values() if len(v) == 1),
        "not_found": [c for c, v in found.items() if not v],
        "ambiguous": [c for c, v in found.items() if len(v) > 1],
    }
    ibge_path = incoming / "municipios_ibge.json"
    if ibge_path.is_file():
        import unicodedata

        def norm(s: str) -> str:
            s = unicodedata.normalize("NFKD", s.upper())
            return (
                "".join(ch for ch in s if not unicodedata.combining(ch))
                .replace("'", " ")
                .replace("-", " ")
            )

        ibge = {r["id"][:6]: r["nome"] for r in read_ibge_municipios(ibge_path)}
        same = 0
        for c, v in found.items():
            if len(v) == 1 and c in ibge:
                label = v[0].label
                label = label[len(c) :].strip() if label.startswith(c) else label
                same += norm(label) == norm(ibge[c])
        out["names_equal_to_ibge"] = same
    return out


RD_FIELDS_OF_INTEREST = (
    "ESPEC", "IDENT", "CAR_INT", "COMPLEX", "SEXO", "RACA_COR", "NAT_JUR", "GESTAO", "DIAG_PRINC",
)  # fmt: skip


def diagnose_rd_def(path: Path) -> dict[str, Any]:
    """Conversion file and start position declared by RD2008.DEF for the model's code fields."""
    text = path.read_bytes().decode("cp1252")
    out: dict[str, list[str]] = {}
    for line in text.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 4 and parts[1] in RD_FIELDS_OF_INTEREST and line[:1] in "LSX":
            out.setdefault(parts[1], []).append(f"start={parts[2]} file={parts[3]}")
    return {"fields": out}


def diagnose_cnv_table(path: Path, spec: dict, powerbi_dir: Path) -> dict[str, Any]:
    """Structure of a TabWin table (categories, width, flags) — codes are resolved on export."""
    table = read_cnv_table(path)
    return {
        "categories": len(table.entries),
        "width": table.width,
        "flags": list(table.flags),
        "hierarchical": any(e.parent for e in table.entries),
        "rd_field": spec.get("rd_field"),
    }


def run_diagnostic(
    incoming: Path, powerbi_dir: Path, sources: dict[str, Any] | None = None
) -> dict[str, Any]:
    sources = sources or load_params()["reference_sources"]
    report: dict[str, Any] = {"incoming": Path(incoming).name, "sources": {}}
    readers = {
        "cnes_st": lambda p, s: diagnose_cnes_st(p, s, powerbi_dir),
        "sigtap": lambda p, s: diagnose_sigtap(p, s, powerbi_dir),
        "tab_cnes": lambda p, s: diagnose_tab_cnes(p),
        "ibge_municipios": lambda p, s: diagnose_ibge(p, powerbi_dir),
        "cnes_cadger": lambda p, s: diagnose_cadger(p, s, powerbi_dir),
        "tp_pfpj": lambda p, s: diagnose_cnv(p, ["1", "3"]),
        "rj_municip": lambda p, s: diagnose_rj_municip(p, powerbi_dir, incoming),
        "cnes_def": lambda p, s: diagnose_def(p),
    }
    readers["tab_sih"] = readers["tab_cnes"]
    readers["sih_rd_def"] = lambda p, s: diagnose_rd_def(p)
    for name, spec in sources.items():
        path = incoming / spec["filename"]
        entry = {"integrity": check_declared(path, spec)}
        reader = readers.get(name) or (
            (lambda p, s: diagnose_cnv_table(p, s, powerbi_dir))
            if spec.get("kind") == "cnv"
            else None
        )
        if reader and entry["integrity"].get("present") and entry["integrity"].get("integrity_ok"):
            try:
                entry["structure"] = reader(path, spec)
            except (ReferenceFormatError, ValueError, KeyError, zipfile.BadZipFile) as exc:
                entry["structure"] = {"error": f"{type(exc).__name__}: {exc}"}
        report["sources"][name] = entry
    return report


def write_diagnostic(report: dict[str, Any], directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "diagnostico_referencias.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", "utf-8")
    return path
