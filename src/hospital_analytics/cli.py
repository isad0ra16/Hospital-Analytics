"""Command line interface: ``hospital-analytics <command>``.

Commands: register-source, convert, validate, build-processed, verify, audit, indicators.

Each step is explicit and verifiable. Any divergence returns exit code 1.
Paths default to ``config/params.yaml``; ``--root`` changes the project root (used in tests).
"""

from __future__ import annotations

import argparse
import json
import logging
import stat
import sys
from decimal import Decimal
from pathlib import Path

from hospital_analytics import pbip, powerbi, reference_diagnose
from hospital_analytics.analysis import run_analysis
from hospital_analytics.analysis import write_report as analysis_write
from hospital_analytics.audit import run_audit
from hospital_analytics.audit import write_report as audit_write
from hospital_analytics.config import load_params, project_root, to_money
from hospital_analytics.convert import (
    DeletedRecordsError,
    EncodingMismatchError,
    IntegrityError,
    convert_dbc_to_parquet,
)
from hospital_analytics.dbc import DbcError, read_dbf_header
from hospital_analytics.dbf import DbfError
from hospital_analytics.enrichment import (
    REQUIRED_SOURCES,
    ReferenceIntegrityError,
    load_references,
)
from hospital_analytics.indicators import run_indicators
from hospital_analytics.indicators import write_report as indicators_write
from hospital_analytics.integrity import check_declared
from hospital_analytics.manifest import (
    ManifestError,
    load_manifest,
    record_derived,
    record_processed,
    register_source,
    save_manifest,
    verify_file,
)
from hospital_analytics.processed import TransformError, build_processed
from hospital_analytics.reference import ReferenceFormatError
from hospital_analytics.validate import ReferenceTargets, validate_raw_parquet

READ_ONLY = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH  # 0o444


def _key(path: Path, root: Path) -> str:
    """Manifest key: path relative to the project root, with forward slashes."""
    return Path(path).resolve().relative_to(root.resolve()).as_posix()


def _defaults(root: Path) -> dict[str, Path]:
    params = load_params()
    raw = root / params["paths"]["raw"]
    return {
        "source": raw / params["source"]["filename"],
        "parquet": raw / params["raw_conversion"]["parquet_filename"],
        "processed": root / params["paths"]["processed"] / params["processing"]["filename"],
        "manifest": root / params["paths"]["manifest"],
    }


def cmd_register_source(args: argparse.Namespace) -> int:
    root = args.root
    source = args.source or _defaults(root)["source"]
    manifest_path = args.manifest or _defaults(root)["manifest"]
    params = load_params()["source"]

    manifest = load_manifest(manifest_path)
    archive = None
    if args.archive_repo:
        archive = {
            "type": "github_release",
            "repository": args.archive_repo,
            "tag": args.archive_tag,
            "asset": args.archive_asset or source.name,
        }
    data_version = {
        "system": params["system"],
        "file_type": params["file_type"],
        "uf": params["uf"],
        "competence": params["competence"],
        "dbf_header_last_update": read_dbf_header(source).last_update,
    }
    entry = register_source(
        manifest,
        _key(source, root),
        source,
        official_url=args.official_url,
        obtained_at=args.obtained_at,
        obtained_by=args.obtained_by,
        data_version=data_version,
        archive=archive,
        expected_sha256=args.expected_sha256,
        expected_size=args.expected_size,
        notes=args.notes,
    )
    source.chmod(READ_ONLY)
    save_manifest(manifest, manifest_path)
    print(json.dumps({_key(source, root): entry}, indent=2, ensure_ascii=False))
    return 0


def cmd_convert(args: argparse.Namespace) -> int:
    root = args.root
    defaults = _defaults(root)
    source = args.source or defaults["source"]
    destination = args.destination or defaults["parquet"]
    manifest_path = args.manifest or defaults["manifest"]

    manifest = load_manifest(manifest_path)
    source_key = _key(source, root)
    entry = manifest["sources"].get(source_key)
    if entry is None:
        print(f"ERROR: {source_key} is not registered; run register-source first.", file=sys.stderr)
        return 1
    ok, observed = verify_file(entry, source)
    if not ok:
        print(
            f"ERROR: {source_key} SHA-256 {observed} != manifest {entry['sha256']}", file=sys.stderr
        )
        return 1

    report = convert_dbc_to_parquet(
        source,
        destination,
        encoding=load_params()["raw_conversion"]["encoding"],
        expected_source_sha256=entry["sha256"],
    )
    record_derived(
        manifest, _key(destination, root), source_key, report, supersede_reason=args.supersede
    )
    destination.chmod(READ_ONLY)
    save_manifest(manifest, manifest_path)

    summary = {
        "parquet": _key(destination, root),
        "records": report.records,
        "columns": report.columns,
        "dbf_header_records": report.dbf_header_records,
        "dbf_last_update": report.dbf_last_update,
        "content_fingerprint": report.content_fingerprint,
        "raw_bytes_fingerprint": report.raw_bytes_fingerprint,
        "encoding": report.encoding,
        "dbf_declared_encoding": report.dbf_declared_encoding,
        "columns_with_non_ascii_bytes": {k: v for k, v in report.non_ascii_counts.items() if v},
        "columns_entirely_blank": [
            k for k, v in report.blank_counts.items() if v == report.records
        ],
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    root = args.root
    defaults = _defaults(root)
    parquet = args.parquet or defaults["parquet"]
    manifest_path = args.manifest or defaults["manifest"]

    params = load_params()
    targets = ReferenceTargets.from_params(params)
    targets = ReferenceTargets(
        records=args.expect_records if args.expect_records is not None else targets.records,
        columns=args.expect_columns if args.expect_columns is not None else targets.columns,
        val_tot_sum=to_money(args.expect_val_tot) if args.expect_val_tot else targets.val_tot_sum,
    )
    derived = load_manifest(manifest_path)["derived"].get(_key(parquet, root))
    report = validate_raw_parquet(
        parquet,
        targets,
        money_column=params["raw_conversion"]["money_column"],
        derived_entry=derived,
    )
    print(report.format_table())
    if derived is None:
        print("WARNING: no manifest entry for this file; preservation checks were not run.")
        return 1
    return 0 if report.passed else 1


def cmd_build_processed(args: argparse.Namespace) -> int:
    root = args.root
    defaults = _defaults(root)
    raw = args.parquet or defaults["parquet"]
    destination = args.destination or defaults["processed"]
    manifest_path = args.manifest or defaults["manifest"]

    manifest = load_manifest(manifest_path)
    raw_key = _key(raw, root)
    raw_entry = manifest["derived"].get(raw_key)
    if raw_entry is None:
        print(f"ERROR: {raw_key} is not recorded; run convert first.", file=sys.stderr)
        return 1
    ok, observed = verify_file(raw_entry, raw)
    if not ok:
        print(f"ERROR: {raw_key} SHA-256 {observed} != manifest", file=sys.stderr)
        return 1

    report = build_processed(raw, destination)
    record_processed(
        manifest, _key(destination, root), raw_key, report, supersede_reason=args.supersede
    )
    destination.chmod(READ_ONLY)
    save_manifest(manifest, manifest_path)
    print(
        json.dumps(
            {
                "processed": _key(destination, root),
                "records": report.records,
                "original_columns": report.original_columns,
                "derived_columns": len(report.derived_columns),
                "original_columns_fingerprint": report.original_columns_fingerprint,
                "invalid_dates": report.invalid_dates,
                "reduced_precision_values": report.reduced_precision_values,
            },
            indent=2,
        )
    )
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    root = args.root
    defaults = _defaults(root)
    report = run_audit(args.parquet or defaults["parquet"], args.processed or defaults["processed"])
    json_path, md_path = audit_write(report, root / "reports" / "audit", "audit_rdrj2401")
    print(f"records={report.records} columns={report.columns}")
    print(f"entirely blank: {report.entirely_blank}")
    print(f"written: {_key(json_path, root)}, {_key(md_path, root)}")
    return 0


def cmd_indicators(args: argparse.Namespace) -> int:
    root = args.root
    processed = args.processed or _defaults(root)["processed"]
    report = run_indicators(processed)
    json_path, md_path = indicators_write(report, root / "reports" / "indicators", "reconciliation")
    for r in report["indicators"]:
        shown = r["rounded"] or r["reproduced"]
        print(f"{r['status']:<28} {r['id']:<32} hist={r['historical']} rep={shown}")
    print(f"pandas x duckdb agree: {report['engines_agree']}")
    for problem in report["disagreements"]:
        print(f"  DISAGREEMENT {problem}")
    print(f"written: {_key(json_path, root)}, {_key(md_path, root)}")
    return 0 if report["engines_agree"] else 1


def cmd_analysis(args: argparse.Namespace) -> int:
    root = args.root
    report = run_analysis(args.processed or _defaults(root)["processed"])
    for path in analysis_write(report, root / "reports" / "analysis", "analysis"):
        print(f"written: {_key(path, root)}")
    return 0


def cmd_powerbi(args: argparse.Namespace) -> int:
    """Export the star schema, write the summary and generated docs, validate the files."""
    root = args.root
    processed = args.processed or _defaults(root)["processed"]
    out = args.output or root / "data" / "powerbi"
    incoming = args.incoming or root / "data" / "reference" / "incoming"
    summary_path = root / "reports" / "powerbi" / "export_summary.json"
    previous_fact_sha = None
    if summary_path.is_file():
        previous = json.loads(summary_path.read_text(encoding="utf-8"))
        previous_fact_sha = previous["tables"]["fato_registro_aih"]["csv"]["sha256"]
    try:
        references = load_references(incoming, load_params()["reference_sources"])
    except (ReferenceIntegrityError, ReferenceFormatError) as exc:
        print(f"ERROR: official reference data: {exc}", file=sys.stderr)
        return 1
    summary = powerbi.export_model(
        processed, out, references=references, parquet=args.parquet, reports=root / "reports"
    )
    powerbi.write_summary(summary, summary_path)
    docs = root / "docs" / "powerbi"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "dicionario_campos.md").write_text(powerbi.field_dictionary_markdown(), "utf-8")
    (docs / "consultas_power_query.pq").write_text(powerbi.power_query_m(), "utf-8")
    for name, entry in summary["tables"].items():
        print(f"exported {name:<28} rows={entry['rows']}")
    enrichment = powerbi.enrichment_report(out)
    ref_reports = root / "reports" / "reference"
    ref_reports.mkdir(parents=True, exist_ok=True)
    (ref_reports / "enriquecimento.json").write_text(
        json.dumps(enrichment, indent=2, ensure_ascii=False) + "\n", "utf-8"
    )
    (ref_reports / "enriquecimento.md").write_text(powerbi.enrichment_markdown(enrichment), "utf-8")

    reconciliation = json.loads(
        (root / "reports" / "indicators" / "reconciliation.json").read_text(encoding="utf-8")
    )
    full = reconciliation["aggregates"]["base"]["full"]
    expected = {
        "records": full["records"],
        "val_tot_cents": full["val_tot_cents"],
        "deaths": full["deaths"],
        "dias_perm_sum": full["dias_perm_sum"],
        "age_years_count": full["age_years_count"],
        "distinct_aih": full["records"]
        - reconciliation["aggregates"]["repeated_aih"]["excess_records"],
    }
    checks = powerbi.validate_model(out, expected)
    if previous_fact_sha is not None:
        checks.append(
            powerbi.ModelCheck(
                "fato_registro_aih.csv byte-identical to the previous export (SHA-256)",
                previous_fact_sha,
                summary["tables"]["fato_registro_aih"]["csv"]["sha256"],
            )
        )
    else:
        print("NOTE: no previous export summary; fact preservation check not run.")
    indicator = {r["id"]: r for r in reconciliation["indicators"]}
    measures = powerbi.measure_values(out)
    pairs = {
        "registros_aih": ("records_full", 1),
        "valor_total": ("val_tot_full", 1),
        "valor_medio": ("val_mean_full", 1),
        "permanencia_media": ("los_mean_full", 1),
        "obitos": ("deaths_full", 1),
        "mortalidade_razao": ("mortality_full", 100),
        "idade_media_anos": ("age_mean_years_full", 1),
        "concentracao_top10_razao": ("top10_share_full", 100),
    }
    q = Decimal("0.0001")
    for measure, (indicator_id, scale) in pairs.items():
        reference = (Decimal(indicator[indicator_id]["reproduced"]) / scale).quantize(q)
        checks.append(
            powerbi.ModelCheck(
                f"measure {measure} == indicator {indicator_id}",
                reference,
                measures[measure].quantize(q),
            )
        )
    checks.append(
        powerbi.ModelCheck(
            "dashboard: distinct AIH == records - repeated-AIH excess",
            Decimal(expected["distinct_aih"]),
            measures["aihs_distintas"],
        )
    )
    analysis_path = root / "reports" / "analysis" / "analysis.json"
    if analysis_path.is_file():
        analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
        lorenz = powerbi.lorenz_points(out)
        for point in analysis["lorenz"]:
            p = point["records_pct"]
            checks.append(
                powerbi.ModelCheck(
                    f"aux_curva_lorenz p={p} == analysis report (%, 2 decimals)",
                    Decimal(point["value_pct"]),
                    (lorenz[p] * 100).quantize(Decimal("0.01")),
                )
            )
    reference_values = {
        k: str(v.quantize(Decimal("0.000001"))) for k, v in sorted(measures.items())
    }
    (root / "reports" / "powerbi" / "medidas_referencia.json").write_text(
        json.dumps(
            {
                "base": "completa (73.046 registros, competência 2024-01)"
                if measures["registros_aih"] == 73046
                else "completa",
                "nota": "Valores exatos das medidas DAX equivalentes (razões não multiplicadas"
                " por 100). Use-os para conferir os cartões no Power BI.",
                "medidas": reference_values,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        "utf-8",
    )
    failed = [c for c in checks if not c.passed]
    for check in checks:
        print(
            f"[{'PASS' if check.passed else 'FAIL'}] {check.name}: "
            f"expected={check.expected} observed={check.observed}"
        )
    print(
        f"RESULT: {'ALL CHECKS PASSED' if not failed else f'{len(failed)} CHECKS FAILED'}"
        f" ({len(checks)} checks)"
    )
    return 0 if not failed else 1


def cmd_pbip(args: argparse.Namespace) -> int:
    """Generate the Power BI Project (TMDL semantic model + PBIR report) under powerbi/."""
    root = args.root
    measures = (root / "docs" / "powerbi" / "medidas.dax").read_text(encoding="utf-8")
    written = pbip.write_project(root / "powerbi", measures)
    (root / "docs" / "powerbi" / "paginas.md").write_text(pbip.pages_markdown(), "utf-8")
    print(f"written {len(written)} files under {_key(root / 'powerbi', root)}/")
    return 0


def cmd_reference_diagnose(args: argparse.Namespace) -> int:
    """Read-only diagnostic of the official reference files (no enrichment)."""
    root = args.root
    incoming = args.incoming or root / "data" / "reference" / "incoming"
    report = reference_diagnose.run_diagnostic(incoming, root / "data" / "powerbi")
    path = reference_diagnose.write_diagnostic(report, root / "reports" / "reference")
    for name, entry in report["sources"].items():
        integrity = entry["integrity"]
        status = (
            "ausente"
            if not integrity["present"]
            else ("OK" if integrity.get("integrity_ok") else "INTEGRIDADE DIVERGENTE")
        )
        print(f"{name:<16} {integrity['file']:<45} {status}")
    print(f"written: {_key(path, root)}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Check that every file in the manifest exists and matches its SHA-256 (read-only)."""
    root = args.root
    manifest = load_manifest(args.manifest or _defaults(root)["manifest"])
    entries = [("source", k, e) for k, e in manifest["sources"].items()]
    entries += [("derived", k, e) for k, e in manifest["derived"].items()]
    if not entries:
        print("Manifest is empty: nothing to verify.")
        return 1
    all_ok = True
    for kind, key, entry in entries:
        path = root / key
        if not path.is_file():
            status, all_ok = "MISSING", all_ok and kind == "derived"
            if kind == "derived":
                status += " (regenerate with: hospital-analytics convert)"
        else:
            ok, observed = verify_file(entry, path)
            status = "OK" if ok else f"SHA-256 MISMATCH (observed {observed})"
            all_ok = all_ok and ok
        print(f"[{kind}] {key}: {status}")
    # Official reference files declared in config/params.yaml (reference_sources).
    incoming = root / "data" / "reference" / "incoming"
    for name, spec in load_params()["reference_sources"].items():
        path = incoming / spec["filename"]
        result = check_declared(path, spec)
        if not result["present"]:
            needed = name in REQUIRED_SOURCES
            status = "MISSING (required by powerbi)" if needed else "not stored (optional)"
        else:
            status = "OK" if result["integrity_ok"] else "SIZE/SHA-256 MISMATCH"
            all_ok = all_ok and result["integrity_ok"]
        print(f"[reference] {_key(path, root) if path.is_file() else spec['filename']}: {status}")
    return 0 if all_ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hospital-analytics", description=__doc__)
    parser.add_argument("--root", type=Path, default=None, help="project root (default: auto)")
    parser.add_argument("--manifest", type=Path, default=None)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("register-source", help="register an original file in the manifest")
    p.add_argument("--source", type=Path)
    p.add_argument("--official-url", required=True)
    p.add_argument("--obtained-at", required=True, help="date (and time, if known) of download")
    p.add_argument("--obtained-by", required=True)
    p.add_argument("--expected-sha256")
    p.add_argument("--expected-size", type=int)
    p.add_argument("--archive-repo")
    p.add_argument("--archive-tag")
    p.add_argument("--archive-asset")
    p.add_argument("--notes", default="")
    p.set_defaults(func=cmd_register_source)

    p = sub.add_parser("convert", help="untreated .dbc -> Parquet conversion (raw layer)")
    p.add_argument("--source", type=Path)
    p.add_argument("--destination", type=Path)
    p.add_argument(
        "--supersede",
        metavar="REASON",
        help="replace a manifest entry with different content; the old entry is kept in history",
    )
    p.set_defaults(func=cmd_convert)

    p = sub.add_parser("validate", help="validate the raw Parquet (exit code 1 on divergence)")
    p.add_argument("--parquet", type=Path)
    p.add_argument("--expect-records", type=int)
    p.add_argument("--expect-columns", type=int)
    p.add_argument("--expect-val-tot", help="exact decimal string, e.g. 123.45")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("build-processed", help="build the processed layer from the raw Parquet")
    p.add_argument("--parquet", type=Path, help="raw-layer Parquet (input)")
    p.add_argument("--destination", type=Path)
    p.add_argument("--supersede", metavar="REASON")
    p.set_defaults(func=cmd_build_processed)

    p = sub.add_parser("audit", help="read-only data audit; writes reports/audit/")
    p.add_argument("--parquet", type=Path, help="raw-layer Parquet")
    p.add_argument("--processed", type=Path)
    p.set_defaults(func=cmd_audit)

    p = sub.add_parser(
        "indicators", help="historical indicators (pandas x DuckDB); reports/indicators/"
    )
    p.add_argument("--processed", type=Path)
    p.set_defaults(func=cmd_indicators)

    p = sub.add_parser("analysis", help="descriptive exploratory analyses -> reports/analysis/")
    p.add_argument("--processed", type=Path)
    p.set_defaults(func=cmd_analysis)

    p = sub.add_parser("powerbi", help="export the Power BI star schema (CSV) and validate it")
    p.add_argument("--processed", type=Path)
    p.add_argument("--output", type=Path, help="default: data/powerbi")
    p.add_argument("--parquet", action="store_true", help="also write Parquet files")
    p.add_argument(
        "--incoming", type=Path, help="official reference files (default: data/reference/incoming)"
    )
    p.set_defaults(func=cmd_powerbi)

    p = sub.add_parser("pbip", help="generate the Power BI Project (TMDL model + PBIR report)")
    p.set_defaults(func=cmd_pbip)

    p = sub.add_parser(
        "reference-diagnose", help="read-only diagnostic of official reference files"
    )
    p.add_argument("--incoming", type=Path, help="default: data/reference/incoming")
    p.set_defaults(func=cmd_reference_diagnose)

    p = sub.add_parser("verify", help="check every manifest file exists and matches its SHA-256")
    p.set_defaults(func=cmd_verify)
    return parser


def safe_console() -> None:
    """Never crash while *printing* a result.

    Reports contain status symbols (✅ 🟠 🔴) and accented text. On Windows, a redirected or
    piped stdout uses the ANSI code page (cp1252), which cannot encode them: the command would
    fail after writing its files. Unencodable characters are printed as escapes instead.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(errors="backslashreplace")


def main(argv: list[str] | None = None) -> int:
    safe_console()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = build_parser().parse_args(argv)
    args.root = (args.root or project_root()).resolve()
    try:
        return args.func(args)
    except (
        ManifestError,
        IntegrityError,
        DeletedRecordsError,
        EncodingMismatchError,
        TransformError,
        DbcError,
        DbfError,
        FileExistsError,
        FileNotFoundError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
