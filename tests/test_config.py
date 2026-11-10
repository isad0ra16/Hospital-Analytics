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
