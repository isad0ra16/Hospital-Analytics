"""Processed (treated) layer: original fields untouched + documented derived columns.

Naming convention: UPPERCASE columns are the 113 original fields, copied byte for byte from the
raw layer; lowercase columns are derived. Two kinds of derivation are kept apart:

* format conversions (text -> integer cents, integer, date). Each one is verified to be
  reversible row by row: converting the derived value back to text must give the original text,
  otherwise the build stops;
* interpretations of codes (e.g. COD_IDADE units). They depend on the codebook
  (``dictionary.py``) and carry its source status.

The build never drops, filters or reorders records.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from hospital_analytics.convert import METADATA_KEY, PARQUET_COMPRESSION, tool_versions
from hospital_analytics.dictionary import CODEBOOK
from hospital_analytics.integrity import ContentFingerprint, sha256_file

log = logging.getLogger(__name__)

PROCESSED_METADATA_KEY = b"hospital_analytics.processed"
_DECIMAL_RE = {d: re.compile(rf"-?\d+\.\d{{1,{d}}}") for d in range(1, 5)}
_INT_RE = re.compile(r"-?\d+")
_DATE_RE = re.compile(r"\d{8}")


class TransformError(Exception):
    """A derivation is not reversible or the input does not have the expected format."""


@dataclass(frozen=True)
class DerivedColumn:
    name: str
    type: str
    sources: tuple[str, ...]
    rule: str
    kind: str  # "format" (reversible conversion) | "interpretation" | "structural"
    interpretation_status: str = "n/a"


# Fixed derived columns (numeric format conversions are added dynamically: one per DBF "N" field).
DERIVED_COLUMNS: tuple[DerivedColumn, ...] = (
    DerivedColumn(
        "competence", "string", ("ANO_CMPT", "MES_CMPT"), "ANO_CMPT || '-' || MES_CMPT", "format"
    ),
    DerivedColumn(
        "admission_date", "date", ("DT_INTER",), "YYYYMMDD -> date; invalid -> null", "format"
    ),
    DerivedColumn(
        "discharge_date", "date", ("DT_SAIDA",), "YYYYMMDD -> date; invalid -> null", "format"
    ),
    DerivedColumn("birth_date", "date", ("NASC",), "YYYYMMDD -> date; invalid -> null", "format"),
    DerivedColumn("discharge_year", "int16", ("DT_SAIDA",), "year(discharge_date)", "format"),
    DerivedColumn(
        "los_days_from_dates",
        "int32",
        ("DT_INTER", "DT_SAIDA"),
        "discharge_date - admission_date (days)",
        "structural",
    ),
    DerivedColumn(
        "age_unit",
        "string",
        ("COD_IDADE",),
        "codebook label of COD_IDADE",
        "interpretation",
        "secondary",
    ),
    DerivedColumn(
        "age_years",
        "float64",
        ("COD_IDADE", "IDADE"),
        "2: IDADE/365.25 · 3: IDADE/12 · 4: IDADE · 5: 100 + IDADE · other: null",
        "interpretation",
        "secondary",
    ),
    DerivedColumn("died", "bool", ("MORTE",), "MORTE == '1'", "interpretation", "secondary"),
    DerivedColumn(
        "ident_label",
        "string",
        ("IDENT",),
        "codebook label of IDENT",
        "interpretation",
        "secondary",
    ),
    DerivedColumn(
        "proc_rea_group", "string", ("PROC_REA",), "first 2 characters (SIGTAP group)", "structural"
    ),
    DerivedColumn(
        "proc_rea_group_label",
        "string",
        ("PROC_REA",),
        "codebook label of the SIGTAP group",
        "interpretation",
        "prior_knowledge",
    ),
    DerivedColumn(
        "aih_occurrences",
        "int32",
        ("N_AIH",),
        "number of records with the same N_AIH",
        "structural",
    ),
    DerivedColumn(
        "aih_repeated",
        "bool",
        ("N_AIH",),
        "aih_occurrences > 1 (flag only; nothing removed)",
        "structural",
    ),
)


# ---------------------------------------------------------------------------
# Reversible format conversions
# ---------------------------------------------------------------------------
def text_to_scaled_int(values: pd.Series, decimals: int) -> pd.Series:
    """'123.45' -> 12345 (decimals=2). Blank -> <NA>. Exact: no float is ever involved.

    Values written with fewer decimal digits than declared ('166200.0' in an N8.2 field) are
    read as written; ``_check_reversible`` only accepts them when the full representation would
    not fit the field width (see ``reduced_precision``).
    """
    pattern = _DECIMAL_RE[decimals] if decimals else _INT_RE
    blank = values == ""
    bad = ~blank & ~values.str.fullmatch(pattern)
    if bad.any():
        raise TransformError(
            f"{bad.sum()} values do not match the numeric format: {values[bad].head(3).tolist()}"
        )
    parsed = []
    for v in values:
        if v == "":
            parsed.append(None)
            continue
        whole, _, frac = v.partition(".")
        parsed.append(int(whole + frac.ljust(decimals, "0")))
    return pd.array(parsed, dtype="Int64")


def scaled_int_to_text(value: int, decimals: int) -> str:
    """Inverse of ``text_to_scaled_int`` for one value."""
    if not decimals:
        return str(value)
    sign, magnitude = ("-", -value) if value < 0 else ("", value)
    whole, frac = divmod(magnitude, 10**decimals)
    return f"{sign}{whole}.{frac:0{decimals}d}"


def text_to_date(values: pd.Series) -> tuple[pd.Series, int]:
    """'YYYYMMDD' -> date. Invalid or blank values become null and are counted (never guessed)."""
    parsed, invalid = [], 0
    for v in values:
        try:
            if not _DATE_RE.fullmatch(v):
                raise ValueError
            parsed.append(date(int(v[:4]), int(v[4:6]), int(v[6:])))
        except ValueError:
            parsed.append(None)
            invalid += 1
    return pd.Series(parsed, index=values.index, dtype="object"), invalid


def reduced_precision(original: pd.Series, back: pd.Series, width: int) -> pd.Series:
    """Values the source wrote with fewer decimals only because the full form exceeds the width.

    Example: 166200.00 needs 9 characters; in an N8.2 field it is stored as '166200.0'.
    Accepted only if the canonical form is too wide AND differs from the stored text by
    trailing zeros alone.
    """
    return pd.Series(
        [
            o != b and len(b) > width and b.startswith(o) and b[len(o) :].strip("0") == ""
            for o, b in zip(original, back, strict=True)
        ],
        index=original.index,
    )


def _check_reversible(
    name: str, original: pd.Series, back: pd.Series, allowed: pd.Series | None = None
) -> None:
    mismatch = original != back
    if allowed is not None:
        mismatch &= ~allowed
    if mismatch.any():
        examples = list(zip(original[mismatch].head(3), back[mismatch].head(3), strict=True))
        raise TransformError(f"{name}: {mismatch.sum()} values are not reversible, e.g. {examples}")


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
@dataclass
class ProcessedReport:
    path: str
    sha256: str
    size_bytes: int
    records: int
    original_columns: int
    derived_columns: list[str]
    original_columns_fingerprint: str
    invalid_dates: dict[str, int]
    reversibility_checked: list[str]
    reduced_precision_values: dict[str, int]
    tool_versions: dict[str, str]
    created_at: str


def raw_dbf_fields(raw_path: Path) -> list[dict]:
    meta = pq.read_schema(raw_path).metadata[METADATA_KEY]
    return json.loads(meta)["dbf_fields"]


def numeric_derived_columns(fields: list[dict]) -> list[DerivedColumn]:
    """One reversible integer column per DBF numeric field: '_cents' (2 decimals) or '_int'."""
    out = []
    for f in fields:
        if f["type"] != "N":
            continue
        dec = f["decimal_count"]
        suffix = "_cents" if dec == 2 else ("_int" if dec == 0 else f"_e{dec}")
        rule = (
            f"{f['name']} text -> integer (x10^{dec}); verified reversible"
            if dec
            else f"{f['name']} text -> integer; verified reversible"
        )
        out.append(DerivedColumn(f["name"].lower() + suffix, "int64", (f["name"],), rule, "format"))
    return out


@dataclass
class Derivation:
    columns: dict[str, pd.Series]
    invalid_dates: dict[str, int]
    reversibility_checked: list[str]
    reduced_precision: dict[str, int]


def derive(df: pd.DataFrame, fields: list[dict]) -> Derivation:
    """Compute derived columns from the original (text) columns."""
    derived: dict[str, pd.Series] = {}
    checked: list[str] = []
    reduced: dict[str, int] = {}

    for col in numeric_derived_columns(fields):
        source = col.sources[0]
        spec = next(f for f in fields if f["name"] == source)
        dec = spec["decimal_count"]
        ints = text_to_scaled_int(df[source], dec)
        back = pd.Series(
            ["" if v is pd.NA else scaled_int_to_text(int(v), dec) for v in ints], index=df.index
        )
        allowed = reduced_precision(df[source], back, spec["length"]) if dec else None
        _check_reversible(col.name, df[source], back, allowed)
        if allowed is not None and allowed.any():
            reduced[source] = int(allowed.sum())
            log.warning("%s: %d values stored with reduced precision", source, allowed.sum())
        derived[col.name] = pd.Series(ints, index=df.index)
        checked.append(col.name)

    derived["competence"] = df["ANO_CMPT"] + "-" + df["MES_CMPT"]

    invalid: dict[str, int] = {}
    for name, source in (
        ("admission_date", "DT_INTER"),
        ("discharge_date", "DT_SAIDA"),
        ("birth_date", "NASC"),
    ):
        parsed, invalid[name] = text_to_date(df[source])
        back = pd.Series(
            [d.strftime("%Y%m%d") if d else df[source].iloc[i] for i, d in enumerate(parsed)],
            index=df.index,
        )
        _check_reversible(name, df[source], back)
        derived[name] = parsed
        checked.append(name)

    derived["discharge_year"] = pd.array(
        [d.year if d else None for d in derived["discharge_date"]], dtype="Int16"
    )
    derived["los_days_from_dates"] = pd.array(
        [
            (s - i).days if s and i else None
            for s, i in zip(derived["discharge_date"], derived["admission_date"], strict=True)
        ],
        dtype="Int32",
    )

    age_codes = CODEBOOK["COD_IDADE"].codes
    derived["age_unit"] = df["COD_IDADE"].map(age_codes)
    idade = text_to_scaled_int(df["IDADE"], 0)
    factors = {"2": 1 / 365.25, "3": 1 / 12, "4": 1.0}
    derived["age_years"] = pd.Series(
        [
            None
            if v is pd.NA
            else (
                100.0 + int(v)
                if code == "5"
                else (int(v) * factors[code] if code in factors else None)
            )
            for code, v in zip(df["COD_IDADE"], idade, strict=True)
        ],
        index=df.index,
        dtype="Float64",
    )
    derived["died"] = df["MORTE"] == "1"
    derived["ident_label"] = df["IDENT"].map(CODEBOOK["IDENT"].codes)
    derived["proc_rea_group"] = df["PROC_REA"].str[:2]
    derived["proc_rea_group_label"] = derived["proc_rea_group"].map(
        CODEBOOK["PROC_REA_GROUP"].codes
    )
    occurrences = df.groupby("N_AIH")["N_AIH"].transform("size")
    derived["aih_occurrences"] = occurrences.astype("int32")
    derived["aih_repeated"] = occurrences > 1
    return Derivation(derived, invalid, checked, reduced)


_ARROW_TYPES = {
    "string": pa.string(),
    "date": pa.date32(),
    "int16": pa.int16(),
    "int32": pa.int32(),
    "int64": pa.int64(),
    "float64": pa.float64(),
    "bool": pa.bool_(),
}


def _to_arrow(values, arrow_type: pa.DataType) -> pa.Array:
    """Convert a pandas Series/ExtensionArray to Arrow; missing values become null."""
    return pa.array(
        [None if pd.isna(v) else v for v in pd.Series(values).astype(object)], type=arrow_type
    )


def check_no_name_clash(original: list[str], derived: list[str]) -> None:
    """SQL engines such as DuckDB resolve names case-insensitively: 'dt_inter' would silently
    resolve to the original 'DT_INTER'. Derived names must differ from every original name
    and from each other, ignoring case."""
    seen = {name.casefold() for name in original}
    for name in derived:
        if name.casefold() in seen:
            raise TransformError(
                f"Derived column {name!r} clashes (ignoring case) with another column."
            )
        seen.add(name.casefold())


def all_derived_columns(fields: list[dict]) -> list[DerivedColumn]:
    return numeric_derived_columns(fields) + list(DERIVED_COLUMNS)


def build_processed(raw_path: Path, destination: Path) -> ProcessedReport:
    """Build the processed layer from the raw Parquet. Never overwrites an existing file."""
    raw_path, destination = Path(raw_path), Path(destination)
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite existing file: {destination}")

    raw = pq.read_table(raw_path)
    fields = raw_dbf_fields(raw_path)
    df = raw.to_pandas()
    log.info("building processed layer from %s (%d records)", raw_path, len(df))
    result = derive(df, fields)
    derived = result.columns

    columns = all_derived_columns(fields)
    check_no_name_clash(raw.column_names, [c.name for c in columns])
    arrays = list(raw.columns)  # original Arrow arrays, untouched
    schema_fields = list(raw.schema)
    for col in columns:
        arrow_type = _ARROW_TYPES[col.type]
        arrays.append(_to_arrow(derived[col.name], arrow_type))
        schema_fields.append(pa.field(col.name, arrow_type))

    metadata = dict(raw.schema.metadata or {})
    metadata[PROCESSED_METADATA_KEY] = json.dumps(
        {"derived_columns": [col.__dict__ for col in columns], "source": str(raw_path.name)},
        default=list,
    ).encode()
    table = pa.Table.from_arrays(arrays, schema=pa.schema(schema_fields, metadata=metadata))
    if table.num_rows != raw.num_rows:
        raise TransformError("Record count changed while building the processed layer.")

    fingerprint = original_columns_fingerprint(table, raw.column_names)
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".partial")
    try:
        pq.write_table(table, partial, compression=PARQUET_COMPRESSION)
        os.replace(partial, destination)
    finally:
        partial.unlink(missing_ok=True)

    return ProcessedReport(
        path=str(destination),
        sha256=sha256_file(destination),
        size_bytes=destination.stat().st_size,
        records=table.num_rows,
        original_columns=raw.num_columns,
        derived_columns=[c.name for c in columns],
        original_columns_fingerprint=fingerprint,
        invalid_dates=result.invalid_dates,
        reversibility_checked=result.reversibility_checked,
        reduced_precision_values=result.reduced_precision,
        tool_versions=tool_versions(),
        created_at=datetime.now(UTC).isoformat(timespec="seconds"),
    )


def original_columns_fingerprint(table: pa.Table, names: list[str]) -> str:
    """Content fingerprint of the original columns only (must equal the raw layer's)."""
    fingerprint = ContentFingerprint(names)
    columns = [table.column(n).to_pylist() for n in names]
    for row in zip(*columns, strict=True):
        fingerprint.update_row(row)
    return fingerprint.hexdigest()
