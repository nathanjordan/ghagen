import { defineFactory } from "./_base.js";
import type {
  OnModel,
  PushTriggerModel,
  PRTriggerModel,
  ScheduleTriggerModel,
  WorkflowDispatchModel,
  WorkflowDispatchInputModel,
  WorkflowCallModel,
  WorkflowCallInputModel,
  WorkflowCallOutputModel,
  WorkflowCallSecretModel,
  ModelSpec,
  Raw,
} from "./_base.js";

/**
 * Input for `push` event trigger configuration. Filters which pushes
 * trigger the workflow.
 */
export interface PushTriggerInput {
  /** Branch filter patterns (supports glob). */
  branches?: string[];
  /** Branch exclusion patterns. Serialized as `branches-ignore`. */
  branchesIgnore?: string[];
  /** Tag filter patterns. */
  tags?: string[];
  /** Tag exclusion patterns. Serialized as `tags-ignore`. */
  tagsIgnore?: string[];
  /** Path filter patterns. Only pushes affecting these paths trigger the workflow. */
  paths?: string[];
  /** Path exclusion patterns. Serialized as `paths-ignore`. */
  pathsIgnore?: string[];
}

/** Serialization spec for {@link PushTriggerModel}. */
export const PUSH_TRIGGER_SPEC: ModelSpec = {
  kind: "pushTrigger",
  fieldMap: {
    branches: "branches",
    branchesIgnore: "branches-ignore",
    tags: "tags",
    tagsIgnore: "tags-ignore",
    paths: "paths",
    pathsIgnore: "paths-ignore",
  },
};

/**
 * Create a push trigger model for the `on.push` configuration.
 *
 * @param input - Push trigger filter properties and optional model metadata.
 * @returns A `PushTriggerModel` for use in an `OnInput`.
 *
 * @example
 * ```ts
 * pushTrigger({
 *   branches: ["main", "release/*"],
 *   paths: ["src/**"],
 *   pathsIgnore: ["docs/**"],
 * })
 * ```
 * @function
 */
export const pushTrigger = defineFactory<PushTriggerModel, PushTriggerInput>(PUSH_TRIGGER_SPEC);

/**
 * Input for `pull_request` and `pull_request_target` event trigger
 * configuration. Filters which pull request events trigger the workflow.
 */
export interface PRTriggerInput {
  /** Branch filter patterns (matches the PR's base branch). */
  branches?: string[];
  /** Branch exclusion patterns. Serialized as `branches-ignore`. */
  branchesIgnore?: string[];
  /** Tag filter patterns. */
  tags?: string[];
  /** Tag exclusion patterns. Serialized as `tags-ignore`. */
  tagsIgnore?: string[];
  /** Path filter patterns. */
  paths?: string[];
  /** Path exclusion patterns. Serialized as `paths-ignore`. */
  pathsIgnore?: string[];
  /** Activity types to filter on (e.g., `["opened", "synchronize", "reopened"]`). */
  types?: string[];
}

/** Serialization spec for {@link PRTriggerModel}. */
export const PR_TRIGGER_SPEC: ModelSpec = {
  kind: "prTrigger",
  fieldMap: {
    branches: "branches",
    branchesIgnore: "branches-ignore",
    tags: "tags",
    tagsIgnore: "tags-ignore",
    paths: "paths",
    pathsIgnore: "paths-ignore",
    types: "types",
  },
};

/**
 * Create a pull request trigger model for the `on.pull_request` or
 * `on.pull_request_target` configuration.
 *
 * @param input - PR trigger filter properties and optional model metadata.
 * @returns A `PRTriggerModel` for use in an `OnInput`.
 *
 * @example
 * ```ts
 * prTrigger({
 *   branches: ["main"],
 *   types: ["opened", "synchronize"],
 * })
 * ```
 * @function
 */
export const prTrigger = defineFactory<PRTriggerModel, PRTriggerInput>(PR_TRIGGER_SPEC);

/**
 * Input for cron-based schedule trigger configuration.
 */
export interface ScheduleTriggerInput {
  /** POSIX cron expression (e.g., `"0 0 * * *"` for daily at midnight). */
  cron: string;
  /** IANA timezone for the cron schedule. */
  timezone?: string;
}

/** Serialization spec for {@link ScheduleTriggerModel}. */
export const SCHEDULE_TRIGGER_SPEC: ModelSpec = {
  kind: "scheduleTrigger",
  fieldMap: { cron: "cron", timezone: "timezone" },
};

/**
 * Create a schedule trigger model for cron-based workflow execution.
 *
 * @param input - Cron expression and optional model metadata.
 * @returns A `ScheduleTriggerModel` for use in `OnInput.schedule`.
 *
 * @example
 * ```ts
 * scheduleTrigger({ cron: "0 0 * * 1" }) // Every Monday at midnight
 * ```
 * @function
 */
export const scheduleTrigger = defineFactory<ScheduleTriggerModel, ScheduleTriggerInput>(
  SCHEDULE_TRIGGER_SPEC,
);

/**
 * Definition for a single input parameter on a `workflow_dispatch` trigger.
 */
export interface WorkflowDispatchInputDef {
  /** Human-readable description of the input. */
  description?: string;
  /** Whether the input is required. */
  required?: boolean;
  /** Default value for the input. */
  default?: string | boolean | number;
  /**
   * Input type (e.g., `"string"`, `"boolean"`, `"choice"`, `"environment"`).
   *
   * Five members here, three on {@link WorkflowCallInputDef.type}: the
   * canonical Snapshot gives the two events different enums. `raw("...")`
   * escapes the union.
   */
  type?: "boolean" | "number" | "string" | "choice" | "environment" | Raw<string>;
  /** Available options when `type` is `"choice"`. */
  options?: string[];
  /**
   * Deprecation notice shown next to the input in the dispatch UI. Emitted as
   * `deprecationMessage` — the Snapshot spells this key in camelCase while its
   * five siblings are lowercase.
   */
  deprecationMessage?: string;
}

/**
 * Input for `workflow_dispatch` (manual) trigger configuration. Allows
 * defining input parameters that users provide when triggering the
 * workflow manually.
 */
export interface WorkflowDispatchInput {
  /** Input parameter definitions, keyed by input name. */
  inputs?: Record<string, WorkflowDispatchInputDef>;
}

/**
 * Serialization spec for a single `workflow_dispatch` input definition.
 *
 * Gives dispatch input defs canonical key ordering (description, required,
 * default, type, options) instead of the user's insertion order.
 */
export const WORKFLOW_DISPATCH_INPUT_SPEC: ModelSpec = {
  kind: "workflowDispatchInput",
  fieldMap: {
    description: "description",
    required: "required",
    default: "default",
    type: "type",
    options: "options",
    deprecationMessage: "deprecationMessage",
  },
};

/** Wrap one `workflow_dispatch` input def into an ordered model. */
const workflowDispatchInputDef = defineFactory<
  WorkflowDispatchInputModel,
  WorkflowDispatchInputDef
>(WORKFLOW_DISPATCH_INPUT_SPEC);

/** Serialization spec for {@link WorkflowDispatchModel}. */
export const WORKFLOW_DISPATCH_SPEC: ModelSpec = {
  kind: "workflowDispatch",
  fieldMap: { inputs: "inputs" },
  wrap: { inputs: { factory: workflowDispatchInputDef, mode: "map" } },
};

/**
 * Create a workflow dispatch trigger model for manual workflow execution.
 *
 * @param input - Dispatch input definitions and optional model metadata.
 * @returns A `WorkflowDispatchModel` for use in an `OnInput`.
 *
 * @example
 * ```ts
 * workflowDispatch({
 *   inputs: {
 *     environment: {
 *       description: "Deployment target",
 *       required: true,
 *       type: "choice",
 *       options: ["staging", "production"],
 *     },
 *   },
 * })
 * ```
 * @function
 */
export const workflowDispatch = defineFactory<WorkflowDispatchModel, WorkflowDispatchInput>(
  WORKFLOW_DISPATCH_SPEC,
);

/**
 * Definition for a single input parameter on a `workflow_call` trigger.
 */
export interface WorkflowCallInputDef {
  /** Human-readable description of the input. */
  description?: string;
  /** Whether the input is required. */
  required?: boolean;
  /** Default value. */
  default?: string | boolean | number;
  /**
   * Input type (`"string"`, `"boolean"`, or `"number"`). Required — the
   * Snapshot marks it so. `raw("...")` escapes the union.
   */
  type: "boolean" | "number" | "string" | Raw<string>;
}

/**
 * Definition for a single output on a `workflow_call` trigger.
 */
export interface WorkflowCallOutputDef {
  /** Human-readable description. */
  description?: string;
  /** The output value, typically referencing a job output expression. */
  value: string;
}

/**
 * Definition for a single secret on a `workflow_call` trigger.
 */
export interface WorkflowCallSecretDef {
  /** Human-readable description. */
  description?: string;
  /** Whether the secret is required. */
  required?: boolean;
}

/**
 * Input for `workflow_call` (reusable workflow) trigger configuration.
 * Defines the interface for a workflow that can be called by other
 * workflows.
 */
export interface WorkflowCallInput {
  /** Input parameter definitions. */
  inputs?: Record<string, WorkflowCallInputDef>;
  /** Output definitions. */
  outputs?: Record<string, WorkflowCallOutputDef>;
  /** Secret definitions. */
  secrets?: Record<string, WorkflowCallSecretDef>;
}

/**
 * Serialization spec for a single `workflow_call` input definition.
 *
 * Python models each `workflow_call` sub-map entry as its own model with its
 * own spec, so it emits canonical key order; TypeScript had no spec for any of
 * the three, so the defs reached the Emitter as plain objects and emitted in
 * the author's insertion order. Python's order is the reference.
 */
export const WORKFLOW_CALL_INPUT_SPEC: ModelSpec = {
  kind: "workflowCallInput",
  fieldMap: {
    description: "description",
    required: "required",
    default: "default",
    type: "type",
  },
};

/** Serialization spec for a single `workflow_call` output definition. */
export const WORKFLOW_CALL_OUTPUT_SPEC: ModelSpec = {
  kind: "workflowCallOutput",
  fieldMap: { description: "description", value: "value" },
};

/** Serialization spec for a single `workflow_call` secret definition. */
export const WORKFLOW_CALL_SECRET_SPEC: ModelSpec = {
  kind: "workflowCallSecret",
  fieldMap: { description: "description", required: "required" },
};

/** Wrap one `workflow_call` input def into an ordered model. */
const workflowCallInputDef = defineFactory<WorkflowCallInputModel, WorkflowCallInputDef>(
  WORKFLOW_CALL_INPUT_SPEC,
);

/** Wrap one `workflow_call` output def into an ordered model. */
const workflowCallOutputDef = defineFactory<WorkflowCallOutputModel, WorkflowCallOutputDef>(
  WORKFLOW_CALL_OUTPUT_SPEC,
);

/** Wrap one `workflow_call` secret def into an ordered model. */
const workflowCallSecretDef = defineFactory<WorkflowCallSecretModel, WorkflowCallSecretDef>(
  WORKFLOW_CALL_SECRET_SPEC,
);

/** Serialization spec for {@link WorkflowCallModel}. */
export const WORKFLOW_CALL_SPEC: ModelSpec = {
  kind: "workflowCall",
  fieldMap: { inputs: "inputs", outputs: "outputs", secrets: "secrets" },
  wrap: {
    inputs: { factory: workflowCallInputDef, mode: "map" },
    outputs: { factory: workflowCallOutputDef, mode: "map" },
    secrets: { factory: workflowCallSecretDef, mode: "map" },
  },
};

/**
 * Create a workflow call trigger model for reusable workflow interfaces.
 *
 * @param input - Inputs, outputs, secrets definitions and optional model metadata.
 * @returns A `WorkflowCallModel` for use in an `OnInput`.
 *
 * @example
 * ```ts
 * workflowCall({
 *   inputs: {
 *     environment: {
 *       description: "Target environment",
 *       required: true,
 *       type: "string",
 *     },
 *   },
 *   secrets: {
 *     DEPLOY_TOKEN: { description: "Deployment token", required: true },
 *   },
 * })
 * ```
 * @function
 */
export const workflowCall = defineFactory<WorkflowCallModel, WorkflowCallInput>(WORKFLOW_CALL_SPEC);

/**
 * Top-level trigger configuration for the `on:` section of a workflow.
 * Common event types have typed fields; less common events accept plain
 * objects for full flexibility.
 *
 * **`{}` is the event, `null` is no event.** An empty object emits GitHub's
 * documented bare-key form (`create:`) for any event here, filterless or
 * merely unfiltered; `null` — like omitting the field — means *unset* and
 * drops the key entirely, the peer of Python's `None` under `exclude_none`.
 * The two used to disagree across the ports, and they emitted semantically
 * different workflows: see `docs/issues/04`.
 */
export interface OnInput {
  /** Push event configuration. Accepts a `PushTriggerModel` or an inline `PushTriggerInput`. */
  push?: PushTriggerModel | PushTriggerInput;
  /** Pull request event configuration. Accepts a `PRTriggerModel` or an inline `PRTriggerInput`. */
  pullRequest?: PRTriggerModel | PRTriggerInput;
  /** Pull request target event configuration. Accepts a `PRTriggerModel` or an inline `PRTriggerInput`. */
  pullRequestTarget?: PRTriggerModel | PRTriggerInput;
  /** Manual dispatch trigger. Set to `true` for no inputs, or provide a `WorkflowDispatchModel` / `WorkflowDispatchInput`. */
  workflowDispatch?: WorkflowDispatchModel | WorkflowDispatchInput | boolean;
  /** Reusable workflow call trigger. Accepts a `WorkflowCallModel` or an inline `WorkflowCallInput`. */
  workflowCall?: WorkflowCallModel | WorkflowCallInput;
  /** Cron schedule triggers. Each entry is a `ScheduleTriggerModel` or an inline `ScheduleTriggerInput`. */
  schedule?: Array<ScheduleTriggerModel | ScheduleTriggerInput>;
  // Less common event triggers -- accept plain objects
  /** Branch protection rule event configuration. */
  branchProtectionRule?: Record<string, unknown>;
  /** Check run event configuration. */
  checkRun?: Record<string, unknown>;
  /** Check suite event configuration. */
  checkSuite?: Record<string, unknown>;
  /** Branch/tag creation event. Pass `{}` for an event with no configuration. */
  create?: Record<string, unknown> | null;
  /** Branch/tag deletion event. The trailing `_` avoids the reserved word; it is stripped during emission. Pass `{}` for an event with no configuration. */
  delete_?: Record<string, unknown> | null;
  /** Deployment event configuration. Pass `{}` for an event with no configuration. */
  deployment?: Record<string, unknown> | null;
  /** Deployment status event. Pass `{}` for an event with no configuration. */
  deploymentStatus?: Record<string, unknown> | null;
  /** Discussion event configuration. */
  discussion?: Record<string, unknown>;
  /** Discussion comment event configuration. */
  discussionComment?: Record<string, unknown>;
  /** Fork event configuration. Pass `{}` for an event with no configuration. */
  fork?: Record<string, unknown> | null;
  /** Gollum (wiki) event configuration. Pass `{}` for an event with no configuration. */
  gollum?: Record<string, unknown> | null;
  /** Issue comment event configuration. */
  issueComment?: Record<string, unknown>;
  /** Issues event configuration. */
  issues?: Record<string, unknown>;
  /** Label event configuration. */
  label?: Record<string, unknown>;
  /** Merge group event configuration. */
  mergeGroup?: Record<string, unknown>;
  /** Milestone event configuration. */
  milestone?: Record<string, unknown>;
  /** GitHub Pages build event. Pass `{}` for an event with no configuration. */
  pageBuild?: Record<string, unknown> | null;
  /** Project event configuration. */
  project?: Record<string, unknown>;
  /** Project card event configuration. */
  projectCard?: Record<string, unknown>;
  /** Project column event configuration. */
  projectColumn?: Record<string, unknown>;
  /** Pull request review event configuration. */
  pullRequestReview?: Record<string, unknown>;
  /** Pull request review comment event configuration. */
  pullRequestReviewComment?: Record<string, unknown>;
  /** Repository visibility change event. Pass `{}` for an event with no configuration. */
  public?: Record<string, unknown> | null;
  /** Registry package event. */
  registryPackage?: Record<string, unknown>;
  /** Release event configuration. */
  release?: Record<string, unknown>;
  /** Repository dispatch event. Pass `{}` for an event with no configuration. */
  repositoryDispatch?: Record<string, unknown> | null;
  /** Commit status event. Pass `{}` for an event with no configuration. */
  status?: Record<string, unknown> | null;
  /** Watch/star event configuration. Pass `{}` for an event with no configuration. */
  watch?: Record<string, unknown> | null;
  /** Workflow run event configuration. */
  workflowRun?: Record<string, unknown>;
}

/**
 * The `on:` field map — every event key {@link OnModel} models, and the single
 * source both {@link ON_SPEC}'s `fieldMap` and its `presentNullWhenEmpty` are
 * read from.
 *
 * Declared apart from the spec only so the present-null rule can be derived
 * from it; `order` is `alphabetical`, so this declaration order is UNREAD (the
 * Emitter sorts every key at emit time).
 */
const ON_FIELD_MAP = {
  push: "push",
  pullRequest: "pull_request",
  pullRequestTarget: "pull_request_target",
  workflowDispatch: "workflow_dispatch",
  workflowCall: "workflow_call",
  schedule: "schedule",
  branchProtectionRule: "branch_protection_rule",
  checkRun: "check_run",
  checkSuite: "check_suite",
  create: "create",
  delete_: "delete",
  deployment: "deployment",
  deploymentStatus: "deployment_status",
  discussion: "discussion",
  discussionComment: "discussion_comment",
  fork: "fork",
  gollum: "gollum",
  issueComment: "issue_comment",
  issues: "issues",
  label: "label",
  mergeGroup: "merge_group",
  milestone: "milestone",
  pageBuild: "page_build",
  project: "project",
  projectCard: "project_card",
  projectColumn: "project_column",
  pullRequestReview: "pull_request_review",
  pullRequestReviewComment: "pull_request_review_comment",
  public: "public",
  registryPackage: "registry_package",
  release: "release",
  repositoryDispatch: "repository_dispatch",
  status: "status",
  watch: "watch",
  workflowRun: "workflow_run",
} as const;

/**
 * Serialization spec for {@link OnModel}.
 *
 * `order` is `alphabetical` — the one spec in the port that is not the default
 * `explicit`: the Emitter sorts every key (typed triggers and dynamic extra
 * events alike) at emit time, matching Python's alphabetical trigger emission.
 * The sort lives in one place, not in this factory. The typed trigger fields
 * carry auto-wrap rules; the plain-object event fields pass through untouched.
 */
export const ON_SPEC: ModelSpec = {
  kind: "on",
  fieldMap: ON_FIELD_MAP,
  order: "alphabetical",
  // Every event key, DERIVED from `ON_FIELD_MAP` rather than listed: an empty
  // map is never the right emission for an `on:` event. GitHub's documented
  // spelling for "this event, no filters" is the bare key — `create:` for an
  // event that takes no filters at all, and equally `push:` or
  // `workflow_call:` for one whose filters were simply left empty. The
  // allowlist used to name `workflow_dispatch` alone, which was not a decision
  // about `workflow_dispatch` — it was the one key somebody needed.
  //
  // It is derived, not listed, so it cannot fall out of date: adding an event
  // to `ON_FIELD_MAP` adds it here in the same edit, and there is no second
  // list for a guard test to compare against the first. (`schema/key-order.yml`
  // already binds this key set across the two ports, so the derivation inherits
  // that cross-port binding for free.) The peer of Python's
  // `present_null_when_empty=frozenset(_ON_YAML_KEYS.values())`.
  presentNullWhenEmpty: Object.values(ON_FIELD_MAP),
  wrap: {
    push: { factory: pushTrigger, mode: "model" },
    pullRequest: { factory: prTrigger, mode: "model" },
    pullRequestTarget: { factory: prTrigger, mode: "model" },
    workflowDispatch: { factory: workflowDispatch, mode: "dispatch" },
    workflowCall: { factory: workflowCall, mode: "model" },
    schedule: { factory: scheduleTrigger, mode: "list" },
  },
};

/**
 * Create a trigger configuration model for the `on:` section of a workflow.
 * Plain-object values for typed trigger fields (`push`, `pullRequest`,
 * `workflowDispatch`, `workflowCall`, `schedule` entries) are automatically
 * wrapped with their respective factory functions.
 *
 * @param input - Trigger event definitions and optional model metadata.
 * @returns An `OnModel` for use in a `WorkflowInput`.
 *
 * @example
 * ```ts
 * on({
 *   push: { branches: ["main"] },
 *   pullRequest: { branches: ["main"] },
 *   workflowDispatch: true,
 * })
 * ```
 * @function
 */
export const on = defineFactory<OnModel, OnInput>(ON_SPEC);
