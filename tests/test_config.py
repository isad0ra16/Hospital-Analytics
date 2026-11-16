from decimal import Decimal

import pytest

from hospital_analytics.config import data_path, load_params, project_root, to_money


def test_project_root_contains_pyproject():
    assert (project_root() / "pyproject.toml").is_file()


def test_params_describe_the_expected_source():
    source = load_params()["source"]
    assert source["system"] == "SIH/SUS"
    assert source["file_type"] == "RD"
    assert source["uf"] == "RJ"
    assert source["competence"] == "2024-01"
    assert source["filename"] == "RDRJ2401.dbc"


@pytest.mark.parametrize("layer", ["raw", "processed"])
def test_data_layers_resolve_inside_project(layer):
    path = data_path(layer)
    assert path.is_relative_to(project_root())
    assert path.is_dir()


def test_unknown_data_layer_is_rejected():
    with pytest.raises(KeyError):
        data_path("nonexistent")


def test_to_money_is_exact():
    assert to_money("0.1") + to_money("0.2") == Decimal("0.3")


def test_to_money_rejects_float():
    with pytest.raises(TypeError):
        to_money(0.1)


def test_cli_defaults_use_config_from_selected_root(tmp_path):
    """--root must select both the file locations and their YAML configuration."""
    from hospital_analytics.cli import _defaults

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "params.yaml").write_text(
        "paths:\n"
        "  raw: custom/raw\n"
        "  processed: custom/processed\n"
        "  manifest: custom/MANIFEST.json\n"
        "source:\n"
        "  filename: OTHER.dbc\n"
        "raw_conversion:\n"
        "  parquet_filename: OTHER.parquet\n"
        "processing:\n"
        "  filename: OTHER_processed.parquet\n",
        encoding="utf-8",
    )

    defaults = _defaults(tmp_path)
    assert defaults == {
        "source": tmp_path / "custom/raw/OTHER.dbc",
        "parquet": tmp_path / "custom/raw/OTHER.parquet",
        "processed": tmp_path / "custom/processed/OTHER_processed.parquet",
        "manifest": tmp_path / "custom/MANIFEST.json",
    }


def test_cli_params_use_selected_root_for_non_path_settings(tmp_path):
    """Commands must not silently use the repository's original reference values."""
    from hospital_analytics.cli import _params

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "params.yaml").write_text(
        "source:\n  system: CUSTOM\nraw_conversion:\n  encoding: latin-1\nreference_sources: {}\n",
        encoding="utf-8",
    )
    params = _params(tmp_path)
    assert params["source"]["system"] == "CUSTOM"
    assert params["raw_conversion"]["encoding"] == "latin-1"
    assert params["reference_sources"] == {}
