"""App class for multi-file synthesis of workflows and actions."""

from __future__ import annotations

import difflib
from pathlib import Path

from ghagen.models.action import Action
from ghagen.models.workflow import Workflow

_Item = Workflow | Action

#: Conventional directory for GitHub Actions workflows inside a repository.
WORKFLOWS_DIR = Path(".github/workflows")


class App:
    """Collects workflows and actions and synthesizes them to YAML files.

    CDK-inspired pattern: register items, then call :meth:`synth` to write
    them all out. Use :meth:`add_workflow` and :meth:`add_action` for the
    common cases and :meth:`add` as an escape hatch when you need to write
    to a non-conventional path.

    Example::

        app = App()
        app.add_workflow(ci_workflow, "ci.yml")   # .github/workflows/ci.yml
        app.add_workflow(release_workflow, "release.yml")
        app.add_action(my_action)                  # ./action.yml
        app.synth()
    """

    def __init__(
        self,
        root: str | Path = ".",
        header: str | None = None,
        source: str | None = None,
    ) -> None:
        """Initialize the App.

        Args:
            root: Repository root directory. All registered paths are
                resolved relative to this. Defaults to the current
                working directory.
            header: Custom header comment for generated files.
                If ``None``, uses the default ghagen header.
            source: Source file path to include in the header comment.
        """
        self.root = Path(root)
        self.header = header
        self.source = source
        self._items: list[tuple[_Item, Path]] = []

    def add(self, item: _Item, path: str | Path) -> None:
        """Register an item at an explicit path relative to ``root``.

        Use this escape hatch when you need to write to a path that
        doesn't fit the standard conventions. For the common cases,
        prefer :meth:`add_workflow` / :meth:`add_action`.

        Args:
            item: The :class:`~ghagen.Workflow` or :class:`~ghagen.Action`
                to generate.
            path: Output path, relative to ``root``.
        """
        self._items.append((item, Path(path)))

    def add_workflow(self, workflow: Workflow, filename: str) -> None:
        """Register a workflow at ``.github/workflows/{filename}``.

        Args:
            workflow: The :class:`~ghagen.Workflow` to generate.
            filename: Output filename (e.g. ``"ci.yml"``).
        """
        self.add(workflow, WORKFLOWS_DIR / filename)

    def add_action(
        self,
        action: Action,
        dir: str | Path = ".",  # noqa: A002 — shadowing `dir` reads naturally
    ) -> None:
        """Register an action, writing ``{dir}/action.yml``.

        Args:
            action: The :class:`~ghagen.Action` to generate.
            dir: Directory (relative to ``root``) where ``action.yml``
                will be written. Defaults to ``"."`` (the repo root).
        """
        self.add(action, Path(dir) / "action.yml")

    def synth(self) -> list[Path]:
        """Synthesize all registered items to YAML files.

        Returns:
            List of file paths that were written.
        """
        written: list[Path] = []
        for item, rel_path in self._items:
            full = self.root / rel_path
            item.to_yaml_file(
                full,
                header=self.header,
                source=self.source,
            )
            written.append(full)
        return written

    def check(self) -> list[tuple[Path, str]]:
        """Check if generated YAML files are up-to-date with Python definitions.

        Returns:
            List of ``(path, diff)`` tuples for files that are out of date.
            Empty list means everything is in sync.
        """
        stale: list[tuple[Path, str]] = []

        for item, rel_path in self._items:
            full = self.root / rel_path
            expected = item.to_yaml(
                header=self.header,
                source=self.source,
            )

            if not full.exists():
                stale.append((full, f"File does not exist: {full}"))
                continue

            actual = full.read_text()
            if actual != expected:
                diff = difflib.unified_diff(
                    actual.splitlines(keepends=True),
                    expected.splitlines(keepends=True),
                    fromfile=f"{full} (on disk)",
                    tofile=f"{full} (generated)",
                )
                stale.append((full, "".join(diff)))

        return stale
