import type { PermissionsEvent as SchemaPermissions } from "../schema/workflow-types.generated.js";
import type { PermissionsModel, WithMeta } from "./_base.js";
import { createModel, extractMeta, mapFields } from "./_base.js";
import { PERMISSIONS_KEY_ORDER } from "../emitter/key-order.js";
import type { PermissionLevel } from "./common.js";

/**
 * Input for configuring `GITHUB_TOKEN` permission scopes at the workflow or
 * job level. Each scope can be set to `"read"`, `"write"`, or `"none"`.
 * Only set the scopes you need; unset scopes are omitted from the output.
 */
export interface PermissionsInput {
  /** Permission for the `actions` scope. */
  actions?: PermissionLevel;
  /** Permission for the `checks` scope. */
  checks?: PermissionLevel;
  /** Permission for the `contents` scope. */
  contents?: PermissionLevel;
  /** Permission for the `deployments` scope. */
  deployments?: PermissionLevel;
  /** Permission for the `discussions` scope. */
  discussions?: PermissionLevel;
  /** Permission for the `id-token` scope. Serialized as `id-token`. */
  idToken?: PermissionLevel;
  /** Permission for the `issues` scope. */
  issues?: PermissionLevel;
  /** Permission for the `packages` scope. */
  packages?: PermissionLevel;
  /** Permission for the `pages` scope. */
  pages?: PermissionLevel;
  /** Permission for the `pull-requests` scope. Serialized as `pull-requests`. */
  pullRequests?: PermissionLevel;
  /** Permission for the `repository-projects` scope. Serialized as `repository-projects`. */
  repositoryProjects?: PermissionLevel;
  /** Permission for the `security-events` scope. Serialized as `security-events`. */
  securityEvents?: PermissionLevel;
  /** Permission for the `statuses` scope. */
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

/**
 * Create a permissions model for controlling `GITHUB_TOKEN` scope access.
 *
 * @param input - Permission scope definitions and optional model metadata.
 * @returns A `PermissionsModel` that serializes to the `permissions:` YAML key.
 *
 * @example
 * ```ts
 * permissions({
 *   contents: "read",
 *   pullRequests: "write",
 *   idToken: "write",
 * })
 * ```
 */
export function permissions(input: WithMeta<PermissionsInput>): PermissionsModel {
  const [data, meta] = extractMeta(input);
  const yamlData = mapFields(data as Record<string, unknown>, PERMISSIONS_FIELD_MAP);
  return createModel("permissions", yamlData, meta, PERMISSIONS_KEY_ORDER) as PermissionsModel;
}
