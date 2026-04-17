/**
 * Output formatters for lint violations.
 *
 * Three formats:
 *   - `formatHuman`  — pretty terminal output for humans
 *   - `formatJson`   — machine-readable JSON for CI and tooling
 *   - `formatGithub` — GitHub Actions workflow-command annotations
 *
 * The JSON and GitHub formats must produce byte-identical output to
 * the Python implementation given identical inputs.
 */

import type { Severity, Violation } from "./violation.js";

function counts(violations: readonly Violation[]): {
  errors: number;
  warnings: number;
} {
  let errors = 0;
  let warnings = 0;
  for (const v of violations) {
    if (v.severity === "error") errors++;
    else if (v.severity === "warning") warnings++;
  }
  return { errors, warnings };
}

function plural(n: number, word: string): string {
  return n === 1 ? word : `${word}s`;
}

// ---------------------------------------------------------------- human

export function formatHuman(violations: readonly Violation[]): string {
  if (violations.length === 0) return "No violations found.\n";

  const lines: string[] = [];
  for (const v of violations) {
    const loc = v.location;
    let prefix: string;
    if (loc.file !== null && loc.line !== null) prefix = `${loc.file}:${loc.line}`;
    else if (loc.file !== null) prefix = loc.file;
    else prefix = "<unknown>";

    lines.push(`${prefix}: ${v.severity}[${v.ruleId}]`);
    lines.push(`  ${v.message}`);
    lines.push(`  Symbolic path: ${loc.symbolic}`);
    if (v.hint) lines.push(`  hint: ${v.hint}`);
    lines.push("");
  }

  const { errors, warnings } = counts(violations);
  const total = errors + warnings;
  const summary =
    `Found ${total} ${plural(total, "violation")} ` +
    `(${errors} ${plural(errors, "error")}, ` +
    `${warnings} ${plural(warnings, "warning")}).`;
  lines.push(summary);
  return lines.join("\n") + "\n";
}

// ---------------------------------------------------------------- json

interface JsonViolation {
  rule_id: string;
  severity: Severity;
  message: string;
  location: { file: string | null; line: number | null; symbolic: string };
  hint: string | null;
}

function violationToJson(v: Violation): JsonViolation {
  return {
    rule_id: v.ruleId,
    severity: v.severity,
    message: v.message,
    location: {
      file: v.location.file,
      line: v.location.line,
      symbolic: v.location.symbolic,
    },
    hint: v.hint ?? null,
  };
}

export function formatJson(violations: readonly Violation[]): string {
  const { errors, warnings } = counts(violations);
  const payload = {
    violations: violations.map(violationToJson),
    summary: { errors, warnings },
  };
  return JSON.stringify(payload, null, 2);
}

// ---------------------------------------------------------------- github

function escapeMessage(msg: string): string {
  return msg
    .split("%").join("%25")
    .split("\r").join("%0D")
    .split("\n").join("%0A");
}

function escapeProperty(value: string): string {
  return value
    .split("%").join("%25")
    .split("\r").join("%0D")
    .split("\n").join("%0A")
    .split(":").join("%3A")
    .split(",").join("%2C");
}

export function formatGithub(violations: readonly Violation[]): string {
  if (violations.length === 0) return "";

  const lines: string[] = [];
  for (const v of violations) {
    const level = v.severity === "error" ? "error" : "warning";
    const props: string[] = [];
    if (v.location.file !== null) {
      props.push(`file=${escapeProperty(v.location.file)}`);
      if (v.location.line !== null) props.push(`line=${v.location.line}`);
    }
    props.push(`title=${escapeProperty(v.ruleId)}`);
    lines.push(`::${level} ${props.join(",")}::${escapeMessage(v.message)}`);
  }

  return lines.join("\n") + "\n";
}
