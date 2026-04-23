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
        if (isCommented(uses)) uses = uses.value;
        if (typeof uses === "string") {
          const pinned = pinUses(uses, lockfile);
          if (pinned !== null) model.data["uses"] = pinned;
        }
      }
    });
    return item;
  };
}

function pinUses(uses: string, lockfile: Lockfile): string | null {
  if (uses.startsWith("./") || uses.startsWith("docker://")) return null;
  if (!uses.includes("@")) return null;

  const entry = lockfile.get(uses);
  if (entry === undefined) {
    throw new PinError(`No lockfile entry for '${uses}'. Run \`ghagen deps pin\` to resolve it.`);
  }

  const at = uses.lastIndexOf("@");
  const actionPart = uses.slice(0, at);
  const ref = uses.slice(at + 1);
  const pinned = `${actionPart}@${entry.sha}`;

  // Return the pinned value wrapped with the original ref as EOL comment
  return withEolComment(pinned, ref);
}
