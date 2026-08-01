import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { App, DEFAULT_WORKFLOWS_DIR as WORKFLOWS_DIR } from "./app.js";
import { workflow } from "./models/workflow.js";
import { job } from "./models/job.js";
import { step } from "./models/step.js";
import { action, compositeRuns } from "./models/action.js";
import { Lockfile, writeLockfile } from "./pin/lockfile.js";
import type { Document, Model } from "./models/_base.js";

let tmp: string;
beforeEach(() => {
  tmp = mkdtempSync(join(tmpdir(), "ghagen-app-"));
});
afterEach(() => {
  rmSync(tmp, { recursive: true, force: true });
});

function tinyWorkflow(uses = "actions/checkout@v4") {
  return workflow({
    name: "CI",
    on: { push: { branches: ["main"] } },
    jobs: {
      test: job({
        runsOn: "ubuntu-latest",
        steps: [step({ uses })],
      }),
    },
  });
}

// App is a thin filesystem tail over the `render` seam (covered in synth.test.ts).
// These tests focus on what App adds: resolving root/relPath, writing / reading /
// diffing, config-driven options, and the one ordering responsibility it owns —
// composing user transforms first and the pin transform last.
describe("App", () => {
  it("synth() writes registered workflows to the resolved path", () => {
    const app = new App({ root: tmp, lockfile: null });
    app.addWorkflow(tinyWorkflow(), "ci.yml");
    const written = app.synth();
    expect(written).toHaveLength(1);
    expect(written[0]).toBe(join(tmp, WORKFLOWS_DIR, "ci.yml"));
    expect(existsSync(written[0]!)).toBe(true);
    const content = readFileSync(written[0]!, "utf8");
    expect(content).toContain("name: CI");
    expect(content).toContain("actions/checkout@v4");
  });

  it("synth() creates parent directories", () => {
    const app = new App({ root: tmp, lockfile: null });
    app.add(tinyWorkflow(), "deeply/nested/out.yml");
    const written = app.synth();
    expect(written[0]).toBe(join(tmp, "deeply/nested/out.yml"));
    expect(existsSync(written[0]!)).toBe(true);
  });

  it("addAction() writes action.yml to the given dir", () => {
    const a = action({
      name: "My action",
      description: "x",
      runs: compositeRuns({
        using: "composite",
        steps: [step({ run: "echo hi", shell: "bash" })],
      }),
    });
    const app = new App({ root: tmp, lockfile: null });
    app.addAction(a, "my-action");
    const written = app.synth();
    expect(written[0]).toBe(join(tmp, "my-action", "action.yml"));
    expect(readFileSync(written[0]!, "utf8")).toContain("My action");
  });

  it("check() returns empty when files are in sync", () => {
    const app = new App({ root: tmp, lockfile: null });
    app.addWorkflow(tinyWorkflow(), "ci.yml");
    app.synth();
    expect(app.check()).toEqual([]);
  });

  it("check() flags missing files", () => {
    const app = new App({ root: tmp, lockfile: null });
    app.addWorkflow(tinyWorkflow(), "ci.yml");
    const stale = app.check();
    expect(stale).toHaveLength(1);
    expect(stale[0]![1]).toContain("File does not exist");
  });

  it("check() flags out-of-date files with a unified diff", () => {
    const app = new App({ root: tmp, lockfile: null });
    app.addWorkflow(tinyWorkflow(), "ci.yml");
    app.synth();
    // Mutate the file on disk.
    const path = join(tmp, WORKFLOWS_DIR, "ci.yml");
    writeFileSync(path, "name: tampered\n");
    const stale = app.check();
    expect(stale).toHaveLength(1);
    expect(stale[0]![1]).toContain("---");
    expect(stale[0]![1]).toContain("+++");
  });

  it("threads auto_dedent=false from .ghagen.yml into synth", () => {
    writeFileSync(join(tmp, ".ghagen.yml"), "options:\n  auto_dedent: false\n");
    const app = new App({ root: tmp, lockfile: null });
    const indented = "\n        echo hi\n        echo bye\n    ";
    app.addWorkflow(
      workflow({
        name: "CI",
        on: { push: {} },
        jobs: { test: job({ runsOn: "ubuntu-latest", steps: [step({ run: indented })] }) },
      }),
      "ci.yml",
    );
    const [written] = app.synth();
    // With auto_dedent disabled, the raw indentation survives into the YAML.
    expect(readFileSync(written!, "utf8")).toContain("        echo hi");
  });

  it("pins refs a user transform injects (user transforms first, pin last)", () => {
    // A user transform rewrites the authored ref (v3, absent from the lockfile)
    // to v4, which is locked. Because pin runs LAST, the injected ref is pinned.
    const sha = "3df4ab11eba7bda6032a0b82a6bb43b11571feac";
    const lf = new Lockfile([["actions/checkout@v4", { sha, resolvedAt: new Date() }]]);
    writeLockfile(lf, join(tmp, ".ghagen.lock.yml"));

    const app = new App({
      root: tmp,
      transforms: [
        (item: Document): Document => {
          const jobs = item.data["jobs"] as Record<string, Model>;
          const steps = jobs["test"]!.data["steps"] as Model[];
          steps[0]!.data["uses"] = "actions/checkout@v4";
          return item;
        },
      ],
    });
    app.addWorkflow(tinyWorkflow("actions/checkout@v3"), "ci.yml");
    const [written] = app.synth();
    const content = readFileSync(written!, "utf8");
    expect(content).toContain(`actions/checkout@${sha}`); // pinned
    expect(content).not.toContain("v3"); // authored ref rewritten before pinning
  });
});
