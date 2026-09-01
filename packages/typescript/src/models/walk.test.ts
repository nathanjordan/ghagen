/**
 * Tests for the generic model traversal primitives `walk()` / `children()`.
 *
 * The port had no test for either until now, which is the gap that let the
 * `extras` divergence (H14) live. Most cases here are *characterization*
 * tests: they pin behaviour that already held (root first, pre-order, `Raw`
 * opaque, `Commented` transparent, extras last) so that the interface
 * narrowing cannot silently change the visit set or the visit order. The
 * `children()` cases additionally assert the narrowed shape -- bare `Model`s
 * rather than `{ key, model }` records.
 */
import { describe, it, expect } from "vitest";
import { Model, raw, withComment } from "./_base.js";
import { workflow } from "./workflow.js";
import { job } from "./job.js";
import { step } from "./step.js";
import { action, compositeRuns } from "./action.js";
import { toYaml } from "../emitter/yaml-writer.js";

/** Every model `walk()` visits, in order, labelled by kind + a stable field. */
function visitLabels(root: Model): string[] {
  const seen: string[] = [];
  root.walk((model) => {
    const tag = model.data["uses"] ?? model.data["name"] ?? model.data["run"];
    seen.push(typeof tag === "string" ? `${model.kind}:${tag}` : model.kind);
  });
  return seen;
}

describe("children()", () => {
  it("yields bare Models, not key/model records", () => {
    const j = job({
      runsOn: "ubuntu-latest",
      steps: [step({ uses: "actions/checkout@v4" }), step({ run: "pytest" })],
    });

    const kids = [...j.children()];

    expect(kids).toHaveLength(2);
    for (const kid of kids) {
      expect(kid).toBeInstanceOf(Model);
    }
    expect(kids.map((m) => m.data["uses"] ?? m.data["run"])).toEqual([
      "actions/checkout@v4",
      "pytest",
    ]);
  });

  it("yields nothing for a model holding only scalars", () => {
    expect([...step({ name: "only scalars", run: "echo hi" }).children()]).toEqual([]);
  });

  it("yields models nested in extras, after the model's own fields", () => {
    // H14 regression guard, at the traversal primitive rather than through
    // `iterUsesSites`: extras live on `meta`, not `data`, so they need their
    // own pass, and Python orders them last.
    const j = job({
      runsOn: "ubuntu-latest",
      steps: [step({ uses: "actions/checkout@v4" })],
      extras: { hidden: step({ uses: "actions/setup-node@v4" }) },
    });

    expect([...j.children()].map((m) => m.data["uses"])).toEqual([
      "actions/checkout@v4",
      "actions/setup-node@v4",
    ]);
  });
});

describe("walk()", () => {
  it("yields the root first", () => {
    const wf = workflow({ name: "CI", jobs: {} });

    const seen: Model[] = [];
    wf.walk((model) => {
      seen.push(model);
    });

    expect(seen[0]).toBe(wf);
  });

  it("visits depth-first, pre-order, over a nested document", () => {
    const wf = workflow({
      name: "CI",
      jobs: {
        build: job({
          runsOn: "ubuntu-latest",
          steps: [step({ uses: "actions/checkout@v4" }), step({ run: "pytest" })],
        }),
        lint: job({ runsOn: "ubuntu-latest", steps: [step({ run: "ruff" })] }),
      },
    });

    expect(visitLabels(wf)).toEqual([
      "workflow:CI",
      "job",
      "step:actions/checkout@v4",
      "step:pytest",
      "job",
      "step:ruff",
    ]);
  });

  it("reaches steps inside a composite action's runs", () => {
    const a = action({
      name: "My Action",
      description: "composite",
      runs: compositeRuns({
        using: "composite",
        steps: [step({ uses: "actions/setup-node@v4" }), step({ run: "npm ci", shell: "bash" })],
      }),
    });

    expect(visitLabels(a).filter((l) => l.startsWith("step:"))).toEqual([
      "step:actions/setup-node@v4",
      "step:npm ci",
    ]);
  });

  it("traverses through Commented wrappers but not into Raw", () => {
    const commentedStep = withComment(step({ uses: "actions/checkout@v4" }), "pin me");
    const wf = workflow({
      name: "CI",
      jobs: {
        build: job({
          runsOn: "ubuntu-latest",
          steps: [commentedStep],
          extras: { escape: raw({ nested: step({ uses: "actions/never-seen@v1" }) }) },
        }),
      },
    });

    // `Commented` is transparent, `Raw` is an opaque escape hatch.
    expect(visitLabels(wf).filter((l) => l.startsWith("step:"))).toEqual([
      "step:actions/checkout@v4",
    ]);
  });

  it("visits models nested in extras, after the containing model's own fields", () => {
    const wf = workflow({
      name: "CI",
      jobs: {
        build: job({
          runsOn: "ubuntu-latest",
          steps: [step({ uses: "actions/checkout@v4" })],
          extras: { hidden: step({ uses: "actions/setup-node@v4" }) },
        }),
      },
    });

    expect(visitLabels(wf)).toEqual([
      "workflow:CI",
      "job",
      "step:actions/checkout@v4",
      "step:actions/setup-node@v4",
    ]);
  });

  it("dedents an extras-nested step's run at emit", () => {
    // The second consequence of H14: the emitter's dedent pass recurses
    // through `orderedEntries` (a job's data fields, then its `extras`), not
    // through `walk()`, so an extras-nested step is already in its reach —
    // this pins that it stays that way. A step the recursion cannot reach
    // keeps its authored indentation and is emitted as `|2-` where Python
    // emits `|-`. Byte parity, not just site parity.
    const wf = workflow({
      jobs: {
        build: job({
          runsOn: "ubuntu-latest",
          steps: [step({ run: "echo one" })],
          extras: { hidden: step({ run: "  echo indented\n  echo more" }) },
        }),
      },
    });

    const yaml = toYaml(wf, { header: null });

    // Undedented, the authored two-space indent survives and `yaml` must emit
    // an explicit indentation indicator (`|2-`) to preserve it.
    expect(yaml).toContain("|-");
    expect(yaml).not.toMatch(/\|\d/);
  });
});
