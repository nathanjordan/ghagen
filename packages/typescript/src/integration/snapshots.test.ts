import { describe, it, expect } from "vitest";
import { Pair, Scalar } from "yaml";
import { loadFixture } from "./test-utils.js";
import { toYaml } from "../emitter/yaml-writer.js";
import { raw, withComment, withEolComment } from "../models/_base.js";
import { workflow } from "../models/workflow.js";
import { job } from "../models/job.js";
import { step } from "../models/step.js";
import { on } from "../models/trigger.js";
import { workflowDispatch } from "../models/trigger.js";
import { imageSnapshot } from "../models/image-snapshot.js";
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
    expect(toYaml(w, { header: null })).toBe(loadFixture("ci_basic.yml"));
  });

  it("comments.yml", () => {
    const w = workflow({
      name: withComment("Commented Workflow", "The name shown in the GitHub UI"),
      on: withEolComment(
        {
          push: { branches: ["main"] },
          // An otherwise-empty sub-model carrying only its own comment.
          // `presentNullWhenEmpty` discards the map; the comment folds onto the
          // bare key rather than vanishing with it. Bound here so the two ports
          // cannot resolve it differently.
          workflowDispatch: workflowDispatch({ comment: "Run it by hand too" }),
        },
        "trigger configuration",
      ),
      jobs: {
        lint: job({
          // A model comment and a field comment on the SAME key: the model's
          // own comment comes first (see attachModelComment).
          name: withComment("Lint", "Shown in the checks list"),
          runsOn: "ubuntu-latest",
          comment: "Run linters before tests",
          steps: [
            step({ uses: "actions/checkout@v4" }),
            step({ name: "Ruff", run: "ruff check .", eolComment: "fast Python linter" }),
          ],
        }),
        test: job({
          name: "Test",
          runsOn: "ubuntu-latest",
          needs: withComment("lint", "Wait for lint to pass"),
          steps: [
            step({ uses: "actions/checkout@v4" }),
            step({ name: "Pytest", run: "python -m pytest" }),
          ],
        }),
      },
    });
    expect(toYaml(w, { header: null })).toBe(loadFixture("comments.yml"));
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
    expect(toYaml(a, { header: null })).toBe(loadFixture("composite_action.yml"));
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
    expect(toYaml(a, { header: null })).toBe(loadFixture("docker_action.yml"));
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
    expect(toYaml(a, { header: null })).toBe(loadFixture("node_action.yml"));
  });

  it("escape_hatches.yml", () => {
    // Also the byte-oracle for a `raw()` `ImageSnapshotInput.version` (issue
    // 22): "latest" fails the field's own grammar (`/^\d+(\.\d+|\*)?$/`), so
    // accepting it here proves `raw()` bypasses the check rather than merely
    // happening to match it, and pins what a `raw()` value emits -- a plain
    // scalar, exactly like an ordinary string.
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
          snapshot: imageSnapshot({ imageName: "custom-image", version: raw("latest") }),
          extras: { "custom-timeout": 30 },
        }),
        raw: { "runs-on": "ubuntu-latest", steps: [{ run: "echo 'raw job'" }] } as any,
      },
    });
    expect(toYaml(w, { header: null })).toBe(loadFixture("escape_hatches.yml"));
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
          snapshot: { imageName: "custom-ubuntu", version: "1.0" },
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
    expect(toYaml(w, { header: null })).toBe(loadFixture("full_featured.yml"));
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
    expect(toYaml(w, { header: null })).toBe(loadFixture("matrix_complex.yml"));
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
    expect(toYaml(w, { header: null })).toBe(loadFixture("multiline_run.yml"));
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
    expect(toYaml(w, { header: null })).toBe(loadFixture("triple_quoted_run.yml"));
  });

  // The five body shapes the byte oracle had no bytes for (docs/issues/02).
  // Every other fixture here is a workflow shape somebody wrote for its own
  // sake; this one exists because the *oracle* had holes, and each hole is a
  // path the ports could have diverged on with both suites green:
  //
  //  1. `defaults:` — at the workflow level and again inside a job, so the one
  //     defaults/defaultsRun pair is byte-bound at both places the schema
  //     allows it.
  //  2. present-null — `workflow_dispatch:` (the rule's original single
  //     member) and `create:` (one of the 34 keys docs/issues/04 widened it
  //     to). Both must be bare keys; neither may be `{}`.
  //  3. a dynamic extras interleave on an alphabetical spec —
  //     `pull_request_review_thread` is a real GitHub event the canonical
  //     Snapshot's `on:` map does not declare, so it cannot be a typed field
  //     (the conformance sweep asserts `on` covers exactly what the Snapshot
  //     declares) and must travel through `extras`. It sorts strictly between
  //     two typed keys, `create` and `push`, so a port that appended extras
  //     instead of interleaving them produces different bytes here.
  //  4. SHA-pinned `uses:` — a bare 40-hex ref, and the `# vX.Y.Z`
  //     end-of-line spelling that pinning tools actually emit.
  //  5. `workflow_call:` with inputs, outputs and secrets — no file under
  //     `fixtures/expected/` contained `workflow_call` at all before this one,
  //     so the canonical key order of the three sub-map defs (bound per-port
  //     by unit tests) had no shared oracle.
  //
  // Peer: `packages/python/tests/test_integration/test_snapshots.py`.
  it("body_shapes.yml", () => {
    const w = workflow({
      name: "Body Shapes",
      on: on({
        // Present-null on a key the old one-element allowlist did not cover.
        create: {},
        push: { branches: ["main"] },
        workflowCall: {
          inputs: {
            environment: {
              description: "Target environment",
              required: true,
              type: "string",
            },
          },
          outputs: {
            digest: {
              description: "Digest of the image this run built",
              value: "${{ jobs.build.outputs.digest }}",
            },
          },
          secrets: {
            "deploy-token": {
              description: "Token the deploy step authenticates with",
              required: true,
            },
          },
        },
        // Present-null on the key the rule started with.
        workflowDispatch: {},
        // An event GitHub ships ahead of the Snapshot: untyped, so it can only
        // arrive through extras, and it sorts between `create` and `push`.
        extras: { pull_request_review_thread: { types: ["resolved"] } },
      }),
      defaults: { run: { shell: "bash", workingDirectory: "src" } },
      jobs: {
        build: job({
          runsOn: "ubuntu-latest",
          defaults: { run: { workingDirectory: "build" } },
          outputs: { digest: "${{ steps.build.outputs.digest }}" },
          steps: [
            step({
              name: "Checkout",
              uses: withEolComment(
                "actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683",
                "v4.2.2",
              ),
            }),
            step({
              name: "Set up Python",
              uses: "actions/setup-python@0b93645e9fea7318ecaed2b359559ac225c90a2b",
            }),
            step({
              id: "build",
              name: "Build",
              run: 'echo "digest=sha256:deadbeef" >> "$GITHUB_OUTPUT"',
            }),
          ],
        }),
      },
    });
    expect(toYaml(w, { header: null })).toBe(loadFixture("body_shapes.yml"));
  });
});

// ---------------------------------------------------------------------------
// Header goldens — the cross-port byte oracle for `formatHeader`.
//
// The six files are generated from the Python port and read byte-for-byte by
// both suites; every byte that differs between them is header. Peer:
// `packages/python/tests/test_integration/test_snapshots.py`.
// ---------------------------------------------------------------------------
describe("header goldens", () => {
  /** The one body every header golden shares: 10 lines, no comments. */
  function headerWorkflow(comment?: string) {
    return workflow({
      name: "CI",
      on: { push: { branches: ["main"] } },
      jobs: {
        build: job({
          runsOn: "ubuntu-latest",
          steps: [step({ uses: "actions/checkout@v4" })],
        }),
      },
      ...(comment === undefined ? {} : { comment }),
    });
  }

  it("header_string.yml", () => {
    expect(toYaml(headerWorkflow(), { header: "Hand written" })).toBe(
      loadFixture("header_string.yml"),
    );
  });

  it("header_multiline.yml", () => {
    expect(toYaml(headerWorkflow(), { header: "line1\n\nline3\n" })).toBe(
      loadFixture("header_multiline.yml"),
    );
  });

  it("header_crlf.yml", () => {
    const out = toYaml(headerWorkflow(), { header: "a\r\nb\rc" });
    expect(out).toBe(loadFixture("header_crlf.yml"));
    expect(out).not.toContain("\r");
  });

  it("header_empty.yml", () => {
    expect(toYaml(headerWorkflow(), { header: "" })).toBe(loadFixture("header_empty.yml"));
  });

  it("header_closure.yml", () => {
    expect(toYaml(headerWorkflow(), { header: (v) => `built by ${v.tool} # verbatim` })).toBe(
      loadFixture("header_closure.yml"),
    );
  });

  it("header_doc_comment.yml", () => {
    expect(toYaml(headerWorkflow("root doc comment"), { header: "Hand written" })).toBe(
      loadFixture("header_doc_comment.yml"),
    );
  });
});
