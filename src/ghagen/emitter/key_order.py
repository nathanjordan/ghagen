"""Canonical key orderings for GitHub Actions YAML output."""

WORKFLOW_KEY_ORDER: list[str] = [
    "name",
    "run-name",
    "on",
    "permissions",
    "env",
    "defaults",
    "concurrency",
    "jobs",
]

JOB_KEY_ORDER: list[str] = [
    "name",
    "runs-on",
    "needs",
    "if",
    "permissions",
    "environment",
    "strategy",
    "env",
    "defaults",
    "steps",
    "outputs",
    "timeout-minutes",
    "continue-on-error",
    "concurrency",
    "services",
    "container",
    "uses",
    "with",
    "secrets",
]

STEP_KEY_ORDER: list[str] = [
    "id",
    "name",
    "if",
    "uses",
    "run",
    "with",
    "env",
    "shell",
    "working-directory",
    "continue-on-error",
    "timeout-minutes",
]

TRIGGER_KEY_ORDER: list[str] = [
    "branches",
    "branches-ignore",
    "tags",
    "tags-ignore",
    "paths",
    "paths-ignore",
    "types",
]

STRATEGY_KEY_ORDER: list[str] = [
    "matrix",
    "fail-fast",
    "max-parallel",
]

MATRIX_KEY_ORDER: list[str] = [
    "include",
    "exclude",
]

CONTAINER_KEY_ORDER: list[str] = [
    "image",
    "credentials",
    "env",
    "ports",
    "volumes",
    "options",
]

CONCURRENCY_KEY_ORDER: list[str] = [
    "group",
    "cancel-in-progress",
]

DEFAULTS_KEY_ORDER: list[str] = [
    "run",
]

PERMISSIONS_KEY_ORDER: list[str] = [
    "actions",
    "checks",
    "contents",
    "deployments",
    "discussions",
    "id-token",
    "issues",
    "packages",
    "pages",
    "pull-requests",
    "repository-projects",
    "security-events",
    "statuses",
]

WORKFLOW_DISPATCH_KEY_ORDER: list[str] = [
    "description",
    "inputs",
]

WORKFLOW_DISPATCH_INPUT_KEY_ORDER: list[str] = [
    "description",
    "required",
    "default",
    "type",
    "options",
]

WORKFLOW_CALL_KEY_ORDER: list[str] = [
    "inputs",
    "outputs",
    "secrets",
]

ENVIRONMENT_KEY_ORDER: list[str] = [
    "name",
    "url",
]
