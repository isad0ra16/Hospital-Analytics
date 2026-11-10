"""SYNTHETIC test data builders. Nothing here is real SIH/SUS data.

* ``build_dbf``: writes a dBase III table (the format of DATASUS files after decompression).
* ``implode_literals``: a minimal PKWare DCL "implode" encoder that emits only uncoded
  literals plus the end-of-stream code. It is enough to produce valid ``.dbc`` input for
  ``pyreaddbc.dbc2dbf`` (which uses Mark Adler's ``blast`` decoder):
    - stream header: byte 0 = 0 (uncoded literals), byte 1 = 4..6 (dictionary size);
    - literal: flag bit 0, then the 8 bits of the byte;
    - end of stream: flag bit 1, length symbol 15 (7-bit code ``1111111``, stored
      inverted as seven 0 bits), then 8 extra bits = 255 -> length 264 + 255 = 519;
    - bits are packed least-significant-bit first.
* ``build_dbc``: DBF header + 4-byte CRC placeholder (not checked by the decoder) +
  imploded records.
"""

from __future__ import annotations

import struct
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FieldSpec:
    name: str
    type: str  # "C" character, "N" numeric
    length: int
    decimal_count: int = 0


# A small, SIH-like layout. Values are fictitious.
SYNTHETIC_FIELDS = (
    FieldSpec("N_AIH", "C", 13),
    FieldSpec("IDENT", "C", 1),
    FieldSpec("MUNIC_RES", "C", 6),
    FieldSpec("DT_INTER", "C", 8),
    FieldSpec("DT_SAIDA", "C", 8),
    FieldSpec("DIAGSEC9", "C", 4),
    FieldSpec("VAL_TOT", "N", 12, 2),
)


def synthetic_rows(n: int) -> list[list[str]]:
    """Deterministic fictitious rows matching SYNTHETIC_FIELDS (leading zeros, blanks...)."""
    rows = []
    for i in range(n):
        rows.append(
            [
                f"{3324100000000 + i:013d}",
                "5" if i % 10 == 0 else "1",
                f"{(330455 + i) % 1000000:06d}" if i % 7 else "003300",  # leading zeros
                f"2023{(i % 12) + 1:02d}15",
                f"2024{(i % 2) + 1:02d}01" if i % 3 else f"2023{(i % 12) + 1:02d}28",
                "",  # always blank, like an empty column
                f"{(i * 137.31) % 9000 + 0.05:.2f}",
            ]
        )
    return rows


def money_sum(rows: Sequence[Sequence[str]], column: int = 6) -> str:
    from decimal import Decimal

    return str(sum((Decimal(r[column]) for r in rows), Decimal(0)))


def build_dbf(
    fields: Sequence[FieldSpec],
    rows: Sequence[Sequence[str]],
    *,
    deleted: frozenset[int] = frozenset(),
    encoding: str = "latin-1",
    eof_marker: bool = True,
    declared_records: int | None = None,
    language_driver: int = 0x00,
) -> bytes:
    """Build a dBase III file in memory. ``deleted`` holds row indexes flagged with '*'."""
    headerlen = 32 + 32 * len(fields) + 1
    recordlen = 1 + sum(f.length for f in fields)
    n = len(rows) if declared_records is None else declared_records
    # 20 reserved bytes; the "language driver" (code page) is byte 29 of the header.
    header = struct.pack(
        "<BBBBIHH17xB2x", 0x03, 125, 2, 8, n, headerlen, recordlen, language_driver
    )
    for f in fields:
        header += struct.pack(
            "<11sc4xBB14x",
            f.name.encode("ascii"),
            f.type.encode("ascii"),
            f.length,
            f.decimal_count,
        )
    header += b"\r"

    body = bytearray()
    for i, row in enumerate(rows):
        body += b"*" if i in deleted else b" "
        for f, value in zip(fields, row, strict=True):
            raw = value.encode(encoding)
            if len(raw) > f.length:
                raise ValueError(f"{f.name}: {value!r} longer than {f.length}")
            body += raw.rjust(f.length) if f.type == "N" else raw.ljust(f.length)
    if eof_marker:
        body += b"\x1a"
    return header + bytes(body)


def implode_literals(data: bytes, dict_size_code: int = 6) -> bytes:
    out = bytearray([0, dict_size_code])
    bitbuf = bitcnt = 0

    def put(value: int, nbits: int) -> None:
        nonlocal bitbuf, bitcnt
        bitbuf |= value << bitcnt
        bitcnt += nbits
        while bitcnt >= 8:
            out.append(bitbuf & 0xFF)
            bitbuf >>= 8
            bitcnt -= 8

    for byte in data:
        put(0, 1)
        put(byte, 8)
    put(1, 1)  # length/distance pair follows
    put(0, 7)  # length symbol 15
    put(0xFF, 8)  # extra bits: 264 + 255 = 519 -> end of stream
    if bitcnt:
        out.append(bitbuf & 0xFF)
    return bytes(out)


def build_dbc(dbf: bytes) -> bytes:
    headerlen = struct.unpack_from("<H", dbf, 8)[0]
    return dbf[:headerlen] + b"\x00\x00\x00\x00" + implode_literals(dbf[headerlen:])


def write(path: Path, content: bytes) -> Path:
    path.write_bytes(content)
    return path
