"""App class for multi-workflow synthesis."""

from __future__ import annotations

import difflib
from pathlib import Path

from ghagen.models.workflow import Workflow


class App:
    """Collects workflows and synthesizes them to YAML files.

    CDK-inspired pattern: register workflows, then call synth() to write all.

    Example::

        app = App(outdir=".github/workflows")
        app.add(ci_workflow, filename="ci.yml")
        app.add(release_workflow, filename="release.yml")
        app.synth()
    """

    def __init__(
        self,
        outdir: str | Path = ".github/workflows",
        header: str | None = None,
        source: str | None = None,
    ) -> None:
        self.outdir = Path(outdir)
        self.header = header
        self.source = source
        self._workflows: list[tuple[Workflow, str]] = []

    def add(self, workflow: Workflow, filename: str) -> None:
        """Register a workflow to be synthesized.

        Args:
            workflow: The Workflow model to generate.
            filename: The output filename (e.g., "ci.yml").
        """
        self._workflows.append((workflow, filename))

    def synth(self) -> list[Path]:
        """Synthesize all registered workflows to YAML files.

        Returns:
            List of file paths that were written.
        """
        written: list[Path] = []
        self.outdir.mkdir(parents=True, exist_ok=True)

        for workflow, filename in self._workflows:
            path = self.outdir / filename
            workflow.to_yaml_file(
                path,
                header=self.header,
                source=self.source,
            )
            written.append(path)

        return written

    def check(self) -> list[tuple[Path, str]]:
        """Check if generated YAML files are up-to-date with Python definitions.

        Returns:
            List of (path, diff) tuples for files that are out of date.
            Empty list means everything is in sync.
        """
        stale: list[tuple[Path, str]] = []

        for workflow, filename in self._workflows:
            path = self.outdir / filename
            expected = workflow.to_yaml(
                header=self.header,
                source=self.source,
            )

            if not path.exists():
                stale.append((path, f"File does not exist: {path}"))
                continue

            actual = path.read_text()
            if actual != expected:
                diff = difflib.unified_diff(
                    actual.splitlines(keepends=True),
                    expected.splitlines(keepends=True),
                    fromfile=f"{path} (on disk)",
                    tofile=f"{path} (generated)",
                )
                stale.append((path, "".join(diff)))

        return stale
