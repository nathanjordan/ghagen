import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { App, DEFAULT_WORKFLOWS_DIR as WORKFLOWS_DIR } from "./app.js";
import { workflow } from "./models/workflow.js";
import { job } from "./models/job.js";
import { step } from "./models/step.js";
import { action, compositeRuns } from "./models/action.js";

let tmp: string;
beforeEach(() => {
  tmp = mkdtempSync(join(tmpdir(), "ghagen-app-"));
});
afterEach(() => {
  rmSync(tmp, { recursive: true, force: true });
});

function tinyWorkflow() {
  return workflow({
    name: "CI",
    on: { push: { branches: ["main"] } },
    jobs: {
      test: job({
        runsOn: "ubuntu-latest",
        steps: [step({ uses: "actions/checkout@v4" })],
      }),
    },
  });
}

describe("App", () => {
  it("synth() writes registered workflows to disk", async () => {
    const app = new App({ root: tmp });
    app.addWorkflow(tinyWorkflow(), "ci.yml");
    const written = await app.synth();
    expect(written).toHaveLength(1);
    expect(written[0]).toBe(join(tmp, WORKFLOWS_DIR, "ci.yml"));
    expect(existsSync(written[0]!)).toBe(true);
    const content = readFileSync(written[0]!, "utf8");
    expect(content).toContain("name: CI");
    expect(content).toContain("actions/checkout@v4");
  });

  it("addAction() writes action.yml to the given dir", async () => {
    const a = action({
      name: "My action",
      description: "x",
      runs: compositeRuns({
        using: "composite",
        steps: [step({ run: "echo hi", shell: "bash" })],
      }),
    });
    const app = new App({ root: tmp });
    app.addAction(a, "my-action");
    const written = await app.synth();
    expect(written[0]).toBe(join(tmp, "my-action", "action.yml"));
    expect(readFileSync(written[0]!, "utf8")).toContain("My action");
  });

  it("check() returns empty when files are in sync", async () => {
    const app = new App({ root: tmp });
    app.addWorkflow(tinyWorkflow(), "ci.yml");
    await app.synth();
    expect(await app.check()).toEqual([]);
  });

  it("check() flags missing files", async () => {
    const app = new App({ root: tmp });
    app.addWorkflow(tinyWorkflow(), "ci.yml");
    const stale = await app.check();
    expect(stale).toHaveLength(1);
    expect(stale[0]![1]).toContain("File does not exist");
  });

  it("check() flags out-of-date files with a unified diff", async () => {
    const app = new App({ root: tmp });
    app.addWorkflow(tinyWorkflow(), "ci.yml");
    await app.synth();
    // Mutate the file on disk.
    const path = join(tmp, WORKFLOWS_DIR, "ci.yml");
    writeFileSync(path, "name: tampered\n");
    const stale = await app.check();
    expect(stale).toHaveLength(1);
    expect(stale[0]![1]).toContain("---");
    expect(stale[0]![1]).toContain("+++");
  });

  it("transforms run on a deep clone, not on user models", async () => {
    const original = tinyWorkflow();
    const app = new App({
      root: tmp,
      transforms: [
        (item) => {
          (item._data as Record<string, string>)["name"] = "RENAMED";
          return item;
        },
      ],
    });
    app.add(original, "out.yml");
    const written = await app.synth();
    expect(readFileSync(written[0]!, "utf8")).toContain("name: RENAMED");
    // Original is untouched.
    expect((original._data as Record<string, string>)["name"]).toBe("CI");
  });

  it("respects autoDedent setting from .ghagen.yml", async () => {
    writeFileSync(join(tmp, ".ghagen.yml"), "options:\n  auto_dedent: false\n");
    // Constructing an App reads options and toggles auto-dedent.
    const _app = new App({ root: tmp });
    // Subsequent step() should NOT dedent.
    const indented = "\n        echo hi\n        echo bye\n    ";
    const s = step({ run: indented });
    expect(s._data["run"]).toBe(indented);
  });
});
