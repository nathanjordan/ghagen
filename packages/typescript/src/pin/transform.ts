/**
 * `PinTransform` — model-level transform that applies lockfile SHAs.
 *
 * Replaces `step.uses` and `job.uses` values with their pinned SHAs from the
 * lockfile, attaching the original ref as a YAML EOL comment. The "which
 * models carry `uses`, and how to reach it through a Commented wrapper" policy
 * lives in `./sites.js`; this module only decides *what* SHA to write.
 */

import type { Document } from "../models/_base.js";
import type { Transform } from "../transforms.js";
import type { Lockfile } from "./lockfile.js";
import { iterUsesSites } from "./sites.js";

/** Raised when a `uses:` ref has no lockfile entry during synthesis. */
export class PinError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "PinError";
  }
}

/** A `Transform` instance that pins refs using the supplied lockfile. */
export type PinTransform = Transform;

/**
 * Build a `Transform` that mutates a model to pin `uses:` refs.
 *
 * Refs that are not pinnable — local paths, docker images, malformed refs, or
 * refs already written as a SHA — are skipped and never consult the lockfile.
 * Only a pinnable ref missing from the lockfile throws a `PinError`.
 */
export function pinTransform(lockfile: Lockfile): PinTransform {
  return function pin(item: Document): Document {
    for (const site of iterUsesSites(item)) {
      if (!site.ref.isPinnable) {
        continue;
      }
      const entry = lockfile.get(site.uses);
      if (entry === undefined) {
        throw new PinError(
          `No lockfile entry for '${site.uses}'. Run \`ghagen deps pin\` to resolve it.`,
        );
      }
      site.replace(site.ref.withSha(entry.sha));
    }
    return item;
  };
}
