import { describe, it, expect } from "vitest";
import { UsesSite, iterUsesSites } from "./sites.js";
import { workflow } from "../models/workflow.js";
import { job } from "../models/job.js";
import { step } from "../models/step.js";
import { action, compositeRuns, dockerRuns, nodeRuns } from "../models/action.js";
import { isCommented, withComment } from "../models/_base.js";
import type { Commented, Document, Model } from "../models/_base.js";
import { toYaml } from "../emitter/yaml-writer.js";

const SHA = "a".repeat(40);

/** The `uses` string of every site yielded for `document`. */
function usesOf(document: Document): string[] {
  return [...iterUsesSites(document)].map((s) => s.uses);
}

describe("iterUsesSites()", () => {
  it("yields sites for nested jobs and steps", () => {
    const j = job({
      runsOn: "ubuntu-latest",
      steps: [step({ uses: "actions/checkout@v4" }), step({ uses: "actions/setup-python@v5" })],
    });
    // The job factory has no `uses` field; set a reusable-workflow call directly.
    (j.data as Record<string, string>)["uses"] = "octo/repo/.github/workflows/ci.yml@v1";
    const wf = workflow({ jobs: { build: j } });

    expect(new Set(usesOf(wf))).toEqual(
      new Set([
        "actions/checkout@v4",
        "actions/setup-python@v5",
        "octo/repo/.github/workflows/ci.yml@v1",
      ]),
    );
  });

  it("carries the parsed ref on each site", () => {
    const wf = workflow({
      jobs: {
        build: job({ runsOn: "ubuntu-latest", steps: [step({ uses: "actions/checkout@v4" })] }),
      },
    });
    const sites = [...iterUsesSites(wf)];
    expect(sites).toHaveLength(1);
    const site = sites[0]!;
    expect(site).toBeInstanceOf(UsesSite);
    expect(site.uses).toBe("actions/checkout@v4");
    expect(site.ref.owner).toBe("actions");
    expect(site.ref.repo).toBe("checkout");
    expect(site.ref.ref).toBe("v4");
    expect(site.ref.isPinnable).toBe(true);
  });

  it("sees through a Commented-wrapped uses", () => {
    const wf = workflow({
      jobs: {
        build: job({
          runsOn: "ubuntu-latest",
          steps: [step({ uses: withComment("actions/checkout@v4", "pin me") })],
        }),
      },
    });
    const sites = [...iterUsesSites(wf)];
    expect(sites).toHaveLength(1);
    expect(sites[0]!.uses).toBe("actions/checkout@v4");
    expect(sites[0]!.ref.isPinnable).toBe(true);
  });

  it("yields no site for local (./) refs", () => {
    const wf = workflow({
      jobs: { build: job({ runsOn: "ubuntu-latest", steps: [step({ uses: "./local-action" })] }) },
    });
    expect([...iterUsesSites(wf)]).toHaveLength(0);
  });

  it("yields no site for docker refs", () => {
    const wf = workflow({
      jobs: {
        build: job({ runsOn: "ubuntu-latest", steps: [step({ uses: "docker://node:18" })] }),
      },
    });
    expect([...iterUsesSites(wf)]).toHaveLength(0);
  });

  it("yields no site for run steps", () => {
    const wf = workflow({
      jobs: { build: job({ runsOn: "ubuntu-latest", steps: [step({ run: "echo hi" })] }) },
    });
    expect([...iterUsesSites(wf)]).toHaveLength(0);
  });

  it("yields a site for an already-SHA ref, but not pinnable", () => {
    const wf = workflow({
      jobs: {
        build: job({ runsOn: "ubuntu-latest", steps: [step({ uses: `actions/checkout@${SHA}` })] }),
      },
    });
    const sites = [...iterUsesSites(wf)];
    expect(sites).toHaveLength(1);
    expect(sites[0]!.uses).toBe(`actions/checkout@${SHA}`);
    expect(sites[0]!.ref.isPinnable).toBe(false);
  });

  it("yields sites for composite-action runs.steps", () => {
    const a = action({
      name: "greet",
      description: "say hi",
      runs: compositeRuns({
        using: "composite",
        steps: [
          step({ uses: "actions/setup-python@v5" }),
          step({ run: "echo hi", shell: "bash" }),
          step({ uses: "./local" }),
        ],
      }),
    });
    expect(usesOf(a)).toEqual(["actions/setup-python@v5"]);
  });

  it("yields no site for a docker action", () => {
    const a = action({
      name: "d",
      description: "d",
      runs: dockerRuns({ image: "docker://alpine:3" }),
    });
    expect([...iterUsesSites(a)]).toHaveLength(0);
  });

  it("yields no site for a node action", () => {
    const a = action({
      name: "n",
      description: "n",
      runs: nodeRuns({ using: "node20", main: "dist/index.js" }),
    });
    expect([...iterUsesSites(a)]).toHaveLength(0);
  });
});

describe("UsesSite.replace()", () => {
  it("wraps the new value with the original ref as an EOL comment", () => {
    const wf = workflow({
      jobs: {
        build: job({ runsOn: "ubuntu-latest", steps: [step({ uses: "actions/checkout@v4" })] }),
      },
    });
    const site = [...iterUsesSites(wf)][0]!;
    site.replace(site.ref.withSha(SHA));

    const jobs = wf.data["jobs"] as Record<string, Model>;
    const steps = jobs["build"]!.data["steps"] as Model[];
    const uses = steps[0]!.data["uses"];
    expect(isCommented(uses)).toBe(true);
    expect((uses as Commented<string>).value).toBe(`actions/checkout@${SHA}`);
    expect((uses as Commented<string>).eolComment).toBe("v4");
  });

  it("preserves an existing block comment through replace", () => {
    const wf = workflow({
      jobs: {
        build: job({
          runsOn: "ubuntu-latest",
          steps: [step({ uses: withComment("actions/checkout@v4", "keep me") })],
        }),
      },
    });
    const site = [...iterUsesSites(wf)][0]!;
    site.replace(site.ref.withSha(SHA));

    const jobs = wf.data["jobs"] as Record<string, Model>;
    const steps = jobs["build"]!.data["steps"] as Model[];
    const uses = steps[0]!.data["uses"] as Commented<string>;
    expect((uses as unknown as { value: string }).value).toBe(`actions/checkout@${SHA}`);
    expect(uses.comment).toBe("keep me");
    expect(uses.eolComment).toBe("v4");
  });

  it("round-trips comments into the emitted YAML", () => {
    const wf = workflow({
      name: "CI",
      jobs: {
        build: job({
          runsOn: "ubuntu-latest",
          steps: [step({ uses: withComment("actions/checkout@v4", "please pin") })],
        }),
      },
    });
    for (const site of iterUsesSites(wf)) {
      site.replace(site.ref.withSha(SHA));
    }
    const yaml = toYaml(wf, { header: null });
    expect(yaml).toContain(`actions/checkout@${SHA}`);
    expect(yaml).toContain("# v4");
    expect(yaml).toContain("# please pin");
  });
});
