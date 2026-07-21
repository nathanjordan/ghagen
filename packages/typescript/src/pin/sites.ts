/**
 * UsesSite — the single traversal policy over a Document's `uses:` refs.
 *
 * Pin's collect (read) and transform (replace) both iterate `UsesSite`
 * objects, so the knowledge of *which* models carry a `uses:` field, and *how*
 * to reach it through a possible `Commented` wrapper, lives here alone. A third
 * `uses`-bearing model is one entry in `iterUsesSites`; the consumers need no
 * change.
 */

import { isCommented, withComment, withEolComment } from "../models/_base.js";
import type { Document, Model } from "../models/_base.js";
import { UsesRef } from "./uses.js";

/** The field name carrying a pinnable `uses:` on every uses-bearing model. */
const USES_FIELD = "uses";

/**
 * One `uses:` occurrence inside a Document.
 *
 * Carries the parsed {@link UsesRef} (which knows whether it is **Pinnable**)
 * and can {@link replace} the ref in place, threading the new value back
 * through any `Commented` wrapper on the field.
 */
export class UsesSite {
  constructor(
    /** The parsed `owner/repo[/path]@ref` reference. */
    readonly ref: UsesRef,
    /** The original `uses:` string, as authored (any wrapper peeled). */
    readonly uses: string,
    private readonly model: Model,
    private readonly field: string,
  ) {}

  /**
   * Rewrite this `uses:` field to `next`.
   *
   * The original ref is attached as an end-of-line comment, and any block
   * comment already on the field is preserved, so the emitted YAML keeps its
   * annotations.
   */
  replace(next: string): void {
    const current = this.model.data[this.field];
    let wrapped: string = withEolComment(next, this.ref.ref);
    if (isCommented(current) && current.comment !== undefined) {
      wrapped = withComment(wrapped, current.comment);
    }
    this.model.data[this.field] = wrapped;
  }
}

/**
 * Yield a {@link UsesSite} for every parseable `uses:` in `document`.
 *
 * Walks the model tree and selects the `uses` field of every step (action
 * references) and job (reusable-workflow calls), wherever they live — workflow
 * jobs or composite-action `runs.steps`. The field value is read through any
 * `Commented` wrapper.
 *
 * Values that do not parse as an `owner/repo[/path]@ref` reference — local
 * `./…` paths, `docker://…` images, or bare strings — yield no site. A ref
 * already written as a SHA *does* yield a site, whose `ref.isPinnable` is
 * `false`.
 */
export function* iterUsesSites(document: Document): Generator<UsesSite> {
  const sites: UsesSite[] = [];
  document.walk((model) => {
    if (model.kind === "step" || model.kind === "job") {
      let value = model.data[USES_FIELD];
      if (isCommented(value)) {
        value = value.value;
      }
      if (typeof value === "string") {
        const ref = UsesRef.parse(value);
        if (ref !== null) {
          sites.push(new UsesSite(ref, value, model, USES_FIELD));
        }
      }
    }
  });
  yield* sites;
}
