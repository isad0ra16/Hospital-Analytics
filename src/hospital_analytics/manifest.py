"""Data manifest (``data/MANIFEST.json``): provenance and integrity of every data file.

The data files are not versioned in git; the manifest is. It records, for each file:

* sources: where the file came from (official URL, archived copy), when and by whom it was
  obtained, its size and SHA-256, and the data version information available;
* derived files: which source they come from, how they were produced (tool versions),
  their shape and content fingerprint.

A registered source is immutable: registering the same path with a different SHA-256 is
refused. A new DATASUS publication must be registered explicitly as a new file.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from hospital_analytics.convert import ConversionReport
from hospital_analytics.integrity import sha256_file

MANIFEST_VERSION = 1


class ManifestError(Exception):
    """The manifest is inconsistent with the files or with a requested change."""


def empty_manifest() -> dict[str, Any]:
    return {"manifest_version": MANIFEST_VERSION, "sources": {}, "derived": {}}


def load_manifest(path: Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        return empty_manifest()
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("manifest_version") != MANIFEST_VERSION:
        raise ManifestError(
            f"{path}: unsupported manifest_version {manifest.get('manifest_version')}"
        )
    return manifest


def save_manifest(manifest: dict[str, Any], path: Path) -> None:
    """Write the manifest atomically, with stable formatting (readable git diffs)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".partial")
    tmp.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n", "utf-8"
    )
    os.replace(tmp, path)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def register_source(
    manifest: dict[str, Any],
    key: str,
    file_path: Path,
    *,
    official_url: str,
    obtained_at: str,
    obtained_by: str,
    data_version: dict[str, Any],
    archive: dict[str, Any] | None = None,
    expected_sha256: str | None = None,
    expected_size: int | None = None,
    notes: str = "",
) -> dict[str, Any]:
    """Register an original data file. ``key`` is its path relative to the project root."""
    file_path = Path(file_path)
    sha, size = sha256_file(file_path), file_path.stat().st_size
    if expected_sha256 is not None and sha != expected_sha256.lower():
        raise ManifestError(f"{file_path}: SHA-256 {sha} differs from expected {expected_sha256}.")
    if expected_size is not None and size != expected_size:
        raise ManifestError(f"{file_path}: size {size} differs from expected {expected_size}.")

    existing = manifest["sources"].get(key)
    if existing is not None:
        if existing["sha256"] != sha:
            raise ManifestError(
                f"{key} is already registered with SHA-256 {existing['sha256']}; refusing to "
                f"replace it with {sha}. Register a new version under a new name."
            )
        return existing  # idempotent: same file, nothing to change

    entry = {
        "sha256": sha,
        "size_bytes": size,
        "official_url": official_url,
        "archive": archive,
        "obtained_at": obtained_at,
        "obtained_by": obtained_by,
        "data_version": data_version,
        "registered_at": _now(),
        "notes": notes,
    }
    manifest["sources"][key] = entry
    return entry


def record_derived(
    manifest: dict[str, Any],
    key: str,
    source_key: str,
    report: ConversionReport,
    *,
    supersede_reason: str | None = None,
) -> dict[str, Any]:
    """Record a file derived from a registered source.

    Regenerating identical output changes nothing. Recording different content for an
    existing key requires ``supersede_reason``; the previous entry is kept in ``history``.
    """
    source = manifest["sources"].get(source_key)
    if source is None:
        raise ManifestError(f"Source {source_key} is not registered.")
    if source["sha256"] != report.source_sha256:
        raise ManifestError(f"{key} was produced from a file that does not match {source_key}.")

    entry = {
        "derived_from": source_key,
        "source_sha256": report.source_sha256,
        "step": "raw_conversion (.dbc -> .dbf -> Arrow -> Parquet, no treatment)",
        "sha256": report.parquet_sha256,
        "size_bytes": report.parquet_size_bytes,
        "records": report.records,
        "columns": report.columns,
        "content_fingerprint": report.content_fingerprint,
        "raw_bytes_fingerprint": report.raw_bytes_fingerprint,
        "encoding": report.encoding,
        "intermediate_dbf": {
            "sha256": report.dbf_sha256,
            "size_bytes": report.dbf_size_bytes,
            "version": report.dbf_version,
            "last_update": report.dbf_last_update,
            "language_driver": report.dbf_language_driver,
            "declared_encoding": report.dbf_declared_encoding,
            "header_records": report.dbf_header_records,
        },
        "tool_versions": report.tool_versions,
        "created_at": report.created_at,
    }

    existing = manifest["derived"].get(key)
    if existing is None:
        manifest["derived"][key] = entry
        return entry
    if _comparable(existing) == _comparable(entry):
        return existing  # idempotent: regenerating identical output changes nothing
    if existing["content_fingerprint"] != entry["content_fingerprint"] and not supersede_reason:
        raise ManifestError(
            f"{key} is already recorded with different content; investigate, then record it "
            "again with an explicit supersede reason."
        )
    previous = {k: v for k, v in existing.items() if k != "history"}
    previous["superseded_at"] = _now()
    previous["superseded_reason"] = supersede_reason or "regenerated with identical content"
    entry["history"] = [*existing.get("history", []), previous]
    manifest["derived"][key] = entry
    return entry


def record_processed(
    manifest: dict[str, Any],
    key: str,
    raw_key: str,
    report: Any,
    *,
    supersede_reason: str | None = None,
) -> dict[str, Any]:
    """Record the processed layer, derived from a recorded raw-layer file.

    The fingerprint of its original (uppercase) columns must equal the raw content fingerprint.
    """
    raw = manifest["derived"].get(raw_key)
    if raw is None:
        raise ManifestError(f"Raw layer {raw_key} is not recorded.")
    if report.original_columns_fingerprint != raw["content_fingerprint"]:
        raise ManifestError(f"{key}: original columns differ from the raw layer {raw_key}.")

    entry = {
        "derived_from": raw_key,
        "step": "processed_layer (original columns untouched + derived columns)",
        "sha256": report.sha256,
        "size_bytes": report.size_bytes,
        "records": report.records,
        "original_columns": report.original_columns,
        "derived_columns": report.derived_columns,
        "original_columns_fingerprint": report.original_columns_fingerprint,
        "invalid_dates": report.invalid_dates,
        "reversibility_checked": report.reversibility_checked,
        "reduced_precision_values": report.reduced_precision_values,
        "tool_versions": report.tool_versions,
        "created_at": report.created_at,
    }
    existing = manifest["derived"].get(key)
    if existing is not None and _comparable(existing) == _comparable(entry):
        return existing
    if existing is not None:
        if existing["sha256"] != entry["sha256"] and not supersede_reason:
            raise ManifestError(f"{key} is already recorded with different content; give a reason.")
        previous = {k: v for k, v in existing.items() if k != "history"}
        previous["superseded_at"] = _now()
        previous["superseded_reason"] = supersede_reason or "regenerated"
        entry["history"] = [*existing.get("history", []), previous]
    manifest["derived"][key] = entry
    return entry


def _comparable(entry: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in entry.items() if k not in {"created_at", "history"}}


def verify_file(entry: dict[str, Any], file_path: Path) -> tuple[bool, str]:
    """Return (matches, observed_sha256) for a file against its manifest entry."""
    observed = sha256_file(file_path)
    return observed == entry["sha256"], observed
