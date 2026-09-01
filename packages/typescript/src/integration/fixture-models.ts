/**
 * The one binding from each emitted fixture in `fixtures/expected/` to the
 * model that produces it.
 *
 * Two consumers read this list, and they must read the *same* one:
 *
 * - `snapshots.test.ts` — the byte oracle. Emits each document and compares it
 *   to its fixture file, byte for byte, against the Python port doing the same.
 * - `to-data-sweep.test.ts` — the walk oracle. Asserts
 *   `parse(toYaml(doc))` equals `toData(doc)` for every document here, so a
 *   divergence between the emitter's two renderings fails on real documents
 *   rather than on one curated one (docs/issues/01).
 *
 * Keeping the models here rather than inline in either test is what makes the
 * second sweep a sweep over the *oracle's* documents instead of a second
 * hand-built registry that could quietly cover less.
 *
 * Peer: `packages/python/tests/test_integration/fixture_models.py`.
 */

import { Pair, Scalar } from "yaml";
import type { Document } from "../models/_base.js";
import { raw, withComment, withEolComment } from "../models/_base.js";
import type { ToYamlOptions } from "../emitter/yaml-writer.js";
import { workflow } from "../models/workflow.js";
import { job } from "../models/job.js";
import { step } from "../models/step.js";
import { on, workflowDispatch } from "../models/trigger.js";
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

/** One fixture document: the file it pins, why it exists, and how to build it. */
export interface FixtureDoc {
  /** File name under `fixtures/expected/`. */
  readonly fixture: string;
  /** What this document is the oracle for. */
  readonly why: string;
  /** Build a fresh model. A factory, not a value, so no two readers share one. */
  readonly build: () => Document;
  /**
   * The `header` argument its oracle was taken with. Required, not optional:
   * omitting it would emit ghagen's default header, which no fixture wants, and
   * an explicit `null` says so at the binding rather than at each call site.
   */
  readonly header: ToYamlOptions["header"];
  /**
   * Root keys this document's `postProcess` hook adds to the emitted YAML.
   *
   * `postProcess` operates on the backend node, so it runs in `toYaml` and, by
   * contract, never in `toData`. That is a declared difference between the two
   * renderings, not a divergence in the walk they share, so the walk sweep
   * subtracts these keys from the parsed YAML before comparing — and asserts
   * each one was actually there, so the subtraction cannot silently paper over
   * a real difference.
   */
  readonly postProcessRootKeys?: readonly string[];
}

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

/** The workflow and action shapes somebody wrote for their own sake. */
export const SNAPSHOT_DOCS: readonly FixtureDoc[] = [
  {
    fixture: "ci_basic.yml",
    why: "Minimal CI workflow.",
    header: null,
    build: () =>
      workflow({
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
      }),
  },
  {
    fixture: "comments.yml",
    why: "Block, EOL, and field-level comments in one workflow.",
    header: null,
    build: () =>
      workflow({
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
      }),
  },
  {
    fixture: "composite_action.yml",
    why: "Composite action.",
    header: null,
    build: () =>
      action({
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
            step({
              id: "greet",
              name: "Greet",
              run: "echo Hello, ${{ inputs.who }}",
              shell: "bash",
            }),
          ],
        }),
      }),
  },
  {
    fixture: "docker_action.yml",
    why: "Docker action.",
    header: null,
    build: () =>
      action({
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
      }),
  },
  {
    fixture: "node_action.yml",
    why: "Node.js action.",
    header: null,
    build: () =>
      action({
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
      }),
  },
  {
    fixture: "escape_hatches.yml",
    why:
      "All four escape hatches in one workflow. Also the byte oracle for a " +
      '`raw()` `ImageSnapshotInput.version` (issue 22): "latest" fails the ' +
      "field's own grammar (`/^\\d+(\\.\\d+|\\*)?$/`), so accepting it here " +
      "proves `raw()` bypasses the check rather than merely happening to match " +
      "it, and pins what a `raw()` value emits -- a plain scalar, exactly like " +
      "an ordinary string.",
    header: null,
    postProcessRootKeys: ["x-generated-by"],
    build: () =>
      workflow({
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
      }),
  },
  {
    fixture: "full_featured.yml",
    why: "Comprehensive workflow exercising all model types.",
    header: null,
    build: () =>
      workflow({
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
      }),
  },
  {
    fixture: "matrix_complex.yml",
    why: "Multi-axis matrix with exclude.",
    header: null,
    build: () =>
      workflow({
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
      }),
  },
  {
    fixture: "multiline_run.yml",
    why: "Multi-line run commands render as YAML literal block scalars.",
    header: null,
    build: () =>
      workflow({
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
      }),
  },
  {
    fixture: "triple_quoted_run.yml",
    why:
      "Similar to multiline_run.yml but uses |- (strip) instead of | (clip), " +
      "because dedentScript strips the artifact trailing newline that Python's " +
      "triple-quoted spelling of the same script produces.",
    header: null,
    build: () =>
      workflow({
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
      }),
  },
  {
    fixture: "body_shapes.yml",
    why:
      "The five body shapes the byte oracle had no bytes for (docs/issues/02). " +
      "Every other fixture here is a workflow shape somebody wrote for its own " +
      "sake; this one exists because the *oracle* had holes, and each hole is a " +
      "path the ports could have diverged on with both suites green: " +
      "(1) `defaults:` at the workflow level and again inside a job, so the one " +
      "defaults/defaultsRun pair is byte-bound at both places the schema allows " +
      "it; (2) present-null on `workflow_dispatch:` (the rule's original single " +
      "member) and on `create:` (one of the 34 keys docs/issues/04 widened it " +
      "to) -- both must be bare keys, neither may be `{}`; (3) a dynamic extras " +
      "interleave on an alphabetical spec -- `pull_request_review_thread` is a " +
      "real GitHub event the canonical Snapshot's `on:` map does not declare, so " +
      "it cannot be a typed field and must travel through `extras`, and it sorts " +
      "strictly between two typed keys, `create` and `push`, so a port that " +
      "appended extras instead of interleaving them produces different bytes " +
      "here; (4) SHA-pinned `uses:` -- a bare 40-hex ref, and the `# vX.Y.Z` " +
      "end-of-line spelling that pinning tools actually emit; (5) " +
      "`workflow_call:` with inputs, outputs and secrets -- no file under " +
      "`fixtures/expected/` contained `workflow_call` at all before this one.",
    header: null,
    build: () =>
      workflow({
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
      }),
  },
];

/**
 * The cross-port byte oracle for `formatHeader`.
 *
 * The six files are generated from the Python port and read byte-for-byte by
 * both suites; every byte that differs between them is header. They all share
 * one 10-line body, so the sweep learns nothing new from five of them — but
 * they are fixture documents, and leaving them out would be shrinking the set
 * rather than sweeping it.
 */
export const HEADER_GOLDENS: readonly FixtureDoc[] = [
  {
    fixture: "header_string.yml",
    why: "A string header sits immediately above the body -- no blank line.",
    header: "Hand written",
    build: () => headerWorkflow(),
  },
  {
    fixture: "header_multiline.yml",
    why: "Blank source line renders a bare `#`; one trailing break is dropped.",
    header: "line1\n\nline3\n",
    build: () => headerWorkflow(),
  },
  {
    fixture: "header_crlf.yml",
    why: "CRLF and a bare CR are both line breaks; no CR reaches the output.",
    header: "a\r\nb\rc",
    build: () => headerWorkflow(),
  },
  {
    fixture: "header_empty.yml",
    why: '`header: ""` is a header -- a lone `#` -- not a skip.',
    header: "",
    build: () => headerWorkflow(),
  },
  {
    fixture: "header_closure.yml",
    why: "The closure branch wraps like the string branch; `#` survives verbatim.",
    header: (v) => `built by ${v.tool} # verbatim`,
    build: () => headerWorkflow(),
  },
  {
    fixture: "header_doc_comment.yml",
    why: "The root Document comment sits directly under the header.",
    header: "Hand written",
    build: () => headerWorkflow("root doc comment"),
  },
];

/**
 * The documents the guides show, pinned to `fixtures/expected/docs_*.yml`.
 *
 * The models live in `docs/src/snippets/emitted.ts`, which is a Vite module in
 * the `docs/` package: it imports its oracles through `?raw` and cannot be
 * loaded from this suite. Rather than transcribe them a third time, this file
 * lists the fixtures it does NOT bind, so a reader can see the sweep's edge
 * instead of guessing at it. Python's `fixture_models.py` DOES bind them (its
 * mirrored models are `test_docs_snippets.py`'s), so every one of them is swept
 * on that side.
 */
export const UNBOUND_DOC_FIXTURES: readonly string[] = [
  "docs_comment_block.yml",
  "docs_comment_eol.yml",
  "docs_comment_field_block.yml",
  "docs_comment_field_eol.yml",
  "docs_comment_full.yml",
  "docs_extras.yml",
  "docs_header_verbatim.yml",
  "docs_quickstart.yml",
  // Not a static model at all: `init_scaffold.yml` is what `ghagen init`'s
  // template emits, so its source is the scaffold the CLI writes. It is swept
  // where it is built, in `cli/init-scaffold.test.ts`.
  "init_scaffold.yml",
];

/** Every fixture document this suite can build a model for. */
export const ALL_FIXTURE_DOCS: readonly FixtureDoc[] = [...SNAPSHOT_DOCS, ...HEADER_GOLDENS];
