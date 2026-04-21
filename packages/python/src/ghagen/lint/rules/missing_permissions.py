"""Rule: flag workflows that don't explicitly declare permissions.

GitHub's default ``GITHUB_TOKEN`` has broad write access. Setting an
explicit ``permissions:`` block at the workflow (or per-job) level
follows OWASP's supply-chain hardening guidance.
"""

from __future__ import annotations

from collections.abc import Iterable

from ghagen.lint.rules._base import RuleContext, rule
from ghagen.lint.violation import Severity, Violation
from ghagen.models.workflow import Workflow


@rule(
    id="missing-permissions",
    severity=Severity.WARNING,
    description=(
        "Workflow has no explicit permissions set. The default GITHUB_TOKEN "
        "has broad write access; an explicit permissions block limits scope."
    ),
)
def check_missing_permissions(wf: Workflow, ctx: RuleContext) -> Iterable[Violation]:
    """Flag workflows without top-level permissions unless every job sets them."""
    if wf.permissions is not None:
        return

    # Check if every job sets its own permissions — in that case,
    # the workflow-level omission is fine.
    if wf.jobs and all(
        getattr(job, "permissions", None) is not None for job in wf.jobs.values()
    ):
        return

    severity = ctx.config.severity.get(
        "missing-permissions", check_missing_permissions.meta.default_severity
    )
    yield Violation(
        rule_id="missing-permissions",
        severity=severity,
        message=(
            f"Workflow '{wf.name or ctx.workflow_key}' has no "
            "top-level permissions set."
        ),
        location=ctx.loc(wf, f"{ctx.workflow_key}.yml"),
        hint=(
            'Add permissions=Permissions(contents="read") (or similar) to '
            "limit the default GITHUB_TOKEN scope, or set permissions on "
            "every job individually."
        ),
    )
