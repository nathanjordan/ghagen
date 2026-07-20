"""PinTransform — model-level transform that applies lockfile SHAs.

Replaces ``Step.uses`` and ``Job.uses`` values with their pinned SHAs
from the lockfile, and attaches the original ref as a YAML end-of-line
comment via :func:`~ghagen.with_eol_comment`.
"""

from __future__ import annotations

from ghagen._commented import unwrap_commented, with_eol_comment
from ghagen.models.action import Action
from ghagen.models.job import Job
from ghagen.models.step import Step
from ghagen.models.workflow import Workflow
from ghagen.pin.lockfile import Lockfile
from ghagen.transforms import SynthContext


class PinError(Exception):
    """Raised when a ``uses:`` ref has no lockfile entry during synthesis."""


class PinTransform:
    """Apply lockfile SHA pins to ``uses:`` references in models.

    This transform is automatically registered by :class:`~ghagen.App`
    when a lockfile is present.
    """

    def __init__(self, lockfile: Lockfile) -> None:
        self._lockfile = lockfile

    def __call__(self, item: Workflow | Action, ctx: SynthContext) -> Workflow | Action:
        for _path, model in item.walk():
            if isinstance(model, Step):
                self._pin_step(model)
            elif isinstance(model, Job):
                self._pin_job(model)
        return item

    def _pin_job(self, job: Job) -> None:
        """Rewrite ``job.uses`` (a reusable workflow call) to its pinned SHA."""
        uses = unwrap_commented(job.uses)
        if isinstance(uses, str):
            pinned = self._pin_uses(uses)
            if pinned is not None:
                job.uses = pinned

    def _pin_step(self, step: Step) -> None:
        """Rewrite ``step.uses`` (an action reference) to its pinned SHA."""
        uses = unwrap_commented(step.uses)
        if uses:
            pinned = self._pin_uses(uses)
            if pinned is not None:
                step.uses = pinned

    def _pin_uses(self, uses: str) -> str | None:
        """Return the pinned ``uses:`` string wrapped with an EOL comment, or None."""
        # Skip local paths and docker images.
        if uses.startswith("./") or uses.startswith("docker://"):
            return None

        if "@" not in uses:
            return None

        entry = self._lockfile.get(uses)
        if entry is None:
            raise PinError(
                f"No lockfile entry for '{uses}'. Run `ghagen pin` to resolve it."
            )

        action_part, ref = uses.rsplit("@", 1)
        pinned = f"{action_part}@{entry.sha}"

        return with_eol_comment(pinned, ref)
