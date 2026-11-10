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


@pytest.fixture
def sih_layers(tmp_path):
    """SYNTHETIC SIH-like raw and processed layers built through the real pipeline."""
    from synthetic_data import SIH_FIELDS, sih_rows

    from hospital_analytics.convert import convert_dbc_to_parquet
    from hospital_analytics.processed import build_processed

    dbc = write(
        tmp_path / "SIH.dbc", build_dbc(build_dbf(SIH_FIELDS, sih_rows(), language_driver=0x02))
    )
    raw = tmp_path / "raw.parquet"
    raw_report = convert_dbc_to_parquet(dbc, raw)
    processed = tmp_path / "processed.parquet"
    processed_report = build_processed(raw, processed)
    return raw, processed, raw_report, processed_report
