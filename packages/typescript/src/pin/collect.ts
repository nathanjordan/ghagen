/**
 * Collect all pinnable `uses:` references from an App.
 */

import type { App } from "../app.js";
import { StepModel, JobModel } from "../models/_base.js";
import { UsesRef } from "./uses.js";

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
    item.walk((model) => {
      if (model instanceof StepModel || model instanceof JobModel) {
        const uses = model.data["uses"];
        if (typeof uses === "string") {
          const parsed = UsesRef.parse(uses);
          if (parsed !== null && parsed.isPinnable) {
            refs.add(uses);
          }
        }
      }
    });
  }

  return refs;
}
