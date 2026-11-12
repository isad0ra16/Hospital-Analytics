"""Reference-data readers, coverage and enrichment guard on SYNTHETIC files only."""

import csv
import json
import zipfile

import pytest
from synthetic_data import FieldSpec, build_dbc, build_dbf, write

from hospital_analytics.integrity import sha256_file
from hospital_analytics.reference import (
    ReferenceFormatError,
    clean_label,
    cnv_lookup,
    coverage,
    enrichment_guard,
    fact_unchanged,
    key_report,
    parse_layout,
    read_cnv,
    read_cnv_table,
    read_fixed_width,
    read_ibge_municipios,
    read_sigtap_table,
)
from hospital_analytics.reference_diagnose import run_diagnostic

LAYOUT = (
    "Coluna,Tamanho,Inicio,Fim,Tipo\r\nCO_PROC,10,1,10,VARCHAR2\r\nNO_PROC,8,11,18,VARCHAR2\r\n"
)


def fixed(code, name):
    return (code.ljust(10) + name.ljust(8)).encode("latin-1")


# ---- layout and fixed width ------------------------------------------------
def test_layout_is_parsed_with_1_based_inclusive_positions():
    fields = parse_layout(LAYOUT)
    assert [(f.name, f.start, f.end, f.length) for f in fields] == [
        ("CO_PROC", 1, 10, 10),
        ("NO_PROC", 11, 18, 8),
    ]


@pytest.mark.parametrize(
    "bad",
    [
        "Nome,Tamanho,Inicio,Fim,Tipo\nA,1,1,1,X\n",  # wrong header
        "Coluna,Tamanho,Inicio,Fim,Tipo\nA,2,1,1,X\n",  # length != end - start + 1
        "Coluna,Tamanho,Inicio,Fim,Tipo\nA,1,1,1,X\nB,1,3,3,X\n",  # gap between fields
        "Coluna,Tamanho,Inicio,Fim,Tipo\nA,1,1,1\n",  # 4 fields
        "Coluna,Tamanho,Inicio,Fim,Tipo\n",  # no fields
    ],
)
def test_inconsistent_layouts_are_rejected(bad):
    with pytest.raises(ReferenceFormatError):
        parse_layout(bad)


def test_fixed_width_keeps_leading_zeros_and_accents():
    data = fixed("0303010037", "CLÍNICO") + b"\r\n" + fixed("0411010034", "PARTO") + b"\n"
    rows = read_fixed_width(data, parse_layout(LAYOUT), "latin-1")
    assert rows == [
        {"CO_PROC": "0303010037", "NO_PROC": "CLÍNICO"},
        {"CO_PROC": "0411010034", "NO_PROC": "PARTO"},
    ]


def test_line_with_wrong_width_stops_the_reader():
    with pytest.raises(ReferenceFormatError, match="layout width"):
        read_fixed_width(fixed("0303010037", "X") + b"EXTRA\n", parse_layout(LAYOUT), "latin-1")


def sigtap_zip(tmp_path, members):
    path = tmp_path / "TabelaUnificada_SYNTH.zip"
    with zipfile.ZipFile(path, "w") as zf:
        for name, content in members.items():
            zf.writestr(name, content)
    return path


def test_sigtap_table_uses_the_layout_from_the_same_archive(tmp_path):
    path = sigtap_zip(
        tmp_path,
        {"tb_proc.txt": fixed("0303010037", "A") + b"\r\n", "tb_proc_layout.txt": LAYOUT},
    )
    assert read_sigtap_table(path, "tb_proc") == [{"CO_PROC": "0303010037", "NO_PROC": "A"}]
    with pytest.raises(ReferenceFormatError, match="not found"):
        read_sigtap_table(path, "tb_missing")
    with pytest.raises(ValueError, match="single-byte"):
        read_sigtap_table(path, "tb_proc", encoding="utf-8")


# ---- IBGE ----------------------------------------------------------------------
def ibge_item(code, name, uf_id, sigla):
    uf = {"id": uf_id, "sigla": sigla, "nome": "x"}
    return {"id": code, "nome": name, "microrregiao": {"mesorregiao": {"UF": uf}}}


def test_ibge_json_is_flattened_and_ids_stay_text(tmp_path):
    path = tmp_path / "m.json"
    path.write_text(json.dumps([ibge_item(3304557, "Rio de Janeiro", 33, "RJ")]), encoding="utf-8")
    assert read_ibge_municipios(path) == [
        {"id": "3304557", "nome": "Rio de Janeiro", "uf_id": "33", "uf_sigla": "RJ"}
    ]


def test_ibge_item_without_uf_is_an_error(tmp_path):
    path = tmp_path / "m.json"
    path.write_text(json.dumps([{"id": 1, "nome": "x"}]), encoding="utf-8")
    with pytest.raises(ReferenceFormatError, match="no UF"):
        read_ibge_municipios(path)


# ---- keys and coverage -------------------------------------------------------------
def test_key_report_flags_duplicates_blanks_and_lengths():
    report = key_report("CNES", ["0000001", "0000001", "", "12345AB"])
    assert report.duplicated_keys == ["0000001"]
    assert report.blank_keys == 1 and report.non_digit_keys == 1 and not report.unique
    assert report.lengths == {0: 1, 7: 3}


def test_coverage_reports_unmatched_and_ambiguous_keys():
    cov = coverage("dim", ["a", "b", "c", "c"], "ref", ["a", "b", "b"])
    assert (cov.dimension_keys, cov.matched) == (3, 1)
    assert cov.unmatched == ["c"] and cov.ambiguous == ["b"]


def test_ibge_six_digit_prefix_coverage():
    cov = coverage("mun", ["330455"], "ibge", ["3304557", "3550308"], transform=lambda i: i[:6])
    assert cov.matched == 1 and not cov.unmatched


# ---- enrichment guard --------------------------------------------------------------
BEFORE = [{"cnes": "1", "uf": "33"}, {"cnes": "2", "uf": "33"}]


def test_guard_accepts_added_columns_only():
    after = [{**r, "nome": f"H{r['cnes']}"} for r in BEFORE]
    assert enrichment_guard(BEFORE, after, "cnes") == []


@pytest.mark.parametrize(
    ("after", "problem"),
    [
        (BEFORE[:1], "row count changed"),
        ([*BEFORE, BEFORE[0]], "duplicated keys"),
        ([BEFORE[0], {"cnes": "2", "uf": "35"}], "original columns modified"),
        ([BEFORE[0], {"cnes": "3", "uf": "33"}], "set of keys changed"),
    ],
)
def test_guard_rejects_any_change_beyond_new_columns(after, problem):
    assert any(problem in p for p in enrichment_guard(BEFORE, after, "cnes"))


def test_fact_unchanged_compares_with_the_export_summary(tmp_path):
    fact = write(tmp_path / "fato.csv", b"registro_id\n1\n")
    summary = tmp_path / "summary.json"
    summary.write_text(
        json.dumps({"tables": {"fato_registro_aih": {"csv": {"sha256": sha256_file(fact)}}}})
    )
    assert fact_unchanged(summary, fact)
    fact.write_bytes(b"registro_id\n2\n")
    assert not fact_unchanged(summary, fact)


# ---- diagnostic end to end ------------------------------------------------------------
def write_csv(path, header, rows):
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


@pytest.fixture
def incoming(tmp_path):
    inc = tmp_path / "incoming"
    inc.mkdir()
    st = build_dbf([FieldSpec("CNES", "C", 7), FieldSpec("CODUFMUN", "C", 6)],
                   [["0000001", "330455"], ["0000009", "330455"]], language_driver=0x02)  # fmt: skip
    write(inc / "ST.dbc", build_dbc(st))
    sigtap = sigtap_zip(
        inc, {"tb_proc.txt": fixed("0303010037", "A") + b"\n", "tb_proc_layout.txt": LAYOUT}
    )
    (inc / "m.json").write_text(json.dumps([ibge_item(3304557, "Rio", 33, "RJ")]), encoding="utf-8")
    pbi = tmp_path / "pbi"
    pbi.mkdir()
    write_csv(pbi / "dim_estabelecimento.csv", ["cnes", "municipio_estabelecimento_cod"],
              [["0000001", "330455"], ["0000002", "330455"]])  # fmt: skip
    write_csv(
        pbi / "dim_municipio_residencia.csv", ["municipio_residencia_cod"], [["330455"], ["350000"]]
    )
    write_csv(pbi / "dim_procedimento.csv", ["procedimento_cod"], [["0303010037"]])
    sources = {
        "cnes_st": {"filename": "ST.dbc", "size_bytes": (inc / "ST.dbc").stat().st_size,
                    "sha256": sha256_file(inc / "ST.dbc"), "key_column": "CNES"},
        "sigtap": {"filename": sigtap.name, "size_bytes": sigtap.stat().st_size, "sha256": sha256_file(sigtap),
                   "tables": {"tb_proc": {"key_column": "CO_PROC", "dimension": "dim_procedimento.procedimento_cod"}}},
        "ibge_municipios": {"filename": "m.json"},
        "tab_cnes": {"filename": "absent.zip", "size_bytes": 1, "sha256": "0" * 64},
    }  # fmt: skip
    return inc, pbi, sources


def test_diagnostic_reports_structure_keys_and_coverage(incoming):
    inc, pbi, sources = incoming
    report = run_diagnostic(inc, pbi, sources)["sources"]
    st = report["cnes_st"]["structure"]
    assert st["columns"] == ["CNES", "CODUFMUN"] and st["records"] == 2
    assert st["coverage"]["matched"] == 1 and st["coverage"]["unmatched"] == ["0000002"]
    assert report["sigtap"]["structure"]["tb_proc"]["coverage"]["matched"] == 1
    ibge = report["ibge_municipios"]["structure"]
    assert ibge["coverage_residencia"]["unmatched"] == ["350000"]
    assert report["tab_cnes"]["integrity"]["present"] is False


def test_file_with_wrong_hash_is_never_read(incoming):
    inc, pbi, sources = incoming
    sources["cnes_st"]["sha256"] = "0" * 64
    entry = run_diagnostic(inc, pbi, sources)["sources"]["cnes_st"]
    assert entry["integrity"]["integrity_ok"] is False
    assert "structure" not in entry


def test_sigtap_default_encoding_is_cp1252(tmp_path):
    name = "SAÚDE \x96 X".encode("latin-1")  # 0x96 is an en dash in CP1252
    data = b"0301040168" + name.ljust(8)[:8] + b"\n"
    path = sigtap_zip(tmp_path, {"tb_proc.txt": data, "tb_proc_layout.txt": LAYOUT})
    (row,) = read_sigtap_table(path, "tb_proc")
    assert row["NO_PROC"] == "SAÚDE –"
    (latin,) = read_sigtap_table(path, "tb_proc", encoding="latin-1")
    assert latin["NO_PROC"] == "SAÚDE \x96"


CNV = (
    "3 6\r\n"
    "      1   MUNICIPIO IGNORADO - RJ                           330000,339999\r\n"
    "      2  330455 RIO DE JANEIRO                              330455,334501-334530\r\n"
    "      3  Não informado                                     ,0-3\r\n"
)


def test_cnv_reader_handles_lists_ranges_and_blank_codes(tmp_path):
    path = tmp_path / "x.cnv"
    path.write_bytes(CNV.encode("cp1252"))
    header, cats = read_cnv(path)
    assert header == ("3", "6")
    assert [(c.sequence, c.label, c.codes) for c in cats] == [
        (1, "MUNICIPIO IGNORADO - RJ", ("330000", "339999")),
        (2, "330455 RIO DE JANEIRO", ("330455", "334501-334530")),
        (3, "Não informado", ("", "0-3")),
    ]
    assert [c.sequence for c in cnv_lookup(cats, "334510")] == [2]  # inside a range
    assert [c.sequence for c in cnv_lookup(cats, "330455")] == [2]
    assert cnv_lookup(cats, "330999") == []


def test_cnv_header_count_must_match(tmp_path):
    path = tmp_path / "x.cnv"
    path.write_bytes(CNV.replace("3 6", "4 6", 1).encode("cp1252"))
    with pytest.raises(ReferenceFormatError, match="declares 4"):
        read_cnv(path)


# ---- TabWin .cnv, full reader (official SIH package variants) ----------------------------
def cnv_file(tmp_path, text, name="x.cnv"):
    path = tmp_path / name
    path.write_bytes(text.encode("cp1252"))
    return read_cnv_table(path)


def test_cnv_table_header_flags_width_and_catch_all_precedence(tmp_path):
    t = cnv_file(tmp_path, "N 3 1 L\n  3  Outras   0-9\n  1  Normal   1\n  2  Longa    5\n")
    assert (t.flags, t.width, len(t.entries)) == (("N", "L"), 1, 3)
    assert t.resolve("1").label == "Normal"  # specific code listed after the catch-all
    assert t.resolve("7").label == "Outras"
    assert t.resolve("X") is None


def test_cnv_table_hierarchy_continuation_and_trailing_comma(tmp_path):
    t = cnv_file(
        tmp_path,
        "3 4\n 01  Administração Pública  1000-1999,\n 01  02  .. Estadual  1023,\n"
        " 01  02  .. Estadual  1058\n 03  Ignorado  0000\n",
    )
    estadual = t.resolve("1058")  # continuation line of category 02
    assert (estadual.sequence, estadual.parent) == ("02", "01")
    assert t.full_label(estadual) == "Administração Pública — Estadual"
    assert t.resolve("1999").label == "Administração Pública"
    assert t.resolve("") is None  # a trailing comma is not a blank code


def test_cnv_table_blank_items_alphanumeric_ranges_and_key_width(tmp_path):
    t = cnv_file(tmp_path, "2 3 L\n  1  X. Respiratório  J00-J99,\n  2  Não preenchido  ,\n")
    assert t.resolve("J189").label == "X. Respiratório"  # first 3 characters, string range
    assert t.resolve("   ").label == "Não preenchido"
    assert t.key("0101234", start=3) == "012"
    pf = cnv_file(tmp_path, "3 1 L\n  3  Não informado  ,0-3\n  1  PF  1\n  2  PJ  3\n")
    assert pf.resolve("3").label == "PJ" and pf.resolve("").label == "Não informado"


def test_cnv_table_refuses_to_guess_when_precedence_rules_disagree(tmp_path):
    # the specific code comes FIRST and the catch-all range LAST: the rules disagree
    t = cnv_file(tmp_path, "2 1\n  1  Normal  1\n  2  Outras  0-9\n")
    with pytest.raises(ReferenceFormatError, match="precedence rules disagree"):
        t.resolve("1")
    tie = cnv_file(tmp_path, "2 1\n  1  A  1\n  2  B  1\n")
    with pytest.raises(ReferenceFormatError, match="equal precedence"):
        tie.resolve("1")


@pytest.mark.parametrize(
    "text",
    ["x 2\n 1 A 1\n", "2 1\n 1 A 1\n", "2 1\n 1 A 1\n 1 B 2\n", "1 1\n 1 Ação Não\n"],
)
def test_inconsistent_cnv_tables_are_rejected(tmp_path, text):
    with pytest.raises(ReferenceFormatError):
        cnv_file(tmp_path, text)


@pytest.mark.parametrize(
    ("label", "code", "clean"),
    [
        ("01-Cirúrgico", "01", "Cirúrgico"),
        ("01 Eletivo", "01", "Eletivo"),
        ("101-5 Orgao Publico Federal", "1015", "Orgao Publico Federal"),
        ("Normal", "1", "Normal"),
        ("330010 ANGRA DOS REIS", "330010", "ANGRA DOS REIS"),
    ],
)
def test_clean_label_removes_only_a_leading_copy_of_the_code(label, code, clean):
    assert clean_label(label, code) == clean
