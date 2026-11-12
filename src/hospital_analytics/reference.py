"""Readers and checks for official reference data (CNES, SIGTAP, IBGE) used to enrich dimensions.

Nothing here changes the production model. The module reads official files exactly as published,
reports structure, key quality and coverage against the current dimensions, and provides the
guard that any later enrichment must pass (same rows, same keys, untouched fact).

Fixed-width SIGTAP files are read with the layout published *inside the same archive*
(``<table>_layout.txt``: header ``Coluna,Tamanho,Inicio,Fim,Tipo``; 1-based inclusive positions).
Column positions are never hard-coded. Every value is kept as text (codes have leading zeros).
"""

from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

LAYOUT_HEADER = ["coluna", "tamanho", "inicio", "fim", "tipo"]


class ReferenceFormatError(Exception):
    """A reference file does not follow its documented layout or expected structure."""


# ---------------------------------------------------------------------------
# SIGTAP fixed-width files
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class FixedField:
    name: str
    length: int
    start: int  # 1-based, inclusive
    end: int  # 1-based, inclusive
    type: str


def parse_layout(text: str) -> list[FixedField]:
    """Parse a ``*_layout.txt`` file. Fails on any inconsistency instead of guessing."""
    rows = [r for r in csv.reader(io.StringIO(text.lstrip("﻿"))) if any(c.strip() for c in r)]
    if not rows or [c.strip().lower() for c in rows[0]] != LAYOUT_HEADER:
        raise ReferenceFormatError(f"layout header must be {LAYOUT_HEADER}, got {rows[:1]}")
    fields: list[FixedField] = []
    expected_start = 1
    for number, row in enumerate(rows[1:], start=2):
        if len(row) != 5:
            raise ReferenceFormatError(f"layout line {number}: expected 5 fields, got {row}")
        name, length, start, end, kind = (c.strip() for c in row)
        try:
            length_i, start_i, end_i = int(length), int(start), int(end)
        except ValueError as exc:
            raise ReferenceFormatError(f"layout line {number}: non-numeric position {row}") from exc
        if end_i - start_i + 1 != length_i:
            raise ReferenceFormatError(f"layout line {number}: {name} length != end - start + 1")
        if start_i != expected_start:
            raise ReferenceFormatError(
                f"layout line {number}: {name} starts at {start_i}, expected {expected_start}"
            )
        fields.append(FixedField(name, length_i, start_i, end_i, kind))
        expected_start = end_i + 1
    if not fields:
        raise ReferenceFormatError("layout has no fields")
    return fields


def read_fixed_width(data: bytes, layout: list[FixedField], encoding: str) -> list[dict[str, str]]:
    """Split each line by the layout. Every line must have exactly the layout width."""
    width = layout[-1].end
    rows = []
    for number, raw in enumerate(data.split(b"\n"), start=1):
        line = raw.rstrip(b"\r")
        if not line:
            continue
        if len(line) != width:
            raise ReferenceFormatError(
                f"data line {number}: {len(line)} bytes, layout width {width}"
            )
        text = line.decode(encoding)
        rows.append({f.name: text[f.start - 1 : f.end].strip(" ") for f in layout})
    return rows


def read_sigtap_table(archive: Path, table: str, encoding: str = "cp1252") -> list[dict[str, str]]:
    """Read ``<table>.txt`` from a SIGTAP archive with ``<table>_layout.txt`` from the same archive.

    Byte positions equal character positions only for single-byte encodings, so only those are
    accepted. Default CP1252: verified on TabelaUnificada_202401 (12 procedure names use bytes
    0x93/0x94/0x96 = quotation marks and en dash, which Latin-1 decodes as control characters).
    """
    if encoding.lower().replace("_", "-") not in {"latin-1", "iso-8859-1", "cp1252", "cp850"}:
        raise ValueError(f"{encoding}: fixed-width byte positions require a single-byte encoding")
    with zipfile.ZipFile(archive) as zf:
        names = set(zf.namelist())
        for needed in (f"{table}.txt", f"{table}_layout.txt"):
            if needed not in names:
                raise ReferenceFormatError(f"{archive.name}: {needed} not found")
        layout = parse_layout(zf.read(f"{table}_layout.txt").decode(encoding))
        return read_fixed_width(zf.read(f"{table}.txt"), layout, encoding)


# ---------------------------------------------------------------------------
# IBGE municipalities (API de Localidades JSON)
# ---------------------------------------------------------------------------
def read_ibge_municipios(path: Path) -> list[dict[str, str]]:
    """Flatten the IBGE municipalities JSON to id (as text), name and UF.

    The UF is taken from the nested territorial hierarchy when present; missing paths are
    reported as an error, never filled in.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ReferenceFormatError("IBGE JSON: expected a non-empty list of municipalities")
    out = []
    for item in data:
        if "id" not in item or "nome" not in item:
            raise ReferenceFormatError(f"IBGE JSON: item without id/nome: {list(item)[:5]}")
        uf = _find_uf(item)
        if uf is None:
            raise ReferenceFormatError(f"IBGE JSON: no UF found for municipality {item['id']}")
        out.append(
            {
                "id": str(item["id"]),
                "nome": item["nome"],
                "uf_id": str(uf["id"]),
                "uf_sigla": uf["sigla"],
            }
        )
    return out


def _find_uf(node: Any) -> dict | None:
    if isinstance(node, dict):
        if "UF" in node and isinstance(node["UF"], dict) and {"id", "sigla"} <= set(node["UF"]):
            return node["UF"]
        for value in node.values():
            found = _find_uf(value)
            if found:
                return found
    return None


# ---------------------------------------------------------------------------
# Key quality and coverage
# ---------------------------------------------------------------------------
@dataclass
class KeyReport:
    name: str
    rows: int
    distinct: int
    duplicated_keys: list[str]
    blank_keys: int
    lengths: dict[int, int]
    non_digit_keys: int

    @property
    def unique(self) -> bool:
        return not self.duplicated_keys and self.blank_keys == 0


def key_report(name: str, keys: list[str]) -> KeyReport:
    counts = Counter(keys)
    return KeyReport(
        name=name,
        rows=len(keys),
        distinct=len(counts),
        duplicated_keys=sorted(k for k, c in counts.items() if c > 1),
        blank_keys=sum(1 for k in keys if k == ""),
        lengths=dict(sorted(Counter(len(k) for k in keys).items())),
        non_digit_keys=sum(1 for k in keys if k and not k.isdigit()),
    )


@dataclass
class Coverage:
    dimension: str
    reference: str
    dimension_keys: int
    matched: int
    unmatched: list[str] = field(default_factory=list)
    ambiguous: list[str] = field(default_factory=list)  # dimension keys matching >1 reference row

    @property
    def matched_pct(self) -> float:
        return round(100 * self.matched / self.dimension_keys, 2) if self.dimension_keys else 0.0


def coverage(
    dimension: str, dim_keys: list[str], reference: str, ref_keys: list[str], *, transform=None
) -> Coverage:
    """Coverage of the dimension keys by the reference (optionally after ``transform`` of the
    reference key, e.g. the 6-digit prefix of an IBGE code)."""
    mapped = Counter(transform(k) if transform else k for k in ref_keys)
    unique_dim = sorted(set(dim_keys))
    return Coverage(
        dimension=dimension,
        reference=reference,
        dimension_keys=len(unique_dim),
        matched=sum(1 for k in unique_dim if mapped.get(k, 0) == 1),
        unmatched=[k for k in unique_dim if k not in mapped],
        ambiguous=[k for k in unique_dim if mapped.get(k, 0) > 1],
    )


# ---------------------------------------------------------------------------
# Guard for any future enrichment
# ---------------------------------------------------------------------------
def enrichment_guard(
    before: list[dict[str, str]], after: list[dict[str, str]], key: str
) -> list[str]:
    """Problems found when comparing a dimension before and after enrichment (empty = safe).

    Enrichment may only ADD columns: same row count, same keys, unique keys, original columns
    unchanged.
    """
    problems = []
    if len(before) != len(after):
        problems.append(f"row count changed: {len(before)} -> {len(after)}")
    keys_before = [r[key] for r in before]
    keys_after = [r[key] for r in after]
    if sorted(keys_before) != sorted(keys_after):
        problems.append("set of keys changed")
    if len(set(keys_after)) != len(keys_after):
        problems.append("duplicated keys after enrichment (join fan-out)")
    by_key = {r[key]: r for r in after}
    original_columns = list(before[0]) if before else []
    changed = [
        r[key]
        for r in before
        if any(by_key.get(r[key], {}).get(c) != r[c] for c in original_columns)
    ]
    if changed:
        problems.append(f"original columns modified for {len(changed)} keys (e.g. {changed[:3]})")
    return problems


def fact_unchanged(export_summary: Path, fact_csv: Path) -> bool:
    """True when the fact CSV is byte-identical to the one recorded in the export summary."""
    from hospital_analytics.integrity import sha256_file

    summary = json.loads(Path(export_summary).read_text(encoding="utf-8"))
    return summary["tables"]["fato_registro_aih"]["csv"]["sha256"] == sha256_file(fact_csv)


# ---------------------------------------------------------------------------
# TabWin conversion files (.cnv)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CnvEntry:
    """One category of a TabWin conversion table, with every code item and its file line."""

    sequence: str
    parent: str | None  # sequence of the parent category (hierarchical files), else None
    label: str
    items: tuple[tuple[str, int], ...]  # (code item, line number) — item: code, "a-b" or ""


@dataclass(frozen=True)
class CnvTable:
    """A TabWin ``.cnv`` file read completely (see ``read_cnv_table``)."""

    name: str
    flags: tuple[str, ...]
    width: int
    entries: tuple[CnvEntry, ...]
    header: tuple[str, ...] = ()  # first line, as published

    def matches(self, value: str, start: int = 1) -> list[CnvEntry]:
        """Every category listing ``value`` (file order), without applying precedence."""
        key = self.key(value, start)
        return [e for e in self.entries if any(_item_matches(i, key) for i, _ in e.items)]

    def entry(self, sequence: str) -> CnvEntry:
        return next(e for e in self.entries if int(e.sequence) == int(sequence))

    def key(self, value: str, start: int = 1) -> str:
        """Lookup key: ``width`` characters of the field from ``start`` (1-based), as TabWin."""
        return value[start - 1 : start - 1 + self.width]

    def resolve(self, value: str, start: int = 1) -> CnvEntry | None:
        """The single category of ``value``, or None when no category lists it.

        Codes may be listed by more than one category (e.g. a catch-all range first, specific
        codes after). The format's precedence rule is not documented in the files, so two
        plausible rules are applied and must agree: the most specific item wins (exact code,
        then the narrowest numeric range) and the last listed item wins. Disagreement or a tie
        is an error — the category is never guessed.
        """
        key = self.key(value, start)
        matches = [
            (e, _specificity(item), line)
            for e in self.entries
            for item, line in e.items
            if _item_matches(item, key)
        ]
        if not matches:
            return None
        best_rank = min(rank for _, rank, _ in matches)
        best = {e.sequence: e for e, rank, _ in matches if rank == best_rank}
        if len(best) > 1:
            raise ReferenceFormatError(
                f"{self.name}: {key!r} matches categories {sorted(best)} with equal precedence"
            )
        (most_specific,) = best.values()
        last_listed = max(matches, key=lambda m: m[2])[0]
        if last_listed.sequence != most_specific.sequence:
            raise ReferenceFormatError(
                f"{self.name}: precedence rules disagree for {key!r} "
                f"(most specific {most_specific.sequence}, last listed {last_listed.sequence})"
            )
        return most_specific

    def full_label(self, entry: CnvEntry) -> str:
        """Label with its parent category in hierarchical files: ``parent — child``."""
        if entry.parent is None:
            return entry.label
        child = entry.label.lstrip(". ").strip()
        return f"{self.entry(entry.parent).label} — {child}"


_CODE_ITEM = re.compile(r"^[0-9A-Za-z]*(-[0-9A-Za-z]*)?$")


def _item_matches(item: str, key: str) -> bool:
    if item == "":
        return key.strip() == ""
    if "-" in item:
        lo, hi = item.split("-", 1)
        if lo.isdigit() and hi.isdigit() and key.isdigit():
            return int(lo) <= int(key) <= int(hi)
        if lo.isdigit() and hi.isdigit():
            return False
        return lo <= key <= hi  # alphanumeric range (e.g. CID-10 "A00-B99"), string order
    return item == key


def _specificity(item: str) -> tuple[int, int]:
    """Lower is more specific: exact code or blank, numeric range by width, other ranges."""
    if "-" not in item:
        return (0, 0)
    lo, hi = item.split("-", 1)
    if lo.isdigit() and hi.isdigit():
        return (1, int(hi) - int(lo))
    return (2, 0)


def read_cnv_table(path: Path, encoding: str = "cp1252") -> CnvTable:
    """Read a TabWin ``.cnv`` file, including the variants found in the official SIH package.

    Header: optional flag tokens (e.g. ``N``), category count, code width, optional flags
    (e.g. ``L``). Each line: [parent sequence] sequence, label, codes (last token: comma
    separated codes, ranges ``a-b`` and empty items for blank values). A category may continue
    on further lines with the same sequence and label. The number of distinct categories must
    equal the declared count.
    """
    path = Path(path)
    lines = [ln for ln in path.read_bytes().decode(encoding).splitlines() if ln.strip()]
    if not lines:
        raise ReferenceFormatError(f"{path.name}: empty file")
    header = lines[0].split()
    numbers = [i for i, tok in enumerate(header) if tok.isdigit()]
    if len(numbers) < 2 or numbers[1] != numbers[0] + 1:
        raise ReferenceFormatError(f"{path.name}: header must hold count and width: {header}")
    count, width = int(header[numbers[0]]), int(header[numbers[1]])
    flags = tuple(t for i, t in enumerate(header) if i not in numbers[:2])

    order: list[str] = []
    data: dict[str, dict[str, Any]] = {}
    for number, line in enumerate(lines[1:], start=2):
        spans = [(m.group(), m.start(), m.end()) for m in re.finditer(r"\S+", line)]
        if len(spans) < 2 or not spans[0][0].isdigit():
            raise ReferenceFormatError(f"{path.name} line {number}: unexpected {line!r}")
        top_level = {int(s) for s in order if data[s]["parent"] is None}
        hierarchical = len(spans) >= 4 and spans[1][0].isdigit() and int(spans[0][0]) in top_level
        parent, (seq, _, seq_end) = (spans[0][0], spans[1]) if hierarchical else (None, spans[0])
        codes, codes_start, _ = spans[-1]
        raw_items = codes.split(",")
        if not all(_CODE_ITEM.match(i) for i in raw_items):
            raise ReferenceFormatError(f"{path.name} line {number}: invalid codes {codes!r}")
        # A trailing comma only terminates the list ("A00-B99,"); an empty item before it
        # (",0-3" or a lone ",") stands for the blank value.
        items = [i for i in raw_items if i]
        if "" in raw_items[:-1]:
            items.append("")
        label = line[seq_end:codes_start].strip()
        key = str(int(seq))
        if key in data:
            if data[key]["label"] != label or data[key]["parent"] != parent:
                raise ReferenceFormatError(
                    f"{path.name} line {number}: sequence {seq} reused with a different label"
                )
        else:
            order.append(key)
            data[key] = {"sequence": seq, "parent": parent, "label": label, "items": []}
        data[key]["items"] += [(i, number) for i in items]
    if len(order) != count:
        raise ReferenceFormatError(
            f"{path.name}: header declares {count} categories, found {len(order)}"
        )
    entries = tuple(
        CnvEntry(d["sequence"], d["parent"], d["label"], tuple(dict.fromkeys(d["items"])))
        for d in (data[k] for k in order)
    )
    return CnvTable(path.name, flags, width, entries, tuple(header))


def clean_label(label: str, code: str) -> str:
    """Official label without a leading copy of its own code (``01-Cirúrgico``, ``01 Eletivo``,
    ``101-5 Orgao …`` for code 1015). The remaining text is kept literally."""
    first, _, rest = label.partition(" ")
    if first.replace("-", "") == code and rest:
        return rest.lstrip("- ").strip()
    for sep in ("-", " "):
        if label.startswith(code + sep) and len(label) > len(code) + 1:
            return label[len(code) + 1 :].strip()
    return label
