"""Semantic contract of the Power BI Project: what a hand-customised report must keep.

The report in ``powerbi/`` may be customised in Power BI Desktop (colours, positions, backgrounds,
new visuals). Those changes are legitimate and must not fail the checks. What must stay intact is
the semantic layer the analysis depends on:

* every exported table and column;
* every relationship, with the same active/inactive state;
* every DAX measure, with the same expression (whitespace and Desktop's ``` fences ignored);
* every field used by a visual must exist in the model.

Removals and changes break the contract (errors). Additions (a new measure, table or relationship)
and Desktop bookkeeping (``lineageTag``, annotations, auto date/time tables) are only reported.
The parser reads the TMDL text as Power BI writes it; it does not evaluate DAX.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

_NAME = r"'(?:[^']|'')*'|[^\s='.]+"
_TABLE = re.compile(rf"^table ({_NAME})\s*$")
_COLUMN = re.compile(rf"^\tcolumn ({_NAME})")
_MEASURE = re.compile(rf"^\tmeasure ({_NAME})\s*=\s*(.*)$")
_REL_PROP = re.compile(r"^\t(fromColumn|toColumn|isActive):\s*(.+?)\s*$")
_QUALIFIED = re.compile(rf"^({_NAME})\.({_NAME})$")
AUTO_DATE_PREFIXES = ("LocalDateTable_", "DateTableTemplate_")


def unquote(name: str) -> str:
    name = name.strip()
    if len(name) >= 2 and name[0] == name[-1] == "'":
        return name[1:-1].replace("''", "'")
    return name


def _normalize_dax(text: str) -> str:
    return " ".join(text.replace("```", " ").split())


@dataclass
class SemanticContract:
    tables: dict[str, list[str]] = field(default_factory=dict)  # table -> columns
    relationships: set[tuple[str, str, bool]] = field(default_factory=set)  # from, to, active
    measures: dict[tuple[str, str], str] = field(default_factory=dict)  # (table, name) -> DAX

    def has_field(self, kind: str, table: str, name: str) -> bool:
        if kind == "Measure":
            return (table, name) in self.measures
        return name in self.tables.get(table, [])


def _is_auto_date(name: str) -> bool:
    return name.startswith(AUTO_DATE_PREFIXES)


def _parse_table_file(text: str, contract: SemanticContract) -> None:
    lines = text.splitlines()
    table = None
    i = 0
    while i < len(lines):
        line = lines[i]
        if m := _TABLE.match(line):
            table = unquote(m.group(1))
            contract.tables.setdefault(table, [])
        elif table and (m := _COLUMN.match(line)):
            contract.tables[table].append(unquote(m.group(1)))
        elif table and (m := _MEASURE.match(line)):
            name, first = unquote(m.group(1)), m.group(2)
            body = [first]
            fenced = first.strip() == "```"
            i += 1
            while i < len(lines):
                nxt = lines[i]
                if fenced:
                    body.append(nxt)
                    if nxt.strip() == "```":
                        i += 1
                        break
                elif nxt.startswith("\t\t\t") or (not nxt.strip() and _continues(lines, i)):
                    body.append(nxt)
                else:
                    break
                i += 1
            contract.measures[(table, name)] = _normalize_dax("\n".join(body))
            continue
        i += 1


def _continues(lines: list[str], i: int) -> bool:
    """A blank line belongs to a measure expression only if the expression goes on after it."""
    for nxt in lines[i + 1 :]:
        if nxt.strip():
            return nxt.startswith("\t\t\t")
    return False


def _qualified(value: str) -> str:
    m = _QUALIFIED.match(value.strip())
    if not m:
        return value.strip()
    return f"{unquote(m.group(1))}.{unquote(m.group(2))}"


def _parse_relationships(text: str, contract: SemanticContract) -> None:
    blocks = re.split(r"^relationship ", text, flags=re.M)[1:]
    for block in blocks:
        props = {}
        for line in block.splitlines()[1:]:
            if m := _REL_PROP.match(line):
                props[m.group(1)] = m.group(2)
        if "fromColumn" in props and "toColumn" in props:
            contract.relationships.add(
                (
                    _qualified(props["fromColumn"]),
                    _qualified(props["toColumn"]),
                    props.get("isActive", "true").lower() != "false",
                )
            )


def read_semantic_contract(project_dir: Path, project: str) -> SemanticContract:
    """Parse ``<project>.SemanticModel/definition`` (tables, relationships, measures)."""
    definition = Path(project_dir) / f"{project}.SemanticModel" / "definition"
    contract = SemanticContract()
    for path in sorted((definition / "tables").glob("*.tmdl")):
        _parse_table_file(path.read_text(encoding="utf-8"), contract)
    relationships = definition / "relationships.tmdl"
    if relationships.is_file():
        _parse_relationships(relationships.read_text(encoding="utf-8"), contract)
    return contract


@dataclass
class ContractReport:
    errors: list[str] = field(default_factory=list)  # removals or changes: contract broken
    notes: list[str] = field(default_factory=list)  # additions and Desktop bookkeeping

    @property
    def ok(self) -> bool:
        return not self.errors


def compare_contracts(expected: SemanticContract, actual: SemanticContract) -> ContractReport:
    report = ContractReport()
    for table, columns in expected.tables.items():
        if table not in actual.tables:
            report.errors.append(f"table removed: {table}")
            continue
        missing = [c for c in columns if c not in actual.tables[table]]
        if missing:
            report.errors.append(f"columns removed from {table}: {missing}")
        added = [c for c in actual.tables[table] if c not in columns]
        if added:
            report.notes.append(f"columns added to {table}: {added}")
    for table in actual.tables:
        if table not in expected.tables:
            kind = "auto date/time table" if _is_auto_date(table) else "table added"
            report.notes.append(f"{kind}: {table}")
    expected_pairs = {(f, t): a for f, t, a in expected.relationships}
    actual_pairs = {(f, t): a for f, t, a in actual.relationships}
    for pair, active in expected_pairs.items():
        if pair not in actual_pairs:
            report.errors.append(f"relationship removed: {pair[0]} -> {pair[1]}")
        elif actual_pairs[pair] != active:
            state = "active" if actual_pairs[pair] else "inactive"
            report.errors.append(f"relationship now {state}: {pair[0]} -> {pair[1]}")
    for pair in actual_pairs.keys() - expected_pairs.keys():
        if not any(_is_auto_date(part.split(".")[0]) for part in pair):
            report.notes.append(f"relationship added: {pair[0]} -> {pair[1]}")
    for key, expression in expected.measures.items():
        if key not in actual.measures:
            report.errors.append(f"measure removed: {key[0]}[{key[1]}]")
        elif actual.measures[key] != expression:
            report.errors.append(f"measure expression changed: {key[0]}[{key[1]}]")
    for key in actual.measures.keys() - expected.measures.keys():
        report.notes.append(f"measure added: {key[0]}[{key[1]}]")
    return report


def field_references(node) -> list[tuple[str, str, str]]:
    """(kind, table, name) of every Column/Measure reference in a PBIR visual definition."""
    found: list[tuple[str, str, str]] = []
    if isinstance(node, dict):
        for kind in ("Column", "Measure"):
            ref = node.get(kind)
            if isinstance(ref, dict) and "Property" in ref:
                entity = ref.get("Expression", {}).get("SourceRef", {}).get("Entity")
                if entity:
                    found.append((kind, entity, ref["Property"]))
        for value in node.values():
            found += field_references(value)
    elif isinstance(node, list):
        for value in node:
            found += field_references(value)
    return found


def broken_visual_fields(project_dir: Path, project: str, contract: SemanticContract) -> list[str]:
    """Visual fields that do not exist in the semantic model (a renamed or deleted field)."""
    pages = Path(project_dir) / f"{project}.Report" / "definition" / "pages"
    broken = []
    for path in sorted(pages.rglob("visual.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        for kind, table, name in field_references(document):
            if not contract.has_field(kind, table, name):
                broken.append(f"{path.relative_to(pages).as_posix()}: {kind} {table}[{name}]")
    return broken
