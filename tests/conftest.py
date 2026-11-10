from pathlib import Path

import pytest
from synthetic_data import SYNTHETIC_FIELDS, build_dbc, build_dbf, synthetic_rows, write


@pytest.fixture
def rows():
    """25 SYNTHETIC rows (fictitious values)."""
    return synthetic_rows(25)


@pytest.fixture
def dbf_bytes(rows) -> bytes:
    return build_dbf(SYNTHETIC_FIELDS, rows)


@pytest.fixture
def dbc_file(tmp_path: Path, dbf_bytes: bytes) -> Path:
    """A SYNTHETIC .dbc file in a temporary directory (never under data/)."""
    return write(tmp_path / "SYNTH.dbc", build_dbc(dbf_bytes))
