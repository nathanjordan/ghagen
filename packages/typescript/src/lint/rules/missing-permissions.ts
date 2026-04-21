/**
 * Rule: flag workflows that don't explicitly declare permissions.
 *
 * GitHub's default GITHUB_TOKEN has broad write access. Setting an
 * explicit `permissions:` block at the workflow (or per-job) level
 * follows OWASP's supply-chain hardening guidance.
 */

import { isModel, type Model } from "../../models/_base.js";
import type { Rule } from "./_base.js";
import { rule } from "./_base.js";

const META = {
  id: "missing-permissions",
  defaultSeverity: "warning" as const,
  description:
    "Workflow has no explicit permissions set. The default GITHUB_TOKEN " +
    "has broad write access; an explicit permissions block limits scope.",
};

export const checkMissingPermissions: Rule = rule(META, function* (wf, ctx) {
  if (wf._data["permissions"] !== undefined) return;

  const jobs = (wf._data["jobs"] ?? {}) as Record<string, unknown>;
  const jobValues = Object.values(jobs).filter(isModel) as Model[];

  // If every job has its own permissions, the workflow-level omission is fine.
  if (jobValues.length > 0 && jobValues.every((j) => j._data["permissions"] !== undefined)) {
    return;
  }

  const severity = ctx.config.severity.get(META.id) ?? META.defaultSeverity;
  const name = (wf._data["name"] as string | undefined) ?? ctx.workflowKey;
  yield {
    ruleId: META.id,
    severity,
    message: `Workflow '${name}' has no top-level permissions set.`,
    location: ctx.loc(wf, `${ctx.workflowKey}.yml`),
    hint:
      "Add permissions: { contents: 'read' } (or similar) to limit the " +
      "default GITHUB_TOKEN scope, or set permissions on every job " +
      "individually.",
  };
});
