import { describe, it, expect } from "vitest";
import { Lockfile } from "./lockfile.js";
import { PinError, pinTransform } from "./transform.js";
import { workflow } from "../models/workflow.js";
import { job } from "../models/job.js";
import { step } from "../models/step.js";
import { action, compositeRuns } from "../models/action.js";
import { cloneModel, isCommented } from "../models/_base.js";
import type { Model, Commented } from "../models/_base.js";

function makeLockfile(): Lockfile {
  const lf = new Lockfile();
  lf.merge([
    [
      "actions/checkout@v4",
      {
        sha: "3df4ab11eba7bda6032a0b82a6bb43b11571feac",
        resolvedAt: new Date(),
      },
    ],
  ]);
  return lf;
}

describe("pinTransform()", () => {
  it("rewrites step.uses to the SHA from the lockfile", () => {
    const wf = workflow({
      jobs: {
        test: job({
          runsOn: "ubuntu-latest",
          steps: [step({ uses: "actions/checkout@v4" })],
        }),
      },
    });
    const cloned = cloneModel(wf);
    const transform = pinTransform(makeLockfile());
    transform(cloned);

    const jobs = cloned.data["jobs"] as Record<string, Model>;
    const steps = jobs["test"]!.data["steps"] as Model[];
    const uses = steps[0]!.data["uses"];
    expect(isCommented(uses)).toBe(true);
    expect((uses as Commented<string>).value).toBe(
      "actions/checkout@3df4ab11eba7bda6032a0b82a6bb43b11571feac",
    );
    expect((uses as Commented<string>).eolComment).toBe("v4");
  });

  it("throws PinError when an entry is missing", () => {
    const wf = workflow({
      jobs: {
        test: job({
          runsOn: "ubuntu-latest",
          steps: [step({ uses: "unknown/repo@v1" })],
        }),
      },
    });
    const cloned = cloneModel(wf);
    const transform = pinTransform(makeLockfile());
    expect(() => transform(cloned)).toThrow(PinError);
  });

  it("leaves a hand-pinned SHA untouched (never throws PinError)", () => {
    const sha = "d".repeat(40);
    const wf = workflow({
      jobs: {
        test: job({
          runsOn: "ubuntu-latest",
          steps: [step({ uses: `actions/checkout@${sha}` })],
        }),
      },
    });
    const cloned = cloneModel(wf);
    // Empty lockfile: a lookup would throw, so this proves the SHA ref is
    // skipped before any lockfile consultation.
    const transform = pinTransform(new Lockfile());
    expect(() => transform(cloned)).not.toThrow();

    const jobs = cloned.data["jobs"] as Record<string, Model>;
    const steps = jobs["test"]!.data["steps"] as Model[];
    expect(steps[0]!.data["uses"]).toBe(`actions/checkout@${sha}`);
  });

  it("skips local refs (./) and docker refs", () => {
    const wf = workflow({
      jobs: {
        test: job({
          runsOn: "ubuntu-latest",
          steps: [step({ uses: "./local/action" }), step({ uses: "docker://node:20" })],
        }),
      },
    });
    const cloned = cloneModel(wf);
    const transform = pinTransform(makeLockfile());
    expect(() => transform(cloned)).not.toThrow();
  });

  it("pins job.uses (reusable workflow refs)", () => {
    // Create a job with a uses field by reaching into data after the
    // factory. The job factory currently has no `uses` field — this is
    // a smoke test that the transform still walks the structure
    // correctly when uses appears at the job level.
    const j = job({
      runsOn: "ubuntu-latest",
      steps: [step({ uses: "actions/checkout@v4" })],
    });
    (j.data as Record<string, string>)["uses"] = "actions/checkout@v4";
    const wf = workflow({ jobs: { test: j } });
    const cloned = cloneModel(wf);
    pinTransform(makeLockfile())(cloned);

    const jobs = cloned.data["jobs"] as Record<string, Model>;
    const jobUses = jobs["test"]!.data["uses"];
    expect(isCommented(jobUses)).toBe(true);
    expect((jobUses as Commented<string>).value).toBe(
      "actions/checkout@3df4ab11eba7bda6032a0b82a6bb43b11571feac",
    );
    expect((jobUses as Commented<string>).eolComment).toBe("v4");
  });

  it("pins composite-action steps", () => {
    const a = action({
      name: "x",
      description: "x",
      runs: compositeRuns({
        using: "composite",
        steps: [step({ uses: "actions/checkout@v4" })],
      }),
    });
    const cloned = cloneModel(a);
    pinTransform(makeLockfile())(cloned);
    const runs = cloned.data["runs"] as Model;
    const steps = runs.data["steps"] as Model[];
    const actionUses = steps[0]!.data["uses"];
    expect(isCommented(actionUses)).toBe(true);
    expect((actionUses as Commented<string>).value).toBe(
      "actions/checkout@3df4ab11eba7bda6032a0b82a6bb43b11571feac",
    );
  });
});
