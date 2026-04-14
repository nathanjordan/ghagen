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
import { checkout, setupPython } from "../helpers/steps.js";

function workflowYaml(w: ReturnType<typeof workflow>): string {
  return toYaml(w, { includeHeader: false });
}

function actionYaml(a: ReturnType<typeof action>): string {
  return toYaml(a, { includeHeader: false });
}

describe("workflow schema validation", () => {
  it("validates a simple CI workflow", () => {
    const w = workflow({
      name: "CI",
      on: { push: { branches: ["main"] } },
      jobs: {
        test: job({
          runsOn: "ubuntu-latest",
          steps: [
            step({ uses: "actions/checkout@v4" }),
            step({ name: "Test", run: "npm test" }),
          ],
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
          steps: [
            step({ uses: "actions/checkout@v4" }),
            step({ name: "Test", run: "npm test" }),
          ],
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
            checkout(),
            setupPython({ version: "${{ matrix.python-version }}" }),
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

  it("validates all 13 permission scopes", () => {
    const w = workflow({
      name: "All Perms",
      on: { push: { branches: ["main"] } },
      permissions: {
        actions: "read",
        checks: "write",
        contents: "read",
        deployments: "read",
        discussions: "read",
        idToken: "write",
        issues: "write",
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
          steps: [
            step({ uses: "actions/checkout@v4" }),
            step({ name: "Test", run: "npm test" }),
          ],
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
        result: actionOutputDef({ description: "The result", value: "${{ steps.run.outputs.result }}" }),
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
