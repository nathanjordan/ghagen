/**
 * `PinTransform` — model-level transform that applies lockfile SHAs.
 *
 * Replaces `step.uses` and `job.uses` values with their pinned SHAs
 * from the lockfile, and attaches the original ref as a YAML EOL
 * comment via `_meta.fieldEolComments.uses`.
 */

import type { Model } from "../models/_base.js";
import { isModel } from "../models/_base.js";
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
    if (item._kind === "workflow") {
      pinWorkflow(item, lockfile);
    } else if (item._kind === "action") {
      const runs = item._data["runs"];
      if (isModel(runs) && (runs as Model)._data["using"] === "composite") {
        pinSteps((runs as Model)._data["steps"], lockfile);
      }
    }
    return item;
  };
}

function pinWorkflow(wf: SynthItem, lockfile: Lockfile): void {
  const jobs = (wf._data["jobs"] ?? {}) as Record<string, unknown>;
  for (const job of Object.values(jobs)) {
    if (!isModel(job)) continue;
    const jobModel = job as Model;
    const uses = jobModel._data["uses"];
    if (typeof uses === "string") {
      const pinned = pinUses(uses, jobModel, lockfile);
      if (pinned !== null) jobModel._data["uses"] = pinned;
    }
    pinSteps(jobModel._data["steps"], lockfile);
  }
}

function pinSteps(steps: unknown, lockfile: Lockfile): void {
  if (!Array.isArray(steps)) return;
  for (const step of steps) {
    if (!isModel(step)) continue;
    const stepModel = step as Model;
    const uses = stepModel._data["uses"];
    if (typeof uses !== "string") continue;
    const pinned = pinUses(uses, stepModel, lockfile);
    if (pinned !== null) stepModel._data["uses"] = pinned;
  }
}

function pinUses(uses: string, model: Model, lockfile: Lockfile): string | null {
  if (uses.startsWith("./") || uses.startsWith("docker://")) return null;
  if (!uses.includes("@")) return null;

  const entry = lockfile.get(uses);
  if (entry === undefined) {
    throw new PinError(
      `No lockfile entry for '${uses}'. Run \`ghagen deps pin\` to resolve it.`,
    );
  }

  const at = uses.lastIndexOf("@");
  const actionPart = uses.slice(0, at);
  const ref = uses.slice(at + 1);
  const pinned = `${actionPart}@${entry.sha}`;

  // Attach original ref as EOL comment on the model's `uses` field.
  // _meta is mutable in our model layout (cloneModel produces a fresh
  // object); make sure fieldEolComments exists.
  const meta = model._meta as { fieldEolComments?: Record<string, string> };
  if (!meta.fieldEolComments) meta.fieldEolComments = {};
  meta.fieldEolComments["uses"] = ref;

  return pinned;
}
