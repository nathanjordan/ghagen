import { describe, it, expect } from "vitest";
import { parse } from "yaml";
import { toData, toYaml } from "./yaml-writer.js";
import { step } from "../models/step.js";
import { job, defaults, strategy, matrix } from "../models/job.js";
import { workflow } from "../models/workflow.js";
import { on } from "../models/trigger.js";
import { raw, withComment, withEolComment } from "../models/_base.js";

// `toData` is THE supported observation surface for model behaviour (proposal
// 02). These tests pin its interface contract directly.
describe("toData", () => {
  it("emits a model to a plain object", () => {
    expect(toData(step({ name: "Test", run: "pytest" }))).toEqual({
      name: "Test",
      run: "pytest",
    });
  });

  it("asserts absence via toEqual", () => {
    const data = toData(step({ uses: "actions/checkout@v4" }));
    expect(data).toEqual({ uses: "actions/checkout@v4" });
  });

  it("maps field names to YAML keys (if_ -> if)", () => {
    expect((toData(step({ run: "echo", if_: "x" })) as Record<string, unknown>)["if"]).toBe("x");
  });

  it("maps with_ to with, coupling to emitted structure", () => {
    const data = toData(step({ uses: "actions/setup-node@v4", with_: { "node-version": "20" } }));
    expect(data).toEqual({ uses: "actions/setup-node@v4", with: { "node-version": "20" } });
  });

  it("emits keys in canonical order", () => {
    const s = step({ timeoutMinutes: 5, name: "Build", uses: "actions/checkout@v4", id: "co" });
    expect(Object.keys(toData(s) as Record<string, unknown>)).toEqual([
      "id",
      "name",
      "uses",
      "timeout-minutes",
    ]);
  });

  it("merges extras after ordered keys", () => {
    const data = toData(step({ name: "Build", extras: { custom: "x" } })) as Record<
      string,
      unknown
    >;
    expect(Object.keys(data)).toEqual(["name", "custom"]);
    expect(data["custom"]).toBe("x");
  });

  it("unwraps Raw to its inner value with no wrapper types", () => {
    const data = toData(step({ run: "echo", shell: raw("future-shell") }));
    expect(data).toEqual({ run: "echo", shell: "future-shell" });
  });

  it("unwraps Commented with comments: false (default)", () => {
    const s = step({ uses: withEolComment("actions/checkout@v4", "pinned") });
    expect(toData(s)).toEqual({ uses: "actions/checkout@v4" });
  });

  it("surfaces an EOL comment as a CommentNode with comments: true", () => {
    const s = step({ uses: withEolComment("actions/checkout@v4", "v4") });
    const uses = (toData(s, { comments: true }) as Record<string, unknown>)["uses"];
    expect(uses).toEqual({ value: "actions/checkout@v4", eolComment: "v4" });
  });

  it("surfaces a block comment as a CommentNode with comments: true", () => {
    const s = step({ name: withComment("Build", "the build step") });
    const name = (toData(s, { comments: true }) as Record<string, unknown>)["name"];
    expect(name).toEqual({ value: "Build", comment: "the build step" });
  });

  it("leaves uncommented values plain with comments: true", () => {
    const s = step({ name: "Build", uses: withEolComment("actions/checkout@v4", "v4") });
    const data = toData(s, { comments: true }) as Record<string, unknown>;
    expect(data["name"]).toBe("Build");
    expect(data["uses"]).toEqual({ value: "actions/checkout@v4", eolComment: "v4" });
  });

  it("emits nested models as plain data", () => {
    const j = job({ runsOn: "ubuntu-latest", steps: [step({ run: "pytest" })] });
    const data = toData(j) as Record<string, unknown>;
    expect(data["runs-on"]).toBe("ubuntu-latest");
    expect(data["steps"]).toEqual([{ run: "pytest" }]);
  });

  it("surfaces a nested model's own comment with comments: true", () => {
    const j = job({ runsOn: "ubuntu-latest", steps: [step({ run: "pytest", comment: "run it" })] });
    const data = toData(j, { comments: true }) as Record<string, unknown>;
    expect(data["steps"]).toEqual([{ value: { run: "pytest" }, comment: "run it" }]);
  });

  it("agrees with toYaml on top-level key order", () => {
    const wf = workflow({
      name: "CI",
      on: { push: {} },
      jobs: {
        build: job({ runsOn: "ubuntu-latest", steps: [step({ uses: "actions/checkout@v4" })] }),
      },
    });
    const data = toData(wf) as Record<string, unknown>;
    const yamlKeys = [...toYaml(wf).matchAll(/^([A-Za-z0-9_-]+):/gm)].map((m) => m[1]);
    expect(Object.keys(data)).toEqual(yamlKeys);
  });

  // Deep structural cross-check (proposal 02): the parsed emitted YAML tree
  // must equal toData's output for a RICH document, so the two duplicated
  // recursions cannot diverge on exclude/unwrap/present-null/dedent — not just
  // top-level ordering. Comments are dropped by the YAML parse, so toData runs
  // with comments off; autoDedent matches toYaml's default-on.
  it("deep-matches the parsed emitted YAML for a rich document", () => {
    const wf = workflow({
      name: "CI",
      on: on({
        push: { branches: ["main"] },
        workflowDispatch: {}, // present-null empty map
        extras: { merge_group: {} }, // extra on the alphabetical On spec
      }),
      jobs: {
        build: job({
          runsOn: "ubuntu-latest",
          defaults: defaults({ run: { shell: withComment("bash", "login shell") } }),
          strategy: strategy({
            // `matrix_`, not `matrix`: the TS field is named `matrix_`
            // (`models/job.ts`) and maps to the `matrix` YAML key. The Python
            // spelling was silently dropped here, so this leg of the document
            // emitted `strategy: {}` and the round-trip oracle agreed with
            // itself about nothing.
            matrix_: matrix({ extras: { "python-version": ["3.11", "3.12"] } }),
          }),
          steps: [
            step({ uses: withEolComment("actions/checkout@v4", "pinned") }),
            step({ name: "run", shell: raw("bash"), run: "  echo hi\n  echo bye" }),
          ],
        }),
      },
    });
    const parsed = parse(toYaml(wf, { header: null }));
    expect(toData(wf, { autoDedent: true })).toEqual(parsed);
  });

  it("keeps the comment on a commented empty present-null map (comments: true)", () => {
    const model = on({ workflowDispatch: withComment({}, "note") });
    const data = toData(model, { comments: true }) as Record<string, unknown>;
    expect(data["workflow_dispatch"]).toEqual({ value: null, comment: "note" });
  });

  it("dedents a bare Step's run with autoDedent (recursion parity with Python)", () => {
    const s = step({ run: "  echo one\n  echo two" });
    const data = toData(s, { autoDedent: true }) as Record<string, unknown>;
    expect(data["run"]).toBe("echo one\necho two");
  });
});
