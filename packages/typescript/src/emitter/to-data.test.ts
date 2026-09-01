import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, it, expect } from "vitest";
import { parse } from "yaml";
import { toData, toYaml } from "./yaml-writer.js";
import { step } from "../models/step.js";
import { job, defaults, strategy, matrix } from "../models/job.js";
import { workflow } from "../models/workflow.js";
import { on, workflowDispatch } from "../models/trigger.js";
import { raw, withComment, withEolComment } from "../models/_base.js";
import { EXPECTED_DIR } from "../paths.js";

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

  // docs/issues/23 item 5 -- `On(extras=...)` is the only reachable path.
  // The issue's own example pair: "\u{1F600}" (astral-plane, U+1F600) and
  // "＀" (U+FF00, BMP). On's spec is order: "alphabetical", so every extras
  // key merges into the same sort orderedEntries runs on typed fields, and
  // these two disagree on where they land depending on whether the
  // comparison is by Unicode code point (Python's native `str` ordering,
  // matched by `codePointCompare`) or by UTF-16 code unit (this port's
  // pre-fix `.sort()`): the BMP char's single code unit (0xFF00) is
  // numerically *larger* than the astral char's leading surrogate (0xD83D),
  // even though the astral char's actual code point (0x1F600) is larger
  // still. fixtures/expected/on_extras_astral_order.txt is the shared oracle
  // the Python peer asserts the same order against.
  it("orders extras astral-plane keys by code point, not UTF-16 code unit", () => {
    const trigger = on({
      push: {},
      extras: { "＀_event": {}, "\u{1F600}_event": {} },
    });

    const data = toData(trigger) as Record<string, unknown>;

    const expected = readFileSync(join(EXPECTED_DIR, "on_extras_astral_order.txt"), "utf8")
      .split("\n")
      .filter((s) => s.length > 0);
    expect(Object.keys(data)).toEqual(expected);
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

  // The comment is the only content the user wrote, so dropping it deletes
  // everything. Both ports dropped it: the comment sat on the empty map, which
  // `presentNullWhenEmpty` then replaced with null, discarding map and comment
  // together. Peer of Python's
  // `test_present_null_model_comment_survives_into_emitted_yaml`.
  it("keeps a discarded present-null sub-model's own comment", () => {
    const wf = workflow({
      name: "CI",
      on: on({ workflowDispatch: workflowDispatch({ comment: "dispatch note" }) }),
      jobs: {},
    });
    expect(toYaml(wf, { header: null })).toContain("# dispatch note\n  workflow_dispatch:\n");
  });

  // ...and `toData` must agree, or the observation surface reports a structure
  // the emitter does not produce.
  it("reports that comment on the present-null key in toData too", () => {
    const wf = workflow({
      name: "CI",
      on: on({ workflowDispatch: workflowDispatch({ comment: "dispatch note" }) }),
      jobs: {},
    });
    const onData = (toData(wf, { comments: true }) as Record<string, unknown>)["on"] as Record<
      string,
      unknown
    >;
    expect(onData["workflow_dispatch"]).toMatchObject({
      value: null,
      comment: "dispatch note",
    });
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
  // with comments off; autoDedent is left at its default, which now matches
  // toYaml's default-on.
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
    expect(toData(wf)).toEqual(parsed);
  });

  it("keeps the comment on a commented empty present-null map (comments: true)", () => {
    const model = on({ workflowDispatch: withComment({}, "note") });
    const data = toData(model, { comments: true }) as Record<string, unknown>;
    expect(data["workflow_dispatch"]).toEqual({ value: null, comment: "note" });
  });

  it("dedents a bare Step's run by default (recursion parity with Python)", () => {
    const s = step({ run: "  echo one\n  echo two" });
    const data = toData(s) as Record<string, unknown>;
    expect(data["run"]).toBe("echo one\necho two");
  });

  // The deliverable invariant (issue 13): a toData / toYaml pair called with
  // no options must never disagree about a Step's run. Both default
  // autoDedent to true, so this must hold for any indented multi-line run.
  it("agrees with toYaml on a Step's run with no options", () => {
    const s = step({ name: "Build", run: "  echo building\n  make all" });
    const wf = workflow({
      name: "CI",
      jobs: { build: job({ runsOn: "ubuntu-latest", steps: [s] }) },
    });
    const parsed = parse(toYaml(wf, { header: null })) as Record<string, unknown>;
    const jobs = parsed["jobs"] as Record<string, { steps: { run: string }[] }>;
    const runFromYaml = jobs["build"].steps[0].run;
    const data = toData(wf) as Record<string, unknown>;
    const dataJobs = data["jobs"] as Record<string, { steps: { run: string }[] }>;
    const runFromData = dataJobs["build"].steps[0].run;
    expect(runFromData).toBe(runFromYaml);
    expect(runFromData).toBe("echo building\nmake all");
  });
});
