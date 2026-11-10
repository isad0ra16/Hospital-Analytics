"""Guarantee that data, secrets and temporary files can never be committed.

Uses ``git check-ignore`` so the real Git behavior is tested, not just the text of .gitignore.
"""

import shutil
import subprocess

import pytest

from hospital_analytics.config import project_root

ROOT = project_root()

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None or not (ROOT / ".git").exists(),
    reason="requires a git checkout",
)


def is_ignored(relative_path: str) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "-q", relative_path],
        cwd=ROOT,
        check=False,
    )
    return result.returncode == 0


@pytest.mark.parametrize(
    "path",
    [
        "data/raw/RDRJ2401.dbc",
        "data/raw/RDRJ2401.dbf",
        "data/raw/RDRJ2401.parquet",
        "data/processed/sih_rj_2024_01.parquet",
        "data/processed/sih_rj_2024_01_tratado.parquet",
        "data/processed/some_export.csv",
        "notebooks/RDRJ2401.dbc",
        "analysis.duckdb",
        ".env",
        ".env.local",
        ".venv/bin/python",
        "notebooks/.ipynb_checkpoints/x.ipynb",
        "src/hospital_analytics/__pycache__/config.cpython-313.pyc",
    ],
)
def test_sensitive_or_bulky_paths_are_ignored(path):
    assert is_ignored(path), f"{path} would be committed"


@pytest.mark.parametrize(
    "path",
    [
        "data/raw/.gitkeep",
        "data/processed/.gitkeep",
        "data/README.md",
        "data/MANIFEST.json",
        "config/params.yaml",
        "pyproject.toml",
        "uv.lock",
        "src/hospital_analytics/config.py",
        "sql/.gitkeep",
    ],
)
def test_project_files_are_not_ignored(path):
    assert not is_ignored(path), f"{path} is wrongly ignored"
