/**
 * Rule: flag steps that use actions pinned to a mutable ref.
 *
 * Refs like `@main`, `@master`, `@latest`, or no ref at all are
 * considered unpinned. Version tags (`@v4`, `@v4.1.2`) and commit
 * SHAs (40 hex chars) are accepted.
 */

import { isModel, type Model } from "../../models/_base.js";
import type { Rule } from "./_base.js";
import { rule } from "./_base.js";

const META = {
  id: "unpinned-actions",
  defaultSeverity: "warning" as const,
  description:
    "Step references an action by a mutable ref (main/master/latest or " +
    "no ref at all). Pin to a version tag or commit SHA for reproducibility.",
};

const UNPINNED_REFS = new Set(["main", "master", "latest"]);
const SHA_RE = /^[0-9a-f]{40}$/;
const VERSION_RE = /^v\d+(\.\d+)*([-+][\w.]+)?$/;
const HAS_DIGIT_RE = /\d/;

function isPinnedRef(ref: string): boolean {
  if (UNPINNED_REFS.has(ref)) return false;
  if (SHA_RE.test(ref)) return true;
  if (VERSION_RE.test(ref)) return true;
  // Unknown ref shape — accept anything with at least one digit (covers
  // custom tags like "1.2.3" without v prefix). Goal is to flag
  // obviously-mutable refs, not enforce strict versioning.
  return HAS_DIGIT_RE.test(ref);
}

export const checkUnpinnedActions: Rule = rule(META, function* (wf, ctx) {
  const severity = ctx.config.severity.get(META.id) ?? META.defaultSeverity;

  const jobs = (wf._data["jobs"] ?? {}) as Record<string, unknown>;
  for (const [jobId, jobValue] of Object.entries(jobs)) {
    if (!isModel(jobValue)) continue;
    const job = jobValue as Model;
    const steps = job._data["steps"];
    if (!Array.isArray(steps)) continue;

    for (let idx = 0; idx < steps.length; idx++) {
      const step = steps[idx];
      if (!isModel(step)) continue;
      const stepModel = step as Model;
      const uses = stepModel._data["uses"];
      if (typeof uses !== "string") continue;

      // Skip local path references and docker images.
      if (uses.startsWith("./") || uses.startsWith("docker://")) continue;

      if (uses.includes("@")) {
        const at = uses.lastIndexOf("@");
        const ref = uses.slice(at + 1);
        if (isPinnedRef(ref)) continue;
        // If the lockfile covers this ref, treat it as pinned.
        if (ctx.lockfile !== null && ctx.lockfile.get(uses) !== undefined) {
          continue;
        }
      }
      // else: no @ref at all → unpinned

      const symbolic = `${ctx.workflowKey}.yml → jobs.${jobId} → steps[${idx}]`;
      yield {
        ruleId: META.id,
        severity,
        message: `Step uses unpinned action '${uses}'.`,
        location: ctx.loc(stepModel, symbolic),
        hint:
          "Pin to a version tag (e.g. @v4) or a 40-character commit SHA " +
          "for reproducibility.",
      };
    }
  }
});
