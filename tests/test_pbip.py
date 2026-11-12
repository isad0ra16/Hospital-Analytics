"""The generated Power BI Project: schema-valid JSON, field references that exist in the model,
TMDL consistent with the export schema, and the committed project in sync with the generator.

The JSON schemas are vendored from github.com/microsoft/json-schemas (MIT licence) in
tests/fixtures/powerbi_schemas, so validation needs no network.
"""

import json
import re
from pathlib import Path

import pytest
from jsonschema import Draft7Validator
from referencing import Registry, Resource

from hospital_analytics import pbip, powerbi
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


def test_committed_project_is_up_to_date():
    directory = ROOT / "powerbi"
    for relative, content in FILES.items():
        path = directory / relative
        assert path.is_file(), relative
        assert path.read_text(encoding="utf-8") == content, (
            f"{relative}: run hospital-analytics pbip"
        )
    generated = {Path(k).as_posix() for k in FILES}
    on_disk = {
        p.relative_to(directory).as_posix()
        for p in directory.rglob("*")
        if p.is_file()
        and ".pbi/localSettings.json" not in p.as_posix()
        and not p.name.endswith(".abf")
    }
    assert on_disk == generated, on_disk ^ generated


def test_generation_is_deterministic():
    assert pbip.project_files(MEASURES_TEXT) == FILES
