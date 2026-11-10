"""Raw DBF reading with SYNTHETIC files."""

import pytest
from synthetic_data import SYNTHETIC_FIELDS, FieldSpec, build_dbf, write

from hospital_analytics.dbc import DbcError
from hospital_analytics.dbf import DbfError, decode_value, inspect_dbf, iter_raw_rows


def test_structure_and_counts(tmp_path, dbf_bytes, rows):
    info = inspect_dbf(write(tmp_path / "t.dbf", dbf_bytes))
    assert info.field_names == [f.name for f in SYNTHETIC_FIELDS]
    assert info.numrecords == info.active_records == len(rows)
    assert info.deleted_records == 0
    assert info.fields[-1].type == "N" and info.fields[-1].decimal_count == 2


def test_values_are_preserved_as_text(tmp_path, dbf_bytes, rows):
    path = write(tmp_path / "t.dbf", dbf_bytes)
    decoded = [[decode_value(v) for v in row] for row in iter_raw_rows(path)]
    assert decoded == rows  # leading zeros kept, padding removed, blanks are ""


def test_latin1_bytes_are_decoded_reversibly(tmp_path):
    fields = [FieldSpec("NOME", "C", 10)]
    path = write(tmp_path / "t.dbf", build_dbf(fields, [["SÃO JOÃO"]]))
    (raw,) = next(iter_raw_rows(path))
    assert decode_value(raw) == "SÃO JOÃO"
    assert decode_value(raw).encode("latin-1") == raw.rstrip(b" ")


def test_deleted_records_are_counted(tmp_path, rows):
    path = write(tmp_path / "t.dbf", build_dbf(SYNTHETIC_FIELDS, rows, deleted=frozenset({3})))
    info = inspect_dbf(path)
    assert (info.active_records, info.deleted_records) == (len(rows) - 1, 1)


def test_unexpected_status_byte_is_detected(tmp_path, dbf_bytes):
    """dbfread silently skips such records; inspect_dbf must not."""
    data = bytearray(dbf_bytes)
    headerlen = int.from_bytes(data[8:10], "little")
    data[headerlen] = ord("?")
    with pytest.raises(DbfError, match="header declares"):
        inspect_dbf(write(tmp_path / "t.dbf", bytes(data)))


def test_header_count_mismatch_is_detected(tmp_path, rows):
    dbf = build_dbf(SYNTHETIC_FIELDS, rows, declared_records=len(rows) + 1)
    with pytest.raises(DbcError, match="inconsistent with its header"):
        inspect_dbf(write(tmp_path / "t.dbf", dbf))


def test_file_without_eof_marker_is_accepted(tmp_path, rows):
    info = inspect_dbf(
        write(tmp_path / "t.dbf", build_dbf(SYNTHETIC_FIELDS, rows, eof_marker=False))
    )
    assert info.active_records == len(rows)
