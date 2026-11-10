"""Read-only data audit: structure, completeness, codes, dates, money, repeated AIHs.

The audit never changes data. It produces a JSON report (machine-readable) and a Markdown
summary (human-readable) under ``reports/audit/``. Reports are deterministic (no timestamps):
the same data and code always produce identical files; provenance comes from git.
Values of identifying or free-text columns are never written to reports; only aggregate
statistics are.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq

from hospital_analytics.dictionary import CODEBOOK
from hospital_analytics.processed import raw_dbf_fields
from hospital_analytics.sql import connect, query

log = logging.getLogger(__name__)

# Identifying or free-text columns: only aggregate statistics are reported, never values.
SENSITIVE_COLUMNS = frozenset(
    {"N_AIH", "CEP", "NASC", "CPF_AUT", "GESTOR_CPF", "AUD_JUST", "SIS_JUST", "INSC_PN"}
)
TOP_VALUES = 5
SQL_CHECKS = (
    "audit/discharge_year",
    "audit/date_consistency",
    "audit/discharge_month_offset",
    "audit/repeated_aih",
    "audit/death_consistency",
    "audit/money_consistency",
    "audit/age_units",
    "audit/full_row_duplicates",
)


@dataclass
class ColumnProfile:
    name: str
    dbf_type: str
    dbf_length: int
    dbf_decimals: int
    blank: int
    blank_pct: float
    distinct: int
    min_length: int
    max_length: int
    top_values: list[tuple[str, int]] | None
    codes_outside_codebook: list[str] | None = None


@dataclass
class AuditReport:
    source: str
    records: int
    columns: int
    profiles: list[ColumnProfile]
    checks: dict[str, list[dict[str, Any]]]
    repeated_aih_varying_columns: dict[str, int]

    @property
    def entirely_blank(self) -> list[str]:
        return [p.name for p in self.profiles if p.blank == self.records]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "records": self.records,
            "columns": self.columns,
            "entirely_blank_columns": self.entirely_blank,
            "profiles": [p.__dict__ for p in self.profiles],
            "checks": self.checks,
            "repeated_aih_varying_columns": self.repeated_aih_varying_columns,
        }


def profile_columns(raw: pd.DataFrame, fields: list[dict]) -> list[ColumnProfile]:
    """Completeness and value profile of every original (text) column."""
    profiles = []
    n = len(raw)
    for spec in fields:
        name = spec["name"]
        col = raw[name]
        lengths = col.str.len()
        blank = int((col == "").sum())
        sensitive = name in SENSITIVE_COLUMNS
        top = (
            None
            if sensitive
            else [(v, int(c)) for v, c in col.value_counts().head(TOP_VALUES).items()]
        )
        outside = None
        if name in CODEBOOK and CODEBOOK[name].complete and not sensitive:
            known = set(CODEBOOK[name].codes)
            outside = sorted(set(col[col != ""]) - known)
        profiles.append(
            ColumnProfile(
                name=name,
                dbf_type=spec["type"],
                dbf_length=spec["length"],
                dbf_decimals=spec["decimal_count"],
                blank=blank,
                blank_pct=round(100 * blank / n, 4) if n else 0.0,
                distinct=int(col.nunique()),
                min_length=int(lengths.min()) if n else 0,
                max_length=int(lengths.max()) if n else 0,
                top_values=top,
                codes_outside_codebook=outside,
            )
        )
    return profiles


def repeated_aih_varying_columns(raw: pd.DataFrame) -> dict[str, int]:
    """For AIH numbers with several records: in how many groups does each column vary?"""
    repeated = raw[raw.duplicated("N_AIH", keep=False)]
    counter: Counter[str] = Counter()
    for _, group in repeated.groupby("N_AIH"):
        for column in group.columns:
            if group[column].nunique() > 1:
                counter[column] += 1
    return dict(counter.most_common())


def run_audit(raw_path: Path, processed_path: Path) -> AuditReport:
    """Run every audit check. Read-only."""
    raw_path, processed_path = Path(raw_path), Path(processed_path)
    fields = raw_dbf_fields(raw_path)
    raw = pq.read_table(raw_path).to_pandas()
    log.info("auditing %s (%d records)", raw_path, len(raw))
    con = connect(raw=raw_path, processed=processed_path)
    checks = {name.split("/", 1)[1]: query(con, name) for name in SQL_CHECKS}
    return AuditReport(
        source=raw_path.name,
        records=len(raw),
        columns=raw.shape[1],
        profiles=profile_columns(raw, fields),
        checks=checks,
        repeated_aih_varying_columns=repeated_aih_varying_columns(raw),
    )


def _table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "_(sem linhas)_\n"
    headers = list(rows[0])
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(str(r[h]) for h in headers) + " |" for r in rows]
    return "\n".join(lines) + "\n"


def to_markdown(report: AuditReport) -> str:
    """Human-readable summary. Generated: do not edit by hand."""
    out = [
        f"# Relatório de auditoria — {report.source}",
        "",
        "> Gerado por `hospital-analytics audit`. Não editar manualmente.",
        "",
        f"- Registros: **{report.records:,}** · Colunas originais: **{report.columns}**",
        f"- Colunas 100% vazias: {', '.join(f'`{c}`' for c in report.entirely_blank) or 'nenhuma'}",
        "",
    ]
    for name, rows in report.checks.items():
        out += [f"## {name}", "", _table(rows)]
    out += ["## Colunas que variam entre registros com o mesmo N_AIH", ""]
    out += [
        _table(
            [
                {"coluna": k, "grupos_com_variacao": v}
                for k, v in report.repeated_aih_varying_columns.items()
            ]
        )
    ]
    out += ["## Perfil das colunas", ""]
    rows = []
    for p in report.profiles:
        top = (
            "(sensível — omitido)"
            if p.top_values is None
            else ", ".join(f"`{v}`:{c}" for v, c in p.top_values)
        )
        outside = "" if not p.codes_outside_codebook else ", ".join(p.codes_outside_codebook)
        rows.append(
            {
                "coluna": f"`{p.name}`",
                "tipo DBF": f"{p.dbf_type}{p.dbf_length}"
                + (f".{p.dbf_decimals}" if p.dbf_decimals else ""),
                "vazios": p.blank,
                "% vazios": p.blank_pct,
                "distintos": p.distinct,
                "mais frequentes": top,
                "fora do dicionário": outside,
            }
        )
    out.append(_table(rows))
    return "\n".join(out)


def write_report(report: AuditReport, directory: Path, stem: str) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    json_path, md_path = directory / f"{stem}.json", directory / f"{stem}.md"
    json_path.write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False, default=str) + "\n", "utf-8"
    )
    md_path.write_text(to_markdown(report), "utf-8")
    return json_path, md_path
