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


# ---------------------------------------------------------------------------
# SIH-like SYNTHETIC layout (subset of RD fields used by processed/audit/indicators).
# ---------------------------------------------------------------------------
MONEY_COMPONENTS = (
    ("VAL_SH", 13), ("VAL_SP", 13), ("VAL_SADT", 13), ("VAL_RN", 13), ("VAL_ACOMP", 13),
    ("VAL_ORTP", 13), ("VAL_SANGUE", 13), ("VAL_SADTSR", 11), ("VAL_TRANSP", 13),
    ("VAL_OBSANG", 11), ("VAL_PED1AC", 11),
)  # fmt: skip

SIH_FIELDS = (
    FieldSpec("ANO_CMPT", "C", 4),
    FieldSpec("MES_CMPT", "C", 2),
    FieldSpec("N_AIH", "C", 13),
    FieldSpec("IDENT", "C", 1),
    FieldSpec("NASC", "C", 8),
    FieldSpec("DT_INTER", "C", 8),
    FieldSpec("DT_SAIDA", "C", 8),
    FieldSpec("COD_IDADE", "C", 1),
    FieldSpec("IDADE", "N", 2),
    FieldSpec("DIAS_PERM", "N", 5),
    FieldSpec("MORTE", "N", 1),
    FieldSpec("COBRANCA", "C", 2),
    FieldSpec("PROC_REA", "C", 10),
    FieldSpec("SEQUENCIA", "N", 9),
    FieldSpec("CNES", "C", 7),
    FieldSpec("SEXO", "C", 1),
    FieldSpec("ESPEC", "C", 2),
    FieldSpec("CAR_INT", "C", 2),
    FieldSpec("COMPLEX", "C", 2),
    FieldSpec("RACA_COR", "C", 2),
    FieldSpec("MUNIC_RES", "C", 6),
    FieldSpec("MUNIC_MOV", "C", 6),
    FieldSpec("DIAG_PRINC", "C", 4),
    FieldSpec("NAT_JUR", "C", 4),
    FieldSpec("GESTAO", "C", 1),
    *(FieldSpec(name, "N", length, 2) for name, length in MONEY_COMPONENTS),
    FieldSpec("VAL_TOT", "N", 14, 2),
    FieldSpec("VAL_UTI", "N", 8, 2),
)


@dataclass(frozen=True)
class SihRecord:
    """One fictitious admission; ``row()`` renders it in SIH_FIELDS order."""

    n_aih: str
    ident: str
    dt_inter: str
    dt_saida: str
    cod_idade: str
    idade: int
    dias_perm: int
    morte: int
    proc_rea: str
    sh: str
    sp: str
    seq: int
    val_uti: str = "0.00"
    nasc: str = "19800101"
    cnes: str = "0000001"
    sexo: str = "1"
    espec: str = "03"
    car_int: str = "02"
    complex: str = "02"
    raca_cor: str = "03"
    munic_res: str = "330455"
    munic_mov: str = "330455"
    diag_princ: str = "J189"
    nat_jur: str = "1023"
    gestao: str = "1"

    @property
    def val_tot(self) -> str:
        from decimal import Decimal

        return str(Decimal(self.sh) + Decimal(self.sp))

    def row(self) -> list[str]:
        cobranca = "41" if self.morte else "12"
        money = [self.sh, self.sp] + ["0.00"] * (len(MONEY_COMPONENTS) - 2)
        return [
            "2024", "01", self.n_aih, self.ident, self.nasc, self.dt_inter, self.dt_saida,
            self.cod_idade, str(self.idade), str(self.dias_perm), str(self.morte), cobranca,
            self.proc_rea, str(self.seq), self.cnes, self.sexo, self.espec, self.car_int,
            self.complex, self.raca_cor, self.munic_res, self.munic_mov, self.diag_princ,
            self.nat_jur, self.gestao, *money, self.val_tot, self.val_uti,
        ]  # fmt: skip


SIH_RECORDS = (
    SihRecord("3324100000001", "1", "20240102", "20240105", "4", 40, 3, 0, "0303010010", "800.00", "200.00", 1),
    SihRecord("3324100000002", "1", "20231220", "20231228", "4", 70, 8, 1, "0415010010", "4000.00", "1000.50", 2, sexo="3", espec="01", cnes="0000002"),
    SihRecord("3324100000003", "1", "20240110", "20240111", "2", 15, 1, 0, "0303150010", "300.00", "0.00", 3),
    SihRecord("3324100000004", "1", "20240103", "20240110", "3", 6, 7, 0, "0303150010", "600.00", "50.00", 4, sexo="3", car_int="01", raca_cor="01", munic_res="350000"),
    SihRecord("3324100000005", "1", "20240105", "20240106", "5", 2, 1, 1, "0303060010", "900.00", "100.00", 5),
    SihRecord("3324100000006", "1", "20231101", "20231130", "4", 55, 29, 0, "0415020010", "9000.00", "3000.00", 6, espec="01", complex="03",
              val_uti="166200.0"),
    SihRecord("3324100000007", "5", "20230101", "20240131", "4", 80, 31, 0, "0303170010", "1500.00", "0.00", 7),
    SihRecord("3324100000007", "1", "20230101", "20231231", "4", 80, 30, 0, "0303170010", "1500.00", "0.00", 8),
    SihRecord("3324100000008", "1", "20240115", "20240120", "4", 33, 5, 0, "0201010010", "120.00", "0.00", 9),
    SihRecord("3324100000009", "1", "20240112", "20240114", "4", 28, 2, 0, "0411010010", "1000.00", "0.00", 10),
    SihRecord("3324100000010", "1", "20240112", "20240114", "4", 28, 2, 0, "0411010010", "1000.00", "0.00", 11),
)  # fmt: skip


def sih_rows() -> list[list[str]]:
    return [r.row() for r in SIH_RECORDS]
