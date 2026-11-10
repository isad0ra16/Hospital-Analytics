"""Historical indicators: definitions, computation in pandas AND DuckDB SQL, reconciliation.

Design:

* both engines compute the same *exact aggregates* (integer sums and counts); means and
  percentages are then derived with ``Decimal``. Only the sum of fractional ``age_years`` is
  compared with a relative tolerance;
* historical values are read from ``config/params.yaml`` (single source of truth);
* a reproduced value is rounded half-up to the precision of the historical value; the status
  follows fixed rules, it is never chosen by hand:
    ✅ equal, criterion documented in the history
    🟡 equal, criterion identified during the reconstruction
    🟠 different, with a documented (possibly hypothetical) explanation
    🔴 different, unexplained
    🆕 new indicator, no historical reference
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

import pandas as pd

from hospital_analytics.config import load_params
from hospital_analytics.sql import connect, query

SCOPES = ("full", "ident_1", "ident_5")
TOP_FRACTION = Decimal("0.1")
SURGICAL_GROUP, CLINICAL_GROUP = "04", "03"


# ---------------------------------------------------------------------------
# Exact aggregates
# ---------------------------------------------------------------------------
def aggregates_pandas(df: pd.DataFrame) -> dict[str, Any]:
    """Exact aggregates from the processed layer, computed with pandas."""
    base = {}
    for scope in SCOPES:
        part = df if scope == "full" else df[df["IDENT"] == scope.split("_")[1]]
        base[scope] = {
            "records": len(part),
            "val_tot_cents": int(part["val_tot_cents"].sum()),
            "dias_perm_sum": int(part["dias_perm_int"].sum()),
            "dias_perm_count": int(part["dias_perm_int"].count()),
            "idade_raw_sum": int(part["idade_int"].sum()),
            "idade_raw_count": int(part["idade_int"].count()),
            "age_years_sum": float(part["age_years"].sum()),
            "age_years_count": int(part["age_years"].count()),
            "deaths": int(part["died"].sum()),
        }
    counts = df.groupby("N_AIH").size()
    repeated = counts[counts > 1]
    top = {}
    for ident in (None, "1"):
        part = df if ident is None else df[df["IDENT"] == ident]
        values = part["val_tot_cents"].sort_values(ascending=False, kind="mergesort")
        k = int(Decimal(len(values)) * TOP_FRACTION)  # floor
        top[ident or "full"] = {
            "records": len(values),
            "top_records": k,
            "top_cents": int(values.iloc[:k].sum()),
            "total_cents": int(values.sum()),
        }
    groups = {}
    for ident in (None, "1"):
        part = df if ident is None else df[df["IDENT"] == ident]
        g = part.groupby("proc_rea_group").agg(
            records=("val_tot_cents", "size"), val_tot_cents=("val_tot_cents", "sum")
        )
        groups[ident or "full"] = {
            k: {"records": int(r.records), "val_tot_cents": int(r.val_tot_cents)}
            for k, r in g.iterrows()
        }
    return {
        "base": base,
        "discharge_year": {int(y): int(c) for y, c in df.groupby("discharge_year").size().items()},
        "repeated_aih": {
            "excess_records": int((repeated - 1).sum()),
            "distinct_numbers": len(repeated),
        },
        "top_share": top,
        "proc_groups": groups,
    }


def aggregates_sql(processed: Path) -> dict[str, Any]:
    """The same exact aggregates, computed with the versioned DuckDB queries."""
    con = connect(processed=processed)
    base = {}
    for row in query(con, "indicators/base_by_scope"):
        scope = row.pop("scope")
        base[scope] = {k: (float(v) if k == "age_years_sum" else int(v)) for k, v in row.items()}
    top = {}
    for ident in (None, "1"):
        (row,) = query(con, "indicators/top_share", ident=ident, fraction=float(TOP_FRACTION))
        top[ident or "full"] = {k: int(v) for k, v in row.items()}
    groups = {}
    for ident in (None, "1"):
        groups[ident or "full"] = {
            r["proc_rea_group"]: {
                "records": int(r["records"]),
                "val_tot_cents": int(r["val_tot_cents"]),
            }
            for r in query(con, "indicators/proc_group_value_share", ident=ident)
        }
    (rep,) = query(con, "audit/repeated_aih")
    return {
        "base": {s: base[s] for s in SCOPES},
        "discharge_year": {
            int(r["discharge_year"]): int(r["records"]) for r in query(con, "audit/discharge_year")
        },
        "repeated_aih": {
            "excess_records": int(rep["excess_records"]),
            "distinct_numbers": int(rep["distinct_numbers"]),
        },
        "top_share": top,
        "proc_groups": groups,
    }


def engines_agree(a: dict[str, Any], b: dict[str, Any]) -> list[str]:
    """Paths where the two engines disagree (empty list = full agreement)."""
    problems: list[str] = []

    def walk(x: Any, y: Any, path: str) -> None:
        if isinstance(x, dict) and isinstance(y, dict):
            if set(x) != set(y):
                problems.append(f"{path}: keys {sorted(map(str, x))} != {sorted(map(str, y))}")
                return
            for key in x:
                walk(x[key], y[key], f"{path}.{key}")
        elif isinstance(x, float) or isinstance(y, float):
            if not math.isclose(x, y, rel_tol=1e-12):
                problems.append(f"{path}: {x} != {y}")
        elif x != y:
            problems.append(f"{path}: {x} != {y}")

    walk(a, b, "aggregates")
    return problems


# ---------------------------------------------------------------------------
# Indicator definitions
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class IndicatorSpec:
    id: str
    name: str
    scope: str
    definition: str
    source_fields: str
    formula: str
    denominator: str
    filters: str
    unit: str
    historical: str | None
    criterion: str  # "documented" | "identified" | "unknown" | "new"
    note: str = ""
    divergence_explanation: str = ""


SCOPE_FILTER = {
    "full": "nenhum (base completa)",
    "ident_1": "IDENT = '1'",
    "ident_5": "IDENT = '5'",
}
SCOPE_LABEL = {"full": "base completa", "ident_1": "AIH tipo 1", "ident_5": "AIH tipo 5"}


def _hist(node: dict[str, Any]) -> str:
    value = node["value"]
    return str(value) if not isinstance(value, float) else f"{value:.2f}"


def specs(params: dict[str, Any] | None = None) -> list[IndicatorSpec]:
    """All indicator definitions, with historical values taken from the parameters file."""
    ref = (params or load_params())["historical_reference"]
    full, by_ident = ref["full_base"], ref["by_ident"]
    out: list[IndicatorSpec] = []
    for scope in SCOPES:
        h = full if scope == "full" else by_ident[scope.split("_")[1]]
        flt, lbl = SCOPE_FILTER[scope], SCOPE_LABEL[scope]
        out += [
            IndicatorSpec(
                f"records_{scope}",
                f"Registros ({lbl})",
                scope,
                "Número de registros de AIH",
                "—",
                "count(*)",
                "—",
                flt,
                "count",
                _hist(h["records"]),
                "documented",
            ),
            IndicatorSpec(
                f"val_tot_{scope}",
                f"Valor total ({lbl})",
                scope,
                "Soma de VAL_TOT",
                "VAL_TOT",
                "sum(val_tot_cents) / 100",
                "—",
                flt,
                "money",
                _hist(h["val_tot_sum"]),
                "documented",
            ),
            IndicatorSpec(
                f"val_mean_{scope}",
                f"Valor médio por registro ({lbl})",
                scope,
                "Valor total dividido pelo número de registros",
                "VAL_TOT",
                "sum(val_tot_cents) / count(*) / 100",
                "registros",
                flt,
                "money",
                _hist(h["mean_val_tot"]),
                "documented",
            ),
            IndicatorSpec(
                f"los_mean_{scope}",
                f"Permanência média ({lbl})",
                scope,
                "Média de dias de permanência",
                "DIAS_PERM",
                "avg(DIAS_PERM)",
                "registros",
                flt,
                "days",
                _hist(h["mean_length_of_stay_days"]),
                "identified",
                "Campo não registrado no histórico; DIAS_PERM reproduz os três valores. "
                "QT_DIARIAS e DT_SAIDA−DT_INTER não reproduzem.",
            ),
            IndicatorSpec(
                f"deaths_{scope}",
                f"Óbitos ({lbl})",
                scope,
                "Registros com óbito",
                "MORTE",
                "count(*) where MORTE = '1'",
                "—",
                flt,
                "count",
                _hist(h["deaths"]),
                "identified",
                "Campo não registrado no histórico; MORTE = 1 coincide registro a registro "
                "com COBRANCA 4x (óbito).",
            ),
        ]
    out += [
        IndicatorSpec(
            "age_mean_hist_full",
            "Idade média — critério histórico (base completa)",
            "full",
            "Média aritmética do campo IDADE, sem considerar a unidade (COD_IDADE)",
            "IDADE",
            "avg(IDADE)",
            "registros",
            "nenhum",
            "years",
            _hist(full["mean_age_years"]),
            "identified",
            "⚠️ Critério metodologicamente incorreto: mistura dias, meses, anos e centenas de "
            "anos (COD_IDADE 2/3/4/5). Reproduz o histórico; não usar em conclusões.",
        ),
        IndicatorSpec(
            "age_mean_years_full",
            "Idade média em anos — corrigida (base completa)",
            "full",
            "Média da idade convertida para anos conforme COD_IDADE",
            "COD_IDADE, IDADE",
            "avg(age_years); 2: IDADE/365,25 · 3: IDADE/12 · 4: IDADE · 5: 100+IDADE",
            "registros com unidade válida",
            "nenhum",
            "years",
            None,
            "new",
            "Interpretação de COD_IDADE por fonte secundária (microdatasus).",
        ),
        IndicatorSpec(
            "mortality_full",
            "Mortalidade bruta (base completa)",
            "full",
            "Óbitos por 100 registros de AIH (não por paciente)",
            "MORTE",
            "100 × óbitos / registros",
            "registros (inclui AIH tipo 5)",
            "nenhum",
            "pct",
            _hist(full["crude_mortality_pct"]),
            "identified",
            "Unidade de análise: registro de AIH.",
            "4.664 / 73.046 = 6,38501…%: arredondamento (half-up ou bancário) dá 6,39%; "
            "apenas truncamento em 2 casas dá 6,38%. Nenhum numerador/denominador "
            "alternativo testado dá 6,38%. Explicação provável: truncamento (não confirmável).",
        ),
    ]
    out += [
        IndicatorSpec(
            f"discharge_{year}",
            f"Saídas em {year}",
            "full",
            "Registros por ano de DT_SAIDA",
            "DT_SAIDA",
            "count(*) where year(discharge_date) = " + year,
            "—",
            "nenhum",
            "count",
            _hist(ref["discharge_year"][year]),
            "documented",
        )
        for year in ("2023", "2024")
    ]
    rep = ref["repeated_aih_numbers"]
    out += [
        IndicatorSpec(
            "aih_repeated_excess",
            "AIHs repetidas — registros excedentes",
            "full",
            "Registros além do primeiro para números de AIH que se repetem",
            "N_AIH",
            "Σ (ocorrências − 1) sobre N_AIH com ocorrências > 1",
            "—",
            "nenhum",
            "count",
            _hist(rep["occurrences"]),
            "identified",
            "Hipótese da Fase 1 confirmada: 56 excedentes, 50 números, 106 registros. "
            "Nenhum registro é removido.",
        ),
        IndicatorSpec(
            "aih_repeated_distinct",
            "AIHs repetidas — números distintos",
            "full",
            "Números de AIH com mais de um registro",
            "N_AIH",
            "count(N_AIH com ocorrências > 1)",
            "—",
            "nenhum",
            "count",
            _hist(rep["distinct_numbers"]),
            "documented",
        ),
        IndicatorSpec(
            "top10_share_full",
            "Concentração: 10% dos registros de maior VAL_TOT (base completa)",
            "full",
            "Participação no VAL_TOT dos k = ⌊0,1·n⌋ registros de maior valor",
            "VAL_TOT",
            "100 × Σ top-k / Σ total",
            "VAL_TOT total",
            "nenhum",
            "pct",
            _hist(ref["spending_concentration_top10_pct"]),
            "unknown",
            "Variantes testadas: base completa ⌊⌋/⌈⌉ 57,74/57,75; AIH tipo 1 58,27; VAL_SH 58,96; "
            "VAL_SH+VAL_SP 57,81; sem zeros 57,67; por N_AIH 57,74; por hospital 50,32.",
        ),
        IndicatorSpec(
            "top10_share_ident_1",
            "Concentração: 10% de maior VAL_TOT (AIH tipo 1)",
            "ident_1",
            "Mesma definição, restrita à AIH tipo 1 (variante mais próxima do histórico)",
            "VAL_TOT",
            "100 × Σ top-k / Σ total",
            "VAL_TOT total (tipo 1)",
            "IDENT = '1'",
            "pct",
            _hist(ref["spending_concentration_top10_pct"]),
            "unknown",
            "Variante mais próxima, mas diferente (58,27 ≠ 58,20).",
        ),
        IndicatorSpec(
            "surgical_value_share_ident_1",
            "Cirúrgicos — participação no valor (AIH tipo 1)",
            "ident_1",
            "Participação no VAL_TOT dos procedimentos do grupo SIGTAP 04",
            "PROC_REA, VAL_TOT",
            "100 × Σ VAL_TOT (grupo 04) / Σ VAL_TOT",
            "VAL_TOT total (tipo 1)",
            "IDENT = '1'",
            "pct",
            _hist(ref["admission_nature_pct"]["surgical"]),
            "identified",
            "O histórico mede VALOR, não número de internações (por contagem: 44,97%).",
        ),
        IndicatorSpec(
            "clinical_value_share_ident_1",
            "Clínicos — participação no valor (AIH tipo 1)",
            "ident_1",
            "Participação no VAL_TOT dos procedimentos do grupo SIGTAP 03",
            "PROC_REA, VAL_TOT",
            "100 × Σ VAL_TOT (grupo 03) / Σ VAL_TOT",
            "VAL_TOT total (tipo 1)",
            "IDENT = '1'",
            "pct",
            _hist(ref["admission_nature_pct"]["clinical"]),
            "identified",
            "O histórico mede VALOR, não número de internações (por contagem: 54,25%).",
        ),
    ]
    return out


# ---------------------------------------------------------------------------
# Values and reconciliation
# ---------------------------------------------------------------------------
def values(agg: dict[str, Any]) -> dict[str, Decimal]:
    """Exact reproduced values (unrounded Decimal) for every indicator id."""
    out: dict[str, Decimal] = {}
    for scope, b in agg["base"].items():
        out[f"records_{scope}"] = Decimal(b["records"])
        out[f"val_tot_{scope}"] = Decimal(b["val_tot_cents"]) / 100
        out[f"val_mean_{scope}"] = Decimal(b["val_tot_cents"]) / b["records"] / 100
        out[f"los_mean_{scope}"] = Decimal(b["dias_perm_sum"]) / b["dias_perm_count"]
        out[f"deaths_{scope}"] = Decimal(b["deaths"])
    full = agg["base"]["full"]
    out["age_mean_hist_full"] = Decimal(full["idade_raw_sum"]) / full["idade_raw_count"]
    out["age_mean_years_full"] = Decimal(repr(full["age_years_sum"])) / full["age_years_count"]
    out["mortality_full"] = Decimal(100 * full["deaths"]) / full["records"]
    for year in ("2023", "2024"):
        out[f"discharge_{year}"] = Decimal(agg["discharge_year"].get(int(year), 0))
    out["aih_repeated_excess"] = Decimal(agg["repeated_aih"]["excess_records"])
    out["aih_repeated_distinct"] = Decimal(agg["repeated_aih"]["distinct_numbers"])
    for key, scope in (("full", "full"), ("1", "ident_1")):
        t = agg["top_share"][key]
        out[f"top10_share_{scope}"] = Decimal(100 * t["top_cents"]) / t["total_cents"]
    groups = agg["proc_groups"]["1"]
    total = sum(g["val_tot_cents"] for g in groups.values())
    out["surgical_value_share_ident_1"] = (
        Decimal(100 * groups[SURGICAL_GROUP]["val_tot_cents"]) / total
    )
    out["clinical_value_share_ident_1"] = (
        Decimal(100 * groups[CLINICAL_GROUP]["val_tot_cents"]) / total
    )
    return out


def _quantum(historical: str) -> Decimal:
    return Decimal(1).scaleb(-len(historical.partition(".")[2]))


def status_for(
    spec: IndicatorSpec, reproduced: Decimal
) -> tuple[str, Decimal | None, Decimal | None]:
    """(status, reproduced rounded to the historical precision, difference)."""
    if spec.historical is None:
        return "🆕 novo", None, None
    hist = Decimal(spec.historical)
    rounded = reproduced.quantize(_quantum(spec.historical), rounding=ROUND_HALF_UP)
    diff = rounded - hist
    if diff == 0:
        return (
            ("✅ reproduzido" if spec.criterion == "documented" else "🟡 critério identificado"),
            rounded,
            diff,
        )
    if spec.divergence_explanation:
        return "🟠 divergente (explicado)", rounded, diff
    return "🔴 divergente", rounded, diff


@dataclass
class IndicatorResult:
    spec: IndicatorSpec
    reproduced: Decimal
    rounded: Decimal | None
    difference: Decimal | None
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self.spec) | {
            "reproduced": str(
                self.reproduced.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
            ),
            "rounded": None if self.rounded is None else str(self.rounded),
            "difference": None if self.difference is None else str(self.difference),
            "status": self.status,
        }


def reconcile(agg: dict[str, Any], params: dict[str, Any] | None = None) -> list[IndicatorResult]:
    vals = values(agg)
    results = []
    for spec in specs(params):
        status, rounded, diff = status_for(spec, vals[spec.id])
        results.append(IndicatorResult(spec, vals[spec.id], rounded, diff, status))
    return results


def run_indicators(processed: Path) -> dict[str, Any]:
    """Compute aggregates with both engines, check agreement, reconcile with the history."""
    df = pd.read_parquet(processed)
    agg_pd = aggregates_pandas(df)
    agg_sql = aggregates_sql(processed)
    disagreements = engines_agree(agg_pd, agg_sql)
    results = reconcile(agg_pd)
    return {
        "source": Path(processed).name,
        "engines_agree": not disagreements,
        "disagreements": disagreements,
        "aggregates": json.loads(json.dumps(agg_pd, default=str)),
        "indicators": [r.to_dict() for r in results],
    }


def _fmt(value: str | None, unit: str) -> str:
    if value is None:
        return "—"
    d = Decimal(value)
    if unit == "count":
        return f"{int(d):,}".replace(",", ".")
    text = f"{d:,}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("R$ " + text) if unit == "money" else (text + ("%" if unit == "pct" else ""))


def to_markdown(report: dict[str, Any]) -> str:
    """Generated reconciliation table (do not edit by hand)."""
    lines = [
        f"# Reconciliação dos indicadores — {report['source']}",
        "",
        "> Gerado por `hospital-analytics indicators`. Não editar manualmente.",
        "",
        "Pandas × DuckDB: **"
        + ("concordam em todos os agregados" if report["engines_agree"] else "DIVERGEM")
        + "**.",
        "",
        "| Indicador | Histórico | Reproduzido (arredondado) | Valor exato | Diferença | Status |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for r in report["indicators"]:
        lines.append(
            f"| {r['name']} | {_fmt(r['historical'], r['unit'])} | {_fmt(r['rounded'], r['unit'])} "
            f"| {r['reproduced']} | {r['difference'] or '—'} | {r['status']} |"
        )
    lines += ["", "## Definições", ""]
    for r in report["indicators"]:
        lines += [
            f"### {r['name']}",
            f"- **Definição:** {r['definition']}",
            f"- **Campos:** {r['source_fields']} · **Fórmula:** `{r['formula']}`",
            f"- **Denominador:** {r['denominator']} · **Filtros:** {r['filters']}",
        ]
        if r["note"]:
            lines.append(f"- **Nota:** {r['note']}")
        if r["divergence_explanation"]:
            lines.append(f"- **Divergência:** {r['divergence_explanation']}")
        lines.append("")
    return "\n".join(lines)


def write_report(report: dict[str, Any], directory: Path, stem: str) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    json_path, md_path = directory / f"{stem}.json", directory / f"{stem}.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", "utf-8")
    md_path.write_text(to_markdown(report), "utf-8")
    return json_path, md_path
