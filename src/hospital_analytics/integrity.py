"""Integrity primitives: file hashes and content fingerprints.

Two different questions need two different tools:

* ``sha256_file`` answers "is this the exact same file (byte for byte)?". It is the right
  identity for the original ``.dbc`` published by DATASUS.
* ``ContentFingerprint`` answers "does this table hold exactly the same values, in the
  same order?". Parquet files embed writer metadata (library version, compression), so two
  conversions of identical data can have different file hashes; the content fingerprint
  stays the same. It is used to prove that no value was lost between the DBF and Parquet.
  Values may be text (hashed as UTF-8) or raw bytes (hashed as they are): a fingerprint over
  raw bytes does not depend on the text encoding used to decode them.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

_CHUNK_SIZE = 1 << 20  # 1 MiB


def check_declared(path: Path, spec: dict[str, Any]) -> dict[str, Any]:
    """Presence, size and SHA-256 of ``path`` against the values declared in ``spec``
    (``size_bytes`` and ``sha256``, as in ``config/params.yaml``). ``integrity_ok`` is False when
    either declared value differs; a value that is not declared is not checked."""
    if not path.is_file():
        return {"file": path.name, "present": False}
    result: dict[str, Any] = {
        "file": path.name,
        "present": True,
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }
    if "size_bytes" in spec:
        result["size_ok"] = result["size_bytes"] == spec["size_bytes"]
    if "sha256" in spec:
        result["sha256_ok"] = result["sha256"] == spec["sha256"].lower()
    result["integrity_ok"] = result.get("size_ok", True) and result.get("sha256_ok", True)
    return result


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

    def _update_values(self, values: Iterable[str | bytes]) -> None:
        for value in values:
            encoded = value if isinstance(value, bytes) else value.encode("utf-8")
            self._digest.update(len(encoded).to_bytes(4, "little"))
            self._digest.update(encoded)

    def update_row(self, values: Sequence[str | bytes]) -> None:
        if len(values) != self._n_columns:
            raise ValueError(f"Row has {len(values)} values; expected {self._n_columns}.")
        self._update_values(values)
        self.rows += 1

    def hexdigest(self) -> str:
        return self._digest.hexdigest()
