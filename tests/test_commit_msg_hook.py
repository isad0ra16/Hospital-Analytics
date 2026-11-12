"""The versioned commit-msg hook enforces the project's commit conventions."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from hospital_analytics.config import project_root

HOOK = project_root() / "scripts" / "git-hooks" / "commit-msg"


def _bash_candidates() -> list[str]:
    """Bash interpreters to try, the one git itself uses first.

    On Windows, ``bash`` on PATH is often ``System32\\bash.exe``: the WSL launcher, which fails
    when no Linux distribution is installed. Git hooks run under the bash bundled with Git for
    Windows, so that one is preferred (``<git>/bin/bash.exe`` next to ``<git>/cmd/git.exe``).
    """
    candidates = []
    git = shutil.which("git")
    if git and os.name == "nt":
        git_root = Path(git).resolve().parent.parent
        candidates += [
            str(git_root / "bin" / "bash.exe"),
            str(git_root / "usr" / "bin" / "bash.exe"),
        ]
    if found := shutil.which("bash"):
        candidates.append(found)
    return candidates


def _working_bash() -> str | None:
    """First candidate that actually runs a script (probing beats trusting PATH)."""
    for candidate in _bash_candidates():
        if not Path(candidate).is_file():
            continue
        try:
            probe = subprocess.run(
                [candidate, "-c", "echo ok"], capture_output=True, text=True, timeout=30
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if probe.returncode == 0 and probe.stdout.strip() == "ok":
            return candidate
    return None


BASH = _working_bash()

pytestmark = pytest.mark.skipif(BASH is None, reason="requires a working bash")


def run_hook(tmp_path, message: str, **env: str) -> subprocess.CompletedProcess:
    path = tmp_path / "COMMIT_EDITMSG"
    path.write_text(message, encoding="utf-8")
    return subprocess.run(
        [BASH, str(HOOK), str(path)],
        capture_output=True,
        text=True,
        env=os.environ | env,
        check=False,
    )


def test_hook_is_executable():
    assert os.access(HOOK, os.X_OK)


@pytest.mark.parametrize(
    "message",
    [
        "feat: add audit\n",
        "fix: handle reduced precision\n\nExplains why the change is needed.\n",
        "docs: mention co-authored-by conventions in prose\n\nThe word session: is fine here.\n",
        "feat: x\n\n# Co-Authored-By: ignored because it is a comment line\n",
    ],
)
def test_clean_messages_pass(tmp_path, message):
    assert run_hook(tmp_path, message).returncode == 0


@pytest.mark.parametrize(
    "message",
    [
        "feat: x\n\nCo-Authored-By: Someone <someone@example.com>\n",
        "feat: x\n\nco-authored-by: Someone <someone@example.com>\n",
        "feat: x\n\nTool-Session: https://example.com/session/123\n",
        "feat: x\n\nGenerated with Some Tool\n",
    ],
)
def test_automatic_lines_are_rejected(tmp_path, message):
    result = run_hook(tmp_path, message)
    assert result.returncode == 1
    assert "rejected" in result.stderr


def test_legitimate_co_author_allowed_with_explicit_opt_in(tmp_path):
    message = "feat: x\n\nCo-Authored-By: Real Person <real@example.com>\n"
    assert run_hook(tmp_path, message).returncode == 1
    assert run_hook(tmp_path, message, ALLOW_CO_AUTHOR="1").returncode == 0


def test_opt_in_never_allows_session_or_generation_lines(tmp_path):
    for line in ("Tool-Session: abc", "Generated with Some Tool"):
        result = run_hook(tmp_path, f"feat: x\n\n{line}\n", ALLOW_CO_AUTHOR="1")
        assert result.returncode == 1, line
