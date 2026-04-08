"""Rule: flag jobs that don't set an explicit ``timeout-minutes``.

GitHub's default job timeout is 6 hours — long enough for a runaway
build to cost real money. Setting an explicit, shorter timeout bounds
the blast radius of hangs and infinite loops.

Reusable-workflow jobs (``job.uses``) are skipped because their timeout
is owned by the reusable workflow itself.
"""

from __future__ import annotations

from collections.abc import Iterable

from ghagen.lint.rules._base import RuleContext, rule
from ghagen.lint.violation import Severity, Violation
from ghagen.models.workflow import Workflow


@rule(
    id="missing-timeout",
    severity=Severity.WARNING,
    description=(
        "Job has no timeout_minutes set. The default job timeout is 6 hours; "
        "setting an explicit shorter timeout bounds runaway builds."
    ),
)
def check_missing_timeout(
    wf: Workflow, ctx: RuleContext
) -> Iterable[Violation]:
    """Yield a violation for each job missing ``timeout_minutes``."""
    severity = ctx.config.severity.get(
        "missing-timeout", check_missing_timeout.meta.default_severity
    )

    for job_id, job in wf.jobs.items():
        # Reusable workflow jobs have their own timeout handling
        if getattr(job, "uses", None) is not None:
            continue

        if getattr(job, "timeout_minutes", None) is not None:
            continue

        symbolic = f"{ctx.workflow_key}.yml → jobs.{job_id}"
        yield Violation(
            rule_id="missing-timeout",
            severity=severity,
            message=f"Job '{job_id}' has no timeout_minutes set.",
            location=ctx.loc(job, symbolic),
            hint=(
                "Set timeout_minutes=N on the Job to bound its maximum "
                "runtime (the default is 360 minutes / 6 hours)."
            ),
        )
