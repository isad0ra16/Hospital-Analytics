"""Untreated conversion ``.dbc -> .dbf -> Arrow table -> Parquet`` (raw layer).

Guarantees:

* the source ``.dbc`` is only read; its SHA-256 is checked before and after;
* every column is stored as text exactly as found in the DBF (padding removed only);
  no type inference, no null conversion, no filtering, no reordering;
* text is decoded with the code page declared in the DBF header; a configured encoding that
  contradicts the header is refused;
* two fingerprints are recorded: one over the decoded text and one over the raw field bytes
  (padding removed). The byte fingerprint does not depend on the encoding, so it proves that
  changing how text is *interpreted* never changes the underlying values;
* the intermediate ``.dbf`` lives in a temporary directory and is discarded, its
  SHA-256 is recorded so it can be reproduced and compared;
* the Parquet is written to a ``.partial`` file, re-read, and its content fingerprint is
  compared with the fingerprint computed while reading the DBF; only then is it renamed
  to its final name (atomic on the same filesystem). Existing outputs are never overwritten.

The in-memory "DataFrame" step is an Apache Arrow table with an explicit all-string
schema. Building it directly (instead of through pandas) avoids pandas type inference.
``read_raw_dataframe`` loads the Parquet into pandas for analysis.
"""

from __future__ import annotations

import codecs
import json
import os
import platform
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from hospital_analytics.dbc import decompress_dbc
from hospital_analytics.dbf import (
    DEFAULT_ENCODING,
    declared_encoding,
    decode_value,
    inspect_dbf,
    iter_raw_rows,
    strip_padding,
)
from hospital_analytics.integrity import ContentFingerprint, sha256_file

BATCH_SIZE = 10_000
PARQUET_COMPRESSION = "zstd"
METADATA_KEY = b"hospital_analytics.raw_conversion"


class IntegrityError(Exception):
    """A file does not match its expected hash, or content changed during conversion."""


class EncodingMismatchError(Exception):
    """The requested text encoding contradicts the code page declared in the DBF header."""


class DeletedRecordsError(Exception):
    """The DBF contains records flagged as deleted; a methodological decision is required."""


@dataclass
class ConversionReport:
    source_path: str
    source_sha256: str
    source_size_bytes: int
    dbf_sha256: str
    dbf_size_bytes: int
    dbf_version: int
    dbf_last_update: str
    dbf_language_driver: int
    dbf_declared_encoding: str | None
    dbf_header_records: int
    dbf_fields: list[dict]
    encoding: str
    parquet_path: str
    parquet_sha256: str
    parquet_size_bytes: int
    records: int
    columns: int
    content_fingerprint: str
    raw_bytes_fingerprint: str
    blank_counts: dict[str, int]
    non_ascii_counts: dict[str, int]
    tool_versions: dict[str, str]
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds"))

    def to_dict(self) -> dict:
        return asdict(self)


def tool_versions() -> dict[str, str]:
    names = ["hospital-analytics", "pyreaddbc", "dbfread", "pyarrow", "pandas"]
    return {"python": platform.python_version()} | {n: version(n) for n in names}


def raw_schema(field_names: list[str], metadata: dict[bytes, bytes]) -> pa.Schema:
    """All columns are non-nullable strings: DBF has no NULL, blanks are ``""``."""
    return pa.schema(
        [pa.field(name, pa.string(), nullable=False) for name in field_names], metadata=metadata
    )


def parquet_fingerprint(
    path: Path, batch_size: int = BATCH_SIZE, *, encode_with: str | None = None
) -> ContentFingerprint:
    """Recompute a fingerprint of a Parquet file, reading it in batches.

    Without ``encode_with`` it is the text fingerprint. With it, every value is encoded back
    to bytes with that codec, which reproduces the raw-bytes fingerprint of the DBF.
    """
    parquet = pq.ParquetFile(path)
    fingerprint = ContentFingerprint(parquet.schema_arrow.names)
    for batch in parquet.iter_batches(batch_size=batch_size):
        columns = [column.to_pylist() for column in batch.columns]
        for row in zip(*columns, strict=True):
            if encode_with:
                fingerprint.update_row([value.encode(encode_with) for value in row])
            else:
                fingerprint.update_row(row)
    return fingerprint


def _write_parquet(dbf_path: Path, partial: Path, schema: pa.Schema, encoding: str, stats: dict):
    names = schema.names
    fingerprint = ContentFingerprint(names)
    raw_fingerprint = ContentFingerprint(names)
    blank = dict.fromkeys(names, 0)
    non_ascii = dict.fromkeys(names, 0)

    with pq.ParquetWriter(partial, schema, compression=PARQUET_COMPRESSION) as writer:
        buffer: list[list[str]] = [[] for _ in names]

        def flush() -> None:
            if buffer[0]:
                arrays = [pa.array(col, type=pa.string()) for col in buffer]
                writer.write_batch(pa.RecordBatch.from_arrays(arrays, schema=schema))
                for col in buffer:
                    col.clear()

        for raw_row in iter_raw_rows(dbf_path, encoding):
            row = []
            for i, raw in enumerate(raw_row):
                value = decode_value(raw, encoding)
                if not raw.isascii():
                    non_ascii[names[i]] += 1
                if value == "":
                    blank[names[i]] += 1
                buffer[i].append(value)
                row.append(value)
            fingerprint.update_row(row)
            raw_fingerprint.update_row([strip_padding(raw) for raw in raw_row])
            if len(buffer[0]) >= BATCH_SIZE:
                flush()
        flush()

    stats.update(
        fingerprint=fingerprint, raw_fingerprint=raw_fingerprint, blank=blank, non_ascii=non_ascii
    )


def convert_dbc_to_parquet(
    source: Path,
    destination: Path,
    *,
    encoding: str = DEFAULT_ENCODING,
    expected_source_sha256: str | None = None,
) -> ConversionReport:
    """Convert a DATASUS ``.dbc`` into an untreated, all-string Parquet file."""
    source, destination = Path(source), Path(destination)
    if not source.is_file():
        raise FileNotFoundError(f"Source not found: {source}")
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite existing file: {destination}")

    source_sha = sha256_file(source)
    if expected_source_sha256 and source_sha != expected_source_sha256.lower():
        raise IntegrityError(
            f"{source}: SHA-256 {source_sha} differs from expected {expected_source_sha256}."
        )

    partial = destination.with_name(destination.name + ".partial")
    with tempfile.TemporaryDirectory(prefix="hospital-analytics-") as tmp:
        dbf_path = Path(tmp) / (source.stem + ".dbf")
        decompress_dbc(source, dbf_path)
        info = inspect_dbf(dbf_path, encoding)
        declared = declared_encoding(info.language_driver)
        if declared and codecs.lookup(declared).name != codecs.lookup(encoding).name:
            raise EncodingMismatchError(
                f"{source}: the DBF header declares {declared} (language driver "
                f"0x{info.language_driver:02x}), but {encoding} was requested."
            )
        if info.deleted_records:
            raise DeletedRecordsError(
                f"{source}: {info.deleted_records} records are flagged as deleted. They are not "
                "converted silently; decide explicitly how to handle them."
            )
        dbf_sha, dbf_size = sha256_file(dbf_path), dbf_path.stat().st_size

        metadata = {
            METADATA_KEY: json.dumps(
                {
                    "source_sha256": source_sha,
                    "encoding": encoding,
                    "dbf_fields": [asdict(f) for f in info.fields],
                    "treatment": "none (fixed-width space padding removed; blanks kept as '')",
                }
            ).encode()
        }
        schema = raw_schema(info.field_names, metadata)

        destination.parent.mkdir(parents=True, exist_ok=True)
        stats: dict = {}
        try:
            _write_parquet(dbf_path, partial, schema, encoding, stats)
            written = stats["fingerprint"]
            reread = parquet_fingerprint(partial)
            reread_raw = parquet_fingerprint(partial, encode_with=encoding)
            if written.rows != info.numrecords:
                raise IntegrityError(
                    f"Read {written.rows} records but the DBF header declares {info.numrecords}."
                )
            if (reread.rows, reread.hexdigest()) != (written.rows, written.hexdigest()):
                raise IntegrityError("Parquet content differs from the DBF content after writing.")
            if reread_raw.hexdigest() != stats["raw_fingerprint"].hexdigest():
                raise IntegrityError("Parquet text does not encode back to the original DBF bytes.")
            if sha256_file(source) != source_sha:
                raise IntegrityError(f"{source} changed during conversion.")
            os.replace(partial, destination)
        finally:
            partial.unlink(missing_ok=True)

    return ConversionReport(
        source_path=str(source),
        source_sha256=source_sha,
        source_size_bytes=source.stat().st_size,
        dbf_sha256=dbf_sha,
        dbf_size_bytes=dbf_size,
        dbf_version=info.version,
        dbf_last_update=info.last_update,
        dbf_language_driver=info.language_driver,
        dbf_declared_encoding=declared,
        dbf_header_records=info.numrecords,
        dbf_fields=[asdict(f) for f in info.fields],
        encoding=encoding,
        parquet_path=str(destination),
        parquet_sha256=sha256_file(destination),
        parquet_size_bytes=destination.stat().st_size,
        records=written.rows,
        columns=len(info.fields),
        content_fingerprint=written.hexdigest(),
        raw_bytes_fingerprint=stats["raw_fingerprint"].hexdigest(),
        blank_counts=stats["blank"],
        non_ascii_counts=stats["non_ascii"],
        tool_versions=tool_versions(),
    )


def read_raw_dataframe(path: Path) -> pd.DataFrame:
    """Load the raw-layer Parquet into pandas (all columns remain text)."""
    return pd.read_parquet(path)
