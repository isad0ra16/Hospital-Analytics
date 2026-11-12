"""Descriptive exploratory analyses (Phase 5) over the processed layer.

Everything here is descriptive: counts, rates with explicit denominators, distributions.
No association is presented as causal. Aggregates come from versioned SQL (``sql/analysis``);
rates are computed with ``Decimal``. Unit of analysis: AIH record (not patient).
"""

from __future__ import annotations

import json
import logging
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

from hospital_analytics.dictionary import CODEBOOK
from hospital_analytics.sql import connect, query

log = logging.getLogger(__name__)

TOP_PROCEDURES = 15
LOS_HISTOGRAM_CAP = 60
DIMENSION_CODEBOOK = {
    "IDENT": "IDENT",
    "ESPEC": "ESPEC",
    "CAR_INT": "CAR_INT",
    "COMPLEX": "COMPLEX",
    "PROC_REA_GROUP": "PROC_REA_GROUP",
    "SEXO": "SEXO",
    "RACA_COR": "RACA_COR",
}
AGE_GROUP_LABELS = {
    "00 <1": "< 1 ano",
    "01 1-4": "1–4",
    "02 5-14": "5–14",
    "03 15-29": "15–29",
    "04 30-44": "30–44",
    "05 45-59": "45–59",
    "06 60-74": "60–74",
    "07 75+": "75+",
}


def pct(numerator: int, denominator: int, places: str = "0.01") -> Decimal | None:
    """100 × n / d with half-up rounding; None when the denominator is zero."""
    if not denominator:
        return None
    return (Decimal(100 * numerator) / denominator).quantize(Decimal(places), ROUND_HALF_UP)


def ratio(numerator: int, denominator: int, places: str = "0.01") -> Decimal | None:
    if not denominator:
        return None
    return (Decimal(numerator) / denominator).quantize(Decimal(places), ROUND_HALF_UP)


def money(cents: int) -> Decimal:
    return (Decimal(cents) / 100).quantize(Decimal("0.01"))


def _enrich(row: dict[str, Any], total_records: int, total_cents: int) -> dict[str, Any]:
    """Add shares and rates (each with its denominator in the name) to an aggregate row."""
    return row | {
        "share_records_pct": pct(row["records"], total_records),
        "share_value_pct": pct(row["val_tot_cents"], total_cents),
        "mortality_per_100_records": pct(row["deaths"], row["records"]),
        "mean_los_days": ratio(row["dias_perm_sum"], row["records"]),
        "mean_value_brl": ratio(row["val_tot_cents"], 100 * row["records"]),
    }


def run_analysis(processed: Path) -> dict[str, Any]:
    con = connect(processed=processed)
    (hosp,) = query(con, "analysis/hospitals")
    total_records, total_cents = int(hosp["records"]), int(hosp["val_tot_cents"])

    dims: dict[str, list[dict[str, Any]]] = {}
    for row in query(con, "analysis/profile_by_dimension"):
        dim = row.pop("dimension")
        book = CODEBOOK[DIMENSION_CODEBOOK[dim]]
        row["label"] = book.codes.get(row["code"], "(sem rótulo)")
        dims.setdefault(dim, []).append(_enrich(row, total_records, total_cents))

    age_rows = query(con, "analysis/age_sex")
    by_age: dict[str, dict[str, int]] = {}
    for r in age_rows:
        agg = by_age.setdefault(
            r["age_group"],
            dict.fromkeys(("records", "deaths", "dias_perm_sum", "val_tot_cents"), 0),
        )
        for k in agg:
            agg[k] += int(r[k])
    age = [
        _enrich({"age_group": AGE_GROUP_LABELS.get(g, g), **v}, total_records, total_cents)
        for g, v in sorted(by_age.items())
    ]
    pyramid = [
        {
            "age_group": AGE_GROUP_LABELS.get(r["age_group"], r["age_group"]),
            "sex": CODEBOOK["SEXO"].codes.get(r["sex_code"], r["sex_code"]),
            "records": int(r["records"]),
            "deaths": int(r["deaths"]),
        }
        for r in age_rows
    ]

    procedures = [
        _enrich(r, total_records, total_cents)
        for r in query(con, "analysis/top_procedures", limit=TOP_PROCEDURES)
    ]
    lorenz = [
        {"records_pct": int(r["pct"]), "value_pct": pct(int(r["cum_cents"]), int(r["total_cents"]))}
        for r in query(con, "analysis/lorenz")
    ]
    # Same definition and query as the indicator top10_share_full (k = floor(0.1 n)).
    (top,) = query(con, "indicators/top_share", ident=None, fraction=0.1)
    return {
        "source": Path(processed).name,
        "unit_of_analysis": "registro de AIH (não paciente)",
        "totals": {"records": total_records, "val_tot_brl": money(total_cents)},
        "age": age,
        "pyramid": pyramid,
        "dimensions": dims,
        "top_procedures": procedures,
        "value_distribution": [
            {
                (k.removesuffix("_cents") + "_brl" if k.endswith("_cents") else k): (
                    money(v) if k.endswith("_cents") else v
                )
                for k, v in r.items()
            }
            for r in query(con, "analysis/value_distribution")
        ],
        "lorenz": lorenz,
        "top10_share_value_pct": pct(int(top["top_cents"]), int(top["total_cents"])),
        "hospitals": {
            "hospitals": int(hosp["hospitals"]),
            "top10_share_value_pct": pct(int(hosp["top10_hospitals_cents"]), total_cents),
            "top10_share_records_pct": pct(int(hosp["top10_hospitals_records"]), total_records),
        },
        "los_distribution": query(con, "analysis/los_distribution"),
        "los_histogram_ident_1": query(con, "analysis/los_histogram", cap=LOS_HISTOGRAM_CAP),
        "discharge_month": query(con, "analysis/discharge_month"),
    }


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def _br(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, Decimal):
        return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if isinstance(value, int):
        return f"{value:,}".replace(",", ".")
    return str(value)


def _table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> list[str]:
    out = ["| " + " | ".join(h for _, h in columns) + " |", "|" + "---|" * len(columns)]
    out += ["| " + " | ".join(_br(r.get(k)) for k, _ in columns) + " |" for r in rows]
    return out + [""]


PROFILE_COLUMNS = [
    ("records", "Registros"),
    ("share_records_pct", "% registros"),
    ("share_value_pct", "% valor"),
    ("mortality_per_100_records", "Óbitos/100 reg."),
    ("mean_los_days", "Perm. média (dias)"),
    ("mean_value_brl", "Valor médio (R$)"),
]
DIMENSION_TITLES = {
    "ESPEC": "Especialidade do leito (ESPEC)",
    "CAR_INT": "Caráter da internação (CAR_INT)",
    "COMPLEX": "Complexidade (COMPLEX)",
    "PROC_REA_GROUP": "Grupo SIGTAP do procedimento realizado",
    "IDENT": "Tipo de AIH (IDENT)",
    "SEXO": "Sexo",
    "RACA_COR": "Raça/cor",
}


def to_markdown(report: dict[str, Any]) -> str:
    """Generated analysis report (do not edit by hand)."""
    t = report["totals"]
    lines = [
        f"# Análises exploratórias — {report['source']}",
        "",
        "> Gerado por `hospital-analytics analysis`. Não editar manualmente. Análises"
        " **descritivas**:",
        "> nenhuma associação é causal. Unidade: registro de AIH. Rótulos de códigos: fonte",
        "> secundária (ver `docs/03_tratamento.md`). Permanência = `DIAS_PERM`.",
        "",
        f"Base: **{_br(t['records'])}** registros · **R$ {_br(t['val_tot_brl'])}**.",
        "",
        "## 1. Perfil demográfico (idade em anos corrigida por `COD_IDADE`)",
        "",
        "![Pirâmide etária](figures/age_pyramid.png)",
        "",
    ]
    lines += _table(report["age"], [("age_group", "Faixa etária"), *PROFILE_COLUMNS])
    for dim in ("SEXO", "RACA_COR"):
        lines += [f"### {DIMENSION_TITLES[dim]}", ""]
        lines += _table(
            report["dimensions"][dim], [("code", "Código"), ("label", "Rótulo"), *PROFILE_COLUMNS]
        )
    lines += ["## 2. Perfil hospitalar", ""]
    for dim in ("IDENT", "ESPEC", "CAR_INT", "COMPLEX", "PROC_REA_GROUP"):
        lines += [f"### {DIMENSION_TITLES[dim]}", ""]
        lines += _table(
            report["dimensions"][dim], [("code", "Código"), ("label", "Rótulo"), *PROFILE_COLUMNS]
        )
    lines += [f"### {TOP_PROCEDURES} procedimentos mais frequentes (código SIGTAP)", ""]
    lines += _table(report["top_procedures"], [("procedure", "PROC_REA"), *PROFILE_COLUMNS])
    lines += [
        "## 3. Mortalidade",
        "",
        "![Óbitos por 100 registros, por faixa etária](figures/mortality_by_age.png)",
        "",
        "Taxas = óbitos por 100 registros de AIH do grupo (denominador: registros do grupo)."
        " Ver as",
        "colunas *Óbitos/100 reg.* nas tabelas acima. Diferenças entre grupos refletem casemix,",
        "tipo de leito e complexidade; **não** indicam qualidade assistencial nem causalidade.",
        "",
        "## 4. Análise financeira",
        "",
        "![Curva de Lorenz do VAL_TOT](figures/lorenz.png)",
        "",
    ]
    lines += _table(
        report["value_distribution"],
        [("scope", "Base"), ("records", "Registros"), ("zero_value", "VAL_TOT = 0"),
         ("p25_brl", "P25 (R$)"), ("p50_brl", "Mediana (R$)"), ("p75_brl", "P75 (R$)"),
         ("p90_brl", "P90 (R$)"), ("p99_brl", "P99 (R$)"), ("max_brl", "Máx. (R$)")],
    )  # fmt: skip
    h = report["hospitals"]
    lorenz = {p["records_pct"]: p["value_pct"] for p in report["lorenz"]}
    lines += [
        f"- Os 50% de registros de menor valor somam **{_br(lorenz[50])}%** do `VAL_TOT`; os"
        " 90% de menor",
        f"  valor somam {_br(lorenz[90])}%. Os 10% de maior valor (k = ⌊0,1·n⌋, mesmo critério do",
        f"  indicador) concentram **{_br(report['top10_share_value_pct'])}%** — ver"
        " `docs/05_validacao.md` sobre a referência histórica de 58,20% (não reproduzida).",
        f"- **{h['hospitals']}** estabelecimentos (CNES); os 10 de maior valor concentram "
        f"**{_br(h['top10_share_value_pct'])}%** do valor e"
        f" {_br(h['top10_share_records_pct'])}% dos registros.",
        "",
        "## 5. Permanência hospitalar",
        "",
        "![Distribuição de DIAS_PERM — AIH tipo 1](figures/los_histogram_ident_1.png)",
        "",
    ]
    lines += _table(
        report["los_distribution"],
        [("IDENT", "IDENT"), ("records", "Registros"), ("zero_days", "0 dias"), ("p25", "P25"),
         ("p50", "Mediana"), ("p75", "P75"), ("p90", "P90"), ("p99", "P99"), ("max_days", "Máx."),
         ("upper_fence", "Limite Tukey"), ("above_upper_fence", "Acima do limite")],
    )  # fmt: skip
    lines += [
        "Valores acima do limite de Tukey (Q3 + 1,5·IIQ) são **contados, não removidos**. Na"
        " AIH tipo 5,",
        "`DIAS_PERM` mede o período coberto pela AIH (máximo 31 dias), não a internação inteira.",
        "",
        "## 6. Distribuição temporal das saídas",
        "",
    ]
    lines += _table(
        report["discharge_month"],
        [("discharge_month", "Mês de saída"), ("IDENT", "IDENT"), ("records", "Registros")],
    )
    lines += [
        "Todos os registros têm competência 2024-01; 40% das saídas ocorreram em 2023.",
        "",
        "## 7. Qualidade dos dados",
        "",
        "Ver [`reports/audit/audit_rdrj2401.md`](../audit/audit_rdrj2401.md) e"
        " `docs/05_validacao.md`.",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Charts (static PNG, light surface; reference palette from the dataviz method)
# ---------------------------------------------------------------------------
SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
SERIES_1, SERIES_2 = "#2a78d6", "#eb6834"


def _style(ax, title: str, subtitle: str) -> None:
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK_2, labelsize=9, length=0)
    ax.figure.text(0.02, 0.97, title, fontsize=12, fontweight="bold", color=INK, va="top")
    ax.figure.text(0.02, 0.915, subtitle, fontsize=9, color=INK_2, va="top")
    ax.figure.text(
        0.02, 0.015,
        "Fonte: SIH/SUS (DATASUS), RD RJ competência 2024-01. Unidade: registro de AIH.",
        fontsize=7.5, color=INK_2,
    )  # fmt: skip


def render_charts(report: dict[str, Any], directory: Path) -> list[Path]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    directory.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "svg.hashsalt": "hospital-analytics"})
    paths = []

    def save(fig, name: str) -> None:
        path = directory / name
        fig.savefig(path, dpi=150, facecolor=SURFACE, metadata={"Software": None})
        plt.close(fig)
        paths.append(path)

    # 1. Age pyramid (two series: sex). Legend + direct labels on the side headers.
    groups = [AGE_GROUP_LABELS[k] for k in AGE_GROUP_LABELS]
    male = {g: 0 for g in groups}
    female = {g: 0 for g in groups}
    for r in report["pyramid"]:
        target = male if r["sex"] == "Masculino" else female
        target[r["age_group"]] += r["records"]
    fig, ax = plt.subplots(figsize=(8, 4.8), facecolor=SURFACE)
    fig.subplots_adjust(left=0.12, right=0.97, top=0.82, bottom=0.14)
    y = range(len(groups))
    ax.barh(y, [-male[g] for g in groups], height=0.72, color=SERIES_1, label="Masculino")
    ax.barh(y, [female[g] for g in groups], height=0.72, color=SERIES_2, label="Feminino")
    ax.set_yticks(list(y), groups)
    limit = max(max(male.values()), max(female.values())) * 1.08  # symmetric axis
    ax.set_xlim(-limit, limit)
    ticks = [t for t in ax.get_xticks() if -limit <= t <= limit]
    ax.set_xticks(ticks, [f"{abs(int(t)):,}".replace(",", ".") for t in ticks])
    ax.axvline(0, color=INK_2, linewidth=0.8)
    ax.grid(axis="x", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.legend(loc="lower right", frameon=False, fontsize=9, labelcolor=INK_2)
    _style(
        ax, "Internações por faixa etária e sexo", "Registros de AIH · idade em anos (COD_IDADE)"
    )
    save(fig, "age_pyramid.png")

    # 2. Mortality per 100 records by age group (one series: no legend; title names it).
    fig, ax = plt.subplots(figsize=(8, 4.6), facecolor=SURFACE)
    fig.subplots_adjust(left=0.12, right=0.95, top=0.82, bottom=0.14)
    rates = [float(r["mortality_per_100_records"]) for r in report["age"]]
    labels = [r["age_group"] for r in report["age"]]
    ax.barh(range(len(rates)), rates, height=0.66, color=SERIES_1)
    for i, v in enumerate(rates):
        ax.text(v + 0.3, i, f"{v:.1f}".replace(".", ","), va="center", fontsize=8.5, color=INK_2)
    ax.set_yticks(range(len(labels)), labels)
    ax.grid(axis="x", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    _style(
        ax,
        "Óbitos por 100 registros, por faixa etária",
        "Taxa bruta descritiva · denominador: registros da faixa",
    )
    save(fig, "mortality_by_age.png")

    # 3. Lorenz curve (one series + equality reference).
    fig, ax = plt.subplots(figsize=(6.4, 5.4), facecolor=SURFACE)
    fig.subplots_adjust(left=0.13, right=0.95, top=0.84, bottom=0.14)
    xs = [p["records_pct"] for p in report["lorenz"]]
    ys = [float(p["value_pct"]) for p in report["lorenz"]]
    ax.plot([0, 100], [0, 100], color=INK_2, linewidth=1, linestyle=(0, (4, 3)))
    ax.text(62, 70, "igualdade", color=INK_2, fontsize=8.5, rotation=40)
    ax.plot(xs, ys, color=SERIES_1, linewidth=2)
    top_share = f"{report['top10_share_value_pct']:.2f}".replace(".", ",")
    ax.annotate(
        f"10% de maior valor:\n{top_share}% do VAL_TOT",
        xy=(90, ys[xs.index(90)]), xytext=(38, 58), fontsize=8.5, color=INK,
        arrowprops={"arrowstyle": "-", "color": INK_2, "linewidth": 0.8},
    )  # fmt: skip
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_xlabel("% acumulado de registros (menor → maior valor)", color=INK_2, fontsize=9)
    ax.set_ylabel("% acumulado do VAL_TOT", color=INK_2, fontsize=9)
    ax.grid(color=GRID, linewidth=0.6)
    _style(
        ax, "Concentração do gasto (curva de Lorenz)", "VAL_TOT por registro de AIH · base completa"
    )
    save(fig, "lorenz.png")

    # 4. LOS histogram, AIH type 1 (one series).
    fig, ax = plt.subplots(figsize=(8, 4.4), facecolor=SURFACE)
    fig.subplots_adjust(left=0.1, right=0.97, top=0.82, bottom=0.17)
    hist = report["los_histogram_ident_1"]
    ax.bar([h["days"] for h in hist], [h["records"] for h in hist], width=0.8, color=SERIES_1)
    ax.set_xlabel(f"DIAS_PERM (último grupo = {LOS_HISTOGRAM_CAP}+ dias)", color=INK_2, fontsize=9)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    yt = ax.get_yticks()
    ax.set_yticks(yt, [f"{int(t):,}".replace(",", ".") for t in yt])
    _style(
        ax, "Permanência hospitalar — AIH tipo 1", "Registros por dias de permanência (DIAS_PERM)"
    )
    save(fig, "los_histogram_ident_1.png")
    return paths


def write_report(report: dict[str, Any], directory: Path, stem: str) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    json_path, md_path = directory / f"{stem}.json", directory / f"{stem}.md"
    json_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n", "utf-8", newline="\n"
    )
    md_path.write_text(to_markdown(report), "utf-8", newline="\n")
    return [json_path, md_path, *render_charts(report, directory / "figures")]
