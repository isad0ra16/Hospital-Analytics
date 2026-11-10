"""Decompression with the real pyreaddbc C code, using SYNTHETIC .dbc files."""

import pytest
from synthetic_data import SYNTHETIC_FIELDS, build_dbc, build_dbf, write

from hospital_analytics.dbc import DbcError, decompress_dbc, read_dbf_header


def test_roundtrip_is_byte_identical(tmp_path, dbc_file, dbf_bytes):
    out = tmp_path / "out.dbf"
    decompress_dbc(dbc_file, out)
    assert out.read_bytes() == dbf_bytes


def test_header_is_parsed(dbc_file):
    header = read_dbf_header(dbc_file)
    assert header.numrecords == 25
    assert header.last_update == "2025-02-08"  # year byte 125 = 1900 + 125
    assert header.recordlen == 1 + sum(f.length for f in SYNTHETIC_FIELDS)


def test_empty_table_roundtrip(tmp_path):
    dbf = build_dbf(SYNTHETIC_FIELDS, [])
    dbc = write(tmp_path / "empty.dbc", build_dbc(dbf))
    out = tmp_path / "out.dbf"
    decompress_dbc(dbc, out)
    assert out.read_bytes() == dbf


def test_source_is_not_modified(tmp_path, dbc_file):
    before = dbc_file.read_bytes()
    decompress_dbc(dbc_file, tmp_path / "out.dbf")
    assert dbc_file.read_bytes() == before


def test_refuses_to_overwrite_destination(tmp_path, dbc_file):
    out = write(tmp_path / "out.dbf", b"keep me")
    with pytest.raises(FileExistsError):
        decompress_dbc(dbc_file, out)
    assert out.read_bytes() == b"keep me"


def test_missing_source(tmp_path):
    with pytest.raises(FileNotFoundError):
        decompress_dbc(tmp_path / "nope.dbc", tmp_path / "out.dbf")


@pytest.mark.parametrize(
    "content",
    [
        b"",  # empty file
        b"not a dbc file at all, just text",  # garbage
        b"\x03\x7d\x02\x08" + b"\x00" * 4 + b"\x05\x00" + b"\x00" * 30,  # headerlen 5 < 33
    ],
    ids=["empty", "garbage", "implausible-header"],
)
def test_invalid_files_are_rejected_without_leftovers(tmp_path, content):
    src = write(tmp_path / "bad.dbc", content)
    out = tmp_path / "out.dbf"
    with pytest.raises(DbcError):
        decompress_dbc(src, out)
    assert not out.exists()


def test_truncated_dbc_is_detected(tmp_path, dbc_file):
    """The C decoder only prints an error on truncated input; the size check must catch it."""
    data = dbc_file.read_bytes()
    src = write(tmp_path / "truncated.dbc", data[: len(data) // 2])
    out = tmp_path / "out.dbf"
    with pytest.raises(DbcError, match="inconsistent with its header"):
        decompress_dbc(src, out)
    assert not out.exists()
