import type {
  OnModel, PushTriggerModel, PRTriggerModel, ScheduleTriggerModel,
  WorkflowDispatchModel, WorkflowCallModel, WithMeta, Model,
} from "./_base.js";
import { createModel, extractMeta, mapFields, isModel } from "./_base.js";
import { ON_KEY_ORDER, TRIGGER_KEY_ORDER, WORKFLOW_DISPATCH_KEY_ORDER, WORKFLOW_CALL_KEY_ORDER } from "../emitter/key-order.js";

export interface PushTriggerInput {
  branches?: string[];
  branchesIgnore?: string[];
  tags?: string[];
  tagsIgnore?: string[];
  paths?: string[];
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

export function pushTrigger(input: WithMeta<PushTriggerInput>): PushTriggerModel {
  const [data, meta] = extractMeta(input);
  const yamlData = mapFields(data as Record<string, unknown>, PUSH_TRIGGER_FIELD_MAP);
  return createModel("pushTrigger", yamlData, meta, TRIGGER_KEY_ORDER) as PushTriggerModel;
}

export interface PRTriggerInput {
  branches?: string[];
  branchesIgnore?: string[];
  tags?: string[];
  tagsIgnore?: string[];
  paths?: string[];
  pathsIgnore?: string[];
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

export function prTrigger(input: WithMeta<PRTriggerInput>): PRTriggerModel {
  const [data, meta] = extractMeta(input);
  const yamlData = mapFields(data as Record<string, unknown>, PR_TRIGGER_FIELD_MAP);
  return createModel("prTrigger", yamlData, meta, TRIGGER_KEY_ORDER) as PRTriggerModel;
}

export interface ScheduleTriggerInput {
  cron: string;
  timezone?: string;
}

export function scheduleTrigger(input: WithMeta<ScheduleTriggerInput>): ScheduleTriggerModel {
  const [data, meta] = extractMeta(input);
  return createModel("scheduleTrigger", data as Record<string, unknown>, meta, []) as ScheduleTriggerModel;
}

export interface WorkflowDispatchInputDef {
  description?: string;
  required?: boolean;
  default?: string | boolean | number;
  type?: "boolean" | "number" | "string" | "choice" | "environment";
  options?: string[];
}

export interface WorkflowDispatchInput {
  inputs?: Record<string, WorkflowDispatchInputDef>;
}

export function workflowDispatch(input: WithMeta<WorkflowDispatchInput>): WorkflowDispatchModel {
  const [data, meta] = extractMeta(input);
  return createModel("workflowDispatch", data as Record<string, unknown>, meta, WORKFLOW_DISPATCH_KEY_ORDER) as WorkflowDispatchModel;
}

export interface WorkflowCallInputDef {
  description?: string;
  required?: boolean;
  default?: string | boolean | number;
  type: "boolean" | "number" | "string";
}

export interface WorkflowCallOutputDef {
  description?: string;
  value: string;
}

export interface WorkflowCallSecretDef {
  description?: string;
  required?: boolean;
}

export interface WorkflowCallInput {
  inputs?: Record<string, WorkflowCallInputDef>;
  outputs?: Record<string, WorkflowCallOutputDef>;
  secrets?: Record<string, WorkflowCallSecretDef>;
}

export function workflowCall(input: WithMeta<WorkflowCallInput>): WorkflowCallModel {
  const [data, meta] = extractMeta(input);
  return createModel("workflowCall", data as Record<string, unknown>, meta, WORKFLOW_CALL_KEY_ORDER) as WorkflowCallModel;
}

export interface OnInput {
  push?: PushTriggerModel | PushTriggerInput;
  pullRequest?: PRTriggerModel | PRTriggerInput;
  pullRequestTarget?: PRTriggerModel | PRTriggerInput;
  workflowDispatch?: WorkflowDispatchModel | WorkflowDispatchInput | boolean;
  workflowCall?: WorkflowCallModel | WorkflowCallInput;
  schedule?: Array<ScheduleTriggerModel | ScheduleTriggerInput>;
  // Less common event triggers -- accept plain objects
  branchProtectionRule?: Record<string, unknown>;
  checkRun?: Record<string, unknown>;
  checkSuite?: Record<string, unknown>;
  create?: Record<string, unknown> | null;
  delete_?: Record<string, unknown> | null;
  deployment?: Record<string, unknown> | null;
  deploymentStatus?: Record<string, unknown> | null;
  discussion?: Record<string, unknown>;
  discussionComment?: Record<string, unknown>;
  fork?: Record<string, unknown> | null;
  gollum?: Record<string, unknown> | null;
  issueComment?: Record<string, unknown>;
  issues?: Record<string, unknown>;
  label?: Record<string, unknown>;
  mergeGroup?: Record<string, unknown>;
  milestone?: Record<string, unknown>;
  pageBuild?: Record<string, unknown> | null;
  project?: Record<string, unknown>;
  projectCard?: Record<string, unknown>;
  projectColumn?: Record<string, unknown>;
  public?: Record<string, unknown> | null;
  registryPackage?: Record<string, unknown>;
  release?: Record<string, unknown>;
  repositoryDispatch?: Record<string, unknown> | null;
  status?: Record<string, unknown> | null;
  watch?: Record<string, unknown> | null;
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

export function on(input: WithMeta<OnInput>): OnModel {
  const [data, meta] = extractMeta(input);
  const yamlData: Record<string, unknown> = {};

  for (const [camelKey, yamlKey] of Object.entries(ON_FIELD_MAP)) {
    const value = (data as Record<string, unknown>)[camelKey];
    if (value === undefined) continue;

    // Auto-wrap plain objects with appropriate factory for typed triggers
    if (camelKey === "push" && !isModel(value)) {
      yamlData[yamlKey] = pushTrigger(value as PushTriggerInput);
    } else if ((camelKey === "pullRequest" || camelKey === "pullRequestTarget") && !isModel(value)) {
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
        isModel(item) ? item : scheduleTrigger(item as ScheduleTriggerInput)
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
