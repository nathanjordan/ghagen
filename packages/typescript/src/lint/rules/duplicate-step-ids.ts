/**
 * Rule: flag duplicate step ids within a single job.
 *
 * GitHub Actions requires step ids to be unique within a job — when
 * two steps share an id, references like
 * `steps.<id>.outputs.<name>` silently resolve to only one of them,
 * producing confusing downstream failures. Step ids are scoped
 * per-job: the same id in two different jobs is fine.
 */

import { isModel, type Model } from "../../models/_base.js";
import type { Rule } from "./_base.js";
import { rule } from "./_base.js";

const META = {
  id: "duplicate-step-ids",
  defaultSeverity: "error" as const,
  description:
    "Two or more steps within a single job share the same id. GitHub " +
    "Actions requires step ids to be unique within a job; duplicates " +
    "break `steps.<id>.outputs` references.",
};

function stepId(step: unknown): string | null {
  if (!isModel(step)) return null;
  const id = (step as Model)._data["id"];
  return typeof id === "string" && id !== "" ? id : null;
}

export const checkDuplicateStepIds: Rule = rule(META, function* (wf, ctx) {
  const severity = ctx.config.severity.get(META.id) ?? META.defaultSeverity;

  const jobs = (wf._data["jobs"] ?? {}) as Record<string, unknown>;
  for (const [jobId, jobValue] of Object.entries(jobs)) {
    if (!isModel(jobValue)) continue;
    const steps = (jobValue as Model)._data["steps"];
    if (!Array.isArray(steps)) continue;

    const seen = new Map<string, number>();
    for (let index = 0; index < steps.length; index++) {
      const step = steps[index];
      const id = stepId(step);
      if (id === null) continue;
      if (seen.has(id)) {
        const firstIndex = seen.get(id)!;
        const symbolic = `${ctx.workflowKey}.yml → jobs.${jobId} → steps[${index}]`;
        yield {
          ruleId: META.id,
          severity,
          message:
            `Duplicate step id '${id}' in job '${jobId}' ` +
            `(first seen at steps[${firstIndex}]).`,
          location: ctx.loc(step as Model, symbolic),
          hint:
            "Step ids must be unique within a job. Rename this step's id " +
            "or remove it if it isn't referenced via steps.<id>.outputs.",
        };
      } else {
        seen.set(id, index);
      }
    }
  }
});
