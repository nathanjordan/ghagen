import { describe, it, expect } from "vitest";
import { render, applyTransforms } from "./synth.js";
import type { Transform } from "./transforms.js";
import { workflow } from "./models/workflow.js";
import { job } from "./models/job.js";
import { step } from "./models/step.js";
import { Lockfile } from "./pin/lockfile.js";
import { pinTransform } from "./pin/transform.js";
import type { Document, Model } from "./models/_base.js";

const SHA_CHECKOUT = "3df4ab11eba7bda6032a0b82a6bb43b11571feac";

function tinyWorkflow(uses = "actions/checkout@v4", name = "CI") {
  return workflow({
    name,
    on: { push: { branches: ["main"] } },
    jobs: {
      build: job({ runsOn: "ubuntu-latest", steps: [step({ uses })] }),
    },
  });
}

function workflowWithRun(run: string) {
  return workflow({
    name: "CI",
    on: { push: {} },
    jobs: { build: job({ runsOn: "ubuntu-latest", steps: [step({ run })] }) },
  });
}

/** A user transform that rewrites the first step's `uses` ref in place. */
function renameUses(newRef: string): Transform {
  return (item: Document): Document => {
    const jobs = item.data["jobs"] as Record<string, Model>;
    const steps = jobs["build"]!.data["steps"] as Model[];
    steps[0]!.data["uses"] = newRef;
    return item;
  };
}

function lockfileWith(uses: string, sha: string): Lockfile {
  return new Lockfile([[uses, { sha, resolvedAt: new Date() }]]);
}

describe("render()", () => {
  it("returns one Rendered per item, carrying the registered path", () => {
    const items: Array<readonly [Document, string]> = [
      [tinyWorkflow(), "ci.yml"],
      [tinyWorkflow(), "nested/dir/cd.yaml"],
    ];
    const results = render(items, [], { header: null, autoDedent: true });
    expect(results).toHaveLength(2);
    expect(results.map((r) => r.path)).toEqual(["ci.yml", "nested/dir/cd.yaml"]);
  });

  it("runs the pin transform after user transforms (list order)", () => {
    // Authored ref is v3 (absent from the lockfile); a user transform rewrites
    // it to v4, which pin (running last) then resolves to a SHA.
    const lf = lockfileWith("actions/checkout@v4", SHA_CHECKOUT);
    const [{ text }] = render(
      [[tinyWorkflow("actions/checkout@v3"), "ci.yml"]],
      [renameUses("actions/checkout@v4"), pinTransform(lf)],
      { header: null, autoDedent: true },
    );
    expect(text).toContain(`actions/checkout@${SHA_CHECKOUT}`); // pinned
    expect(text).toContain("v4"); // user edit survived (as the pin's EOL comment)
    expect(text).not.toContain("v3");
  });

  it("does not mutate the caller's models (deep clone)", () => {
    const original = tinyWorkflow("actions/checkout@v4");
    render([[original, "ci.yml"]], [renameUses("actions/setup-node@v4")], {
      header: null,
      autoDedent: true,
    });
    const jobs = original.data["jobs"] as Record<string, Model>;
    const steps = jobs["build"]!.data["steps"] as Model[];
    expect(steps[0]!.data["uses"]).toBe("actions/checkout@v4");
  });

  it("emits no header when header is null", () => {
    const [{ text }] = render([[tinyWorkflow(), "ci.yml"]], [], {
      header: null,
      autoDedent: true,
    });
    expect(text.startsWith("#")).toBe(false);
  });

  it("threads a string header through verbatim", () => {
    const [{ text }] = render([[tinyWorkflow(), "ci.yml"]], [], {
      header: "hand written",
      autoDedent: true,
    });
    expect(text.startsWith("# hand written")).toBe(true);
  });

  it("threads a default header when header is undefined", () => {
    const [{ text }] = render([[tinyWorkflow(), "ci.yml"]], [], {
      header: undefined,
      autoDedent: true,
    });
    expect(text.startsWith("#")).toBe(true);
  });

  it("passes the raw run through when autoDedent is false", () => {
    const run = "\n        echo hi\n        echo bye\n    ";
    const [{ text }] = render([[workflowWithRun(run), "ci.yml"]], [], {
      header: null,
      autoDedent: false,
    });
    expect(text).toContain("        echo hi");
  });

  it("dedented output differs from the verbatim output", () => {
    const run = "\n        echo hi\n        echo bye\n    ";
    const [dedented] = render([[workflowWithRun(run), "ci.yml"]], [], {
      header: null,
      autoDedent: true,
    });
    const [raw] = render([[workflowWithRun(run), "ci.yml"]], [], {
      header: null,
      autoDedent: false,
    });
    expect(dedented!.text).toContain("echo hi");
    expect(dedented!.text).not.toBe(raw!.text);
  });
});

describe("applyTransforms()", () => {
  it("returns the same object when there are no transforms", () => {
    const wf = tinyWorkflow();
    expect(applyTransforms(wf, [])).toBe(wf);
  });

  it("applies transforms in order on a clone", () => {
    const wf = tinyWorkflow("actions/checkout@v1");
    const result = applyTransforms(wf, [
      renameUses("actions/checkout@v2"),
      renameUses("actions/checkout@v3"),
    ]);
    expect(result).not.toBe(wf);
    const jobs = result.data["jobs"] as Record<string, Model>;
    const steps = jobs["build"]!.data["steps"] as Model[];
    expect(steps[0]!.data["uses"]).toBe("actions/checkout@v3");
    // Original untouched.
    const origJobs = wf.data["jobs"] as Record<string, Model>;
    const origSteps = origJobs["build"]!.data["steps"] as Model[];
    expect(origSteps[0]!.data["uses"]).toBe("actions/checkout@v1");
  });
});
