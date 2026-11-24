"""The generated Power BI Project: schema-valid JSON, field references that exist in the model,
TMDL consistent with the export schema, and the committed project in sync with the generator.

The JSON schemas are vendored from github.com/microsoft/json-schemas (MIT licence) in
tests/fixtures/powerbi_schemas, so validation needs no network.
"""

import json
import re

import pytest
from jsonschema import Draft7Validator
from referencing import Registry, Resource

from hospital_analytics import pbip, pbip_contract, powerbi
from hospital_analytics.config import project_root

ROOT = project_root()
SCHEMAS = ROOT / "tests" / "fixtures" / "powerbi_schemas"
MEASURES_TEXT = (ROOT / "docs" / "powerbi" / "medidas.dax").read_text(encoding="utf-8")
FILES = pbip.project_files(MEASURES_TEXT)
MEASURES = {m.name: m for m in pbip.parse_measures(MEASURES_TEXT)}


def _registry() -> Registry:
    resources = []
    for path in SCHEMAS.rglob("*.json"):
        url = pbip.SCHEMA + path.relative_to(SCHEMAS / "fabric").as_posix()
        resources.append((url, Resource.from_contents(json.loads(path.read_text("utf-8")))))
    return Registry().with_resources(resources)


REGISTRY = _registry()
JSON_FILES = {k: v for k, v in FILES.items() if k.endswith((".json", ".pbir", ".pbism", ".pbip"))}


@pytest.mark.parametrize("relative", sorted(k for k, v in JSON_FILES.items() if '"$schema"' in v))
def test_json_files_validate_against_the_official_schemas(relative):
    document = json.loads(FILES[relative])
    schema = REGISTRY.get_or_retrieve(document["$schema"]).value.contents
    errors = sorted(
        Draft7Validator(schema, registry=REGISTRY).iter_errors(document), key=lambda e: e.path
    )
    assert not errors, [f"{list(e.path)}: {e.message}" for e in errors[:5]]


def _references(node):
    if isinstance(node, dict):
        for kind in ("Column", "Measure"):
            if kind in node and "Property" in node[kind]:
                yield kind, node[kind]["Expression"]["SourceRef"]["Entity"], node[kind]["Property"]
        for value in node.values():
            yield from _references(value)
    elif isinstance(node, list):
        for value in node:
            yield from _references(value)


def test_every_visual_field_exists_in_the_semantic_model():
    columns = {(t.name, c.name) for t in powerbi.ALL_TABLES for c in t.columns}
    found = 0
    for relative, content in FILES.items():
        if relative.endswith("visual.json"):
            for kind, table, name in _references(json.loads(content)):
                found += 1
                if kind == "Measure":
                    assert table == pbip.MEASURES_TABLE and name in MEASURES, (relative, name)
                else:
                    assert (table, name) in columns, (relative, table, name)
    assert found > 50


def test_six_pages_each_with_title_footer_and_synchronised_slicers():
    pages = json.loads(FILES[f"{pbip.PROJECT}.Report/definition/pages/pages.json"])["pageOrder"]
    assert len(pages) == 6
    for page in pbip.PAGES:
        kinds = [v.kind for v in page.visuals]
        assert kinds.count("textbox") >= 2 and kinds.count("slicer") == 5
        for v in page.visuals:
            assert v.x >= 0 and v.y >= 0 and v.x + v.w <= pbip.PAGE_W and v.y + v.h <= pbip.PAGE_H
    groups = {v.sync for p in pbip.PAGES for v in p.visuals if v.kind == "slicer"}
    assert len(groups) == 5  # the same 5 groups on every page -> filters follow the user


def test_tmdl_tables_columns_and_relationships_match_the_export_schema():
    model = f"{pbip.PROJECT}.SemanticModel/definition"
    for table in powerbi.ALL_TABLES:
        tmdl = FILES[f"{model}/tables/{table.name}.tmdl"]
        declared = re.findall(r"^\tcolumn (\S+)$", tmdl, flags=re.M)
        assert declared == [pbip.tmdl_name(c.name) for c in table.columns], table.name
        assert f'PastaDados & "{table.name}.csv"' in tmdl
    relationships = FILES[f"{model}/relationships.tmdl"]
    assert relationships.count("relationship ") == len(powerbi.RELATIONSHIPS)
    assert relationships.count("isActive: false") == 1  # only mes_internacao
    model_refs = re.findall(r"^ref table (\S+)$", FILES[f"{model}/model.tmdl"], flags=re.M)
    assert len(model_refs) == len(powerbi.ALL_TABLES) + 1


def test_measures_are_parsed_with_format_folder_and_description():
    assert len(MEASURES) >= 30
    assert MEASURES["Mortalidade hospitalar (razão)"].format_string == "0.00%"
    assert MEASURES["Valor total"].format_string == "R$ #,0.00"
    assert MEASURES["Registros de AIH"].format_string == "#,0"
    assert MEASURES["Registros - masculino (pirâmide)"].format_string == "#,0;#,0"
    assert MEASURES["Registros de AIH"].folder == "Contagens"
    assert "TOPN" in MEASURES["Concentração do valor - top 10%"].expression
    assert all(m.expression.strip() for m in MEASURES.values())
    tmdl = FILES[f"{pbip.PROJECT}.SemanticModel/definition/tables/{pbip.MEASURES_TABLE}.tmdl"]
    assert tmdl.count("\tmeasure ") == len(MEASURES)


def test_project_holds_no_data_and_no_local_path():
    content = "".join(FILES.values())
    assert "Users" not in content and "@" not in content.replace("@odata", "")
    assert (
        pbip.DATA_FOLDER_PLACEHOLDER
        in FILES[f"{pbip.PROJECT}.SemanticModel/definition/expressions.tmdl"]
    )
    assert not any(k.endswith((".csv", ".abf", ".pbix")) for k in FILES)


# ---- the committed project: semantic contract, not visual equality ---------------------
# The committed report may be customised in Power BI Desktop. It must keep the semantic layer
# (tables, columns, relationships, measures, valid field references); its look is free.
PROJECT_DIR = ROOT / "powerbi"


@pytest.fixture(scope="module")
def generated_contract(tmp_path_factory):
    directory = tmp_path_factory.mktemp("generated")
    pbip.write_project(directory, MEASURES_TEXT)
    return pbip_contract.read_semantic_contract(directory, pbip.PROJECT)


def test_generator_output_is_deterministic_in_an_isolated_folder(tmp_path):
    """The generator is tested on its own, in a temporary folder, never on powerbi/."""
    pbip.write_project(tmp_path, MEASURES_TEXT)
    written = {
        p.relative_to(tmp_path).as_posix(): p.read_text(encoding="utf-8")
        for p in tmp_path.rglob("*")
        if p.is_file()
    }
    assert written == FILES
    pbip.write_project(tmp_path, MEASURES_TEXT)
    assert pbip.manual_changes(tmp_path, MEASURES_TEXT) == []


def test_generated_contract_matches_the_export_schema(generated_contract):
    exported = {t.name: t.column_names for t in powerbi.ALL_TABLES}
    assert {k: v for k, v in generated_contract.tables.items() if k in exported} == exported
    assert len(generated_contract.relationships) == len(powerbi.RELATIONSHIPS)
    assert sum(not active for *_, active in generated_contract.relationships) == 1
    assert {name for _, name in generated_contract.measures} == set(MEASURES)


def test_committed_project_keeps_the_semantic_contract(generated_contract):
    actual = pbip_contract.read_semantic_contract(PROJECT_DIR, pbip.PROJECT)
    report = pbip_contract.compare_contracts(generated_contract, actual)
    assert report.ok, report.errors


def test_committed_visuals_only_use_fields_of_the_model():
    actual = pbip_contract.read_semantic_contract(PROJECT_DIR, pbip.PROJECT)
    assert pbip_contract.broken_visual_fields(PROJECT_DIR, pbip.PROJECT, actual) == []


def test_committed_report_has_the_six_documented_pages():
    definition = PROJECT_DIR / f"{pbip.PROJECT}.Report" / "definition"
    order = json.loads((definition / "pages" / "pages.json").read_text("utf-8"))["pageOrder"]
    assert len(order) == 6
    assert all((definition / "pages" / page / "page.json").is_file() for page in order)


def test_committed_json_is_valid_and_schema_checked_when_the_schema_is_known():
    """Every JSON file parses; files declaring a vendored schema version are validated against it.
    A newer schema version written by Power BI Desktop is not an error (just not vendored)."""
    validated = 0
    for path in sorted(PROJECT_DIR.rglob("*")):
        if path.suffix not in {".json", ".pbir", ".pbism", ".pbip"} or ".pbi" in path.parts:
            continue
        document = json.loads(path.read_text(encoding="utf-8"))
        url = document.get("$schema") if isinstance(document, dict) else None
        if not url:
            continue
        try:
            schema = REGISTRY.get_or_retrieve(url).value.contents
        except Exception:  # schema version not vendored: reported by `pbip --check`, not an error
            continue
        errors = list(Draft7Validator(schema, registry=REGISTRY).iter_errors(document))
        assert not errors, (path.name, [e.message for e in errors[:3]])
        validated += 1
    assert validated > 0


def test_committed_project_holds_no_data_and_no_personal_path():
    for path in PROJECT_DIR.rglob("*"):
        if not path.is_file() or ".pbi" in path.parts:
            continue
        assert path.suffix.lower() not in {".csv", ".abf", ".pbix", ".parquet"}, path
        text = path.read_text(encoding="utf-8", errors="replace")
        assert "\\Users\\" not in text and "/Users/" not in text and "/home/" not in text, path


def test_generation_is_deterministic():
    assert pbip.project_files(MEASURES_TEXT) == FILES


def test_pages_document_is_generated_from_the_same_specification():
    doc = (ROOT / "docs" / "powerbi" / "paginas.md").read_text(encoding="utf-8")
    assert doc == pbip.pages_markdown(), "run hospital-analytics pbip"
    for page in pbip.PAGES:
        assert f"## {page.title}" in doc


# ---- protection of a hand-customised report -------------------------------------------
@pytest.fixture
def pbip_root(tmp_path):
    (tmp_path / "docs" / "powerbi").mkdir(parents=True)
    (tmp_path / "docs" / "powerbi" / "medidas.dax").write_text(MEASURES_TEXT, encoding="utf-8")
    return tmp_path


def test_pbip_refuses_to_overwrite_a_hand_edited_project(pbip_root, capsys):
    from hospital_analytics.cli import main

    args = ["--root", str(pbip_root), "pbip"]
    assert main(args) == 0  # fresh folder
    assert main(args) == 0  # identical content: regenerating is harmless
    page = next((pbip_root / "powerbi").rglob("page.json"))
    custom = page.read_text(encoding="utf-8").replace('"displayName"', '"displayName" ', 1)
    page.write_text(custom, encoding="utf-8")
    extra = page.parent / "visuals" / "manual" / "visual.json"
    extra.parent.mkdir(parents=True)
    extra.write_text("{}", encoding="utf-8")
    capsys.readouterr()
    assert main(args) == 1
    err = capsys.readouterr().err
    assert "Nothing was written" in err and "modified:" in err and "not generated:" in err
    assert page.read_text(encoding="utf-8") == custom and extra.is_file()  # untouched

    assert main([*args, "--force"]) == 0  # explicit decision to discard the edits
    assert not extra.exists() and pbip.manual_changes(pbip_root / "powerbi", MEASURES_TEXT) == []


def test_crlf_line_endings_are_not_reported_as_manual_changes(pbip_root):
    pbip.write_project(pbip_root / "powerbi", MEASURES_TEXT)
    page = next((pbip_root / "powerbi").rglob("page.json"))
    page.write_bytes(page.read_bytes().replace(b"\n", b"\r\n"))
    assert pbip.manual_changes(pbip_root / "powerbi", MEASURES_TEXT) == []


def test_pipeline_target_never_regenerates_the_report():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    pipeline = next(ln for ln in makefile.splitlines() if ln.startswith("pipeline:"))
    assert "pbip" not in pipeline.split("##")[0]


# ---- the contract tolerates Desktop rewrites and visual edits, and catches semantic ones ----
@pytest.fixture
def desktop_like(tmp_path):
    """A generated project rewritten the way Power BI Desktop saves it."""
    pbip.write_project(tmp_path, MEASURES_TEXT)
    definition = tmp_path / f"{pbip.PROJECT}.SemanticModel" / "definition"
    measures = definition / "tables" / f"{pbip.MEASURES_TABLE}.tmdl"
    text = measures.read_text(encoding="utf-8")
    head = "\tmeasure 'Concentração do valor - top 10%' =\n"
    assert head in text
    # Desktop wraps multi-line DAX in ``` fences and adds bookkeeping lines.
    start = text.index(head)
    close = text.index("\t\tformatString:", start)  # first property line of THIS measure
    text = (
        text[:start]
        + head.replace("=\n", "= ```\n")
        + text[start + len(head) : close]
        + "\t\t\t```\n"
        + text[close:]
    )
    text += "\n\tannotation PBI_Id = 123\n"
    measures.write_text(text, encoding="utf-8")
    (definition / "tables" / "LocalDateTable_x.tmdl").write_text(
        "table LocalDateTable_x\n\tisHidden\n\n\tcolumn Date\n\t\tdataType: dateTime\n",
        encoding="utf-8",
    )
    rel = definition / "relationships.tmdl"
    rel.write_text(
        rel.read_text(encoding="utf-8") + "\nrelationship abc\n\tjoinOnDateBehavior: datePartOnly\n"
        "\tfromColumn: fato_registro_aih.mes_saida\n\ttoColumn: LocalDateTable_x.Date\n",
        encoding="utf-8",
    )
    page = next((tmp_path / f"{pbip.PROJECT}.Report").rglob("visual.json"))
    visual = json.loads(page.read_text(encoding="utf-8"))
    visual["position"]["x"] = visual["position"]["x"] + 7  # a purely visual edit
    page.write_text(json.dumps(visual), encoding="utf-8")
    return tmp_path


def _check(directory, generated_contract):
    actual = pbip_contract.read_semantic_contract(directory, pbip.PROJECT)
    return pbip_contract.compare_contracts(generated_contract, actual), actual


def test_desktop_rewrites_and_visual_edits_keep_the_contract(desktop_like, generated_contract):
    report, actual = _check(desktop_like, generated_contract)
    assert report.ok, report.errors
    assert any("auto date/time table" in n for n in report.notes)
    assert pbip_contract.broken_visual_fields(desktop_like, pbip.PROJECT, actual) == []
    changes = pbip.manual_changes(desktop_like, MEASURES_TEXT)
    assert changes  # the hand edits are detected ...
    assert all(c.startswith(("modified:", "not generated:")) for c in changes)  # ... and listed


def test_pbip_check_reports_hand_edits_without_failing(desktop_like, capsys):
    from hospital_analytics.cli import main

    root = desktop_like.parent / "root"
    (root / "docs" / "powerbi").mkdir(parents=True)
    (root / "docs" / "powerbi" / "medidas.dax").write_text(MEASURES_TEXT, encoding="utf-8")
    desktop_like.rename(root / "powerbi")
    before = {p: p.read_bytes() for p in (root / "powerbi").rglob("*") if p.is_file()}
    assert main(["--root", str(root), "pbip", "--check"]) == 0
    out = capsys.readouterr().out
    assert "semantic contract OK" in out and "files changed by hand (informational): 0" not in out
    assert before == {p: p.read_bytes() for p in (root / "powerbi").rglob("*") if p.is_file()}


@pytest.mark.parametrize(
    ("edit", "expected"),
    [
        (lambda t: t.replace("DISTINCTCOUNT ( fato_registro_aih[aih_id] )",
                             "COUNTROWS ( fato_registro_aih )"), "measure expression changed"),
        (lambda t: t.replace("\tisActive: false\n", ""), "relationship now active"),
    ],
)  # fmt: skip
def test_semantic_changes_break_the_contract(desktop_like, generated_contract, edit, expected):
    definition = desktop_like / f"{pbip.PROJECT}.SemanticModel" / "definition"
    for path in [definition / "relationships.tmdl", *definition.glob("tables/*.tmdl")]:
        path.write_text(edit(path.read_text(encoding="utf-8")), encoding="utf-8")
    report, _ = _check(desktop_like, generated_contract)
    assert any(e.startswith(expected) for e in report.errors), report.errors


def test_removed_column_and_broken_visual_field_are_reported(desktop_like, generated_contract):
    table = desktop_like / f"{pbip.PROJECT}.SemanticModel/definition/tables/dim_carater.tmdl"
    text = table.read_text(encoding="utf-8")
    assert "\tcolumn descricao_oficial\n" in text  # used by visuals on pages 3 and 4
    table.write_text(text.replace("\tcolumn descricao_oficial\n", "\tcolumn rotulo\n"), "utf-8")
    report, actual = _check(desktop_like, generated_contract)
    assert any("columns removed from dim_carater" in e for e in report.errors)
    broken = pbip_contract.broken_visual_fields(desktop_like, pbip.PROJECT, actual)
    assert any("dim_carater[descricao_oficial]" in b for b in broken)
