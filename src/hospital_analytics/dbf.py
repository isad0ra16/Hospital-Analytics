"""Raw reading of ``.dbf`` files, without interpreting field values.

Values are returned exactly as stored, decoded as text:

* bytes are decoded with the code page declared in the DBF header ("language driver" byte).
  DATASUS files declare 0x02 = CP850 (MS-DOS Latin-1). CP850, like Latin-1, maps every byte
  0-255 to exactly one character: decoding never fails and is fully reversible;
* only the fixed-width padding (ASCII spaces at both ends) is removed. DBF has no NULL:
  a blank field becomes the empty string ``""``. Interpreting blanks as missing values is a
  treatment and belongs to a later phase.

``dbfread`` silently skips records whose status byte is not ``' '`` (active) or ``'*'``
(deleted) and does not compare against the header record count. ``inspect_dbf`` performs
that comparison explicitly.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from dbfread import DBF

from hospital_analytics.dbc import check_dbf_size, read_dbf_header

# dBase "language driver" byte (header offset 29) -> Python codec.
LANGUAGE_DRIVER_ENCODINGS = {0x01: "cp437", 0x02: "cp850", 0x03: "cp1252"}
DEFAULT_ENCODING = "cp850"  # declared by DATASUS SIH/SUS files (language driver 0x02)
PADDING = b" "


def declared_encoding(language_driver: int) -> str | None:
    """Encoding declared by the DBF header, or None if the header does not declare one."""
    return LANGUAGE_DRIVER_ENCODINGS.get(language_driver)


class DbfError(Exception):
    """The .dbf file is structurally inconsistent."""


@dataclass(frozen=True)
class DbfField:
    name: str
    type: str
    length: int
    decimal_count: int


@dataclass(frozen=True)
class DbfInfo:
    version: int
    last_update: str
    language_driver: int
    numrecords: int
    headerlen: int
    recordlen: int
    fields: tuple[DbfField, ...]
    active_records: int
    deleted_records: int

    @property
    def field_names(self) -> list[str]:
        return [f.name for f in self.fields]


def _open(path: Path, encoding: str) -> DBF:
    return DBF(
        str(path),
        encoding=encoding,
        raw=True,  # return field bytes untouched
        load=False,  # stream records instead of loading everything in memory
        char_decode_errors="strict",
        ignore_missing_memofile=True,
    )


def inspect_dbf(path: Path, encoding: str = DEFAULT_ENCODING) -> DbfInfo:
    """Read DBF structure and verify record counts and file size against the header."""
    path = Path(path)
    header = read_dbf_header(path)
    check_dbf_size(path, header)

    table = _open(path, encoding)
    h = table.header
    active = len(table.records)
    deleted = len(table.deleted)
    if active + deleted != h.numrecords:
        raise DbfError(
            f"{path}: header declares {h.numrecords} records, but found {active} active + "
            f"{deleted} deleted = {active + deleted}. Records with unexpected status bytes "
            "would be silently skipped by the reader."
        )

    fields = tuple(DbfField(f.name, f.type, f.length, f.decimal_count) for f in table.fields)
    return DbfInfo(
        version=h.dbversion,
        last_update=header.last_update,
        language_driver=h.language_driver,
        numrecords=h.numrecords,
        headerlen=h.headerlen,
        recordlen=h.recordlen,
        fields=fields,
        active_records=active,
        deleted_records=deleted,
    )


def iter_raw_rows(path: Path, encoding: str = DEFAULT_ENCODING) -> Iterator[list[bytes]]:
    """Yield active records as lists of the raw field bytes, in file order."""
    for record in _open(Path(path), encoding):
        yield list(record.values())


def strip_padding(raw: bytes) -> bytes:
    """Remove fixed-width space padding (byte 0x20 at both ends), nothing else."""
    return raw.strip(PADDING)


def decode_value(raw: bytes, encoding: str = DEFAULT_ENCODING) -> str:
    """Decode one raw field without its padding.

    Byte 0x20 is the only byte that decodes to " " in the supported code pages, so
    ``decode_value(raw).encode(encoding) == strip_padding(raw)``: the stored text can always
    be turned back into the original bytes.
    """
    return strip_padding(raw).decode(encoding)
