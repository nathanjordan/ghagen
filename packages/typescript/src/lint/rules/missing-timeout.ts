/**
 * Rule: flag jobs that don't set an explicit `timeout-minutes`.
 *
 * GitHub's default job timeout is 6 hours — long enough for a runaway
 * build to cost real money. Setting an explicit, shorter timeout
 * bounds the blast radius of hangs and infinite loops.
 *
 * Reusable-workflow jobs (`job.uses`) are skipped because their
 * timeout is owned by the reusable workflow itself.
 */

import { isModel, type Model } from "../../models/_base.js";
import type { Rule } from "./_base.js";
import { rule } from "./_base.js";

const META = {
  id: "missing-timeout",
  defaultSeverity: "warning" as const,
  description:
    "Job has no timeout-minutes set. The default job timeout is 6 hours; " +
    "setting an explicit shorter timeout bounds runaway builds.",
};

export const checkMissingTimeout: Rule = rule(META, function* (wf, ctx) {
  const severity = ctx.config.severity.get(META.id) ?? META.defaultSeverity;

  const jobs = (wf._data["jobs"] ?? {}) as Record<string, unknown>;
  for (const [jobId, jobValue] of Object.entries(jobs)) {
    if (!isModel(jobValue)) continue;
    const job = jobValue as Model;

    // Reusable workflow jobs have their own timeout handling.
    if (job._data["uses"] !== undefined) continue;

    if (job._data["timeout-minutes"] !== undefined) continue;

    const symbolic = `${ctx.workflowKey}.yml → jobs.${jobId}`;
    yield {
      ruleId: META.id,
      severity,
      message: `Job '${jobId}' has no timeout-minutes set.`,
      location: ctx.loc(job, symbolic),
      hint:
        "Set timeoutMinutes: N on the job to bound its maximum runtime " +
        "(the default is 360 minutes / 6 hours).",
    };
  }
});
