/** Violation, Severity, and SourceLocation types for ghagen lint. */

/** Severity level for a lint violation. */
export type Severity = "error" | "warning";

export const SEVERITY_VALUES: readonly Severity[] = ["error", "warning"] as const;

/**
 * Where in the user's code a violation was found.
 *
 * `file` and `line` point at the TS/JS source that constructed the
 * offending model (captured via stack walking). `symbolic` is always
 * set and describes the logical path within the workflow tree
 * (e.g. `"ci.yml → jobs.build → steps[2]"`).
 */
export interface SourceLocation {
  readonly file: string | null;
  readonly line: number | null;
  readonly symbolic: string;
}

/** A single lint violation produced by a rule. */
export interface Violation {
  readonly ruleId: string;
  readonly severity: Severity;
  readonly message: string;
  readonly location: SourceLocation;
  readonly hint?: string | null;
}
