"""Enrichment of the Power BI dimensions with official references, on SYNTHETIC files only:
integrity before reading, exact-code joins, unique reference keys, coverage reported (never
forced), untouched fact and original columns, no personal registry fields exported."""

import csv
import dataclasses

import pytest
from synthetic_data import SIH_FIELDS, SIH_RECORDS, build_dbc, build_dbf, write
from synthetic_references import SIGTAP_TABLES, build_references

from hospital_analytics import powerbi
from hospital_analytics.convert import convert_dbc_to_parquet
from hospital_analytics.enrichment import ReferenceIntegrityError, load_references
from hospital_analytics.processed import build_processed
from hospital_analytics.reference import ReferenceFormatError, enrichment_guard

EDGE = dataclasses.replace(SIH_RECORDS[0], n_aih="3324100000099", espec="87", seq=99)
RECORDS = (*SIH_RECORDS, EDGE)


@pytest.fixture
def processed(tmp_path):
    dbf = build_dbf(SIH_FIELDS, [r.row() for r in RECORDS], language_driver=0x02)
    dbc = write(tmp_path / "S.dbc", build_dbc(dbf))
    convert_dbc_to_parquet(dbc, tmp_path / "raw.parquet")
    build_processed(tmp_path / "raw.parquet", tmp_path / "processed.parquet")
    return tmp_path / "processed.parquet"


def export(tmp_path, processed, name="out", **build_kwargs):
    ref = tmp_path / f"ref_{name}"
    refs = load_references(ref, build_references(ref, **build_kwargs))
    out = tmp_path / name
    powerbi.export_model(processed, out, references=refs)
    return out


def expected():
    cents = [int(r.val_tot.replace(".", "")) for r in RECORDS]
    return {
        "records": len(RECORDS),
        "val_tot_cents": sum(cents),
        "deaths": sum(r.morte for r in RECORDS),
        "dias_perm_sum": sum(r.dias_perm for r in RECORDS),
        "age_years_count": sum(r.cod_idade in {"2", "3", "4", "5"} for r in RECORDS),
    }


def rows(directory, table):
    with (directory / f"{table}.csv").open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def by(directory, table, key):
    return {r[key]: r for r in rows(directory, table)}


def test_dimensions_receive_official_names_by_exact_code(tmp_path, processed):
    out = export(tmp_path, processed)
    est = by(out, "dim_estabelecimento", "cnes")
    assert est["0000001"]["estabelecimento_nome"] == "HOSPITAL SINTETICO UM"
    assert est["0000001"]["estabelecimento_rotulo"] == "HOSPITAL SINTETICO UM (0000001)"
    assert est["0000001"]["municipio_estabelecimento_nome"] == "Rio de Janeiro"
    assert est["0000001"]["natureza_juridica_descricao"] == "Orgao Publico Estadual"
    assert est["0000001"]["esfera_juridica"] == "Administração Pública — Estadual"
    assert est["0000001"]["gestao_descricao"] == "Municipal plena assist"
    proc = by(out, "dim_procedimento", "procedimento_cod")["0415010010"]
    assert proc["procedimento_nome"] == "CIRURGIA SINTETICA A"
    assert (proc["subgrupo_cod"], proc["subgrupo_nome"]) == ("0415", "Múltiplas")
    assert proc["forma_organizacao_cod"] == "041501"
    mun = by(out, "dim_municipio_residencia", "municipio_residencia_cod")
    assert mun["350000"]["municipio_residencia_rotulo"] == "Sintética (SP)"
    assert mun["330455"]["municipio_residencia_ibge"] == "3304557"
    diag = by(out, "dim_diagnostico", "diagnostico_cod")["J189"]
    assert diag["categoria_nome"] == "Pneumonia sintética"
    assert diag["capitulo"] == "X. Doenças do aparelho respiratório"
    assert by(out, "dim_tipo_aih", "tipo_aih_cod")["1"]["descricao_oficial"] == "Normal"
    profile = rows(out, "dim_perfil_demografico")
    assert {p["sexo_cod"]: p["sexo_descricao_oficial"] for p in profile} == {
        "1": "Masculino",
        "3": "Feminino",
    }


def test_full_validation_passes_including_coverage_and_no_fan_out(tmp_path, processed):
    out = export(tmp_path, processed)
    checks = powerbi.validate_model(out, expected())
    assert [c for c in checks if not c.passed] == []
    names = {c.name for c in checks}
    assert "RI fato.diagnostico_principal_cod -> dim_diagnostico.diagnostico_cod: orphans" in names
    assert any(n.startswith("coverage dim_estabelecimento.estabelecimento_nome") for n in names)


def test_enrichment_only_adds_columns_and_keeps_the_fact_byte_identical(tmp_path, processed):
    full = export(tmp_path, processed, "full")
    # Same export with a SIGTAP lacking one procedure: names change, nothing else may.
    tables = dict(SIGTAP_TABLES)
    fields, proc_rows = tables["tb_procedimento"]
    tables["tb_procedimento"] = (fields, [r for r in proc_rows if r[0] != "0303060010"])
    partial = export(tmp_path, processed, "partial", sigtap_tables=tables)
    fact = "fato_registro_aih.csv"
    assert (full / fact).read_bytes() == (partial / fact).read_bytes()
    for table in powerbi.TABLES:
        original = [c.name for c in table.columns if not c.enriched]
        before = [{c: r[c] for c in original} for r in rows(partial, table.name)]
        after = rows(full, table.name)
        assert enrichment_guard(before, after, table.key[0]) == [], table.name


def test_missing_reference_code_stays_blank_and_fails_the_coverage_check(tmp_path, processed):
    tables = dict(SIGTAP_TABLES)
    fields, proc_rows = tables["tb_procedimento"]
    tables["tb_procedimento"] = (fields, [r for r in proc_rows if r[0] != "0303060010"])
    out = export(tmp_path, processed, sigtap_tables=tables)
    proc = by(out, "dim_procedimento", "procedimento_cod")
    assert proc["0303060010"]["procedimento_nome"] == ""  # never filled by approximation
    assert len(proc) == len({r.proc_rea for r in RECORDS})  # row kept
    failed = {c.name for c in powerbi.validate_model(out, expected()) if not c.passed}
    assert "coverage dim_procedimento.procedimento_nome: rows with official value" in failed


def test_duplicated_reference_key_is_rejected(tmp_path):
    tables = dict(SIGTAP_TABLES)
    fields, proc_rows = tables["tb_procedimento"]
    tables["tb_procedimento"] = (fields, [*proc_rows, ("0303010010", "DUPLICADO", "202401")])
    sources = build_references(tmp_path, sigtap_tables=tables)
    with pytest.raises(ReferenceFormatError, match="duplicated keys"):
        load_references(tmp_path, sources)


def test_reference_with_wrong_hash_or_missing_is_never_read(tmp_path):
    sources = build_references(tmp_path)
    sources["cnes_cadger"] = {**sources["cnes_cadger"], "sha256": "0" * 64}
    with pytest.raises(ReferenceIntegrityError, match="not read"):
        load_references(tmp_path, sources)
    sources = build_references(tmp_path)
    (tmp_path / "LEITOS.CNV").unlink()
    with pytest.raises(ReferenceIntegrityError, match="not found"):
        load_references(tmp_path, sources)


def test_personal_fields_of_the_cnes_registry_are_never_exported(tmp_path, processed):
    out = export(tmp_path, processed)
    content = "".join((out / f"{t.name}.csv").read_text(encoding="utf-8") for t in powerbi.TABLES)
    assert "RAZAO SOCIAL SECRETA" not in content
    assert "11111111000191" not in content
    assert "CLINICA FORA DO MODELO" not in content  # only establishments present in the fact


def test_synthetic_reference_files_are_deterministic(tmp_path):
    """The reproducibility tests rebuild these files; their bytes must not depend on the clock."""
    import time

    first = build_references(tmp_path / "a")
    time.sleep(2.1)  # longer than the 2-second resolution of ZIP timestamps
    second = build_references(tmp_path / "b")
    assert {k: v["sha256"] for k, v in first.items()} == {k: v["sha256"] for k, v in second.items()}
