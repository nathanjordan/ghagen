import type { HttpsJsonSchemastoreOrgGithubWorkflowJson as SchemaWorkflow } from "../generated/workflow-types.js";
import type {
  WorkflowModel, OnModel, PermissionsModel, ConcurrencyModel, DefaultsModel,
  WithMeta, Raw,
} from "./_base.js";
import { createModel, extractMeta, mapFields, isModel } from "./_base.js";
import { WORKFLOW_KEY_ORDER } from "../emitter/key-order.js";
import type { JobModel } from "./_base.js";
import type { OnInput } from "./trigger.js";
import { on } from "./trigger.js";
import type { PermissionsInput } from "./permissions.js";
import { permissions } from "./permissions.js";
import type { ConcurrencyInput } from "./job.js";
import { concurrency, defaults } from "./job.js";
import type { DefaultsInput } from "./job.js";

export interface WorkflowInput {
  name?: string;
  runName?: string;
  on?: OnModel | OnInput;
  permissions?: PermissionsModel | PermissionsInput | "read-all" | "write-all" | Raw<string>;
  env?: Record<string, string>;
  defaults?: DefaultsModel | DefaultsInput;
  concurrency?: string | ConcurrencyModel | ConcurrencyInput;
  jobs: Record<string, JobModel>;
}

const WORKFLOW_FIELD_MAP = {
  name: "name",
  runName: "run-name",
  on: "on",
  permissions: "permissions",
  env: "env",
  defaults: "defaults",
  concurrency: "concurrency",
  jobs: "jobs",
} as const satisfies Record<keyof WorkflowInput, keyof SchemaWorkflow>;

export function workflow(input: WithMeta<WorkflowInput>): WorkflowModel {
  const [data, meta] = extractMeta(input);
  const yamlData: Record<string, unknown> = {};

  for (const [camelKey, yamlKey] of Object.entries(WORKFLOW_FIELD_MAP)) {
    const value = (data as Record<string, unknown>)[camelKey];
    if (value === undefined) continue;

    if (camelKey === "on" && !isModel(value)) {
      yamlData[yamlKey] = on(value as OnInput);
    } else if (camelKey === "permissions" && typeof value === "object" && !isModel(value)) {
      yamlData[yamlKey] = permissions(value as PermissionsInput);
    } else if (camelKey === "defaults" && typeof value === "object" && !isModel(value)) {
      yamlData[yamlKey] = defaults(value as DefaultsInput);
    } else if (camelKey === "concurrency" && typeof value === "object" && !isModel(value)) {
      yamlData[yamlKey] = concurrency(value as ConcurrencyInput);
    } else {
      yamlData[yamlKey] = value;
    }
  }

  return createModel("workflow", yamlData, meta, WORKFLOW_KEY_ORDER) as WorkflowModel;
}
