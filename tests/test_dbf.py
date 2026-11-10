"""Raw DBF reading with SYNTHETIC files."""

import pytest
from synthetic_data import SYNTHETIC_FIELDS, FieldSpec, build_dbf, write

from hospital_analytics.dbc import DbcError
from hospital_analytics.dbf import (
    DbfError,
    declared_encoding,
    decode_value,
    inspect_dbf,
    iter_raw_rows,
    strip_padding,
)


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


@pytest.mark.parametrize("encoding", ["cp850", "latin-1"])
def test_text_is_decoded_reversibly(tmp_path, encoding):
    fields = [FieldSpec("NOME", "C", 12)]
    path = write(tmp_path / "t.dbf", build_dbf(fields, [["MÉDICO ÁREA"]], encoding=encoding))
    (raw,) = next(iter_raw_rows(path))
    assert decode_value(raw, encoding) == "MÉDICO ÁREA"
    assert decode_value(raw, encoding).encode(encoding) == strip_padding(raw)


def test_cp850_bytes_seen_in_aud_just():
    """Bytes 0x90 and 0xA0 (found in the real AUD_JUST field) are 'É' and 'á' in CP850."""
    assert decode_value(b"\x90 \xa0 ") == "É á"
    assert b"\x90\xa0".decode("latin-1") != "Éá"  # the previous, wrong interpretation


@pytest.mark.parametrize("encoding", ["cp850", "latin-1"])
def test_every_byte_roundtrips(encoding):
    """No byte can be lost: all 256 values decode and encode back unchanged."""
    every_byte = bytes(range(256))
    assert every_byte.decode(encoding).encode(encoding) == every_byte


def test_space_is_the_only_byte_decoding_to_space():
    """Guarantees decode-then-strip == strip-then-decode, so text maps back to raw bytes."""
    for encoding in ("cp850", "latin-1"):
        assert [b for b in range(256) if bytes([b]).decode(encoding) == " "] == [0x20]


@pytest.mark.parametrize(("driver", "expected"), [(0x02, "cp850"), (0x03, "cp1252"), (0x00, None)])
def test_declared_encoding(tmp_path, rows, driver, expected):
    path = write(tmp_path / "t.dbf", build_dbf(SYNTHETIC_FIELDS, rows, language_driver=driver))
    assert declared_encoding(inspect_dbf(path).language_driver) == expected


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
