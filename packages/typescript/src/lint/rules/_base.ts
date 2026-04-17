/** Base types for lint rules: `rule()` factory, `RuleMeta`, `RuleContext`. */

import type { Lockfile } from "../../pin/lockfile.js";
import type { Model, WorkflowModel } from "../../models/_base.js";
import type { LintConfig } from "../config.js";
import type { Severity, SourceLocation, Violation } from "../violation.js";

/** Metadata describing a lint rule. */
export interface RuleMeta {
  readonly id: string;
  readonly description: string;
  readonly defaultSeverity: Severity;
}

/** Context passed to rule functions during a lint run. */
export interface RuleContext {
  readonly workflowKey: string;
  readonly config: LintConfig;
  readonly lockfile: Lockfile | null;
  /**
   * Build a `SourceLocation` from a model's captured `_sourceLocation`
   * and a symbolic path string. Degrades gracefully if the model has
   * no captured location.
   */
  loc(model: Model | null | undefined, symbolic: string): SourceLocation;
}

/** A lint rule: a function that yields Violations for a workflow. */
export interface Rule {
  readonly meta: RuleMeta;
  (wf: WorkflowModel, ctx: RuleContext): Iterable<Violation>;
}

/**
 * Build a `Rule` by attaching `RuleMeta` to a generator function.
 *
 * No decorators — plain factory:
 *
 *     export const checkX: Rule = rule(
 *       { id: "x", defaultSeverity: "warning", description: "..." },
 *       function* (wf, ctx) { yield ... },
 *     );
 */
export function rule(
  meta: RuleMeta,
  fn: (wf: WorkflowModel, ctx: RuleContext) => Iterable<Violation>,
): Rule {
  const wrapped = ((wf, ctx) => fn(wf, ctx)) as Rule;
  Object.defineProperty(wrapped, "meta", { value: meta, enumerable: true });
  Object.defineProperty(wrapped, "name", { value: `rule:${meta.id}` });
  return wrapped;
}

/**
 * Build a `RuleContext` with a `loc()` helper that pulls
 * `_sourceLocation` off the supplied model.
 */
export function makeRuleContext(
  workflowKey: string,
  config: LintConfig,
  lockfile: Lockfile | null,
): RuleContext {
  return {
    workflowKey,
    config,
    lockfile,
    loc(model, symbolic) {
      const src = model?._sourceLocation ?? null;
      if (src === null) return { file: null, line: null, symbolic };
      return { file: src.file, line: src.line, symbolic };
    },
  };
}
