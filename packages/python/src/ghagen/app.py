"""App class for multi-file synthesis of workflows and actions."""

from __future__ import annotations

import difflib
from pathlib import Path

from ghagen.config import DEFAULT_LOCKFILE_PATH, GhagenOptions, load_options
from ghagen.emitter.header import DEFAULT, HeaderInput
from ghagen.models.action import Action
from ghagen.models.workflow import Workflow
from ghagen.synth import render
from ghagen.transforms import Transform

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
        header: HeaderInput = DEFAULT,
        lockfile: str | Path | None = DEFAULT_LOCKFILE_PATH,
        transforms: list[Transform] | None = None,
        options: GhagenOptions | None = None,
    ) -> None:
        """Initialize the App.

        Args:
            root: Repository root directory. All registered output
                paths and the lockfile are resolved relative to this.
                Defaults to the current working directory. Note that
                ``{source_file}`` in the header is resolved separately,
                via the nearest ancestor directory containing
                ``.ghagen.yml``.
            header: Header comment for every generated file. Four
                shapes are accepted:

                - omit (``DEFAULT`` sentinel) — emit ghagen's default
                  header (mentions the originating ``.py`` file).
                - ``None`` — emit no header.
                - ``str`` — emit the string verbatim. No
                  ``{variable}`` substitution; literal braces are
                  preserved.
                - ``Callable[[HeaderVariables], str]`` — invoke with a
                  fully-populated
                  :class:`~ghagen.emitter.header.HeaderVariables` and
                  emit the returned string.
            lockfile: Path to the pin lockfile, relative to *root*.
                Set to ``None`` to disable lockfile auto-loading.
                Defaults to ``".ghagen.lock.yml"``.
            transforms: Additional model transforms to apply during
                synthesis.  The pin transform is auto-registered when
                a lockfile is present; these are appended after it.
            options: Pre-loaded project options. When omitted, ``App`` reads
                them from ``.ghagen.yml`` itself (standalone ``App()`` works
                unchanged); pass a value to avoid a redundant read when the
                config was already parsed.
        """
        self.root = Path(root)
        self.header: HeaderInput = header
        self.lockfile_path = Path(lockfile) if lockfile is not None else None
        self._items: list[tuple[_Item, Path]] = []
        self._transforms: list[Transform] = list(transforms or [])

        # Load project-level options (e.g. auto_dedent) from .ghagen.yml.
        # These are threaded into the emitter at synth/check time rather than
        # applied via a module-level global (ADR-0002). load_options is total —
        # a malformed `entrypoint:` never breaks it.
        resolved_options = options if options is not None else load_options(self.root)
        self._auto_dedent = resolved_options.auto_dedent

    def documents(self) -> list[_Item]:
        """Return the registered Documents (Workflows and Actions).

        The public accessor for pin and other read-only consumers; the
        ``(item, path)`` storage stays private to ``App``.
        """
        return [item for item, _path in self._items]

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
        """Build the full transform list, auto-registering pin last if needed.

        User transforms run first so they see the authored ``uses:`` refs; the
        pin transform runs *last* so it locks whatever refs survive to the end
        of the pipeline, including refs a user transform injected.
        """
        transforms: list[Transform] = list(self._transforms)

        if self.lockfile_path is not None:
            full_lockfile = self.root / self.lockfile_path
            if full_lockfile.is_file():
                from ghagen.pin.lockfile import read_lockfile
                from ghagen.pin.transform import PinTransform

                lockfile = read_lockfile(full_lockfile)
                transforms.append(PinTransform(lockfile))

        return transforms

    def synth(self) -> list[Path]:
        """Synthesize all registered items to YAML files.

        Returns:
            List of file paths that were written.
        """
        written: list[Path] = []
        for r in render(
            self._items,
            self._build_transforms(),
            header=self.header,
            auto_dedent=self._auto_dedent,
        ):
            full = self.root / r.path
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(r.text)
            written.append(full)
        return written

    def check(self) -> list[tuple[Path, str]]:
        """Check if generated YAML files are up-to-date with Python definitions.

        Returns:
            List of ``(path, diff)`` tuples for files that are out of date.
            Empty list means everything is in sync.
        """
        stale: list[tuple[Path, str]] = []
        for r in render(
            self._items,
            self._build_transforms(),
            header=self.header,
            auto_dedent=self._auto_dedent,
        ):
            full = self.root / r.path

            if not full.exists():
                stale.append((full, f"File does not exist: {full}"))
                continue

            actual = full.read_text()
            if actual != r.text:
                diff = difflib.unified_diff(
                    actual.splitlines(keepends=True),
                    r.text.splitlines(keepends=True),
                    fromfile=f"{full} (on disk)",
                    tofile=f"{full} (generated)",
                )
                stale.append((full, "".join(diff)))

        return stale
