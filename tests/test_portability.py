"""Cross-platform guards: behavior must not depend on the operating system's locale."""

import ast
import io
import sys

from hospital_analytics.cli import safe_console
from hospital_analytics.config import project_root

SRC = project_root() / "src" / "hospital_analytics"
TEXT_METHODS = {"read_text", "write_text"}


def _text_io_without_encoding(tree: ast.AST) -> list[int]:
    """Lines with text-mode file I/O that relies on the locale default encoding."""
    lines = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute | ast.Name):
            continue
        name = node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
        keywords = {k.arg for k in node.keywords}
        if "encoding" in keywords:
            continue
        positional_encoding = {"read_text": 0, "write_text": 1}  # index of the encoding argument
        if name in positional_encoding:
            if len(node.args) <= positional_encoding[name]:
                lines.append(node.lineno)
        elif name == "open":
            # builtin open(file, mode) vs Path.open(mode); default mode is text ("r").
            position = 1 if isinstance(node.func, ast.Name) else 0
            mode_node = next((k.value for k in node.keywords if k.arg == "mode"), None)
            if mode_node is None and len(node.args) > position:
                mode_node = node.args[position]
            mode = mode_node.value if isinstance(mode_node, ast.Constant) else "r"
            if "b" not in str(mode):
                lines.append(node.lineno)
    return lines


def test_source_never_relies_on_the_locale_encoding():
    """On Windows the default is cp1252: UTF-8 reports with accents or emoji would break."""
    offenders = {}
    for path in sorted(SRC.glob("*.py")):
        found = _text_io_without_encoding(ast.parse(path.read_text(encoding="utf-8")))
        if found:
            offenders[path.name] = found
    assert offenders == {}


def test_guard_detects_missing_encoding():
    code = "p.read_text()\np.write_text('x')\np.open()\nopen(f, 'w')\np.open('rb')\n"
    assert _text_io_without_encoding(ast.parse(code)) == [1, 2, 3, 4]


def test_console_that_cannot_encode_symbols_does_not_crash(monkeypatch):
    out = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    monkeypatch.setattr(sys, "stdout", out)
    monkeypatch.setattr(sys, "stderr", io.TextIOWrapper(io.BytesIO(), encoding="cp1252"))
    safe_console()
    print("✅ validado · São Gonçalo")
    out.flush()
    text = out.buffer.getvalue().decode("cp1252")
    assert text.startswith("\\u2705 validado · São Gonçalo")
