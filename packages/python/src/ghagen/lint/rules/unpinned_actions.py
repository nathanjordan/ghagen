"""Rule: flag steps that use actions pinned to a mutable ref.

Refs like ``@main``, ``@master``, ``@latest``, or a missing ref are
considered unpinned — they can change under the user. Version tags
(``@v4``, ``@v4.1.2``) and commit SHAs (40 hex chars) are accepted.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from ghagen.lint.rules._base import RuleContext, rule
from ghagen.lint.violation import Severity, Violation
from ghagen.models.workflow import Workflow

# Mutable refs that are not safe to depend on.
_UNPINNED_REFS = frozenset({"main", "master", "latest"})

# A 40-character lowercase hex string (a git commit SHA).
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")

# A version tag like v4 or v4.1.2 (optionally with patch/prerelease).
_VERSION_RE = re.compile(r"^v\d+(\.\d+)*([-+][\w.]+)?$")


def _is_pinned_ref(ref: str) -> bool:
    """Return True if ``ref`` looks like an acceptable pinned reference."""
    if ref in _UNPINNED_REFS:
        return False
    if _SHA_RE.match(ref):
        return True
    if _VERSION_RE.match(ref):
        return True
    # Unknown ref shape — accept anything with at least one digit (covers
    # custom tags like "1.2.3" without v prefix). The goal is to flag
    # obviously-mutable refs, not enforce strict versioning.
    return bool(re.search(r"\d", ref))


@rule(
    id="unpinned-actions",
    severity=Severity.WARNING,
    description=(
        "Step references an action by a mutable ref (main/master/latest or "
        "no ref at all). Pin to a version tag or commit SHA for reproducibility."
    ),
)
def check_unpinned_actions(wf: Workflow, ctx: RuleContext) -> Iterable[Violation]:
    """Yield a violation for each step using an unpinned action."""
    severity = ctx.config.severity.get(
        "unpinned-actions", check_unpinned_actions.meta.default_severity
    )

    for job_id, job in wf.jobs.items():
        steps = getattr(job, "steps", None) or []
        for idx, step in enumerate(steps):
            uses = getattr(step, "uses", None)
            if not isinstance(uses, str):
                continue

            # Skip local path references (./path) and docker images.
            if uses.startswith("./") or uses.startswith("docker://"):
                continue

            if "@" in uses:
                _, ref = uses.rsplit("@", 1)
                if _is_pinned_ref(ref):
                    continue

                # If the lockfile covers this ref, treat it as pinned.
                if ctx.lockfile is not None and ctx.lockfile.get(uses) is not None:
                    continue
            # else: no @ref at all → unpinned

            symbolic = f"{ctx.workflow_key}.yml → jobs.{job_id} → steps[{idx}]"
            yield Violation(
                rule_id="unpinned-actions",
                severity=severity,
                message=f"Step uses unpinned action '{uses}'.",
                location=ctx.loc(step, symbolic),
                hint=(
                    "Pin to a version tag (e.g. @v4) or a 40-character commit "
                    "SHA for reproducibility."
                ),
            )
