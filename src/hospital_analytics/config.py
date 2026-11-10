"""Project configuration: locate the project root and load ``config/params.yaml``."""

from __future__ import annotations

from decimal import Decimal
from functools import cache
from pathlib import Path
from typing import Any

import yaml

PARAMS_RELATIVE_PATH = Path("config") / "params.yaml"


def project_root() -> Path:
    """Return the project root: the nearest ancestor of this file holding ``pyproject.toml``."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise FileNotFoundError("Could not locate project root (no pyproject.toml found).")


@cache
def load_params(path: Path | None = None) -> dict[str, Any]:
    """Load the YAML parameters file (cached; treat the result as read-only)."""
    params_path = path or project_root() / PARAMS_RELATIVE_PATH
    with params_path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def data_path(layer: str) -> Path:
    """Absolute path of a data layer declared under ``paths`` (e.g. ``raw``, ``processed``)."""
    paths = load_params()["paths"]
    if layer not in paths:
        raise KeyError(f"Unknown data layer {layer!r}; expected one of {sorted(paths)}.")
    return project_root() / paths[layer]


def to_money(value: str | int) -> Decimal:
    """Parse a monetary value stored as text into an exact ``Decimal``.

    Floats are rejected: they cannot represent cents exactly.
    """
    if isinstance(value, float):
        raise TypeError("Monetary values must be given as str or int, never float.")
    return Decimal(str(value))
