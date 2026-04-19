/**
 * Canonical key orderings for GitHub Actions YAML output.
 *
 * Each array defines the order in which keys appear in the generated YAML
 * for a given model type, matching the conventional ordering used in
 * GitHub Actions documentation and examples.
 *
 * @module
 */

export const ON_KEY_ORDER = [] as const;

export const WORKFLOW_KEY_ORDER = [
  "name",
  "run-name",
  "on",
  "permissions",
  "env",
  "defaults",
  "concurrency",
  "jobs",
] as const;

export const JOB_KEY_ORDER = [
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
] as const;

export const STEP_KEY_ORDER = [
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
] as const;

export const TRIGGER_KEY_ORDER = [
  "branches",
  "branches-ignore",
  "tags",
  "tags-ignore",
  "paths",
  "paths-ignore",
  "types",
] as const;

export const STRATEGY_KEY_ORDER = ["matrix", "fail-fast", "max-parallel"] as const;

export const MATRIX_KEY_ORDER = ["include", "exclude"] as const;

export const CONTAINER_KEY_ORDER = [
  "image",
  "credentials",
  "env",
  "ports",
  "volumes",
  "options",
] as const;

export const CONCURRENCY_KEY_ORDER = ["group", "cancel-in-progress"] as const;

export const DEFAULTS_KEY_ORDER = ["run"] as const;

export const PERMISSIONS_KEY_ORDER = [
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
] as const;

export const WORKFLOW_DISPATCH_KEY_ORDER = ["description", "inputs"] as const;

export const WORKFLOW_DISPATCH_INPUT_KEY_ORDER = [
  "description",
  "required",
  "default",
  "type",
  "options",
] as const;

export const WORKFLOW_CALL_KEY_ORDER = ["inputs", "outputs", "secrets"] as const;

export const ENVIRONMENT_KEY_ORDER = ["name", "url"] as const;

export const ACTION_KEY_ORDER = [
  "name",
  "description",
  "author",
  "branding",
  "inputs",
  "outputs",
  "runs",
] as const;

export const ACTION_INPUT_KEY_ORDER = [
  "description",
  "required",
  "default",
  "deprecationMessage",
] as const;

export const ACTION_OUTPUT_KEY_ORDER = ["description", "value"] as const;

export const BRANDING_KEY_ORDER = ["icon", "color"] as const;

export const COMPOSITE_RUNS_KEY_ORDER = ["using", "steps"] as const;

export const DOCKER_RUNS_KEY_ORDER = [
  "using",
  "image",
  "env",
  "args",
  "pre-entrypoint",
  "pre-if",
  "entrypoint",
  "post-entrypoint",
  "post-if",
] as const;

export const NODE_RUNS_KEY_ORDER = ["using", "main", "pre", "post", "pre-if", "post-if"] as const;
