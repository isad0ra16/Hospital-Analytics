"""Power BI Project (PBIP) generated from the model schema: TMDL semantic model + PBIR report.

Single sources of truth: tables, columns and relationships come from ``powerbi.TABLES`` /
``powerbi.RELATIONSHIPS``; measures from ``docs/powerbi/medidas.dax``; report pages from
``PAGES`` below. Output: ``powerbi/HospitalAnalytics.pbip`` and its two item folders. The project
holds no data: Power BI Desktop imports the CSV files from the folder in the ``PastaDados``
parameter when the model is refreshed.

Identifiers (lineage tags, visual names) are deterministic UUIDv5 values, so regenerating the
project produces the same files (clean diffs). JSON files declare the public Microsoft schemas
they follow; ``tests/test_pbip.py`` validates them against vendored copies of those schemas.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hospital_analytics.powerbi import ALL_TABLES, CUR, DATE, INT, NUM, RELATIONSHIPS, TXT, Table

PROJECT = "HospitalAnalytics"
NAMESPACE = uuid.UUID("6f1c2b0e-7d4a-4c1e-9a55-3b8d2f0c9e11")
MEASURES_TABLE = "_Medidas"
DATA_FOLDER_PLACEHOLDER = "C:\\Hospital-Analytics-Codigo\\data\\powerbi\\"
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/"
SCHEMAS = {
    "pbip": SCHEMA + "pbip/pbipProperties/1.0.0/schema.json",
    "pbir": SCHEMA + "item/report/definitionProperties/2.0.0/schema.json",
    "pbism": SCHEMA + "item/semanticModel/definitionProperties/1.0.0/schema.json",
    "editor": SCHEMA + "item/semanticModel/editorSettings/1.0.0/schema.json",
    "report": SCHEMA + "item/report/definition/report/3.3.0/schema.json",
    "version": SCHEMA + "item/report/definition/versionMetadata/1.0.0/schema.json",
    "pages": SCHEMA + "item/report/definition/pagesMetadata/1.1.0/schema.json",
    "page": SCHEMA + "item/report/definition/page/2.1.0/schema.json",
    "visual": SCHEMA + "item/report/definition/visualContainer/2.13.0/schema.json",
}
PAGE_W, PAGE_H = 1280, 720
FOOTER = (
    "Fonte: SIH/SUS (DATASUS), arquivo RD do RJ, competência 2024-01 · nomes: SIGTAP 2024-01, "
    "IBGE, CNES e tabelas TabWin do SIH · unidade: registro de AIH (não é paciente)"
)


def tag(*parts: str) -> str:
    return str(uuid.uuid5(NAMESPACE, "/".join(parts)))


# ---------------------------------------------------------------------------
# Measures parsed from docs/powerbi/medidas.dax
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Measure:
    name: str
    expression: str
    description: str
    folder: str
    format_string: str | None


_SECTION = re.compile(r"^// ---- (.+?) -+\s*$")
_HEADER = re.compile(r"^(\S.*?) =\s*(.*)$")


def measure_format(comment: str) -> str | None:
    """Format string from the ``Formato:`` note of a measure (the file's own convention)."""
    explicit = re.search(r"Formato: `([^`]+)`", comment)
    if explicit:
        return explicit.group(1)
    note = comment.lower()
    if "formato: moeda" in note:
        return "R$ #,0.00"
    if "formato: porcentagem" in note:
        return "0.00%"
    if "formato: número inteiro" in note:
        return "#,0"
    if "formato: decimal" in note:
        return "#,0.00"
    return None


def parse_measures(text: str) -> list[Measure]:
    """Measures of ``medidas.dax``: comments, ``Name =`` line, expression up to a blank line."""
    measures: list[Measure] = []
    folder, comments, lines = "Medidas", [], iter(text.splitlines())
    for line in lines:
        if section := _SECTION.match(line):
            folder, comments = section.group(1).strip(), []
        elif line.startswith("//"):
            comments.append(line[2:].strip())
        elif not line.strip():
            comments = []
        elif header := _HEADER.match(line):
            body = [header.group(2)] if header.group(2) else []
            for expr_line in lines:
                if not expr_line.strip():
                    break
                body.append(expr_line.rstrip())
            comment = " ".join(c for c in comments if c and not set(c) <= {"=", "-"})
            measures.append(
                Measure(header.group(1).strip(), "\n".join(body), comment, folder,
                        measure_format(comment))
            )  # fmt: skip
            comments = []
        else:
            raise ValueError(f"medidas.dax: unexpected line {line!r}")
    names = [m.name for m in measures]
    if len(names) != len(set(names)):
        raise ValueError("medidas.dax: duplicated measure names")
    return measures


# ---------------------------------------------------------------------------
# TMDL semantic model
# ---------------------------------------------------------------------------
TMDL_TYPE = {TXT: "string", INT: "int64", DATE: "dateTime", NUM: "double", CUR: "decimal"}
HIDDEN_FACT_COLUMNS = True  # the fact is used only through measures
SORT_BY = {
    ("dim_perfil_demografico", "faixa_etaria"): "faixa_etaria_ordem",
    ("dim_mes", "ano_mes"): "ano_mes_ordem",
    ("dim_mes", "mes_abrev"): "mes_num",
    ("dim_diagnostico", "capitulo"): "capitulo_ordem",
}
DATA_CATEGORY = {
    ("dim_municipio_residencia", "municipio_residencia_nome"): "City",
    ("dim_municipio_residencia", "uf_residencia_sigla"): "StateOrProvince",
    ("dim_estabelecimento", "municipio_estabelecimento_nome"): "City",
    ("dim_estabelecimento", "uf_estabelecimento_sigla"): "StateOrProvince",
}
PROVENANCE_COLUMNS = {"fonte", "descricao", "grupo_descricao", "grupo_fonte", "sexo_descricao",
                      "raca_cor_descricao", "fonte_oficial"}  # fmt: skip


def tmdl_name(name: str) -> str:
    return (
        name
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name)
        else "'" + name.replace("'", "''") + "'"
    )


def _description(text: str, indent: str) -> list[str]:
    return [f"{indent}/// {line}" for line in _wrap(text)] if text else []


def _wrap(text: str, width: int = 96) -> list[str]:
    words, lines, current = text.split(), [], ""
    for word in words:
        if current and len(current) + len(word) + 1 > width:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    return lines + ([current] if current else [])


def _expression(expression: str, indent: str) -> list[str]:
    return [f"{indent}{line}" if line.strip() else "" for line in expression.splitlines()]


def column_format(table: Table, column) -> str | None:
    if column.m_type == CUR:
        return "R$ #,0.00"
    if column.m_type == DATE:
        return "yyyy-mm"
    if column.m_type == INT:
        return "0"
    if column.m_type == NUM:
        return (
            "0.00%" if table.name == "aux_curva_lorenz" and column.name != "percentil" else "#,0.00"
        )
    return None


def table_tmdl(table: Table, power_query: str) -> str:
    out = _description(table.grain, "")
    out += [f"table {tmdl_name(table.name)}", f"\tlineageTag: {tag('table', table.name)}"]
    if table.name == "dim_mes":
        out.append("\tdataCategory: Time")
    out.append("")
    for column in table.columns:
        out += _description(column.description + f" (origem: {column.origin})", "\t")
        out += [f"\tcolumn {tmdl_name(column.name)}", f"\t\tdataType: {TMDL_TYPE[column.m_type]}"]
        if table.name == "dim_mes" and column.name == "mes":
            out.append("\t\tisKey")
        if fmt := column_format(table, column):
            out.append(f"\t\tformatString: {fmt}")
        hidden = (table.name == "fato_registro_aih" and HIDDEN_FACT_COLUMNS) or (
            column.name.endswith("_ordem") and column.name != "capitulo_ordem"
        )
        if hidden:
            out.append("\t\tisHidden")
        if column.name in PROVENANCE_COLUMNS or column.name.endswith("_fonte"):
            out.append("\t\tdisplayFolder: Proveniência e fonte secundária")
        if category := DATA_CATEGORY.get((table.name, column.name)):
            out.append(f"\t\tdataCategory: {category}")
        if sort := SORT_BY.get((table.name, column.name)):
            out.append(f"\t\tsortByColumn: {sort}")
        out += [
            f"\t\tlineageTag: {tag('column', table.name, column.name)}",
            "\t\tsummarizeBy: none",
            f"\t\tsourceColumn: {column.name}",
            "",
            "\t\tannotation SummarizationSetBy = User",
        ]
        if column.m_type == DATE:
            out += ["", "\t\tannotation UnderlyingDateTimeDataType = Date"]
        out.append("")
    out += [f"\tpartition {tmdl_name(table.name)} = m", "\t\tmode: import", "\t\tsource ="]
    out += _expression(power_query, "\t\t\t")
    out += ["", "\tannotation PBI_ResultType = Table", ""]
    return "\n".join(out)


def measures_table_tmdl(measures: list[Measure]) -> str:
    out = _description(
        "Medidas DAX do dashboard (docs/powerbi/medidas.dax). Unidade: registro de AIH.", ""
    )
    out += [f"table {MEASURES_TABLE}", f"\tlineageTag: {tag('table', MEASURES_TABLE)}", ""]
    for m in measures:
        out += _description(m.description, "\t")
        first, *rest = m.expression.splitlines() or [""]
        if rest:
            out.append(f"\tmeasure {tmdl_name(m.name)} =")
            out += _expression(m.expression, "\t\t\t")
        else:
            out.append(f"\tmeasure {tmdl_name(m.name)} = {first}")
        if m.format_string:
            out.append(f"\t\tformatString: {m.format_string}")
        out += [f"\t\tdisplayFolder: {m.folder}", f"\t\tlineageTag: {tag('measure', m.name)}", ""]
    out += [
        "\tcolumn Coluna",
        "\t\tdataType: string",
        "\t\tisHidden",
        f"\t\tlineageTag: {tag('column', MEASURES_TABLE, 'Coluna')}",
        "\t\tsummarizeBy: none",
        "\t\tsourceColumn: Coluna",
        "",
        "\t\tannotation SummarizationSetBy = Automatic",
        "",
        f"\tpartition {MEASURES_TABLE} = m",
        "\t\tmode: import",
        "\t\tsource =",
        "\t\t\t#table(type table [Coluna = text], {})",
        "",
        "\tannotation PBI_ResultType = Table",
        "",
    ]
    return "\n".join(out)


def power_query_blocks() -> dict[str, str]:
    """The M query of each table, as in docs/powerbi/consultas_power_query.pq."""
    from hospital_analytics.powerbi import power_query_m

    blocks: dict[str, str] = {}
    for chunk in power_query_m().split("// ---- ")[1:]:
        name, _, body = chunk.partition(" ----\n")
        blocks[name] = body.strip()
    return blocks


def semantic_model_files(measures: list[Measure]) -> dict[str, str]:
    blocks = power_query_blocks()
    tables = list(ALL_TABLES)
    files = {
        "definition.pbism": _json({"$schema": SCHEMAS["pbism"], "version": "4.0", "settings": {}}),
        ".pbi/editorSettings.json": _json(
            {
                "$schema": SCHEMAS["editor"],
                "autodetectRelationships": False,
                "typeDetectionEnabled": False,
                "relationshipImportEnabled": False,
            }
        ),
        "definition/database.tmdl": "database\n\tcompatibilityLevel: 1567\n\n",
    }
    order = json.dumps(["PastaDados", *[t.name for t in tables], MEASURES_TABLE])
    files["definition/model.tmdl"] = "\n".join(
        [
            "model Model",
            "\tculture: pt-BR",
            "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
            "\tsourceQueryCulture: pt-BR",
            "\tdataAccessOptions",
            "\t\tlegacyRedirects",
            "\t\treturnErrorValuesAsNull",
            "",
            "annotation __PBI_TimeIntelligenceEnabled = 0",
            "",
            f"annotation PBI_QueryOrder = {order}",
            "",
            *[f"ref table {tmdl_name(t.name)}" for t in [*tables]],
            f"ref table {MEASURES_TABLE}",
            "",
        ]
    )
    files["definition/expressions.tmdl"] = "\n".join(
        [
            "/// Pasta com os CSV de data/powerbi (caminho completo, terminado em \\).",
            f'expression PastaDados = "{DATA_FOLDER_PLACEHOLDER}" meta [IsParameterQuery=true, '
            'Type="Text", IsParameterQueryRequired=true]',
            f"\tlineageTag: {tag('expression', 'PastaDados')}",
            "",
            "\tannotation PBI_ResultType = Text",
            "",
        ]
    )
    rel = []
    for fact_col, dim, dim_col, _, active in RELATIONSHIPS:
        rel.append(f"relationship {tag('relationship', fact_col, dim, dim_col)}")
        if not active:
            rel.append("\tisActive: false")
        rel += [f"\tfromColumn: fato_registro_aih.{fact_col}", f"\ttoColumn: {dim}.{dim_col}", ""]
    files["definition/relationships.tmdl"] = "\n".join(rel)
    for t in tables:
        files[f"definition/tables/{t.name}.tmdl"] = table_tmdl(t, blocks[t.name])
    files[f"definition/tables/{MEASURES_TABLE}.tmdl"] = measures_table_tmdl(measures)
    return files


# ---------------------------------------------------------------------------
# PBIR report: pages and visuals
# ---------------------------------------------------------------------------
def lit(value: Any) -> dict:
    if isinstance(value, bool):
        text = "true" if value else "false"
    elif isinstance(value, int):
        text = f"{value}L"
    elif isinstance(value, float):
        text = f"{value}D"
    else:
        text = "'" + str(value).replace("'", "''") + "'"
    return {"expr": {"Literal": {"Value": text}}}


@dataclass(frozen=True)
class Field:
    table: str
    name: str
    label: str | None = None

    @property
    def is_measure(self) -> bool:
        return self.table == MEASURES_TABLE

    def expression(self) -> dict:
        kind = "Measure" if self.is_measure else "Column"
        return {kind: {"Expression": {"SourceRef": {"Entity": self.table}}, "Property": self.name}}

    def projection(self) -> dict:
        out = {"field": self.expression(), "queryRef": f"{self.table}.{self.name}",
               "nativeQueryRef": self.name}  # fmt: skip
        if self.label:
            out["displayName"] = self.label
        return out


def M(name: str, label: str | None = None) -> Field:  # noqa: N802 - reads like the DAX name
    return Field(MEASURES_TABLE, name, label)


def C(table: str, name: str, label: str | None = None) -> Field:  # noqa: N802
    return Field(table, name, label)


@dataclass(frozen=True)
class Visual:
    kind: str  # card, barChart, clusteredBarChart, clusteredColumnChart, lineChart, tableEx, ...
    x: int
    y: int
    w: int
    h: int
    roles: dict[str, tuple[Field, ...]] = field(default_factory=dict)
    title: str | None = None
    subtitle: str | None = None
    text: tuple[tuple[str, dict], ...] = ()  # textbox paragraphs: (text, textStyle)
    sort: tuple[Field, str] | None = None  # (field, "Ascending" | "Descending")
    sync: str | None = None  # slicer sync group
    labels: bool = False  # data labels


@dataclass(frozen=True)
class Page:
    name: str
    title: str
    subtitle: str
    visuals: tuple[Visual, ...]


def textbox(x, y, w, h, *paragraphs: tuple[str, dict]) -> Visual:
    return Visual("textbox", x, y, w, h, text=paragraphs)


H1 = {"fontWeight": "bold", "fontSize": "20pt"}
H2 = {"fontSize": "11pt", "color": "#5A5A5A"}
NOTE = {"fontSize": "9pt", "color": "#5A5A5A"}
BODY = {"fontSize": "10pt"}

SLICERS_X, SLICERS_W = 1036, 220


def slicers() -> tuple[Visual, ...]:
    """Slicers synchronised across pages (right-hand panel)."""
    specs = [
        ("Tipo de AIH", C("dim_tipo_aih", "descricao_oficial", "Tipo de AIH")),
        ("Caráter", C("dim_carater", "descricao_oficial", "Caráter")),
        ("Complexidade", C("dim_complexidade", "descricao_oficial", "Complexidade")),
        ("Faixa etária", C("dim_perfil_demografico", "faixa_etaria", "Faixa etária")),
        ("Sexo", C("dim_perfil_demografico", "sexo_descricao_oficial", "Sexo")),
    ]
    return tuple(
        Visual("slicer", SLICERS_X, 80 + i * 112, SLICERS_W, 100, {"Values": (f,)}, title=title,
               sync=f"filtro_{f.name}_{f.table}")
        for i, (title, f) in enumerate(specs)
    )  # fmt: skip


def frame(page_title: str, subtitle: str) -> tuple[Visual, ...]:
    return (
        textbox(24, 8, 1000, 64, (page_title, H1), (subtitle, H2)),
        textbox(24, 684, 1232, 30, (FOOTER, NOTE)),
        *slicers(),
    )


def bar(
    x,
    y,
    w,
    h,
    category: Field,
    value: Field,
    title,
    subtitle=None,
    *,
    kind="clusteredBarChart",
    tooltips: tuple[Field, ...] = (),
    sort_by_value=True,
) -> Visual:
    roles = {"Category": (category,), "Y": (value,)}
    if tooltips:
        roles["Tooltips"] = tooltips
    sort = (value, "Descending") if sort_by_value else (category, "Ascending")
    return Visual(kind, x, y, w, h, roles, title=title, subtitle=subtitle, sort=sort, labels=True)


def card(x, y, w, measure: Field, title: str, subtitle: str | None = None) -> Visual:
    return Visual("card", x, y, w, 96, {"Values": (measure,)}, title=title, subtitle=subtitle)


def cards(y: int, specs: list[tuple[str, str, str | None]], x0: int = 24, total_w: int = 1000):
    gap = 12
    w = (total_w - gap * (len(specs) - 1)) // len(specs)
    return tuple(card(x0 + i * (w + gap), y, w, M(m), t, s) for i, (m, t, s) in enumerate(specs))


PAGES: tuple[Page, ...] = (
    Page(
        "p1_visao_geral",
        "1. Visão geral",
        "Internações do SUS no estado do Rio de Janeiro — registros de AIH processados em "
        "janeiro de 2024",
        (
            *cards(
                80,
                [
                    ("Registros de AIH", "Registros de AIH", "1 registro ≠ 1 paciente"),
                    ("AIHs distintas", "AIHs distintas", "números de AIH"),
                    ("Valor total", "Valor total aprovado", "VAL_TOT, R$"),
                    ("Valor médio por registro", "Valor médio", "por registro"),
                    ("Permanência média (dias)", "Permanência média", "dias, DIAS_PERM"),
                    ("Mortalidade hospitalar (razão)", "Mortalidade hospitalar", "taxa bruta"),
                ],
            ),  # fmt: skip
            bar(
                24,
                188,
                488,
                220,
                C("dim_tipo_aih", "descricao_oficial", "Tipo de AIH"),
                M("Registros de AIH"),
                "Registros por tipo de AIH",
                "Longa permanência: apresentações sucessivas de uma internação",
            ),
            bar(
                524,
                188,
                500,
                220,
                C("dim_mes", "ano_mes", "Mês de saída"),
                M("Registros de AIH"),
                "Registros por mês de saída",
                "Competência 2024-01: o mês de saída NÃO é série histórica",
                kind="clusteredColumnChart",
                sort_by_value=False,
            ),
            bar(
                24,
                420,
                488,
                252,
                C("dim_complexidade", "descricao_oficial", "Complexidade"),
                M("Valor total"),
                "Valor aprovado por complexidade",
            ),
            textbox(
                524,
                420,
                500,
                252,
                ("Como ler este painel", {"fontWeight": "bold", "fontSize": "12pt"}),
                (
                    "• A unidade é o registro de AIH do arquivo RD: uma internação longa gera "
                    "vários registros e não há identificador de paciente.",
                    BODY,
                ),
                (
                    "• Competência 2024-01 é o mês de processamento: cada mês de saída contém "
                    "apenas o que foi apresentado nessa competência.",
                    BODY,
                ),
                (
                    "• A mortalidade é bruta (sem ajuste de risco): diferenças refletem o perfil "
                    "dos casos, não a qualidade do cuidado.",
                    BODY,
                ),
                (
                    "• Os totais conferem com o pipeline validado: 73.046 registros e "
                    "R$ 125.440.636,13.",
                    BODY,
                ),
            ),
            *frame("1. Visão geral", "Internações do SUS no RJ · competência 2024-01"),
        ),
    ),
    Page(
        "p2_perfil",
        "2. Perfil e origem",
        "Perfil demográfico dos registros e município de residência",
        (
            Visual(
                "barChart",
                24,
                80,
                520,
                380,
                {
                    "Category": (C("dim_perfil_demografico", "faixa_etaria", "Faixa etária"),),
                    "Y": (
                        M("Registros - masculino (pirâmide)", "Masculino"),
                        M("Registros - feminino (pirâmide)", "Feminino"),
                    ),
                },
                title="Registros por faixa etária e sexo",
                subtitle="Perfil dos REGISTROS (o RD não identifica pacientes)",
                sort=(C("dim_perfil_demografico", "faixa_etaria"), "Descending"),
            ),
            bar(
                556,
                80,
                468,
                270,
                C("dim_perfil_demografico", "raca_cor_descricao_oficial", "Raça/cor"),
                M("% dos registros"),
                "Registros por raça/cor (%)",
                'Inclui "sem informação"',
            ),
            *cards(
                362,
                [
                    ("Idade média (anos)", "Idade média", "anos, pela unidade COD_IDADE"),
                    (
                        "% residentes de outro município",
                        "Outro município",
                        "residência ≠ estabelecimento",
                    ),
                    ("% residentes fora do RJ", "Fora do RJ", "UF de residência"),
                ],
                x0=556,
                total_w=468,
            ),  # fmt: skip
            bar(
                24,
                472,
                1000,
                200,
                C(
                    "dim_municipio_residencia",
                    "municipio_residencia_rotulo",
                    "Município de residência",
                ),
                M("Registros - top 10 municípios de residência", "Registros"),
                "Top 10 municípios de residência",
                "Nomes: IBGE (código SIH de 6 dígitos)",
                kind="clusteredColumnChart",
            ),
            *frame("2. Perfil e origem", "Perfil dos registros de AIH e município de residência"),
        ),
    ),
    Page(
        "p3_internacoes",
        "3. Internações e permanência",
        "Especialidade do leito, caráter da internação, procedimentos e permanência",
        (
            bar(
                24,
                80,
                330,
                300,
                C("dim_especialidade", "descricao_oficial", "Especialidade"),
                M("Registros de AIH"),
                "Registros por especialidade do leito",
            ),
            bar(
                366,
                80,
                330,
                300,
                C("dim_especialidade", "descricao_oficial", "Especialidade"),
                M("Permanência média (dias)"),
                "Permanência média por especialidade (dias)",
                "Leia por tipo de AIH: na longa permanência, DIAS_PERM é o período do registro",
            ),
            bar(
                708,
                80,
                316,
                190,
                C("dim_carater", "descricao_oficial", "Caráter"),
                M("Registros de AIH"),
                "Registros por caráter da internação",
            ),
            *cards(
                282,
                [
                    (
                        "Permanência média - AIH principal",
                        "Permanência — AIH principal",
                        "dias, tipo 1",
                    ),
                    ("Registros de longa permanência", "Longa permanência", "registros tipo 5"),
                ],
                x0=708,
                total_w=316,
            ),  # fmt: skip
            Visual(
                "tableEx",
                24,
                392,
                1000,
                280,
                {
                    "Values": (
                        C("dim_procedimento", "procedimento_nome", "Procedimento (SIGTAP)"),
                        C("dim_procedimento", "grupo_nome_sigtap", "Grupo"),
                        M("Registros de AIH", "Registros"),
                        M("Valor total", "Valor"),
                        M("Permanência média (dias)", "Permanência média"),
                        M("Mortalidade hospitalar (razão)", "Mortalidade"),
                    )
                },
                title="Procedimentos realizados — ordenados por número de registros",
                subtitle="Nomes oficiais do SIGTAP, competência 2024-01",
                sort=(M("Registros de AIH"), "Descending"),
            ),
            *frame("3. Internações e permanência", "Leito, caráter, procedimentos e permanência"),
        ),
    ),
    Page(
        "p4_mortalidade",
        "4. Mortalidade hospitalar",
        "Mortalidade hospitalar bruta por perfil e diagnóstico",
        (
            *cards(
                80,
                [
                    ("Óbitos", "Óbitos", "registros com MORTE = 1"),
                    (
                        "Mortalidade hospitalar (razão)",
                        "Mortalidade hospitalar",
                        "todos os registros",
                    ),
                    (
                        "Mortalidade hospitalar - AIH principal (razão)",
                        "Mortalidade — AIH principal",
                        "apenas tipo 1",
                    ),
                ],
                total_w=640,
            ),  # fmt: skip
            textbox(
                676,
                80,
                348,
                96,
                (
                    "Taxa BRUTA, por registro, sem ajuste por idade, gravidade ou casemix. Não "
                    "compare estabelecimentos ou grupos como medida de qualidade; não há leitura "
                    "causal.",
                    {"fontSize": "10pt", "color": "#B03A2E"},
                ),
            ),
            bar(
                24,
                188,
                488,
                236,
                C("dim_perfil_demografico", "faixa_etaria", "Faixa etária"),
                M("Mortalidade hospitalar (razão)", "Mortalidade"),
                "Mortalidade por faixa etária",
                "Tooltip: registros (denominador) e óbitos",
                tooltips=(M("Registros de AIH"), M("Óbitos")),
                sort_by_value=False,
            ),
            bar(
                524,
                188,
                500,
                236,
                C("dim_carater", "descricao_oficial", "Caráter"),
                M("Mortalidade hospitalar (razão)", "Mortalidade"),
                "Mortalidade por caráter",
                tooltips=(M("Registros de AIH"), M("Óbitos")),
            ),
            bar(
                24,
                436,
                488,
                236,
                C("dim_diagnostico", "capitulo", "Capítulo CID-10"),
                M("Mortalidade hospitalar (razão)", "Mortalidade"),
                "Mortalidade por capítulo CID-10 do diagnóstico principal",
                tooltips=(M("Registros de AIH"), M("Óbitos")),
            ),
            bar(
                524,
                436,
                500,
                236,
                C("dim_diagnostico", "diagnostico_rotulo", "Diagnóstico"),
                M("Registros - top 10 diagnósticos", "Registros"),
                "Top 10 diagnósticos principais (registros)",
                "Descrições: SIGTAP tb_cid 2024-01",
                tooltips=(M("Óbitos"), M("Mortalidade hospitalar (razão)")),
            ),
            *frame("4. Mortalidade hospitalar", "Taxa bruta por registro — sem ajuste de risco"),
        ),
    ),
    Page(
        "p5_financeiro",
        "5. Análise financeira",
        "Valor aprovado (VAL_TOT) e sua concentração",
        (
            *cards(
                80,
                [
                    ("Valor total", "Valor total aprovado", "R$"),
                    ("Valor médio por registro", "Valor médio", "por registro"),
                    (
                        "Concentração do valor - top 10%",
                        "Top 10% dos registros",
                        "parcela do valor; histórico 58,20% não reproduzido",
                    ),
                ],
                total_w=640,
            ),  # fmt: skip
            Visual(
                "lineChart",
                676,
                80,
                348,
                300,
                {
                    "Category": (C("aux_curva_lorenz", "percentil", "% acumulado de registros"),),
                    "Y": (
                        M("Lorenz - % acumulado do valor", "Valor acumulado"),
                        M("Lorenz - linha de igualdade", "Igualdade"),
                    ),
                },
                title="Curva de Lorenz do valor",
                subtitle="Base completa (estática: não responde aos filtros)",
                sort=(C("aux_curva_lorenz", "percentil"), "Ascending"),
            ),
            bar(
                24,
                188,
                640,
                192,
                C("dim_procedimento", "grupo_nome_sigtap", "Grupo SIGTAP"),
                M("% do valor"),
                "Participação no valor por grupo de procedimento (SIGTAP)",
            ),
            bar(
                24,
                392,
                640,
                280,
                C("dim_estabelecimento", "estabelecimento_rotulo", "Estabelecimento (CNES)"),
                M("Valor total - top 10 estabelecimentos", "Valor total"),
                "Top 10 estabelecimentos por valor aprovado",
                "Nome fantasia no cadastro CNES de 2026-10 (pode diferir do nome em 2024)",
            ),
            bar(
                676,
                392,
                348,
                280,
                C("dim_estabelecimento", "esfera_juridica", "Esfera jurídica"),
                M("% do valor"),
                "Valor por esfera jurídica (%)",
                "Natureza jurídica: TabWin SIH",
            ),
            *frame("5. Análise financeira", "Valor aprovado (VAL_TOT) e concentração"),
        ),
    ),
    Page(
        "p6_qualidade",
        "6. Qualidade e metodologia",
        "Reconciliação com o histórico, completude dos campos e limitações",
        (
            *cards(
                80,
                [
                    (
                        "Registros excedentes de AIH",
                        "Registros excedentes",
                        "registros − AIHs distintas",
                    ),
                    (
                        "Registros de AIH repetida",
                        "Registros de AIH repetida",
                        "sinalizados, não removidos",
                    ),
                    ("Registros com valor zero", "Valor zero", "todos com ESPEC 87"),
                ],
                total_w=640,
            ),  # fmt: skip
            Visual(
                "tableEx",
                24,
                188,
                640,
                248,
                {
                    "Values": (
                        C("ref_indicadores_validados", "indicador", "Indicador"),
                        C("ref_indicadores_validados", "base", "Base"),
                        C("ref_indicadores_validados", "historico", "Histórico"),
                        C("ref_indicadores_validados", "reproduzido", "Reproduzido"),
                        C("ref_indicadores_validados", "status", "Situação"),
                    )
                },
                title="Indicadores do histórico × reproduzidos pelo pipeline",
                subtitle="Divergências explicadas, nunca ajustadas",
            ),
            Visual(
                "tableEx",
                24,
                448,
                640,
                224,
                {
                    "Values": (
                        C("qualidade_campos", "campo", "Campo do RD"),
                        C("qualidade_campos", "pct_vazios", "% vazio"),
                        C("qualidade_campos", "distintos", "Valores distintos"),
                        C("qualidade_campos", "exportado_powerbi", "No modelo"),
                    )
                },
                title="Completude dos 113 campos originais",
                sort=(C("qualidade_campos", "pct_vazios"), "Descending"),
            ),
            textbox(
                676,
                80,
                348,
                592,
                ("Fontes e limitações", {"fontWeight": "bold", "fontSize": "12pt"}),
                (
                    "Dados: SIH/SUS (DATASUS), arquivo RD do RJ, competência 2024-01; SHA-256 "
                    "conferido e preservação byte a byte verificada.",
                    BODY,
                ),
                (
                    "Nomes oficiais: SIGTAP 2024-01 (procedimentos e CID-10), IBGE (municípios), "
                    "CNES (nome fantasia, cadastro de 2026-10), tabelas TabWin do SIH (rótulos dos "
                    "códigos). Cobertura de 100%, junção por código exato.",
                    BODY,
                ),
                (
                    "Registro de AIH ≠ paciente ≠ internação: não há medida de pacientes nem de "
                    "episódios.",
                    BODY,
                ),
                (
                    "Mês de saída não é série histórica: a competência reúne o que foi processado "
                    "em janeiro de 2024.",
                    BODY,
                ),
                ("Mortalidade bruta, sem ajuste de risco.", BODY),
                (
                    "Privacidade: sem N_AIH, nascimento, CEP, CPF ou texto livre; datas apenas "
                    "por mês.",
                    BODY,
                ),
                ("Detalhes: docs/ no repositório (decisões D-001 a D-040).", NOTE),
            ),
            *frame("6. Qualidade e metodologia", "Reconciliação, completude e limitações"),
        ),
    ),
)


def _visual_json(page: Page, index: int, v: Visual) -> dict:
    name = tag("visual", page.name, str(index)).replace("-", "")[:20]
    container: dict[str, Any] = {
        "$schema": SCHEMAS["visual"],
        "name": name,
        "position": {"x": v.x, "y": v.y, "z": index * 100, "width": v.w, "height": v.h,
                     "tabOrder": index * 100},
        "visual": {"visualType": v.kind, "drillFilterOtherVisuals": True},
    }  # fmt: skip
    visual = container["visual"]
    if v.roles:
        visual["query"] = {
            "queryState": {
                role: {"projections": [f.projection() for f in fields]}
                for role, fields in v.roles.items()
            }
        }
        if v.sort:
            f, direction = v.sort
            visual["query"]["sortDefinition"] = {
                "sort": [{"field": f.expression(), "direction": direction}],
                "isDefaultSort": False,
            }
    objects: dict[str, Any] = {}
    if v.text:
        objects["general"] = [
            {"properties": {"paragraphs": [
                {"textRuns": [{"value": text, "textStyle": style}]} for text, style in v.text
            ]}}
        ]  # fmt: skip
    if v.labels:
        objects["labels"] = [{"properties": {"show": lit(True)}}]
    if v.kind == "slicer":
        objects["data"] = [{"properties": {"mode": lit("Dropdown")}}]
        visual["syncGroup"] = {"groupName": v.sync, "fieldChanges": True, "filterChanges": True}
    if objects:
        visual["objects"] = objects
    container_objects: dict[str, Any] = {}
    if v.title:
        container_objects["title"] = [{"properties": {"show": lit(True), "text": lit(v.title)}}]
    if v.subtitle:
        container_objects["subTitle"] = [
            {"properties": {"show": lit(True), "text": lit(v.subtitle)}}
        ]
    if container_objects:
        visual["visualContainerObjects"] = container_objects
    return container


THEME = {
    "name": "Hospital Analytics",
    "dataColors": [
        "#2A78D6",
        "#EC6B35",
        "#1B9E77",
        "#7570B3",
        "#D95F02",
        "#66A61E",
        "#E6AB02",
        "#A6761D",
        "#666666",
    ],  # fmt: skip
    "background": "#FFFFFF",
    "foreground": "#252423",
    "tableAccent": "#2A78D6",
    "good": "#1B9E77",
    "neutral": "#E6AB02",
    "bad": "#B03A2E",
    "textClasses": {
        "title": {"fontFace": "Segoe UI Semibold", "fontSize": 12, "color": "#252423"},
        "label": {"fontFace": "Segoe UI", "fontSize": 10, "color": "#3A3A3A"},
        "callout": {"fontFace": "Segoe UI Semibold", "fontSize": 24, "color": "#2A78D6"},
    },
}


def report_files() -> dict[str, str]:
    theme_file = "HospitalAnalytics.json"
    versions = {"visual": "2.13.0", "report": "3.3.0", "page": "2.1.0"}
    files = {
        "definition.pbir": _json(
            {
                "$schema": SCHEMAS["pbir"],
                "version": "4.0",
                "datasetReference": {"byPath": {"path": f"../{PROJECT}.SemanticModel"}},
            }
        ),  # fmt: skip
        "definition/version.json": _json({"$schema": SCHEMAS["version"], "version": "2.0.0"}),
        "definition/report.json": _json(
            {
                "$schema": SCHEMAS["report"],
                "themeCollection": {
                    "customTheme": {
                        "name": theme_file,
                        "reportVersionAtImport": versions,
                        "type": "RegisteredResources",
                    }
                },
                "resourcePackages": [
                    {
                        "name": "RegisteredResources",
                        "type": "RegisteredResources",
                        "items": [{"name": theme_file, "path": theme_file, "type": "CustomTheme"}],
                    }
                ],
            }
        ),
        f"StaticResources/RegisteredResources/{theme_file}": _json(THEME),
        "definition/pages/pages.json": _json(
            {
                "$schema": SCHEMAS["pages"],
                "pageOrder": [p.name for p in PAGES],
                "activePageName": PAGES[0].name,
            }
        ),  # fmt: skip
    }
    for page in PAGES:
        base = f"definition/pages/{page.name}"
        files[f"{base}/page.json"] = _json(
            {"$schema": SCHEMAS["page"], "name": page.name, "displayName": page.title,
             "displayOption": "FitToPage", "height": PAGE_H, "width": PAGE_W}
        )  # fmt: skip
        for i, v in enumerate(page.visuals, start=1):
            content = _visual_json(page, i, v)
            files[f"{base}/visuals/{content['name']}/visual.json"] = _json(content)
    return files


def project_files(measures_text: str) -> dict[str, str]:
    measures = parse_measures(measures_text)
    files = {
        f"{PROJECT}.pbip": _json(
            {
                "$schema": SCHEMAS["pbip"],
                "version": "1.0",
                "artifacts": [{"report": {"path": f"{PROJECT}.Report"}}],
                "settings": {"enableAutoRecovery": True},
            }
        ),  # fmt: skip
        ".gitignore": "**/.pbi/localSettings.json\n**/.pbi/cache.abf\n",
    }
    files |= {f"{PROJECT}.SemanticModel/{k}": v for k, v in semantic_model_files(measures).items()}
    files |= {f"{PROJECT}.Report/{k}": v for k, v in report_files().items()}
    return files


def _json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def write_project(directory: Path, measures_text: str) -> list[Path]:
    """(Re)write the project folder: generated files only, so stale visuals cannot linger."""
    directory = Path(directory)
    files = project_files(measures_text)
    written = []
    for relative, content in files.items():
        path = directory / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
        written.append(path)
    # Remove generated files that no longer exist in the specification (e.g. a deleted visual).
    # Files Power BI Desktop keeps locally (.pbi/localSettings.json, cache.abf) are left alone.
    for item in (f"{PROJECT}.SemanticModel", f"{PROJECT}.Report"):
        for path in sorted((directory / item).rglob("*"), reverse=True):
            relative = path.relative_to(directory).as_posix()
            if path.is_file() and relative not in files and not _local_only(relative):
                path.unlink()
            elif path.is_dir() and not any(path.iterdir()):
                path.rmdir()
    return written


def _local_only(relative: str) -> bool:
    return relative.endswith((".pbi/localSettings.json", ".pbi/cache.abf"))
