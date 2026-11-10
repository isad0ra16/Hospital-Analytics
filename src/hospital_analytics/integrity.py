"""Integrity primitives: file hashes and content fingerprints.

Two different questions need two different tools:

* ``sha256_file`` answers "is this the exact same file (byte for byte)?". It is the right
  identity for the original ``.dbc`` published by DATASUS.
* ``ContentFingerprint`` answers "does this table hold exactly the same values, in the
  same order?". Parquet files embed writer metadata (library version, compression), so two
  conversions of identical data can have different file hashes; the content fingerprint
  stays the same. It is used to prove that no value was lost between the DBF and Parquet.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Sequence
from pathlib import Path

_CHUNK_SIZE = 1 << 20  # 1 MiB


def sha256_file(path: Path) -> str:
    """Return the hex SHA-256 digest of a file, read in chunks (constant memory)."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        while chunk := fh.read(_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


class ContentFingerprint:
    """Order-sensitive SHA-256 over column names and row values.

    Every value is length-prefixed before hashing, so different splits of the same
    characters (``["ab", "c"]`` vs ``["a", "bc"]``) produce different fingerprints.
    """

    def __init__(self, column_names: Sequence[str]) -> None:
        self._digest = hashlib.sha256()
        self._n_columns = len(column_names)
        self.rows = 0
        self._update_values(column_names)

    def _update_values(self, values: Iterable[str]) -> None:
        for value in values:
            encoded = value.encode("utf-8")
            self._digest.update(len(encoded).to_bytes(4, "little"))
            self._digest.update(encoded)

    def update_row(self, values: Sequence[str]) -> None:
        if len(values) != self._n_columns:
            raise ValueError(f"Row has {len(values)} values; expected {self._n_columns}.")
        self._update_values(values)
        self.rows += 1

    def hexdigest(self) -> str:
        return self._digest.hexdigest()
