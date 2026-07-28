/**
 * Unit tests for `collectUsesRefs` — extracting pinnable `uses:` refs.
 *
 * Kept in lockstep with packages/python/tests/test_pin/test_collect.py.
 * `collectUsesRefs` returns parsed, deduplicated `UsesRef`s sorted by their
 * full ref string (`UsesRef.uses`), not bare strings. Assertions compare on
 * `refs.map((r) => r.uses)` (the lockfile key) and, where the richer type
 * matters, on the parsed components the engine relies on.
 */

import { describe, it, expect } from "vitest";
import { App } from "../app.js";
import { action, compositeRuns, dockerRuns, nodeRuns } from "../models/action.js";
import { job } from "../models/job.js";
import { step } from "../models/step.js";
import { workflow } from "../models/workflow.js";
import { collectUsesRefs } from "./collect.js";

function appWithSteps(...uses: string[]): App {
  const app = new App({ root: "/tmp/ghagen-collect" });
  app.addWorkflow(
    workflow({
      name: "CI",
      on: { push: { branches: ["main"] } },
      jobs: {
        build: job({
          runsOn: "ubuntu-latest",
          steps: uses.map((u) => step({ uses: u })),
        }),
      },
    }),
    "ci.yml",
  );
  return app;
}

describe("collectUsesRefs", () => {
  it("collects a basic action ref with its parsed components", () => {
    const refs = collectUsesRefs(appWithSteps("actions/checkout@v4"));
    expect(refs.map((r) => r.uses)).toEqual(["actions/checkout@v4"]);
    expect(refs[0]!.owner).toBe("actions");
    expect(refs[0]!.repo).toBe("checkout");
    expect(refs[0]!.ref).toBe("v4");
  });

  it("returns refs sorted by full ref string regardless of authored order", () => {
    const refs = collectUsesRefs(appWithSteps("actions/setup-python@v5", "actions/checkout@v4"));
    expect(refs.map((r) => r.uses)).toEqual(["actions/checkout@v4", "actions/setup-python@v5"]);
  });

  it("deduplicates by full ref string", () => {
    const app = new App({ root: "/tmp/ghagen-collect" });
    app.addWorkflow(
      workflow({
        name: "CI",
        on: { push: { branches: ["main"] } },
        jobs: {
          a: job({ runsOn: "ubuntu-latest", steps: [step({ uses: "actions/checkout@v4" })] }),
          b: job({ runsOn: "ubuntu-latest", steps: [step({ uses: "actions/checkout@v4" })] }),
        },
      }),
      "ci.yml",
    );
    const refs = collectUsesRefs(app);
    expect(refs).toHaveLength(1);
    expect(refs[0]!.uses).toBe("actions/checkout@v4");
  });

  it("keeps distinct refs of the same repo separate", () => {
    const refs = collectUsesRefs(appWithSteps("actions/checkout@v4", "actions/checkout@v5"));
    expect(refs.map((r) => r.uses)).toEqual(["actions/checkout@v4", "actions/checkout@v5"]);
  });

  it("skips local refs", () => {
    expect(collectUsesRefs(appWithSteps("./local-action"))).toEqual([]);
  });

  it("skips docker refs", () => {
    expect(collectUsesRefs(appWithSteps("docker://node:18"))).toEqual([]);
  });

  it("skips refs already pinned to a SHA", () => {
    expect(collectUsesRefs(appWithSteps(`actions/checkout@${"a".repeat(40)}`))).toEqual([]);
  });

  it("skips run steps", () => {
    const app = new App({ root: "/tmp/ghagen-collect" });
    app.addWorkflow(
      workflow({
        name: "CI",
        on: { push: { branches: ["main"] } },
        jobs: {
          build: job({ runsOn: "ubuntu-latest", steps: [step({ run: "echo hello" })] }),
        },
      }),
      "ci.yml",
    );
    expect(collectUsesRefs(app)).toEqual([]);
  });

  it("collects a reusable-workflow ref with its path", () => {
    const app = new App({ root: "/tmp/ghagen-collect" });
    app.addWorkflow(
      workflow({
        name: "CI",
        on: { push: { branches: ["main"] } },
        jobs: {
          call: job({ uses: "octo-org/repo/.github/workflows/ci.yml@v1" }),
        },
      }),
      "ci.yml",
    );
    const refs = collectUsesRefs(app);
    expect(refs.map((r) => r.uses)).toEqual(["octo-org/repo/.github/workflows/ci.yml@v1"]);
    expect(refs[0]!.path).toBe(".github/workflows/ci.yml");
    expect(refs[0]!.ref).toBe("v1");
  });
});

describe("collectUsesRefs from actions", () => {
  it("collects composite-action steps just like workflow steps", () => {
    const app = new App({ root: "/tmp/ghagen-collect" });
    app.addAction(
      action({
        name: "greet",
        description: "say hi",
        runs: compositeRuns({
          using: "composite",
          steps: [
            step({ uses: "actions/setup-python@v5" }),
            step({ uses: "actions/checkout@v4" }),
            step({ run: "echo hi", shell: "bash" }),
          ],
        }),
      }),
    );
    const refs = collectUsesRefs(app);
    expect(refs.map((r) => r.uses)).toEqual(["actions/checkout@v4", "actions/setup-python@v5"]);
  });

  it("skips local and docker refs in composite steps", () => {
    const app = new App({ root: "/tmp/ghagen-collect" });
    app.addAction(
      action({
        name: "greet",
        description: "say hi",
        runs: compositeRuns({
          using: "composite",
          steps: [step({ uses: "./local-step" }), step({ uses: "docker://alpine:3" })],
        }),
      }),
    );
    expect(collectUsesRefs(app)).toEqual([]);
  });

  it("does not scan docker action runs", () => {
    const app = new App({ root: "/tmp/ghagen-collect" });
    app.addAction(
      action({
        name: "docker-action",
        description: "runs in a container",
        runs: dockerRuns({ image: "docker://alpine:3" }),
      }),
    );
    expect(collectUsesRefs(app)).toEqual([]);
  });

  it("does not scan node action runs", () => {
    const app = new App({ root: "/tmp/ghagen-collect" });
    app.addAction(
      action({
        name: "node-action",
        description: "runs node",
        runs: nodeRuns({ using: "node20", main: "dist/index.js" }),
      }),
    );
    expect(collectUsesRefs(app)).toEqual([]);
  });

  it("merges and deduplicates refs from workflows and actions", () => {
    const app = new App({ root: "/tmp/ghagen-collect" });
    app.addWorkflow(
      workflow({
        name: "CI",
        on: { push: { branches: ["main"] } },
        jobs: {
          build: job({ runsOn: "ubuntu-latest", steps: [step({ uses: "actions/checkout@v4" })] }),
        },
      }),
      "ci.yml",
    );
    app.addAction(
      action({
        name: "a",
        description: "d",
        runs: compositeRuns({
          using: "composite",
          steps: [
            step({ uses: "actions/checkout@v4" }), // duplicate
            step({ uses: "actions/setup-python@v5" }),
          ],
        }),
      }),
    );
    const refs = collectUsesRefs(app);
    expect(refs.map((r) => r.uses)).toEqual(["actions/checkout@v4", "actions/setup-python@v5"]);
  });
});
