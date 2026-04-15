import type { PermissionsEvent as SchemaPermissions } from "../generated/workflow-types.js";
import type { PermissionsModel, WithMeta } from "./_base.js";
import { createModel, extractMeta, mapFields } from "./_base.js";
import { PERMISSIONS_KEY_ORDER } from "../emitter/key-order.js";
import type { PermissionLevel } from "./common.js";

export interface PermissionsInput {
  actions?: PermissionLevel;
  checks?: PermissionLevel;
  contents?: PermissionLevel;
  deployments?: PermissionLevel;
  discussions?: PermissionLevel;
  idToken?: PermissionLevel;
  issues?: PermissionLevel;
  packages?: PermissionLevel;
  pages?: PermissionLevel;
  pullRequests?: PermissionLevel;
  repositoryProjects?: PermissionLevel;
  securityEvents?: PermissionLevel;
  statuses?: PermissionLevel;
}

const PERMISSIONS_FIELD_MAP = {
  actions: "actions",
  checks: "checks",
  contents: "contents",
  deployments: "deployments",
  discussions: "discussions",
  idToken: "id-token",
  issues: "issues",
  packages: "packages",
  pages: "pages",
  pullRequests: "pull-requests",
  repositoryProjects: "repository-projects",
  securityEvents: "security-events",
  statuses: "statuses",
} as const satisfies Record<keyof PermissionsInput, keyof SchemaPermissions>;

export function permissions(input: WithMeta<PermissionsInput>): PermissionsModel {
  const [data, meta] = extractMeta(input);
  const yamlData = mapFields(data as Record<string, unknown>, PERMISSIONS_FIELD_MAP);
  return createModel("permissions", yamlData, meta, PERMISSIONS_KEY_ORDER) as PermissionsModel;
}
