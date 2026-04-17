import { describe, it, expect } from "vitest";
import { Lockfile } from "./lockfile.js";
import { PinError, pinTransform } from "./transform.js";
import { workflow } from "../models/workflow.js";
import { job } from "../models/job.js";
import { step } from "../models/step.js";
import { action, compositeRuns } from "../models/action.js";
import { cloneModel } from "../models/_base.js";
import type { Model } from "../models/_base.js";

const ctx = { workflowKey: "ci", itemType: "workflow" as const, root: "/" };

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
    transform(cloned, ctx);

    const jobs = cloned._data["jobs"] as Record<string, Model>;
    const steps = jobs["test"]!._data["steps"] as Model[];
    expect(steps[0]!._data["uses"]).toBe(
      "actions/checkout@3df4ab11eba7bda6032a0b82a6bb43b11571feac",
    );
    expect(steps[0]!._meta.fieldEolComments).toEqual({ uses: "v4" });
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
    expect(() => transform(cloned, ctx)).toThrow(PinError);
  });

  it("skips local refs (./) and docker refs", () => {
    const wf = workflow({
      jobs: {
        test: job({
          runsOn: "ubuntu-latest",
          steps: [
            step({ uses: "./local/action" }),
            step({ uses: "docker://node:20" }),
          ],
        }),
      },
    });
    const cloned = cloneModel(wf);
    const transform = pinTransform(makeLockfile());
    expect(() => transform(cloned, ctx)).not.toThrow();
  });

  it("pins job.uses (reusable workflow refs)", () => {
    // Create a job with a uses field by reaching into _data after the
    // factory. The job factory currently has no `uses` field — this is
    // a smoke test that the transform still walks the structure
    // correctly when uses appears at the job level.
    const j = job({
      runsOn: "ubuntu-latest",
      steps: [step({ uses: "actions/checkout@v4" })],
    });
    (j._data as Record<string, string>)["uses"] = "actions/checkout@v4";
    const wf = workflow({ jobs: { test: j } });
    const cloned = cloneModel(wf);
    pinTransform(makeLockfile())(cloned, ctx);

    const jobs = cloned._data["jobs"] as Record<string, Model>;
    expect(jobs["test"]!._data["uses"]).toBe(
      "actions/checkout@3df4ab11eba7bda6032a0b82a6bb43b11571feac",
    );
    expect(jobs["test"]!._meta.fieldEolComments?.["uses"]).toBe("v4");
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
    pinTransform(makeLockfile())(cloned, { ...ctx, itemType: "action" });
    const runs = cloned._data["runs"] as Model;
    const steps = runs._data["steps"] as Model[];
    expect(steps[0]!._data["uses"]).toBe(
      "actions/checkout@3df4ab11eba7bda6032a0b82a6bb43b11571feac",
    );
  });
});
