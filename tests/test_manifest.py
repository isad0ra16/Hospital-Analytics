import pytest
from synthetic_data import write

from hospital_analytics.convert import convert_dbc_to_parquet
from hospital_analytics.integrity import sha256_file
from hospital_analytics.manifest import (
    ManifestError,
    empty_manifest,
    load_manifest,
    record_derived,
    register_source,
    save_manifest,
    verify_file,
)

SOURCE_INFO = dict(
    official_url="ftp://example.invalid/SYNTH.dbc",
    obtained_at="2026-01-01",
    obtained_by="test",
    data_version={"competence": "synthetic"},
)


def test_register_source_records_size_and_hash(dbc_file):
    manifest = empty_manifest()
    entry = register_source(manifest, "data/raw/SYNTH.dbc", dbc_file, **SOURCE_INFO)
    assert entry["sha256"] == sha256_file(dbc_file)
    assert entry["size_bytes"] == dbc_file.stat().st_size
    assert manifest["sources"]["data/raw/SYNTH.dbc"] is entry


def test_register_is_idempotent_for_same_file(dbc_file):
    manifest = empty_manifest()
    first = register_source(manifest, "k", dbc_file, **SOURCE_INFO)
    assert register_source(manifest, "k", dbc_file, **SOURCE_INFO) == first


def test_registered_source_cannot_be_replaced(tmp_path, dbc_file):
    manifest = empty_manifest()
    register_source(manifest, "k", dbc_file, **SOURCE_INFO)
    other = write(tmp_path / "other.dbc", dbc_file.read_bytes() + b"x")
    with pytest.raises(ManifestError, match="refusing to replace"):
        register_source(manifest, "k", other, **SOURCE_INFO)


@pytest.mark.parametrize(
    "kwargs", [{"expected_sha256": "0" * 64}, {"expected_size": 1}], ids=["sha", "size"]
)
def test_expected_values_are_enforced(dbc_file, kwargs):
    with pytest.raises(ManifestError):
        register_source(empty_manifest(), "k", dbc_file, **SOURCE_INFO, **kwargs)


def test_save_load_roundtrip(tmp_path, dbc_file):
    manifest = empty_manifest()
    register_source(manifest, "k", dbc_file, **SOURCE_INFO)
    path = tmp_path / "MANIFEST.json"
    save_manifest(manifest, path)
    assert load_manifest(path) == manifest
    assert load_manifest(tmp_path / "missing.json") == empty_manifest()


def test_record_derived_requires_matching_source(tmp_path, dbc_file):
    report = convert_dbc_to_parquet(dbc_file, tmp_path / "x.parquet")
    manifest = empty_manifest()
    with pytest.raises(ManifestError, match="not registered"):
        record_derived(manifest, "x", "k", report)
    register_source(manifest, "k", dbc_file, **SOURCE_INFO)
    entry = record_derived(manifest, "x", "k", report)
    assert entry["content_fingerprint"] == report.content_fingerprint
    assert entry["intermediate_dbf"]["header_records"] == report.records


def test_verify_file_detects_modification(tmp_path, dbc_file):
    manifest = empty_manifest()
    entry = register_source(manifest, "k", dbc_file, **SOURCE_INFO)
    assert verify_file(entry, dbc_file)[0]
    tampered = write(tmp_path / "t.dbc", dbc_file.read_bytes()[:-1] + b"\x00")
    assert not verify_file(entry, tampered)[0]


def test_record_derived_is_idempotent_for_identical_output(tmp_path, dbc_file):
    """Regenerating the same Parquet must not change the manifest (no noisy git diffs)."""
    manifest = empty_manifest()
    register_source(manifest, "k", dbc_file, **SOURCE_INFO)
    first = record_derived(manifest, "x", "k", convert_dbc_to_parquet(dbc_file, tmp_path / "a.pq"))
    first_copy = dict(first)
    again = convert_dbc_to_parquet(dbc_file, tmp_path / "b.pq")
    again.created_at = "2099-01-01T00:00:00+00:00"
    assert record_derived(manifest, "x", "k", again) == first_copy
    assert manifest["derived"]["x"]["created_at"] == first_copy["created_at"]


def test_different_content_requires_supersede_reason_and_keeps_history(tmp_path):
    from synthetic_data import FieldSpec, build_dbc, build_dbf

    dbf = build_dbf([FieldSpec("T", "C", 4)], [["É"]], encoding="cp850")
    src = write(tmp_path / "s.dbc", build_dbc(dbf))
    manifest = empty_manifest()
    register_source(manifest, "k", src, **SOURCE_INFO)
    old = record_derived(
        manifest, "x", "k", convert_dbc_to_parquet(src, tmp_path / "a.pq", encoding="latin-1")
    )
    new_report = convert_dbc_to_parquet(src, tmp_path / "b.pq", encoding="cp850")

    with pytest.raises(ManifestError, match="supersede"):
        record_derived(manifest, "x", "k", new_report)
    assert manifest["derived"]["x"] is old  # unchanged after refusal

    new = record_derived(manifest, "x", "k", new_report, supersede_reason="adopt CP850")
    assert new["encoding"] == "cp850"
    assert new["raw_bytes_fingerprint"] == old["raw_bytes_fingerprint"]
    (previous,) = new["history"]
    assert previous["content_fingerprint"] == old["content_fingerprint"]
    assert previous["superseded_reason"] == "adopt CP850"
    # identical regeneration after a supersede is still a no-op (history kept)
    assert record_derived(manifest, "x", "k", new_report) is new
