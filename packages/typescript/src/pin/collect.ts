/**
 * Collect all pinnable `uses:` references from an App.
 */

import type { App } from "../app.js";
import { iterUsesSites } from "./sites.js";
import type { UsesRef } from "./uses.js";

/**
 * Return every pinnable `uses:` ref across the app, parsed and deduped.
 *
 * Iterates the `UsesSite`s of every Document (the single traversal policy —
 * see `iterUsesSites`) and keeps the refs that are **Pinnable**.
 *
 * Dedup is by full ref string (`UsesRef.uses`) — the same key the lockfile
 * uses, so a collected ref lines up with its lockfile entry by construction.
 * A `Map` keyed by that string is the dedup mechanism because `UsesRef` is a
 * class with no value-equality. The result is sorted by `uses`, so engine
 * consumers get deterministic iteration without re-sorting.
 *
 * Parse failure and the pinnable filter live in `iterUsesSites` / `UsesRef`;
 * a ref that reaches this list is guaranteed parseable and Pinnable. Local
 * refs (`./…`), docker images (`docker://…`), and refs already pinned to a
 * 40-char SHA are skipped.
 */
export function collectUsesRefs(app: App): UsesRef[] {
  const byKey = new Map<string, UsesRef>();

  for (const document of app.documents()) {
    for (const site of iterUsesSites(document)) {
      if (site.ref.isPinnable) {
        byKey.set(site.uses, site.ref);
      }
    }
  }

  return [...byKey.keys()].sort().map((k) => byKey.get(k)!);
}
