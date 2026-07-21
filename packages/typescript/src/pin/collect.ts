/**
 * Collect all pinnable `uses:` references from an App.
 */

import type { App } from "../app.js";
import { iterUsesSites } from "./sites.js";

/**
 * Walk every registered Document in *app* and return pinnable `uses:` strings.
 *
 * Iterates the `UsesSite`s of every Document (the single traversal policy —
 * see `iterUsesSites`) and keeps the refs that are **Pinnable**.
 *
 * Skips local refs (`./…`), docker images (`docker://…`), and refs already
 * pinned to a 40-char SHA.
 */
export function collectUsesRefs(app: App): Set<string> {
  const refs = new Set<string>();

  for (const document of app.documents()) {
    for (const site of iterUsesSites(document)) {
      if (site.ref.isPinnable) {
        refs.add(site.uses);
      }
    }
  }

  return refs;
}
