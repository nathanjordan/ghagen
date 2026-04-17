/**
 * Apply version updates to user TS/JS source files.
 *
 * Replaces `uses` string literals in-place, scoped to files identified
 * by the source-tracking module.
 */

import { readFileSync, writeFileSync } from "node:fs";

/**
 * Replace `uses` strings in user source files.
 *
 * Returns the sorted list of files that were actually changed.
 */
export function applyUpdates(
  updates: ReadonlyMap<string, string> | Readonly<Record<string, string>>,
  refLocations: ReadonlyMap<string, readonly string[]> | Readonly<Record<string, readonly string[]>>,
): string[] {
  const updatesMap =
    updates instanceof Map ? updates : new Map(Object.entries(updates));
  const locMap =
    refLocations instanceof Map
      ? refLocations
      : new Map(Object.entries(refLocations));

  const changed = new Set<string>();
  for (const [oldUses, newUses] of updatesMap.entries()) {
    if (oldUses === newUses) continue;
    const files = locMap.get(oldUses);
    if (!files || files.length === 0) continue;
    for (const path of files) {
      const content = readFileSync(path, "utf8");
      if (content.includes(oldUses)) {
        writeFileSync(path, content.split(oldUses).join(newUses));
        changed.add(path);
      }
    }
  }

  return [...changed].sort();
}
