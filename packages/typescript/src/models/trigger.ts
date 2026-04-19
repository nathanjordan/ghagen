import type {
  OnModel,
  PushTriggerModel,
  PRTriggerModel,
  ScheduleTriggerModel,
  WorkflowDispatchModel,
  WorkflowCallModel,
  WithMeta,
} from "./_base.js";
import { createModel, extractMeta, mapFields, isModel } from "./_base.js";
import {
  ON_KEY_ORDER,
  TRIGGER_KEY_ORDER,
  WORKFLOW_DISPATCH_KEY_ORDER,
  WORKFLOW_CALL_KEY_ORDER,
} from "../emitter/key-order.js";

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

const PUSH_TRIGGER_FIELD_MAP = {
  branches: "branches",
  branchesIgnore: "branches-ignore",
  tags: "tags",
  tagsIgnore: "tags-ignore",
  paths: "paths",
  pathsIgnore: "paths-ignore",
} as const;

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
 */
export function pushTrigger(input: WithMeta<PushTriggerInput>): PushTriggerModel {
  const [data, meta] = extractMeta(input);
  const yamlData = mapFields(data as Record<string, unknown>, PUSH_TRIGGER_FIELD_MAP);
  return createModel("pushTrigger", yamlData, meta, TRIGGER_KEY_ORDER) as PushTriggerModel;
}

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

const PR_TRIGGER_FIELD_MAP = {
  branches: "branches",
  branchesIgnore: "branches-ignore",
  tags: "tags",
  tagsIgnore: "tags-ignore",
  paths: "paths",
  pathsIgnore: "paths-ignore",
  types: "types",
} as const;

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
 */
export function prTrigger(input: WithMeta<PRTriggerInput>): PRTriggerModel {
  const [data, meta] = extractMeta(input);
  const yamlData = mapFields(data as Record<string, unknown>, PR_TRIGGER_FIELD_MAP);
  return createModel("prTrigger", yamlData, meta, TRIGGER_KEY_ORDER) as PRTriggerModel;
}

/**
 * Input for cron-based schedule trigger configuration.
 */
export interface ScheduleTriggerInput {
  /** POSIX cron expression (e.g., `"0 0 * * *"` for daily at midnight). */
  cron: string;
  /** IANA timezone for the cron schedule. */
  timezone?: string;
}

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
 */
export function scheduleTrigger(input: WithMeta<ScheduleTriggerInput>): ScheduleTriggerModel {
  const [data, meta] = extractMeta(input);
  return createModel(
    "scheduleTrigger",
    data as Record<string, unknown>,
    meta,
    [],
  ) as ScheduleTriggerModel;
}

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
  /** Input type (e.g., `"string"`, `"boolean"`, `"choice"`, `"environment"`). */
  type?: "boolean" | "number" | "string" | "choice" | "environment";
  /** Available options when `type` is `"choice"`. */
  options?: string[];
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
 */
export function workflowDispatch(input: WithMeta<WorkflowDispatchInput>): WorkflowDispatchModel {
  const [data, meta] = extractMeta(input);
  return createModel(
    "workflowDispatch",
    data as Record<string, unknown>,
    meta,
    WORKFLOW_DISPATCH_KEY_ORDER,
  ) as WorkflowDispatchModel;
}

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
  /** Input type (`"string"`, `"boolean"`, or `"number"`). */
  type: "boolean" | "number" | "string";
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
 */
export function workflowCall(input: WithMeta<WorkflowCallInput>): WorkflowCallModel {
  const [data, meta] = extractMeta(input);
  return createModel(
    "workflowCall",
    data as Record<string, unknown>,
    meta,
    WORKFLOW_CALL_KEY_ORDER,
  ) as WorkflowCallModel;
}

/**
 * Top-level trigger configuration for the `on:` section of a workflow.
 * Common event types have typed fields; less common events accept plain
 * objects for full flexibility.
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
  /** Branch/tag creation event. Pass `null` for an event with no configuration. */
  create?: Record<string, unknown> | null;
  /** Branch/tag deletion event. The trailing `_` avoids the reserved word; it is stripped during emission. Pass `null` for an event with no configuration. */
  delete_?: Record<string, unknown> | null;
  /** Deployment event configuration. Pass `null` for an event with no configuration. */
  deployment?: Record<string, unknown> | null;
  /** Deployment status event. Pass `null` for an event with no configuration. */
  deploymentStatus?: Record<string, unknown> | null;
  /** Discussion event configuration. */
  discussion?: Record<string, unknown>;
  /** Discussion comment event configuration. */
  discussionComment?: Record<string, unknown>;
  /** Fork event configuration. Pass `null` for an event with no configuration. */
  fork?: Record<string, unknown> | null;
  /** Gollum (wiki) event configuration. Pass `null` for an event with no configuration. */
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
  /** GitHub Pages build event. Pass `null` for an event with no configuration. */
  pageBuild?: Record<string, unknown> | null;
  /** Project event configuration. */
  project?: Record<string, unknown>;
  /** Project card event configuration. */
  projectCard?: Record<string, unknown>;
  /** Project column event configuration. */
  projectColumn?: Record<string, unknown>;
  /** Repository visibility change event. Pass `null` for an event with no configuration. */
  public?: Record<string, unknown> | null;
  /** Registry package event. */
  registryPackage?: Record<string, unknown>;
  /** Release event configuration. */
  release?: Record<string, unknown>;
  /** Repository dispatch event. Pass `null` for an event with no configuration. */
  repositoryDispatch?: Record<string, unknown> | null;
  /** Commit status event. Pass `null` for an event with no configuration. */
  status?: Record<string, unknown> | null;
  /** Watch/star event configuration. Pass `null` for an event with no configuration. */
  watch?: Record<string, unknown> | null;
  /** Workflow run event configuration. */
  workflowRun?: Record<string, unknown>;
}

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
  public: "public",
  registryPackage: "registry_package",
  release: "release",
  repositoryDispatch: "repository_dispatch",
  status: "status",
  watch: "watch",
  workflowRun: "workflow_run",
} as const;

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
 */
export function on(input: WithMeta<OnInput>): OnModel {
  const [data, meta] = extractMeta(input);
  const yamlData: Record<string, unknown> = {};

  for (const [camelKey, yamlKey] of Object.entries(ON_FIELD_MAP)) {
    const value = (data as Record<string, unknown>)[camelKey];
    if (value === undefined) continue;

    // Auto-wrap plain objects with appropriate factory for typed triggers
    if (camelKey === "push" && !isModel(value)) {
      yamlData[yamlKey] = pushTrigger(value as PushTriggerInput);
    } else if (
      (camelKey === "pullRequest" || camelKey === "pullRequestTarget") &&
      !isModel(value)
    ) {
      yamlData[yamlKey] = prTrigger(value as PRTriggerInput);
    } else if (camelKey === "workflowDispatch") {
      if (typeof value === "boolean" || value === null) {
        yamlData[yamlKey] = value;
      } else if (!isModel(value)) {
        yamlData[yamlKey] = workflowDispatch(value as WorkflowDispatchInput);
      } else {
        yamlData[yamlKey] = value;
      }
    } else if (camelKey === "workflowCall" && !isModel(value)) {
      yamlData[yamlKey] = workflowCall(value as WorkflowCallInput);
    } else if (camelKey === "schedule" && Array.isArray(value)) {
      yamlData[yamlKey] = value.map((item) =>
        isModel(item) ? item : scheduleTrigger(item as ScheduleTriggerInput),
      );
    } else {
      yamlData[yamlKey] = value;
    }
  }

  // Sort keys alphabetically (matching Python behavior — no explicit ON_KEY_ORDER)
  const sortedData: Record<string, unknown> = {};
  for (const key of Object.keys(yamlData).sort()) {
    sortedData[key] = yamlData[key];
  }

  return createModel("on", sortedData, meta, ON_KEY_ORDER) as OnModel;
}
