"""Read-only validation of the raw-layer Parquet.

Every check records what was expected, what was observed and whether it passed.
Validation never modifies, filters or drops data: a divergence is reported, not fixed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from hospital_analytics.config import to_money
from hospital_analytics.convert import parquet_fingerprint
from hospital_analytics.integrity import sha256_file

# Plain decimal number as written in DBF numeric fields (no exponent, no thousands separator).
MONEY_PATTERN = re.compile(r"-?\d+(\.\d+)?")


@dataclass(frozen=True)
class Check:
    name: str
    expected: Any
    observed: Any
    passed: bool
    note: str = ""


@dataclass
class ValidationReport:
    target: str
    checks: list[Check] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    def add(self, name: str, expected: Any, observed: Any, note: str = "") -> None:
        self.checks.append(Check(name, expected, observed, expected == observed, note))

    def format_table(self) -> str:
        lines = [f"Validation of {self.target}", ""]
        for c in self.checks:
            mark = "PASS" if c.passed else "FAIL"
            lines.append(f"[{mark}] {c.name}: expected={c.expected} observed={c.observed}")
            if c.note:
                lines.append(f"       {c.note}")
        lines += ["", "RESULT: " + ("ALL CHECKS PASSED" if self.passed else "DIVERGENCE FOUND")]
        return "\n".join(lines)


@dataclass(frozen=True)
class ReferenceTargets:
    """The three historical references the raw layer must reproduce exactly."""

    records: int
    columns: int
    val_tot_sum: Decimal

    @classmethod
    def from_params(cls, params: dict[str, Any]) -> ReferenceTargets:
        base = params["historical_reference"]["full_base"]
        return cls(
            records=base["records"]["value"],
            columns=base["columns"]["value"],
            val_tot_sum=to_money(base["val_tot_sum"]["value"]),
        )


@dataclass(frozen=True)
class MoneySummary:
    total: Decimal
    blanks: int
    invalid: int
    invalid_examples: tuple[str, ...]


def summarize_money(table: pa.Table, column: str) -> MoneySummary:
    """Exact sum of a text money column. Blanks and malformed values are counted, not hidden."""
    total, blanks, invalid, examples = Decimal(0), 0, 0, []
    for value in table.column(column).to_pylist():
        if value == "":
            blanks += 1
        elif MONEY_PATTERN.fullmatch(value):
            total += Decimal(value)
        else:
            invalid += 1
            if len(examples) < 5:
                examples.append(value)
    return MoneySummary(total, blanks, invalid, tuple(examples))


def validate_raw_parquet(
    parquet_path: Path,
    targets: ReferenceTargets,
    *,
    money_column: str = "VAL_TOT",
    derived_entry: dict[str, Any] | None = None,
) -> ValidationReport:
    """Validate shape, types, money integrity and (with a manifest entry) preservation."""
    parquet_path = Path(parquet_path)
    report = ValidationReport(target=str(parquet_path))
    table = pq.read_table(parquet_path)

    # 1. Shape against the historical references
    report.add("records == historical reference", targets.records, table.num_rows)
    report.add("columns == historical reference", targets.columns, table.num_columns)

    # 2. Types: the raw layer is untreated text only
    non_string = [f.name for f in table.schema if not pa.types.is_string(f.type)]
    report.add("all columns are text (raw layer)", [], non_string)
    nullable = [f.name for f in table.schema if f.nullable]
    report.add("no nullable columns (DBF has no NULL)", [], nullable)

    # 3. Money integrity
    has_money = money_column in table.column_names
    report.add(f"{money_column} column present", True, has_money)
    if has_money:
        money = summarize_money(table, money_column)
        report.add(
            f"{money_column} malformed values",
            0,
            money.invalid,
            note=f"examples: {list(money.invalid_examples)}" if money.invalid else "",
        )
        report.add(
            f"{money_column} exact sum == historical reference",
            targets.val_tot_sum,
            money.total,
            note=f"blank values: {money.blanks}",
        )

    # 4. Preservation against the manifest (values recorded at conversion time)
    if derived_entry is not None:
        report.add(
            "records == DBF header records",
            derived_entry["intermediate_dbf"]["header_records"],
            table.num_rows,
        )
        report.add(
            "parquet SHA-256 == manifest", derived_entry["sha256"], sha256_file(parquet_path)
        )
        report.add(
            "content fingerprint == manifest (DBF values preserved)",
            derived_entry["content_fingerprint"],
            parquet_fingerprint(parquet_path).hexdigest(),
        )
        if "raw_bytes_fingerprint" in derived_entry:
            report.add(
                "raw bytes fingerprint == manifest (original bytes preserved)",
                derived_entry["raw_bytes_fingerprint"],
                parquet_fingerprint(
                    parquet_path, encode_with=derived_entry["encoding"]
                ).hexdigest(),
            )
    return report
