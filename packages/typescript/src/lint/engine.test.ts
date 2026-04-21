import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { App } from "../app.js";
import { workflow } from "../models/workflow.js";
import { job } from "../models/job.js";
import { step } from "../models/step.js";
import { permissions } from "../models/permissions.js";
import { runLint } from "./engine.js";
import { ALL_RULES } from "./rules/index.js";

let tmp: string;
beforeEach(() => {
  tmp = mkdtempSync(join(tmpdir(), "ghagen-lint-"));
});
afterEach(() => {
  rmSync(tmp, { recursive: true, force: true });
});

const EMPTY_CONFIG = { disable: new Set<string>(), severity: new Map() };

describe("ALL_RULES", () => {
  it("registers four built-in rules", () => {
    expect(ALL_RULES).toHaveLength(4);
    expect(ALL_RULES.map((r) => r.meta.id)).toEqual([
      "missing-permissions",
      "unpinned-actions",
      "missing-timeout",
      "duplicate-step-ids",
    ]);
  });
});

describe("missing-permissions", () => {
  it("flags workflows with no top-level permissions", () => {
    const app = new App({ root: tmp });
    app.addWorkflow(
      workflow({
        name: "CI",
        jobs: {
          test: job({ runsOn: "ubuntu-latest", timeoutMinutes: 5, steps: [] }),
        },
      }),
      "ci.yml",
    );
    const violations = runLint(app, EMPTY_CONFIG);
    expect(violations.some((v) => v.ruleId === "missing-permissions")).toBe(true);
  });

  it("does not flag workflows that set permissions", () => {
    const app = new App({ root: tmp });
    app.addWorkflow(
      workflow({
        name: "CI",
        permissions: permissions({ contents: "read" }),
        jobs: {
          test: job({ runsOn: "ubuntu-latest", timeoutMinutes: 5, steps: [] }),
        },
      }),
      "ci.yml",
    );
    const violations = runLint(app, EMPTY_CONFIG);
    expect(violations.filter((v) => v.ruleId === "missing-permissions")).toHaveLength(0);
  });
});

describe("missing-timeout", () => {
  it("flags jobs without timeoutMinutes", () => {
    const app = new App({ root: tmp });
    app.addWorkflow(
      workflow({
        name: "CI",
        permissions: permissions({ contents: "read" }),
        jobs: { test: job({ runsOn: "ubuntu-latest", steps: [] }) },
      }),
      "ci.yml",
    );
    const violations = runLint(app, EMPTY_CONFIG);
    expect(violations.some((v) => v.ruleId === "missing-timeout")).toBe(true);
  });

  it("does not flag jobs with timeoutMinutes set", () => {
    const app = new App({ root: tmp });
    app.addWorkflow(
      workflow({
        name: "CI",
        permissions: permissions({ contents: "read" }),
        jobs: {
          test: job({ runsOn: "ubuntu-latest", timeoutMinutes: 10, steps: [] }),
        },
      }),
      "ci.yml",
    );
    const violations = runLint(app, EMPTY_CONFIG);
    expect(violations.filter((v) => v.ruleId === "missing-timeout")).toHaveLength(0);
  });
});

describe("unpinned-actions", () => {
  it("flags steps using @main", () => {
    const app = new App({ root: tmp });
    app.addWorkflow(
      workflow({
        name: "CI",
        permissions: permissions({ contents: "read" }),
        jobs: {
          test: job({
            runsOn: "ubuntu-latest",
            timeoutMinutes: 5,
            steps: [step({ uses: "actions/checkout@main" })],
          }),
        },
      }),
      "ci.yml",
    );
    const violations = runLint(app, EMPTY_CONFIG);
    expect(violations.some((v) => v.ruleId === "unpinned-actions")).toBe(true);
  });

  it("does not flag pinned versions or SHAs", () => {
    const app = new App({ root: tmp });
    app.addWorkflow(
      workflow({
        name: "CI",
        permissions: permissions({ contents: "read" }),
        jobs: {
          test: job({
            runsOn: "ubuntu-latest",
            timeoutMinutes: 5,
            steps: [
              step({ uses: "actions/checkout@v4" }),
              step({ uses: `actions/setup-node@${"a".repeat(40)}` }),
            ],
          }),
        },
      }),
      "ci.yml",
    );
    const violations = runLint(app, EMPTY_CONFIG);
    expect(violations.filter((v) => v.ruleId === "unpinned-actions")).toHaveLength(0);
  });
});

describe("duplicate-step-ids", () => {
  it("flags two steps in the same job sharing an id", () => {
    const app = new App({ root: tmp });
    app.addWorkflow(
      workflow({
        name: "CI",
        permissions: permissions({ contents: "read" }),
        jobs: {
          test: job({
            runsOn: "ubuntu-latest",
            timeoutMinutes: 5,
            steps: [step({ id: "x", run: "echo 1" }), step({ id: "x", run: "echo 2" })],
          }),
        },
      }),
      "ci.yml",
    );
    const violations = runLint(app, EMPTY_CONFIG);
    const dups = violations.filter((v) => v.ruleId === "duplicate-step-ids");
    expect(dups).toHaveLength(1);
    expect(dups[0]!.severity).toBe("error");
  });

  it("allows the same id in two different jobs", () => {
    const app = new App({ root: tmp });
    app.addWorkflow(
      workflow({
        name: "CI",
        permissions: permissions({ contents: "read" }),
        jobs: {
          a: job({
            runsOn: "ubuntu-latest",
            timeoutMinutes: 5,
            steps: [step({ id: "x", run: "echo 1" })],
          }),
          b: job({
            runsOn: "ubuntu-latest",
            timeoutMinutes: 5,
            steps: [step({ id: "x", run: "echo 2" })],
          }),
        },
      }),
      "ci.yml",
    );
    const violations = runLint(app, EMPTY_CONFIG);
    expect(violations.filter((v) => v.ruleId === "duplicate-step-ids")).toHaveLength(0);
  });
});

describe("config interaction", () => {
  it("disabled rules don't run", () => {
    const app = new App({ root: tmp });
    app.addWorkflow(
      workflow({
        name: "CI",
        jobs: { test: job({ runsOn: "ubuntu-latest", steps: [] }) },
      }),
      "ci.yml",
    );
    const config = {
      disable: new Set(["missing-permissions", "missing-timeout"]),
      severity: new Map(),
    };
    const violations = runLint(app, config);
    expect(violations).toHaveLength(0);
  });

  it("severity overrides apply to emitted violations", () => {
    const app = new App({ root: tmp });
    app.addWorkflow(
      workflow({
        name: "CI",
        jobs: {
          test: job({ runsOn: "ubuntu-latest", timeoutMinutes: 5, steps: [] }),
        },
      }),
      "ci.yml",
    );
    const severity = new Map<string, "error" | "warning">();
    severity.set("missing-permissions", "error");
    const config = { disable: new Set<string>(), severity };
    const violations = runLint(app, config);
    const v = violations.find((x) => x.ruleId === "missing-permissions");
    expect(v?.severity).toBe("error");
  });
});
