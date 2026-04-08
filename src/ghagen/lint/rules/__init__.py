"""Built-in lint rules for ghagen workflows."""

from ghagen.lint.rules._base import Rule, RuleContext, RuleMeta, rule
from ghagen.lint.rules.missing_permissions import check_missing_permissions
from ghagen.lint.rules.missing_timeout import check_missing_timeout
from ghagen.lint.rules.unpinned_actions import check_unpinned_actions

# All built-in rules, registered in the order they should run.
ALL_RULES: list[Rule] = [
    check_missing_permissions,
    check_unpinned_actions,
    check_missing_timeout,
]

__all__ = [
    "ALL_RULES",
    "Rule",
    "RuleContext",
    "RuleMeta",
    "rule",
]
