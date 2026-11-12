"""Every internal link of the Markdown documentation points to an existing file and heading.

Anchors follow GitHub's rule: lower case, punctuation removed, spaces turned into hyphens.
Links inside fenced code blocks and external URLs are ignored.
"""

import re
from pathlib import Path

import pytest

from hospital_analytics.config import project_root

ROOT = project_root()
DOCS = sorted(
    p
    for p in [ROOT / "README.md", *ROOT.glob("data/*.md"), *ROOT.glob("docs/**/*.md"),
              *ROOT.glob("reports/**/*.md")]
    if p.is_file()
)  # fmt: skip
LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)\)")
FENCE = re.compile(r"^```.*?^```", flags=re.M | re.S)


def anchor(heading: str) -> str:
    text = re.sub(r"[`*_]", "", heading.strip().lower())
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def anchors(path: Path) -> set[str]:
    text = FENCE.sub("", path.read_text(encoding="utf-8"))
    return {anchor(m.group(1)) for m in re.finditer(r"^#{1,6} (.+)$", text, flags=re.M)}


def links(path: Path) -> list[str]:
    text = FENCE.sub("", path.read_text(encoding="utf-8"))
    return [t for t in LINK.findall(text) if not re.match(r"[a-z]+:", t)]


def test_documentation_files_are_found():
    names = {p.relative_to(ROOT).as_posix() for p in DOCS}
    assert {"README.md", "docs/01_fontes_de_dados.md", "docs/08_limitacoes.md"} <= names


@pytest.mark.parametrize("path", DOCS, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_internal_links_resolve(path):
    broken = []
    for target in links(path):
        file_part, _, fragment = target.partition("#")
        destination = (path.parent / file_part).resolve() if file_part else path
        if not destination.exists():
            broken.append(f"{target}: file not found")
        elif fragment and destination.suffix == ".md" and fragment not in anchors(destination):
            broken.append(f"{target}: heading not found")
    assert not broken, broken


def test_anchor_rule_matches_github():
    assert anchor("Reconciliação com o histórico") == "reconciliação-com-o-histórico"
    assert anchor("Competência, internação e saída") == "competência-internação-e-saída"
    assert (
        anchor("Privacidade e risco de reidentificação") == "privacidade-e-risco-de-reidentificação"
    )
