import type { PermissionsEvent as SchemaPermissions } from "../schema/workflow-types.generated.js";
import { defineFactory } from "./_base.js";
import type { Raw, ModelSpec, PermissionsModel } from "./_base.js";
import type { PermissionLevel } from "./common.js";

/**
 * Input for configuring `GITHUB_TOKEN` permission scopes at the workflow or
 * job level. Each scope can be set to `"read"`, `"write"`, or `"none"`.
 * Only set the scopes you need; unset scopes are omitted from the output.
 *
 * Every scope also accepts `raw("...")` for a level GitHub has shipped but
 * ghagen has not yet modelled — the mirror of Python's
 * `PermissionLevel | Raw[str] | None` (`models/permissions.py`).
 */
export interface PermissionsInput {
  /** Permission for the `actions` scope. */
  actions?: PermissionLevel | Raw<string>;
  /** Permission for the `artifact-metadata` scope. Serialized as `artifact-metadata`. */
  artifactMetadata?: PermissionLevel | Raw<string>;
  /** Permission for the `attestations` scope. */
  attestations?: PermissionLevel | Raw<string>;
  /** Permission for the `checks` scope. */
  checks?: PermissionLevel | Raw<string>;
  /** Permission for the `contents` scope. */
  contents?: PermissionLevel | Raw<string>;
  /** Permission for the `deployments` scope. */
  deployments?: PermissionLevel | Raw<string>;
  /** Permission for the `discussions` scope. */
  discussions?: PermissionLevel | Raw<string>;
  /** Permission for the `id-token` scope. Serialized as `id-token`. */
  idToken?: PermissionLevel | Raw<string>;
  /** Permission for the `issues` scope. */
  issues?: PermissionLevel | Raw<string>;
  /**
   * Permission for the `models` scope. The Snapshot narrows this one scope to
   * `read | none`; ghagen types it like its fifteen siblings and does not
   * enforce the narrower enum — see the ADR-0003 amendment.
   */
  models?: PermissionLevel | Raw<string>;
  /** Permission for the `packages` scope. */
  packages?: PermissionLevel | Raw<string>;
  /** Permission for the `pages` scope. */
  pages?: PermissionLevel | Raw<string>;
  /** Permission for the `pull-requests` scope. Serialized as `pull-requests`. */
  pullRequests?: PermissionLevel | Raw<string>;
  /** Permission for the `repository-projects` scope. Serialized as `repository-projects`. */
  repositoryProjects?: PermissionLevel | Raw<string>;
  /** Permission for the `security-events` scope. Serialized as `security-events`. */
  securityEvents?: PermissionLevel | Raw<string>;
  /** Permission for the `statuses` scope. */
  statuses?: PermissionLevel | Raw<string>;
}

/**
 * Everything a `permissions:` key accepts, at either level.
 *
 * The canonical Snapshot defines `permissions` once (`definitions.permissions`)
 * as a two-way `oneOf` — the blanket enum `"read-all"` / `"write-all"`, or the
 * per-scope `permissions-event` object — and both `WorkflowInput.permissions`
 * and `JobInput.permissions` are a bare `$ref` to it. One schema node, one
 * alias: writing the union out at each use site is how the two ports drifted
 * apart in the first place (issue 27 — Python's `Job` was missing the string
 * shorthand, and the API reference published this alias under this name while
 * neither port defined it).
 *
 * `Raw<string>` is the hatch for a blanket keyword GitHub ships before ghagen
 * models it. Bound to the Snapshot, with accept/reject vectors, by
 * `schema/conformance-inputs.yml` under `job.permissions` and
 * `workflow.permissions`. The Python peer is `PermissionsValue` in
 * `models/permissions.py`.
 */
export type PermissionsValue =
  | PermissionsModel
  | PermissionsInput
  | "read-all"
  | "write-all"
  | Raw<string>;

/** Serialization spec for {@link PermissionsModel}. */
export const PERMISSIONS_SPEC: ModelSpec = {
  kind: "permissions",
  fieldMap: {
    actions: "actions",
    artifactMetadata: "artifact-metadata",
    attestations: "attestations",
    checks: "checks",
    contents: "contents",
    deployments: "deployments",
    discussions: "discussions",
    idToken: "id-token",
    issues: "issues",
    models: "models",
    packages: "packages",
    pages: "pages",
    pullRequests: "pull-requests",
    repositoryProjects: "repository-projects",
    securityEvents: "security-events",
    statuses: "statuses",
  } satisfies Record<keyof PermissionsInput, keyof SchemaPermissions>,
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
 * @function
 */
export const permissions = defineFactory<PermissionsModel, PermissionsInput>(PERMISSIONS_SPEC);
