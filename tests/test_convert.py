"""End-to-end raw conversion with SYNTHETIC .dbc files."""

import json

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from synthetic_data import SYNTHETIC_FIELDS, FieldSpec, build_dbc, build_dbf, write

from hospital_analytics.convert import (
    METADATA_KEY,
    DeletedRecordsError,
    EncodingMismatchError,
    IntegrityError,
    convert_dbc_to_parquet,
    parquet_fingerprint,
    read_raw_dataframe,
)
from hospital_analytics.integrity import sha256_file


@pytest.fixture
def converted(tmp_path, dbc_file):
    out = tmp_path / "out" / "SYNTH.parquet"
    return out, convert_dbc_to_parquet(dbc_file, out)


def test_shape_and_values(converted, rows):
    out, report = converted
    table = pq.read_table(out)
    assert (table.num_rows, table.num_columns) == (len(rows), len(SYNTHETIC_FIELDS))
    assert (report.records, report.columns) == (len(rows), len(SYNTHETIC_FIELDS))
    assert [list(r.values()) for r in table.to_pylist()] == rows


def test_all_columns_are_non_nullable_text(converted):
    out, _ = converted
    schema = pq.read_schema(out)
    assert all(pa.types.is_string(f.type) and not f.nullable for f in schema)


def test_pandas_dataframe_keeps_text(converted, rows):
    out, _ = converted
    df = read_raw_dataframe(out)
    assert df.shape == (len(rows), len(SYNTHETIC_FIELDS))
    assert df["MUNIC_RES"].iloc[0] == "003300"  # leading zeros preserved
    assert all(df[c].map(type).eq(str).all() for c in df.columns)


def test_report_and_metadata(converted, dbc_file, rows):
    out, report = converted
    assert report.source_sha256 == sha256_file(dbc_file)
    assert report.parquet_sha256 == sha256_file(out)
    assert report.content_fingerprint == parquet_fingerprint(out).hexdigest()
    assert report.blank_counts["DIAGSEC9"] == len(rows)
    assert report.dbf_header_records == len(rows)
    assert report.dbf_last_update == "2025-02-08"
    meta = json.loads(pq.read_schema(out).metadata[METADATA_KEY])
    assert meta["source_sha256"] == report.source_sha256
    assert [f["name"] for f in meta["dbf_fields"]] == [f.name for f in SYNTHETIC_FIELDS]


def test_source_is_untouched(tmp_path, dbc_file):
    before = sha256_file(dbc_file)
    convert_dbc_to_parquet(dbc_file, tmp_path / "x.parquet")
    assert sha256_file(dbc_file) == before


def test_no_leftover_files(converted):
    out, _ = converted
    assert sorted(p.name for p in out.parent.iterdir()) == [out.name]


def test_refuses_to_overwrite(tmp_path, dbc_file):
    out = write(tmp_path / "x.parquet", b"existing")
    with pytest.raises(FileExistsError):
        convert_dbc_to_parquet(dbc_file, out)
    assert out.read_bytes() == b"existing"


def test_expected_hash_mismatch_stops_before_writing(tmp_path, dbc_file):
    out = tmp_path / "x.parquet"
    with pytest.raises(IntegrityError):
        convert_dbc_to_parquet(dbc_file, out, expected_source_sha256="0" * 64)
    assert not out.exists()


def test_deleted_records_stop_conversion(tmp_path, rows):
    dbf = build_dbf(SYNTHETIC_FIELDS, rows, deleted=frozenset({0}))
    src = write(tmp_path / "d.dbc", build_dbc(dbf))
    out = tmp_path / "d.parquet"
    with pytest.raises(DeletedRecordsError):
        convert_dbc_to_parquet(src, out)
    assert not out.exists()
    assert not (tmp_path / "d.parquet.partial").exists()


def test_encoding_contradicting_the_header_is_refused(tmp_path, rows):
    dbf = build_dbf(SYNTHETIC_FIELDS, rows, language_driver=0x02)  # declares CP850
    src = write(tmp_path / "e.dbc", build_dbc(dbf))
    out = tmp_path / "e.parquet"
    with pytest.raises(EncodingMismatchError, match="cp850"):
        convert_dbc_to_parquet(src, out, encoding="latin-1")
    assert not out.exists()
    assert convert_dbc_to_parquet(src, out, encoding="cp850").dbf_declared_encoding == "cp850"


def test_byte_fingerprint_does_not_depend_on_encoding(tmp_path):
    """Re-interpreting text changes the text fingerprint, never the raw-bytes fingerprint."""
    fields = [FieldSpec("AUD_JUST", "C", 10)]
    dbf = build_dbf(fields, [["MÉDICA"], ["SEM ACENTO"]], encoding="cp850")
    src = write(tmp_path / "s.dbc", build_dbc(dbf))
    as_latin1 = convert_dbc_to_parquet(src, tmp_path / "l.parquet", encoding="latin-1")
    as_cp850 = convert_dbc_to_parquet(src, tmp_path / "c.parquet", encoding="cp850")
    assert as_latin1.raw_bytes_fingerprint == as_cp850.raw_bytes_fingerprint
    assert as_latin1.content_fingerprint != as_cp850.content_fingerprint
    assert pq.read_table(tmp_path / "c.parquet").column(0).to_pylist()[0] == "MÉDICA"
    assert parquet_fingerprint(tmp_path / "l.parquet", encode_with="latin-1").hexdigest() == (
        as_cp850.raw_bytes_fingerprint
    )
