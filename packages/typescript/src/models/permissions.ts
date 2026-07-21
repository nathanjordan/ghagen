import type { PermissionsEvent as SchemaPermissions } from "../schema/workflow-types.generated.js";
import { buildModel, extractMeta } from "./_base.js";
import type { WithMeta, ModelSpec, PermissionsModel } from "./_base.js";
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

/** Serialization spec for {@link PermissionsModel}. */
export const PERMISSIONS_SPEC: ModelSpec = {
  kind: "permissions",
  fieldMap: {
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
  } satisfies Record<keyof PermissionsInput, keyof SchemaPermissions>,
  order: [
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
  ],
};

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
  return buildModel<PermissionsModel>(PERMISSIONS_SPEC, data as Record<string, unknown>, meta);
}
