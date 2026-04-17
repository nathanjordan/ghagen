import { describe, it, expect } from "vitest";
import { formatGithub, formatHuman, formatJson } from "./output.js";
import type { Violation } from "./violation.js";

const sample: Violation[] = [
  {
    ruleId: "missing-timeout",
    severity: "warning",
    message: "Job 'build' has no timeout-minutes set.",
    location: {
      file: "/repo/.github/workflows.ts",
      line: 42,
      symbolic: "ci.yml → jobs.build",
    },
    hint: "Set timeoutMinutes on the job.",
  },
  {
    ruleId: "duplicate-step-ids",
    severity: "error",
    message: "Duplicate step id 'x' in job 'build'.",
    location: { file: null, line: null, symbolic: "ci.yml → jobs.build → steps[1]" },
  },
];

describe("formatHuman()", () => {
  it("returns 'No violations' for an empty list", () => {
    expect(formatHuman([])).toBe("No violations found.\n");
  });

  it("renders violations with file:line prefix and summary", () => {
    const out = formatHuman(sample);
    expect(out).toContain("/repo/.github/workflows.ts:42");
    expect(out).toContain("warning[missing-timeout]");
    expect(out).toContain("error[duplicate-step-ids]");
    expect(out).toContain("Found 2 violations (1 error, 1 warning).");
  });
});

describe("formatJson()", () => {
  it("emits valid JSON with rule_id (snake_case) and summary counts", () => {
    const out = formatJson(sample);
    const parsed = JSON.parse(out) as {
      violations: Array<{ rule_id: string; severity: string }>;
      summary: { errors: number; warnings: number };
    };
    expect(parsed.violations[0]!.rule_id).toBe("missing-timeout");
    expect(parsed.violations[1]!.rule_id).toBe("duplicate-step-ids");
    expect(parsed.summary).toEqual({ errors: 1, warnings: 1 });
  });

  it("represents missing locations as null", () => {
    const out = formatJson(sample);
    expect(out).toContain('"file": null');
    expect(out).toContain('"line": null');
  });
});

describe("formatGithub()", () => {
  it("emits ::level annotations with file/line/title", () => {
    const out = formatGithub(sample);
    expect(out).toContain("::warning ");
    expect(out).toContain("file=/repo/.github/workflows.ts");
    expect(out).toContain("line=42");
    expect(out).toContain("title=missing-timeout");
    expect(out).toContain("::error ");
    expect(out).toContain("title=duplicate-step-ids");
  });

  it("escapes %, CR, LF in messages and properties", () => {
    const v: Violation = {
      ruleId: "x",
      severity: "warning",
      message: "100% off\nnewline",
      location: { file: "a:b,c", line: 1, symbolic: "x" },
    };
    const out = formatGithub([v]);
    expect(out).toContain("100%25 off%0Anewline");
    expect(out).toContain("file=a%3Ab%2Cc");
  });

  it("returns empty string for no violations", () => {
    expect(formatGithub([])).toBe("");
  });
});
