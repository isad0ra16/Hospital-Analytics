import pytest

from hospital_analytics.sql import SQL_DIR, connect, query, read_sql


def test_every_sql_file_has_a_header_comment():
    files = sorted(SQL_DIR.rglob("*.sql"))
    assert files
    assert all(p.read_text(encoding="utf-8").startswith("--") for p in files)


def test_missing_sql_file():
    with pytest.raises(FileNotFoundError):
        read_sql("audit/does_not_exist")


def test_views_and_parameters(sih_layers):
    raw, processed, _, _ = sih_layers
    con = connect(raw=raw, processed=processed)
    assert con.execute("select count(*) from raw_rd").fetchall() == [(11,)]
    all_rows = query(con, "indicators/proc_group_value_share", ident=None)
    ident5 = query(con, "indicators/proc_group_value_share", ident="5")
    assert sum(r["records"] for r in all_rows) == 11
    assert sum(r["records"] for r in ident5) == 1
