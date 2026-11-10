"""Versioned SQL (DuckDB): load ``sql/<group>/<name>.sql`` and run it against the data layers.

Views registered on every connection:

* ``raw_rd``: raw layer (113 text columns, exactly as in the DBF);
* ``rd``: processed layer (original columns + lowercase derived columns).

Parameters are bound with DuckDB's ``$name`` placeholders, never by string formatting.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb

from hospital_analytics.config import project_root

SQL_DIR = project_root() / "sql"


def read_sql(name: str) -> str:
    """Return the text of ``sql/<name>.sql`` (``name`` like ``"audit/discharge_year"``)."""
    path = SQL_DIR / f"{name}.sql"
    if not path.is_file():
        raise FileNotFoundError(f"SQL file not found: {path}")
    return path.read_text(encoding="utf-8")


def _literal_path(path: Path) -> str:
    return "'" + str(Path(path).resolve()).replace("'", "''") + "'"


def connect(raw: Path | None = None, processed: Path | None = None) -> duckdb.DuckDBPyConnection:
    """In-memory DuckDB connection with the data layers registered as views."""
    con = duckdb.connect()
    if raw is not None:
        con.execute(f"create view raw_rd as select * from read_parquet({_literal_path(raw)})")
    if processed is not None:
        con.execute(f"create view rd as select * from read_parquet({_literal_path(processed)})")
    return con


def query(con: duckdb.DuckDBPyConnection, name: str, **params: Any) -> list[dict[str, Any]]:
    """Run a versioned query and return its rows as dictionaries."""
    cursor = con.execute(read_sql(name), params or None)
    columns = [d[0] for d in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]
