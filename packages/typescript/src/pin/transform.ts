/**
 * `PinTransform` — model-level transform that applies lockfile SHAs.
 *
 * Replaces `step.uses` and `job.uses` values with their pinned SHAs
 * from the lockfile, and attaches the original ref as a YAML EOL
 * comment via `withEolComment()`.
 */

import { StepModel, JobModel, isCommented, withEolComment } from "../models/_base.js";
import type { SynthContext, SynthItem, Transform } from "../transforms.js";
import type { Lockfile } from "./lockfile.js";
import { UsesRef } from "./uses.js";

/** Raised when a `uses:` ref has no lockfile entry during synthesis. */
export class PinError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "PinError";
  }
}

/** A `Transform` instance that pins refs using the supplied lockfile. */
export type PinTransform = Transform;

/** Build a `Transform` that mutates a model to pin `uses:` refs. */
export function pinTransform(lockfile: Lockfile): PinTransform {
  return function pin(item: SynthItem, _ctx: SynthContext): SynthItem {
    item.walk((model) => {
      if (model instanceof StepModel || model instanceof JobModel) {
        let uses = model.data["uses"];
        if (isCommented(uses)) {
          uses = uses.value;
        }
        if (typeof uses === "string") {
          const pinned = pinUses(uses, lockfile);
          if (pinned !== null) {
            model.data["uses"] = pinned;
          }
        }
      }
    });
    return item;
  };
}

/**
 * Refs that are not pinnable — local paths, docker images, malformed refs,
 * or refs already written as a SHA — are skipped (return `null`) and never
 * consult the lockfile. Only a pinnable ref missing from the lockfile throws
 * a `PinError`.
 */
function pinUses(uses: string, lockfile: Lockfile): string | null {
  const ref = UsesRef.parse(uses);
  if (ref === null || !ref.isPinnable) {
    return null;
  }

  const entry = lockfile.get(uses);
  if (entry === undefined) {
    throw new PinError(`No lockfile entry for '${uses}'. Run \`ghagen deps pin\` to resolve it.`);
  }

  const pinned = ref.withSha(entry.sha);

  // Return the pinned value wrapped with the original ref as EOL comment
  return withEolComment(pinned, ref.ref);
}
