"""App class for multi-file synthesis of workflows and actions."""

from __future__ import annotations

import difflib
from pathlib import Path

import ghagen._dedent as _dedent_mod
from ghagen.config import load_options
from ghagen.emitter.header import HeaderOption, _UNSET
from ghagen.models.action import Action
from ghagen.models.workflow import Workflow
from ghagen.transforms import SynthContext, Transform

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
        header: HeaderOption | object = _UNSET,
        lockfile: str | Path | None = ".ghagen.lock.yml",
        transforms: list[Transform] | None = None,
    ) -> None:
        """Initialize the App.

        Args:
            root: Repository root directory. All registered output
                paths and the lockfile are resolved relative to this.
                Defaults to the current working directory.
            header: Header comment for generated files.

                - **callable** — called with a
                  :class:`~ghagen.emitter.header.HeaderVariables`
                  object, returns plain text
                - **str** — output verbatim (no interpolation)
                - **None** — suppress header entirely
                - **omitted** — use
                  :data:`~ghagen.emitter.header.DEFAULT_HEADER_FN`
            lockfile: Path to the pin lockfile, relative to *root*.
                Set to ``None`` to disable lockfile auto-loading.
                Defaults to ``".ghagen.lock.yml"``.
            transforms: Additional model transforms to apply during
                synthesis.  The pin transform is auto-registered when
                a lockfile is present; these are appended after it.
        """
        self.root = Path(root)
        self.header = header
        self.lockfile_path = Path(lockfile) if lockfile is not None else None
        self._items: list[tuple[_Item, Path]] = []
        self._transforms: list[Transform] = list(transforms or [])

        # Apply project-level options (e.g. auto_dedent) from .ghagen.yml.
        options = load_options(self.root)
        _dedent_mod.auto_dedent = options.auto_dedent

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

    def _build_transforms(self) -> list[Transform]:
        """Build the full transform list, auto-registering pin if needed."""
        transforms: list[Transform] = []

        if self.lockfile_path is not None:
            full_lockfile = self.root / self.lockfile_path
            if full_lockfile.is_file():
                from ghagen.pin.lockfile import read_lockfile
                from ghagen.pin.transform import PinTransform

                lockfile = read_lockfile(full_lockfile)
                transforms.append(PinTransform(lockfile))

        transforms.extend(self._transforms)
        return transforms

    def _apply_transforms(
        self, item: _Item, rel_path: Path, transforms: list[Transform]
    ) -> _Item:
        """Deep-copy a model and apply all transforms."""
        if not transforms:
            return item

        working = item.model_copy(deep=True)
        item_type = "workflow" if isinstance(item, Workflow) else "action"
        ctx = SynthContext(
            workflow_key=rel_path.stem,
            item_type=item_type,
            root=self.root,
        )
        for transform in transforms:
            working = transform(working, ctx)
        return working

    def synth(self) -> list[Path]:
        """Synthesize all registered items to YAML files.

        Returns:
            List of file paths that were written.
        """
        transforms = self._build_transforms()
        written: list[Path] = []
        for item, rel_path in self._items:
            full = self.root / rel_path
            working = self._apply_transforms(item, rel_path, transforms)
            working.to_yaml_file(full, header=self.header)
            written.append(full)
        return written

    def check(self) -> list[tuple[Path, str]]:
        """Check if generated YAML files are up-to-date with Python definitions.

        Returns:
            List of ``(path, diff)`` tuples for files that are out of date.
            Empty list means everything is in sync.
        """
        transforms = self._build_transforms()
        stale: list[tuple[Path, str]] = []

        for item, rel_path in self._items:
            full = self.root / rel_path
            working = self._apply_transforms(item, rel_path, transforms)
            expected = working.to_yaml(header=self.header)

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
