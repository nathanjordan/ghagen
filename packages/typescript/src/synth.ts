/**
 * The synthesis pipeline: Document + transforms -> emitted YAML text.
 *
 * This module is the single `Document in -> transformed clone -> YAML text out`
 * seam. It is *filesystem-free* and *root-free*: it carries each Document's
 * registered path through untouched so the caller knows where the text goes,
 * but it never joins a root, creates a directory, or reads/writes a file.
 * `App.synth` and `App.check` are thin consumers that differ only in what they
 * do with each `(path, text)` pair (write vs. diff).
 */

import { cloneModel } from "./models/_base.js";
import type { Document } from "./models/_base.js";
import { toYaml } from "./emitter/yaml-writer.js";
import type { ToYamlOptions } from "./emitter/yaml-writer.js";
import type { Transform } from "./transforms.js";

/** The header shapes accepted by the emitter (see {@link ToYamlOptions}). */
type HeaderInput = ToYamlOptions["header"];

/** One Document rendered to YAML, tagged with its registered path. */
export interface Rendered {
  /** The registered path, relative to `App.root`; opaque to the pipeline. */
  readonly path: string;
  /** The complete emitted YAML. */
  readonly text: string;
}

/**
 * Deep-clone `document` and fold `transforms` over the clone, in order.
 *
 * The input is never mutated. With no transforms the clone is skipped and the
 * original is returned (callers must treat the result as read-only).
 */
export function applyTransforms(document: Document, transforms: readonly Transform[]): Document {
  if (transforms.length === 0) {
    return document;
  }
  let working = cloneModel(document);
  for (const transform of transforms) {
    working = transform(working);
  }
  return working;
}

/**
 * Render every `[document, path]` pair to YAML.
 *
 * Invariants:
 *   - Transforms apply in list order: index 0 first, last index last. This is
 *     the whole ordering contract — the pipeline does not sort or reorder.
 *   - Each document is rendered from an independent deep clone; the caller's
 *     models are never mutated.
 *   - `header` and `autoDedent` are threaded straight into `toYaml` on every
 *     document (ADR-0002: no global carries them).
 */
export function render(
  items: ReadonlyArray<readonly [Document, string]>,
  transforms: readonly Transform[],
  opts: { header: HeaderInput; autoDedent: boolean },
): Rendered[] {
  return items.map(([document, path]) => ({
    path,
    text: toYaml(applyTransforms(document, transforms), {
      header: opts.header,
      autoDedent: opts.autoDedent,
    }),
  }));
}
