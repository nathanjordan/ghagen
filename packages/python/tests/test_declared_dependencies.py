"""The manifest must declare every distribution the source actually imports.

``pyproject.toml`` is the only artefact a fresh checkout reads. ``uv.lock`` is
gitignored (``.gitignore:31``), so a dependency that resolves only because some
*other* dependency happens to require it is held together by an untracked file
on one machine.

That is not hypothetical: ``cli/main.py`` imported ``click`` while the manifest
declared only ``typer>=0.12``. typer 0.25 vendors click and drops the top-level
requirement, so a fresh resolve picked typer 0.27 with no click at all and four
``test_cli/`` modules failed to collect. See
``docs/adr/0009-click-is-a-declared-dependency.md``.
"""

from __future__ import annotations

import ast
import sys
import tomllib
from importlib.metadata import packages_distributions
from pathlib import Path

import pytest

from ghagen._package_paths import GHAGEN_ROOT

FIRST_PARTY = {"ghagen"}

# Distributions ghagen imports directly and deliberately does *not* declare.
# An entry here needs a reason that says why a declaration would be worse than
# the transitive -- "it works today" is not one.
UNDECLARED_BY_DESIGN = {
    # `_raw.py` and `_commented.py` implement `__get_pydantic_core_schema__`,
    # pydantic v2's published extension protocol, which requires naming
    # `pydantic_core` types. pydantic pins it as `pydantic-core==2.41.5` -- an
    # exact equality it bumps in lockstep -- so any constraint ghagen wrote
    # could only ever conflict with pydantic's. This is the opposite of the
    # click case: there the intermediary dropped the dependency, here the
    # intermediary owns the version outright.
    "pydantic_core",
}


def _repo_root() -> Path:
    for parent in GHAGEN_ROOT.parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    pytest.skip("not running from a source checkout")


def _declared() -> dict[str, str]:
    """Map normalized distribution name -> the raw requirement string."""
    manifest = tomllib.loads((_repo_root() / "pyproject.toml").read_text())
    out: dict[str, str] = {}
    for req in manifest["project"]["dependencies"]:
        name = req.split(";")[0]
        for sep in ("[", "=", "<", ">", "!", "~", " "):
            name = name.split(sep)[0]
        out[name.strip().lower().replace("_", "-")] = req
    return out


def _imported_top_level_modules() -> set[str]:
    """Every top-level module name imported anywhere under ``ghagen/``."""
    found: set[str] = set()
    for path in sorted(GHAGEN_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found.update(alias.name.split(".")[0] for alias in node.names)
            # level > 0 is a relative import -- first-party by construction.
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                found.add(node.module.split(".")[0])
    return found - sys.stdlib_module_names - FIRST_PARTY - UNDECLARED_BY_DESIGN


class TestDeclaredDependencies:
    def test_every_imported_distribution_is_declared(self) -> None:
        """No third-party import may arrive as somebody else's transitive."""
        module_to_dists = packages_distributions()
        declared = _declared()

        undeclared: dict[str, list[str]] = {}
        for module in sorted(_imported_top_level_modules()):
            dists = module_to_dists.get(module)
            assert dists, f"import of {module!r} resolves to no installed distribution"
            normalized = {d.lower().replace("_", "-") for d in dists}
            if not normalized & declared.keys():
                undeclared[module] = sorted(dists)

        assert not undeclared, (
            "ghagen imports these distributions but pyproject.toml does not "
            f"declare them: {undeclared}. Declared: {sorted(declared)}"
        )

    def test_click_is_declared_directly(self) -> None:
        """The specific case ADR-0009 records, pinned by name."""
        assert "click" in _declared()

    def test_typer_is_capped_below_the_click_vendoring(self) -> None:
        """typer 0.25+ vendors click as the private ``typer._click``.

        Without a ceiling the resolver picks it and ``cli/main.py``'s
        ``from click.exceptions import ...`` raises. The cap is what makes the
        upgrade a deliberate migration instead of a silent break.
        """
        assert "<0.25" in _declared()["typer"]
