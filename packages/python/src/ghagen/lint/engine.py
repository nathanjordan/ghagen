"""Lint engine: iterate workflows × rules and collect violations."""

from __future__ import annotations

import sys

from ghagen.app import App
from ghagen.lint.config import LintConfig
from ghagen.lint.rules import ALL_RULES
from ghagen.lint.rules._base import RuleContext
from ghagen.lint.violation import Violation
from ghagen.models.workflow import Workflow


def run_lint(app: App, config: LintConfig) -> list[Violation]:
    """Run all enabled lint rules against every Workflow in the app.

    Actions (``action.yml``) are not currently linted — v1 scope is
    workflows only.

    A rule that raises an exception is caught and skipped; other rules
    continue. A warning is printed to stderr naming the failing rule.

    Args:
        app: The ghagen :class:`~ghagen.App` with registered workflows.
        config: The :class:`~ghagen.lint.config.LintConfig` to apply.

    Returns:
        A list of :class:`~ghagen.lint.violation.Violation`s in the order
        they were produced.
    """
    # Load lockfile if available so rules can check pin status.
    lockfile = None
    if app.lockfile_path is not None:
        lockfile_full = app.root / app.lockfile_path
        if lockfile_full.is_file():
            from ghagen.pin.lockfile import read_lockfile

            lockfile = read_lockfile(lockfile_full)

    violations: list[Violation] = []

    for item, path in app._items:
        if not isinstance(item, Workflow):
            continue

        workflow_key = path.stem  # e.g. "ci" from "ci.yml"
        ctx = RuleContext(workflow_key=workflow_key, config=config, lockfile=lockfile)

        for rule_fn in ALL_RULES:
            rule_id = rule_fn.meta.id
            if rule_id in config.disable:
                continue
            try:
                for violation in rule_fn(item, ctx):
                    violations.append(violation)
            except Exception as exc:  # noqa: BLE001 — rule isolation is the point
                print(
                    f"warning: rule '{rule_id}' crashed on workflow "
                    f"'{workflow_key}' — skipped ({type(exc).__name__}: {exc})",
                    file=sys.stderr,
                )
                continue

    return violations
