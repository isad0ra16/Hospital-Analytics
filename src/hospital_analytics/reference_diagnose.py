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
from hospital_analytics.integrity import sha256_file
from hospital_analytics.reference import (
    ReferenceFormatError,
    coverage,
    key_report,
    read_ibge_municipios,
    read_sigtap_table,
)


def _dimension_keys(powerbi_dir: Path, table: str, column: str) -> list[str]:
    path = powerbi_dir / f"{table}.csv"
    with path.open(encoding="utf-8", newline="") as fh:
        return [row[column] for row in csv.DictReader(fh)]


def check_file(path: Path, spec: dict[str, Any]) -> dict[str, Any]:
    """Presence, size and SHA-256 against the declared values."""
    if not path.is_file():
        return {"file": path.name, "present": False}
    result = {
        "file": path.name,
        "present": True,
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }
    if "size_bytes" in spec:
        result["size_ok"] = result["size_bytes"] == spec["size_bytes"]
    if "sha256" in spec:
        result["sha256_ok"] = result["sha256"] == spec["sha256"].lower()
    result["integrity_ok"] = result.get("size_ok", True) and result.get("sha256_ok", True)
    return result


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
    }
    for name, spec in sources.items():
        path = incoming / spec["filename"]
        entry = {"integrity": check_file(path, spec)}
        if entry["integrity"].get("present") and entry["integrity"].get("integrity_ok"):
            try:
                entry["structure"] = readers[name](path, spec)
            except (ReferenceFormatError, ValueError, KeyError, zipfile.BadZipFile) as exc:
                entry["structure"] = {"error": f"{type(exc).__name__}: {exc}"}
        report["sources"][name] = entry
    return report


def write_diagnostic(report: dict[str, Any], directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "diagnostico_referencias.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", "utf-8")
    return path
