/** Lint engine: iterate workflows × rules and collect violations. */

import { existsSync, statSync } from "node:fs";
import { resolve } from "node:path";
import type { App } from "../app.js";
import type { Lockfile } from "../pin/lockfile.js";
import { readLockfile } from "../pin/lockfile.js";
import type { LintConfig } from "./config.js";
import { ALL_RULES, makeRuleContext } from "./rules/index.js";
import type { Violation } from "./violation.js";

/**
 * Run all enabled lint rules against every workflow in the app.
 *
 * Actions (`action.yml`) are not currently linted — v1 scope is
 * workflows only.
 *
 * A rule that throws is caught and skipped; other rules continue. A
 * warning is written to stderr naming the failing rule.
 */
export function runLint(app: App, config: LintConfig): Violation[] {
  // Load the lockfile if available so rules can check pin status.
  let lockfile: Lockfile | null = null;
  if (app.lockfilePath !== null) {
    const full = resolve(app.root, app.lockfilePath);
    if (existsSync(full) && statSync(full).isFile()) {
      lockfile = readLockfile(full);
    }
  }

  const violations: Violation[] = [];

  for (const { item, relPath } of app._items) {
    if (item._kind !== "workflow") continue;
    const workflowKey = stem(relPath);
    const ctx = makeRuleContext(workflowKey, config, lockfile);

    for (const ruleFn of ALL_RULES) {
      const ruleId = ruleFn.meta.id;
      if (config.disable.has(ruleId)) continue;
      try {
        for (const violation of ruleFn(item, ctx)) {
          violations.push(violation);
        }
      } catch (err) {
        process.stderr.write(
          `warning: rule '${ruleId}' crashed on workflow '${workflowKey}' ` +
            `— skipped (${(err as Error).name}: ${(err as Error).message})\n`,
        );
        continue;
      }
    }
  }

  return violations;
}

function stem(path: string): string {
  const base = path.replace(/^.*[\\/]/, "");
  const dot = base.lastIndexOf(".");
  return dot > 0 ? base.slice(0, dot) : base;
}
