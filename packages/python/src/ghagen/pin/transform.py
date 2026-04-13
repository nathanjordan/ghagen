"""PinTransform — model-level transform that applies lockfile SHAs.

Replaces ``Step.uses`` and ``Job.uses`` values with their pinned SHAs
from the lockfile, and attaches the original ref as a YAML end-of-line
comment via ``field_eol_comments``.
"""

from __future__ import annotations

from ghagen.models._base import GhagenModel
from ghagen.models.action import Action, CompositeRuns
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

    def __call__(
        self, item: Workflow | Action, ctx: SynthContext
    ) -> Workflow | Action:
        if isinstance(item, Workflow):
            self._pin_workflow(item)
        elif isinstance(item, Action) and isinstance(item.runs, CompositeRuns):
            self._pin_steps(item.runs.steps)
        return item

    def _pin_workflow(self, wf: Workflow) -> None:
        for job in wf.jobs.values():
            if not isinstance(job, GhagenModel):
                continue

            # Job.uses — reusable workflow calls
            uses = getattr(job, "uses", None)
            if isinstance(uses, str):
                pinned = self._pin_uses(uses, model=job)
                if pinned is not None:
                    job.uses = pinned  # type: ignore[assignment]

            # Step.uses — action references
            self._pin_steps(getattr(job, "steps", None) or [])

    def _pin_steps(self, steps: list[object]) -> None:
        """Rewrite ``step.uses`` to its pinned SHA for each :class:`Step`."""
        for step in steps:
            if not isinstance(step, Step):
                continue
            if step.uses:
                pinned = self._pin_uses(step.uses, model=step)
                if pinned is not None:
                    step.uses = pinned

    def _pin_uses(
        self, uses: str, model: GhagenModel | None = None
    ) -> str | None:
        """Return the pinned ``uses:`` string, or None if not pinnable."""
        # Skip local paths and docker images.
        if uses.startswith("./") or uses.startswith("docker://"):
            return None

        if "@" not in uses:
            return None

        entry = self._lockfile.get(uses)
        if entry is None:
            raise PinError(
                f"No lockfile entry for '{uses}'. "
                "Run `ghagen pin` to resolve it."
            )

        action_part, ref = uses.rsplit("@", 1)
        pinned = f"{action_part}@{entry.sha}"

        # Attach original ref as EOL comment on the model.
        if model is not None:
            model.field_eol_comments["uses"] = ref

        return pinned
