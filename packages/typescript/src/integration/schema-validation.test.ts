import { describe, it, expect } from "vitest";
import { validateWorkflowYaml, validateActionYaml } from "./test-utils.js";
import { toYaml } from "../emitter/yaml-writer.js";
import { workflow } from "../models/workflow.js";
import { job } from "../models/job.js";
import { step } from "../models/step.js";
import {
  action,
  actionInputDef,
  actionOutputDef,
  branding,
  compositeRuns,
  dockerRuns,
  nodeRuns,
} from "../models/action.js";
function workflowYaml(w: ReturnType<typeof workflow>): string {
  return toYaml(w, { header: null });
}

function actionYaml(a: ReturnType<typeof action>): string {
  return toYaml(a, { header: null });
}

describe("workflow schema validation", () => {
  it("validates a simple CI workflow", () => {
    const w = workflow({
      name: "CI",
      on: { push: { branches: ["main"] } },
      jobs: {
        test: job({
          runsOn: "ubuntu-latest",
          steps: [step({ uses: "actions/checkout@v4" }), step({ name: "Test", run: "npm test" })],
        }),
      },
    });
    expect(() => validateWorkflowYaml(workflowYaml(w))).not.toThrow();
  });

  it("validates a matrix workflow", () => {
    const w = workflow({
      name: "Matrix",
      on: { push: { branches: ["main"] } },
      jobs: {
        test: job({
          runsOn: "ubuntu-latest",
          strategy: {
            matrix_: { "node-version": ["18", "20", "22"] },
          },
          steps: [step({ uses: "actions/checkout@v4" }), step({ name: "Test", run: "npm test" })],
        }),
      },
    });
    expect(() => validateWorkflowYaml(workflowYaml(w))).not.toThrow();
  });

  it("validates a full-featured workflow", () => {
    const w = workflow({
      name: "Full",
      on: {
        push: { branches: ["main"], tags: ["v*"] },
        pullRequest: { branches: ["main"] },
        schedule: [{ cron: "0 0 * * 0" }],
        workflowDispatch: {
          inputs: {
            env: { description: "Target environment", required: true, type: "string" },
          },
        },
      },
      permissions: { contents: "read", pullRequests: "write" },
      env: { CI: "true" },
      concurrency: { group: "${{ github.workflow }}", cancelInProgress: true },
      jobs: {
        build: job({
          runsOn: "ubuntu-latest",
          strategy: {
            matrix_: { "python-version": ["3.11", "3.12"] },
          },
          container: { image: "python:3.12" },
          services: {
            redis: { image: "redis:7", ports: [6379] },
          },
          steps: [
            step({ name: "Checkout", uses: "actions/checkout@v6", with_: { "fetch-depth": 1 } }),
            step({
              name: "Set up Python",
              uses: "actions/setup-python@v6",
              with_: { "python-version": "${{ matrix.python-version }}" },
            }),
            step({ name: "Build", run: "make build" }),
          ],
        }),
      },
    });
    expect(() => validateWorkflowYaml(workflowYaml(w))).not.toThrow();
  });

  it("validates schedule and workflow_dispatch triggers", () => {
    const w = workflow({
      name: "Scheduled",
      on: {
        schedule: [{ cron: "30 5 * * 1" }],
        workflowDispatch: {
          inputs: {
            debug: { description: "Enable debug", type: "boolean", default: false },
          },
        },
      },
      jobs: {
        run: job({
          runsOn: "ubuntu-latest",
          steps: [step({ name: "Go", run: "echo running" })],
        }),
      },
    });
    expect(() => validateWorkflowYaml(workflowYaml(w))).not.toThrow();
  });

  it("validates all 16 permission scopes", () => {
    const w = workflow({
      name: "All Perms",
      on: { push: { branches: ["main"] } },
      permissions: {
        actions: "read",
        artifactMetadata: "read",
        attestations: "write",
        checks: "write",
        contents: "read",
        deployments: "read",
        discussions: "read",
        idToken: "write",
        issues: "write",
        models: "read",
        packages: "read",
        pages: "write",
        pullRequests: "write",
        repositoryProjects: "read",
        securityEvents: "read",
        statuses: "read",
      },
      jobs: {
        noop: job({
          runsOn: "ubuntu-latest",
          steps: [step({ name: "Noop", run: "echo ok" })],
        }),
      },
    });
    expect(() => validateWorkflowYaml(workflowYaml(w))).not.toThrow();
  });

  it("validates a container and services workflow", () => {
    const w = workflow({
      name: "Containers",
      on: { push: { branches: ["main"] } },
      jobs: {
        test: job({
          runsOn: "ubuntu-latest",
          container: { image: "node:20" },
          services: {
            db: { image: "postgres:16", env: { POSTGRES_PASSWORD: "test" }, ports: [5432] },
          },
          steps: [step({ uses: "actions/checkout@v4" }), step({ name: "Test", run: "npm test" })],
        }),
      },
    });
    expect(() => validateWorkflowYaml(workflowYaml(w))).not.toThrow();
  });
});

describe("action schema validation", () => {
  it("validates a composite action", () => {
    const a = action({
      name: "My Action",
      description: "Does something",
      inputs: {
        name: actionInputDef({ description: "A name", required: true }),
      },
      outputs: {
        result: actionOutputDef({
          description: "The result",
          value: "${{ steps.run.outputs.result }}",
        }),
      },
      runs: compositeRuns({
        using: "composite",
        steps: [step({ id: "run", name: "Run", run: "echo hi", shell: "bash" })],
      }),
    });
    expect(() => validateActionYaml(actionYaml(a))).not.toThrow();
  });

  it("validates a Docker action", () => {
    const a = action({
      name: "Docker Action",
      description: "Runs in Docker",
      branding: branding({ icon: "box", color: "blue" }),
      inputs: {
        who: actionInputDef({ description: "Target", default: "world" }),
      },
      runs: dockerRuns({
        using: "docker",
        image: "Dockerfile",
        args: ["${{ inputs.who }}"],
      }),
    });
    expect(() => validateActionYaml(actionYaml(a))).not.toThrow();
  });

  it("validates a Node.js action", () => {
    const a = action({
      name: "Node Action",
      description: "Runs on Node",
      branding: branding({ icon: "code", color: "yellow" }),
      runs: nodeRuns({
        using: "node20",
        main: "dist/index.js",
        post: "dist/cleanup.js",
        postIf: "always()",
      }),
    });
    expect(() => validateActionYaml(actionYaml(a))).not.toThrow();
  });
});

describe("published input unions reach the file intact", () => {
  it("emits the blanket permissions shorthand as a bare scalar at both levels", () => {
    // Peer of the Python test of the same name. Divergence 2 of issue 27 ran
    // the other way here -- TypeScript already accepted the shorthand on a
    // job -- so this port's job is to hold the emission contract the Python
    // widening had to be measured against: an unquoted scalar on the key's
    // own line, never a one-key mapping.
    const w = workflow({
      name: "Blanket",
      on: { push: { branches: ["main"] } },
      permissions: "read-all",
      jobs: {
        test: job({
          runsOn: "ubuntu-latest",
          permissions: "write-all",
          steps: [step({ uses: "actions/checkout@v4" })],
        }),
      },
    });

    const text = workflowYaml(w);
    expect(text).toContain("\npermissions: read-all\n");
    expect(text).toContain("\n    permissions: write-all\n");
    // A mapping would leave the key alone on its line, scopes beneath it.
    expect(text).not.toContain("permissions:\n");
    expect(text).not.toContain("'read-all'");
    expect(text).not.toContain('"write-all"');
    expect(() => validateWorkflowYaml(text)).not.toThrow();
  });

  it("emits workflow_dispatch input defaults across the whole type union", () => {
    // Divergence 3: `default` is `string | boolean | number` here and was
    // `str | None` in Python. This is the emission side of the union both
    // ports now declare -- and the reason Python spells `int` alongside
    // `float`, since `3.0` would be a different document.
    const w = workflow({
      name: "Defaults",
      on: {
        workflowDispatch: {
          inputs: {
            flag: { type: "boolean", default: true },
            count: { type: "number", default: 3 },
            ratio: { type: "number", default: 3.5 },
            label: { type: "string", default: "a-string" },
          },
        },
      },
      jobs: {
        test: job({
          runsOn: "ubuntu-latest",
          steps: [step({ uses: "actions/checkout@v4" })],
        }),
      },
    });

    const text = workflowYaml(w);
    expect(text).toContain("default: true\n");
    expect(text).toContain("default: 3\n");
    expect(text).toContain("default: 3.5\n");
    expect(text).toContain("default: a-string\n");
    expect(text).not.toContain("default: 3.0\n");
    expect(() => validateWorkflowYaml(text)).not.toThrow();
  });
});
