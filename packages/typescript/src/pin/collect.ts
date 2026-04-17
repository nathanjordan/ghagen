/**
 * Collect all pinnable `uses:` references from an App.
 */

import type { App } from "../app.js";
import type { Model } from "../models/_base.js";
import { isModel } from "../models/_base.js";

// 40-character lowercase hex — already a commit SHA.
const SHA_RE = /^[0-9a-f]{40}$/;

function isPinnable(uses: string): boolean {
  if (uses.startsWith("./") || uses.startsWith("docker://")) return false;
  if (!uses.includes("@")) return false;
  const at = uses.lastIndexOf("@");
  const ref = uses.slice(at + 1);
  return !SHA_RE.test(ref);
}

function collectFromSteps(steps: unknown, refs: Set<string>): void {
  if (!Array.isArray(steps)) return;
  for (const step of steps) {
    if (!isModel(step)) continue;
    if ((step as Model)._kind !== "step") continue;
    const uses = (step as Model)._data["uses"];
    if (typeof uses === "string" && isPinnable(uses)) {
      refs.add(uses);
    }
  }
}

/**
 * Walk all items in *app* and return pinnable `uses:` strings.
 *
 * Scans:
 *   - Workflow jobs (`Job.uses` for reusable workflows, `Step.uses` for
 *     action references)
 *   - Composite Action steps (`Step.uses` inside `compositeRuns`)
 *
 * Skips local refs (`./…`), docker images (`docker://…`), and refs
 * already pinned to a 40-char SHA.
 */
export function collectUsesRefs(app: App): Set<string> {
  const refs = new Set<string>();

  for (const { item } of app._items) {
    if (item._kind === "workflow") {
      const jobs = (item._data["jobs"] ?? {}) as Record<string, unknown>;
      for (const job of Object.values(jobs)) {
        if (!isModel(job)) continue;
        const jobModel = job as Model;
        const uses = jobModel._data["uses"];
        if (typeof uses === "string" && isPinnable(uses)) refs.add(uses);
        collectFromSteps(jobModel._data["steps"], refs);
      }
    } else if (item._kind === "action") {
      const runs = item._data["runs"];
      if (!isModel(runs)) continue;
      const runsModel = runs as Model;
      if (runsModel._data["using"] !== "composite") continue;
      collectFromSteps(runsModel._data["steps"], refs);
    }
  }

  return refs;
}
