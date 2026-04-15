import { describe, it, expect } from "vitest";
import { Pair, Scalar } from "yaml";
import { loadFixture } from "./test-utils.js";
import { toYaml } from "../emitter/yaml-writer.js";
import { raw } from "../models/_base.js";
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
describe("snapshot tests", () => {
  it("ci_basic.yml", () => {
    const w = workflow({
      name: "CI",
      on: { push: { branches: ["main"] }, pullRequest: { branches: ["main"] } },
      jobs: {
        test: job({
          runsOn: "ubuntu-latest",
          steps: [
            step({ uses: "actions/checkout@v4" }),
            step({ name: "Run tests", run: "python -m pytest" }),
          ],
        }),
      },
    });
    expect(toYaml(w, { includeHeader: false })).toBe(loadFixture("ci_basic.yml"));
  });

  it("comments.yml", () => {
    const w = workflow({
      name: "Commented Workflow",
      on: { push: { branches: ["main"] } },
      fieldComments: { name: "The name shown in the GitHub UI" },
      fieldEolComments: { on: "trigger configuration" },
      jobs: {
        lint: job({
          name: "Lint",
          runsOn: "ubuntu-latest",
          steps: [
            step({ uses: "actions/checkout@v4" }),
            step({ name: "Ruff", run: "ruff check .", eolComment: "fast Python linter" }),
          ],
        }),
        test: job({
          name: "Test",
          runsOn: "ubuntu-latest",
          needs: "lint",
          fieldComments: { needs: "Wait for lint to pass" },
          steps: [
            step({ uses: "actions/checkout@v4" }),
            step({ name: "Pytest", run: "python -m pytest" }),
          ],
        }),
      },
    });
    expect(toYaml(w, { includeHeader: false })).toBe(loadFixture("comments.yml"));
  });

  it("composite_action.yml", () => {
    const a = action({
      name: "Greet",
      description: "Say hello to someone",
      author: "ghagen",
      branding: branding({ icon: "heart", color: "purple" }),
      inputs: {
        who: actionInputDef({ description: "Who to greet", required: true, default: "world" }),
        shout: actionInputDef({
          description: "Uppercase the greeting",
          required: false,
          default: "false",
        }),
      },
      outputs: {
        message: actionOutputDef({
          description: "The greeting message",
          value: "${{ steps.greet.outputs.text }}",
        }),
      },
      runs: compositeRuns({
        using: "composite",
        steps: [
          step({ id: "greet", name: "Greet", run: "echo Hello, ${{ inputs.who }}", shell: "bash" }),
        ],
      }),
    });
    expect(toYaml(a, { includeHeader: false })).toBe(loadFixture("composite_action.yml"));
  });

  it("docker_action.yml", () => {
    const a = action({
      name: "Docker Greet",
      description: "Greet inside a container",
      branding: branding({ icon: "box", color: "blue" }),
      inputs: {
        who: actionInputDef({ description: "Who to greet", default: "world" }),
      },
      outputs: {
        time: actionOutputDef({ description: "Time the action ran" }),
      },
      runs: dockerRuns({
        using: "docker",
        image: "Dockerfile",
        env: { GREETING: "Hello" },
        args: ["${{ inputs.who }}"],
        entrypoint: "entrypoint.sh",
        postEntrypoint: "cleanup.sh",
        postIf: "always()",
      }),
    });
    expect(toYaml(a, { includeHeader: false })).toBe(loadFixture("docker_action.yml"));
  });

  it("node_action.yml", () => {
    const a = action({
      name: "Node Greet",
      description: "Greet from a Node script",
      branding: branding({ icon: "code", color: "yellow" }),
      inputs: {
        who: actionInputDef({ description: "Who to greet", default: "world" }),
      },
      outputs: {
        message: actionOutputDef({ description: "The greeting" }),
      },
      runs: nodeRuns({
        using: "node20",
        main: "dist/index.js",
        pre: "dist/setup.js",
        post: "dist/cleanup.js",
        postIf: "always()",
      }),
    });
    expect(toYaml(a, { includeHeader: false })).toBe(loadFixture("node_action.yml"));
  });

  it("escape_hatches.yml", () => {
    const w = workflow({
      name: "Escape Hatches",
      on: { push: { branches: ["main"] } },
      postProcess: (node) => {
        node.add(new Pair(new Scalar("x-generated-by"), "ghagen"));
      },
      jobs: {
        typed: job({
          runsOn: "ubuntu-latest",
          steps: [step({ name: "Custom shell", run: "echo hello", shell: raw("custom-shell") })],
          extras: { "custom-timeout": 30 },
        }),
        raw: { "runs-on": "ubuntu-latest", steps: [{ run: "echo 'raw job'" }] } as any,
      },
    });
    expect(toYaml(w, { includeHeader: false })).toBe(loadFixture("escape_hatches.yml"));
  });

  it("full_featured.yml", () => {
    const w = workflow({
      name: "Full Featured",
      on: {
        push: { branches: ["main"], tags: ["v*"] },
        pullRequest: { branches: ["main"] },
        schedule: [{ cron: "0 0 * * 0" }],
        workflowDispatch: {
          inputs: {
            target: { description: "Deploy target", required: true, type: "string" },
          },
        },
      },
      permissions: { contents: "read", pullRequests: "write" },
      env: { CI: "true" },
      concurrency: { group: "${{ github.workflow }}-${{ github.ref }}", cancelInProgress: true },
      jobs: {
        lint: job({
          name: "Lint",
          runsOn: "ubuntu-latest",
          steps: [
            step({ name: "Checkout", uses: "actions/checkout@v6", with_: { "fetch-depth": 1 } }),
            step({ name: "Ruff", run: "ruff check ." }),
          ],
        }),
        test: job({
          name: "Test",
          runsOn: "ubuntu-latest",
          needs: "lint",
          strategy: { matrix_: { "python-version": ["3.11", "3.12", "3.13"] } },
          steps: [
            step({ name: "Checkout", uses: "actions/checkout@v6", with_: { "fetch-depth": 1 } }),
            step({
              name: "Set up Python",
              uses: "actions/setup-python@v6",
              with_: { "python-version": "${{ matrix.python-version }}" },
            }),
            step({ name: "Test", run: "python -m pytest" }),
          ],
        }),
        "container-test": job({
          name: "Container Test",
          runsOn: "ubuntu-latest",
          needs: "lint",
          container: { image: "python:3.13" },
          services: {
            db: { image: "postgres:16", env: { POSTGRES_PASSWORD: "test" }, ports: [5432] },
          },
          steps: [
            step({ name: "Checkout", uses: "actions/checkout@v6", with_: { "fetch-depth": 1 } }),
            step({ name: "Test with DB", run: "python -m pytest --db" }),
          ],
        }),
        deploy: job({
          uses: "octo-org/deploy/.github/workflows/deploy.yml@main",
          needs: ["test", "container-test"],
          with_: { environment: "production" },
          secrets: "inherit",
        }),
      },
    });
    expect(toYaml(w, { includeHeader: false })).toBe(loadFixture("full_featured.yml"));
  });

  it("matrix_complex.yml", () => {
    const w = workflow({
      name: "Matrix CI",
      on: { push: { branches: ["main"] } },
      jobs: {
        test: job({
          name: "Test (${{ matrix.python-version }}, ${{ matrix.os }})",
          runsOn: raw("${{ matrix.os }}"),
          strategy: {
            matrix_: {
              "python-version": ["3.11", "3.12", "3.13"],
              os: ["ubuntu-latest", "macos-latest", "windows-latest"],
              exclude: [{ os: "windows-latest", "python-version": "3.11" }],
            },
            failFast: false,
          },
          steps: [
            step({ name: "Checkout", uses: "actions/checkout@v6", with_: { "fetch-depth": 1 } }),
            step({
              name: "Set up Python",
              uses: "actions/setup-python@v6",
              with_: { "python-version": "${{ matrix.python-version }}" },
            }),
            step({ name: "Install deps", run: "pip install -e '.[test]'" }),
            step({ name: "Test", run: "python -m pytest" }),
          ],
        }),
      },
    });
    expect(toYaml(w, { includeHeader: false })).toBe(loadFixture("matrix_complex.yml"));
  });

  it("multiline_run.yml", () => {
    const w = workflow({
      name: "Multiline",
      on: { push: { branches: ["main"] } },
      jobs: {
        test: job({
          runsOn: "ubuntu-latest",
          steps: [
            step({ uses: "actions/checkout@v4" }),
            step({ name: "Tests", run: "python -m pytest\ncoverage report\n" }),
            step({ name: "Inline", run: "echo single-line" }),
            step({ name: "Strip", run: "echo one\necho two" }),
          ],
        }),
      },
    });
    expect(toYaml(w, { includeHeader: false })).toBe(loadFixture("multiline_run.yml"));
  });

  it("triple_quoted_run.yml", () => {
    const w = workflow({
      name: "Multiline",
      on: { push: { branches: ["main"] } },
      jobs: {
        test: job({
          runsOn: "ubuntu-latest",
          steps: [
            step({ uses: "actions/checkout@v4" }),
            step({ name: "Tests", run: "python -m pytest\ncoverage report" }),
            step({ name: "Inline", run: "echo single-line" }),
            step({ name: "Strip", run: "echo one\necho two" }),
          ],
        }),
      },
    });
    expect(toYaml(w, { includeHeader: false })).toBe(loadFixture("triple_quoted_run.yml"));
  });
});
