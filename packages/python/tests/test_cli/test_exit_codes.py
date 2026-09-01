"""The exit-code contract, driven from ``fixtures/cli-exit-codes.yml``.

This is the shared table both ports must satisfy: ``0`` success, ``1`` expected
failure, ``2`` usage error. The TypeScript mirror is
``packages/typescript/src/cli/exit-codes.test.ts``.

Most rows are project-independent -- they load no user config module -- so the
driver only has to ``chdir`` into an empty directory. A row may instead carry
``project:``, naming a directory under ``fixtures/cli-exit-code-projects/``
that is copied into the temp dir first; see :func:`_row_cwd`. That key exists
because the codes that depend on *user code running* cannot be reached from an
empty directory, and that is precisely where the two ports had drifted.

The second half of this module guards the *rendering*, not the code. Running
click in ``standalone_mode=False`` moves error rendering out of the framework
and into :func:`ghagen.cli.main.main`, and the obvious implementation
(``exc.show()``) silently downgrades every Typer-rendered error to click's
plain one -- a ~5x shrink of the message with no change to the exit code, which
the table above therefore cannot see.

Those cases assert on ``capsys``'s ``err`` stream specifically, never on a
mixed stream: ``click.testing.Result.output`` interleaves stdout and stderr in
write order (click 8.2 dropped ``mix_stderr``), so an ``in result.output``
assertion would pass identically whether the panel reached stderr, stdout, or
neither. These are the only stream-routing assertions in this file; every other
one is an integer.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
import typer.core
from ruamel.yaml import YAML

from ghagen.cli.main import main
from ghagen_schema.paths import FIXTURES_DIR

_TABLE: list[dict[str, Any]] = YAML(typ="safe").load(
    (FIXTURES_DIR / "cli-exit-codes.yml").read_text()
)

assert _TABLE, (
    "fixtures/cli-exit-codes.yml is empty -- every row below would be vacuous"
)

#: Fixture projects named by a row's optional ``project:`` key.
_PROJECTS_DIR = FIXTURES_DIR / "cli-exit-code-projects"


def _row_cwd(row: dict[str, Any], tmp_path: Path) -> Path:
    """Return the directory *row* runs in, materialising its project if any.

    Rows without ``project:`` run in an empty directory, exactly as before.
    Rows with it get a *copy* of the fixture project, so a command that writes
    (``synth``) cannot mutate the checked-in fixture.
    """
    project = row.get("project")
    if project is None:
        return tmp_path
    source = _PROJECTS_DIR / project
    assert source.is_dir(), f"{row['id']}: no fixture project at {source}"
    dest = tmp_path / project
    shutil.copytree(source, dest)
    return dest


@pytest.mark.parametrize("row", _TABLE, ids=[row["id"] for row in _TABLE])
def test_exit_code_contract(row: dict[str, Any], tmp_path: Path, monkeypatch: Any):
    """``main(argv)`` returns the code the shared table specifies."""
    monkeypatch.chdir(_row_cwd(row, tmp_path))
    assert main(row["argv"]) == row["exit"], row["id"]


def test_main_returns_for_every_row(tmp_path: Path, monkeypatch: Any):
    """``main()`` returns for every row rather than killing the process.

    The whole point of ``standalone_mode=False``: click's standalone mode calls
    ``sys.exit`` from inside ``command.main``, which no in-process caller can
    observe as a value. A row that *raises* out of ``main()`` fails here too --
    an exception is not a return value either.
    """
    codes = []
    for index, row in enumerate(_TABLE):
        # A fresh subdirectory per row: `_row_cwd` copies into it, and two rows
        # naming the same project must not collide.
        row_root = tmp_path / str(index)
        row_root.mkdir()
        monkeypatch.chdir(_row_cwd(row, row_root))
        codes.append(main(row["argv"]))
    assert len(codes) == len(_TABLE)
    assert all(isinstance(code, int) for code in codes)


# ---------------------------------------------------------------------------
# stderr-rendering fidelity: Typer's renderer, not click's
# ---------------------------------------------------------------------------

#: ``(argv, fragments, prog)``. ``prog`` is ``None`` for the one case Typer
#: renders without a usage preamble (a missing option argument is raised before
#: the failing option's context carries one).
#:
#: ``fragments`` are matched as substrings, not as a whole message, and they
#: deliberately exclude click's punctuation around the offending token. click
#: reworded its usage errors in 8.4 (``No such option: --bogus`` became
#: ``No such option '--bogus'.``), and `pyproject.toml` declares ``click>=8.2.1``
#: with no ceiling, so both wordings are manifest-legal and a fresh resolve gets
#: whichever is current. What this test is *for* is the renderer -- the rich
#: panel below -- not click's prose, so pinning the prose only made the test
#: fail on a wording change it does not care about.
_FIDELITY_CASES = [
    pytest.param(
        ["bogus-command"],
        ("No such command", "bogus-command"),
        "ghagen",
        id="unknown-command",
    ),
    pytest.param(
        ["synth", "--bogus"],
        ("No such option", "--bogus"),
        "ghagen synth",
        id="unknown-option",
    ),
    pytest.param(
        ["init", "--outdir"],
        ("Option '--outdir' requires an argument.",),
        None,
        id="missing-option-argument",
    ),
    pytest.param(
        ["--version"],
        ("No such option", "--version"),
        "ghagen",
        id="unknown-top-level-option",
    ),
]


@pytest.mark.skipif(
    not typer.core.HAS_RICH,
    reason="TYPER_USE_RICH=0 -- Typer itself falls back to click's plain renderer, "
    "and main() mirrors that branch",
)
@pytest.mark.parametrize(("argv", "fragments", "prog"), _FIDELITY_CASES)
def test_error_rendering_is_typers_not_clicks(
    argv: list[str],
    fragments: tuple[str, ...],
    prog: str | None,
    tmp_path: Path,
    monkeypatch: Any,
    capsys: pytest.CaptureFixture[str],
):
    """Usage errors keep Typer's rich rendering under ``standalone_mode=False``.

    ``exc.show()`` -- the obvious handler -- emits no panel at all, so asserting
    the box-drawn ``Error`` panel fails on any downgrade to click's plain
    renderer while staying stable against Typer's own formatting tweaks.
    """
    monkeypatch.chdir(tmp_path)

    assert main(argv) == 2

    err = capsys.readouterr().err
    assert "╭─" in err, "Typer's rich error panel is gone -- click's plain renderer?"
    assert "Error" in err
    assert "╰─" in err
    for fragment in fragments:
        assert fragment in err
    if prog is not None:
        assert err.startswith("Usage: ")
        assert f"Try '{prog} --help' for help." in err
