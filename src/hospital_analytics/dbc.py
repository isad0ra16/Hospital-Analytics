"""Decompression of DATASUS ``.dbc`` files into ``.dbf``.

A ``.dbc`` file is the DBF header, followed by a 4-byte CRC, followed by the DBF records
compressed with PKWare DCL "implode". ``pyreaddbc.dbc2dbf`` (C code) decompresses it, in a
child process (see ``_run_decoder``).

Important: on error, the C function only *prints* a message and returns normally; it may
leave an empty or truncated ``.dbf`` behind. This module therefore never trusts the call
alone: it checks that the output has exactly the size declared by the DBF header.
"""

from __future__ import annotations

import struct
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

DBF_HEADER_PREFIX = struct.Struct(
    "<BBBBIHH"
)  # version, YY, MM, DD, numrecords, headerlen, recordlen
MIN_HEADER_LEN = 33  # 32-byte table header + 0x0D terminator (no fields)
DBF_EOF_MARKER = 0x1A


class DbcError(Exception):
    """The .dbc file is invalid or its decompression did not produce a consistent .dbf."""


def dbf_date(yy: int, mm: int, dd: int) -> str:
    """DBF "last update" date. The year byte counts years since 1900 (e.g. 125 -> 2025)."""
    return f"{1900 + yy:04d}-{mm:02d}-{dd:02d}"


@dataclass(frozen=True)
class DbfHeader:
    version: int
    last_update: str
    numrecords: int
    headerlen: int
    recordlen: int

    @property
    def expected_size(self) -> int:
        """Size of header + records, without the optional trailing EOF marker."""
        return self.headerlen + self.numrecords * self.recordlen


def read_dbf_header(path: Path) -> DbfHeader:
    """Parse the fixed part of a DBF header (also valid for the start of a .dbc)."""
    with Path(path).open("rb") as fh:
        raw = fh.read(DBF_HEADER_PREFIX.size)
    if len(raw) < DBF_HEADER_PREFIX.size:
        raise DbcError(f"{path}: too small to contain a DBF header ({len(raw)} bytes).")
    version, yy, mm, dd, numrecords, headerlen, recordlen = DBF_HEADER_PREFIX.unpack(raw)
    if headerlen < MIN_HEADER_LEN or recordlen < 1:
        raise DbcError(
            f"{path}: implausible DBF header (headerlen={headerlen}, recordlen={recordlen})."
        )
    return DbfHeader(version, dbf_date(yy, mm, dd), numrecords, headerlen, recordlen)


def check_dbf_size(path: Path, header: DbfHeader) -> None:
    """Raise if the file size does not match header + records (+ optional 0x1A marker)."""
    size = Path(path).stat().st_size
    expected = header.expected_size
    if size == expected:
        return
    if size == expected + 1:
        with Path(path).open("rb") as fh:
            fh.seek(-1, 2)
            if fh.read(1)[0] == DBF_EOF_MARKER:
                return
    raise DbcError(
        f"{path}: size {size} bytes is inconsistent with its header "
        f"({header.headerlen} + {header.numrecords} x {header.recordlen} = {expected} bytes)."
    )


def decompress_dbc(source: Path, destination: Path) -> DbfHeader:
    """Decompress ``source`` (.dbc) into ``destination`` (.dbf) and verify the result.

    The source is only read. The destination must not exist. On any failure the partial
    destination is removed and ``DbcError`` is raised.
    """
    source, destination = Path(source), Path(destination)
    if not source.is_file():
        raise FileNotFoundError(f"Source .dbc not found: {source}")
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite existing file: {destination}")

    header = read_dbf_header(source)
    try:
        diagnostics = _run_decoder(source, destination)
        if not destination.is_file():
            raise DbcError(f"Decompression produced no output for {source}. {diagnostics}".strip())
        try:
            check_dbf_size(destination, header)
        except DbcError as exc:
            raise DbcError(f"{exc} {diagnostics}".strip()) from None
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return header


_DECODER = "import sys, pyreaddbc; pyreaddbc.dbc2dbf(sys.argv[1], sys.argv[2])"


def _run_decoder(source: Path, destination: Path) -> str:
    """Run ``pyreaddbc.dbc2dbf`` in a child process and return its diagnostic output.

    On invalid input the C decoder returns without closing the output file. In-process, that
    leaked handle keeps the partial ``.dbf`` locked on Windows (WinError 32), so it could not be
    removed. A child process releases every handle when it exits, on any platform, and also lets
    the messages the C code prints be captured instead of leaking to the console.
    """
    result = subprocess.run(
        # -I: isolated mode, so the current directory never shadows an installed module.
        [sys.executable, "-I", "-c", _DECODER, str(source), str(destination)],
        capture_output=True,
        text=True,
        check=False,
    )
    output = " ".join((result.stdout + " " + result.stderr).split())
    if result.returncode != 0:
        raise DbcError(f"Decoder failed for {source} (exit {result.returncode}): {output}")
    return f"(decoder output: {output})" if output else ""
