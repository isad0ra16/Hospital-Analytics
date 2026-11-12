"""Power BI star schema on SYNTHETIC data: keys, relationships, totals, nulls, privacy,
reproducibility, measure semantics and generated documentation."""

import csv
import dataclasses
import re
import shutil
from decimal import Decimal

import pytest
from synthetic_data import SIH_FIELDS, SIH_RECORDS, build_dbc, build_dbf, write
from synthetic_references import build_references

from hospital_analytics import powerbi
from hospital_analytics.config import project_root
from hospital_analytics.convert import convert_dbc_to_parquet
from hospital_analytics.enrichment import load_references
from hospital_analytics.processed import build_processed

EDGE_RECORD = dataclasses.replace(
    SIH_RECORDS[0], n_aih="3324100000099", cod_idade="0", idade=0, espec="87", seq=99
)
RECORDS = (*SIH_RECORDS, EDGE_RECORD)


@pytest.fixture
def exported(tmp_path):
    rows = [r.row() for r in RECORDS]
    dbc = write(tmp_path / "S.dbc", build_dbc(build_dbf(SIH_FIELDS, rows, language_driver=0x02)))
    convert_dbc_to_parquet(dbc, tmp_path / "raw.parquet")
    build_processed(tmp_path / "raw.parquet", tmp_path / "processed.parquet")
    out = tmp_path / "powerbi"
    refs = load_references(tmp_path / "ref", build_references(tmp_path / "ref"))
    summary = powerbi.export_model(tmp_path / "processed.parquet", out, references=refs)
    return out, summary


def references(tmp_path):
    return load_references(tmp_path / "ref", build_references(tmp_path / "ref"))


def read(directory, table):
    with (directory / f"{table}.csv").open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def expected():
    cents = [int(r.val_tot.replace(".", "")) for r in RECORDS]
    return {
        "records": len(RECORDS),
        "val_tot_cents": sum(cents),
        "deaths": sum(r.morte for r in RECORDS),
        "dias_perm_sum": sum(r.dias_perm for r in RECORDS),
        "age_years_count": sum(r.cod_idade in {"2", "3", "4", "5"} for r in RECORDS),
        "distinct_aih": len({r.n_aih for r in RECORDS}),
    }


def test_every_check_passes_on_a_consistent_export(exported):
    out, _ = exported
    failed = [c for c in powerbi.validate_model(out, expected()) if not c.passed]
    assert not failed, failed


def test_relationships_have_no_orphans_and_joins_do_not_duplicate(exported):
    out, _ = exported
    checks = {c.name: c for c in powerbi.validate_model(out, expected())}
    assert checks["join with all active dimensions keeps row count"].observed == len(RECORDS)
    assert all(c.observed == 0 for n, c in checks.items() if n.startswith("RI "))


def test_missing_dimension_row_is_detected(tmp_path, exported):
    out, _ = exported
    broken = tmp_path / "broken"
    shutil.copytree(out, broken)
    path = broken / "dim_especialidade.csv"
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    path.write_text("".join(line for line in lines if not line.startswith("87,")), encoding="utf-8")
    failed = {c.name for c in powerbi.validate_model(broken, expected()) if not c.passed}
    assert "RI fato.especialidade_cod -> dim_especialidade.especialidade_cod: orphans" in failed


def test_duplicated_dimension_row_is_detected(tmp_path, exported):
    out, _ = exported
    broken = tmp_path / "broken"
    shutil.copytree(out, broken)
    path = broken / "dim_tipo_aih.csv"
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    path.write_text("".join(lines) + lines[1], encoding="utf-8")
    failed = {c.name for c in powerbi.validate_model(broken, expected()) if not c.passed}
    assert "dim_tipo_aih: key tipo_aih_cod unique" in failed
    assert "join with all active dimensions keeps row count" in failed  # fan-out caught


def test_financial_total_is_preserved_exactly(exported):
    out, summary = exported
    fact = read(out, "fato_registro_aih")
    assert sum(int(r["valor_total_centavos"]) for r in fact) == expected()["val_tot_cents"]
    assert (
        sum(Decimal(r["valor_total"]) for r in fact) == Decimal(expected()["val_tot_cents"]) / 100
    )
    assert summary["fact_valor_total_centavos"] == expected()["val_tot_cents"]


def test_unknown_age_unit_becomes_null_and_unlabelled_code_is_kept(exported):
    out, _ = exported
    fact = read(out, "fato_registro_aih")
    edge = next(r for r in fact if r["especialidade_cod"] == "87")
    assert edge["idade_anos"] == ""  # empty field = null in Power Query
    profile = {p["perfil_id"]: p for p in read(out, "dim_perfil_demografico")}
    assert profile[edge["perfil_id"]]["faixa_etaria"] == "sem informação"
    espec = {d["especialidade_cod"]: d for d in read(out, "dim_especialidade")}
    assert espec["87"]["descricao"] == ""
    assert espec["87"]["fonte"] == "sem rótulo na fonte disponível"
    assert espec["01"]["fonte"] == "fonte secundária (microdatasus)"
    # the official TabWin table labels the code the secondary source left blank
    assert espec["87"]["descricao_oficial"] == "Saúde Mental (Clínico)"
    assert espec["87"]["fonte_oficial"].endswith("LEITOS.CNV")


def test_dates_are_exported_at_month_granularity_only(exported):
    out, _ = exported
    fact = read(out, "fato_registro_aih")
    assert all(r["mes_saida"].endswith("-01") and r["mes_internacao"].endswith("-01") for r in fact)
    assert [int(r["dias_permanencia"]) for r in fact] == [r.dias_perm for r in RECORDS]
    months = {m["mes"] for m in read(out, "dim_mes")}
    assert {r["mes_saida"] for r in fact} <= months


def test_identifying_fields_are_never_exported(exported):
    out, _ = exported
    headers = set()
    for t in powerbi.TABLES:
        with (out / f"{t.name}.csv").open(encoding="utf-8") as fh:
            headers |= set(next(csv.reader(fh)))
    forbidden = {"N_AIH", "NASC", "CEP", "CPF_AUT", "GESTOR_CPF", "INSC_PN", "AUD_JUST", "SIS_JUST"}
    assert not {h.upper() for h in headers} & forbidden
    assert {"data_saida", "data_internacao"}.isdisjoint(headers)
    content = "".join((out / f"{t.name}.csv").read_text(encoding="utf-8") for t in powerbi.TABLES)
    assert "3324100000007" not in content  # an N_AIH value
    assert "19800101" not in content  # a NASC value


def test_pseudonymous_aih_id_supports_distinct_counts(exported):
    out, _ = exported
    fact = read(out, "fato_registro_aih")
    assert len({r["aih_id"] for r in fact}) == expected()["distinct_aih"]
    repeated = [r for r in fact if r["aih_repetida"] == "1"]
    assert len(repeated) == 2 and len({r["aih_id"] for r in repeated}) == 1


def test_export_is_reproducible_byte_for_byte(tmp_path, exported):
    out, summary = exported
    again = powerbi.export_model(
        tmp_path / "processed.parquet", tmp_path / "again", references=references(tmp_path)
    )
    assert again == summary
    for t in powerbi.TABLES:
        assert (out / f"{t.name}.csv").read_bytes() == (
            tmp_path / "again" / f"{t.name}.csv"
        ).read_bytes()


def test_optional_parquet_matches_csv(tmp_path, exported):
    import duckdb

    powerbi.export_model(
        tmp_path / "processed.parquet",
        tmp_path / "pq",
        references=references(tmp_path),
        parquet=True,
    )
    con = duckdb.connect()
    for t in powerbi.TABLES:
        base = tmp_path / "pq" / t.name
        csv_rows = con.execute(f"select * from read_csv('{base}.csv', all_varchar=true)").fetchall()
        pq_rows = con.execute(f"select * from read_parquet('{base}.parquet')").fetchall()
        assert len(csv_rows) == len(pq_rows), t.name


def test_measure_semantics(exported):
    out, _ = exported
    m = powerbi.measure_values(out)
    e = expected()
    assert m["mortalidade_razao"] == Decimal(e["deaths"]) / e["records"]  # a ratio, not x100
    assert m["mortalidade_razao"] < 1
    cents = sorted((int(r.val_tot.replace(".", "")) for r in RECORDS), reverse=True)
    k = len(RECORDS) // 10
    assert m["concentracao_top10_razao"] == Decimal(sum(cents[:k])) / sum(cents)


DOCS = project_root() / "docs" / "powerbi"


def test_generated_documentation_is_up_to_date():
    assert (DOCS / "dicionario_campos.md").read_text(
        encoding="utf-8"
    ) == powerbi.field_dictionary_markdown()
    assert (DOCS / "consultas_power_query.pq").read_text(
        encoding="utf-8"
    ) == powerbi.power_query_m()


def test_dax_measures_follow_the_project_rules():
    dax = (DOCS / "medidas.dax").read_text(encoding="utf-8")
    mortality = dax.split("Mortalidade hospitalar (razão)")[1].split("\n\n")[0]
    assert "* 100" not in mortality and "DIVIDE" in mortality
    assert "fato_registro_aih[registro_id], ASC" in dax  # TOPN tie-break -> exactly k rows
    assert "USERELATIONSHIP ( fato_registro_aih[mes_internacao], dim_mes[mes] )" in dax
    referenced = set(re.findall(r"(\w+)\[(\w+)\]", dax))
    known = {(t.name, c.name) for t in powerbi.TABLES for c in t.columns}
    assert referenced <= known, referenced - known


def test_dashboard_measures_semantics(exported):
    out, _ = exported
    m = powerbi.measure_values(out)
    n = len(RECORDS)
    assert m["aihs_distintas"] == len({r.n_aih for r in RECORDS})
    assert m["registros_excedentes_aih"] == n - len({r.n_aih for r in RECORDS})
    assert m["estabelecimentos"] == len({r.cnes for r in RECORDS})
    assert m["pct_urgencia_razao"] == Decimal(sum(r.car_int == "02" for r in RECORDS)) / n
    moved = sum(r.munic_res != r.munic_mov for r in RECORDS)  # residence != establishment
    assert m["pct_residentes_outro_municipio_razao"] == Decimal(moved) / n
    assert (
        m["pct_residentes_fora_rj_razao"]
        == Decimal(sum(not r.munic_res.startswith("33") for r in RECORDS)) / n
    )
    principal = [r for r in RECORDS if r.ident == "1"]
    assert m["mortalidade_aih_principal_razao"] == Decimal(sum(r.morte for r in principal)) / len(
        principal
    )


def test_lorenz_table_is_monotonic_and_matches_the_value_shares(exported):
    out, _ = exported
    points = powerbi.lorenz_points(out)
    assert sorted(points) == list(range(101))
    assert points[0] == 0 and points[100] == 1
    values = [points[p] for p in range(101)]
    assert values == sorted(values)  # cumulative share never decreases
    cents = sorted(int(r.val_tot.replace(".", "")) for r in RECORDS)
    m = len(cents) * 50 // 100  # floor(n * p / 100), poorest records first
    assert points[50] == (Decimal(sum(cents[:m])) / sum(cents)).quantize(Decimal("0.000001"))
