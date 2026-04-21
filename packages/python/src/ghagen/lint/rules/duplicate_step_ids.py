"""Rule: flag duplicate Step.id values within a single job.

GitHub Actions requires step ids to be unique within a job — when two
steps share an id, references like ``steps.<id>.outputs.<name>`` silently
resolve to only one of them, producing confusing downstream failures.
This rule catches the bug at the Python model level before any YAML is
emitted.

Step ids are scoped per-job: the same id in two different jobs is fine.
"""

from __future__ import annotations

from collections.abc import Iterable

from ruamel.yaml.comments import CommentedMap

from ghagen.lint.rules._base import RuleContext, rule
from ghagen.lint.violation import Severity, Violation
from ghagen.models.step import Step
from ghagen.models.workflow import Workflow


def _step_id(step: Step | CommentedMap) -> str | None:
    """Return the step's id if it has a non-empty string id, else None."""
    if isinstance(step, Step):
        return step.id or None
    # CommentedMap escape-hatch: id may be missing or a non-string value
    raw = step.get("id")
    return raw if isinstance(raw, str) and raw else None


@rule(
    id="duplicate-step-ids",
    severity=Severity.ERROR,
    description=(
        "Two or more steps within a single job share the same id. GitHub "
        "Actions requires step ids to be unique within a job; duplicates "
        "break `steps.<id>.outputs` references."
    ),
)
def check_duplicate_step_ids(wf: Workflow, ctx: RuleContext) -> Iterable[Violation]:
    """Yield a violation for each duplicate ``Step.id`` within a job."""
    severity = ctx.config.severity.get(
        "duplicate-step-ids",
        check_duplicate_step_ids.meta.default_severity,
    )

    for job_id, job in wf.jobs.items():
        seen: dict[str, int] = {}  # id → index of first occurrence
        for index, step in enumerate(job.steps or []):
            step_id = _step_id(step)
            if step_id is None:
                continue
            if step_id in seen:
                first_index = seen[step_id]
                symbolic = f"{ctx.workflow_key}.yml → jobs.{job_id} → steps[{index}]"
                yield Violation(
                    rule_id="duplicate-step-ids",
                    severity=severity,
                    message=(
                        f"Duplicate step id '{step_id}' in job "
                        f"'{job_id}' (first seen at steps[{first_index}])."
                    ),
                    location=ctx.loc(step, symbolic),
                    hint=(
                        "Step ids must be unique within a job. Rename "
                        "this step's id or remove it if it isn't "
                        "referenced via steps.<id>.outputs."
                    ),
                )
            else:
                seen[step_id] = index
