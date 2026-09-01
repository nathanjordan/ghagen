/**
 * The YAML shown in the guides, produced by running the emitter at docs-build time.
 *
 * Every ` ```yaml ` fence in the guides used to be a hand-transcribed copy of what
 * `to_yaml()` / `toYaml()` prints. `oxfmt` has write authority over `.mdx` and cannot
 * tell a transcript from an example it is allowed to restyle, so it silently
 * re-indented those blocks and collapsed the emitter's two-column end-of-line gutter.
 * The landing page shipped every sequence item two columns too deep for exactly this
 * reason. See `docs/issues/18`.
 *
 * The fix is to stop transcribing. Each entry below builds a real model, runs the real
 * emitter over it, and exports the resulting string; the `.mdx` renders it through
 * Starlight's `<Code>` component, so there is no fence for the formatter to edit and
 * no way for the page to disagree with the emitter.
 *
 * ## The cross-port binding
 *
 * This module only exercises the TypeScript port -- it is the one the docs build can
 * run, since the docs job has Node and no Python. Every document is therefore also
 * pinned to a byte oracle in `fixtures/expected/docs_*.yml`, checked here and checked
 * again from Python by
 * `packages/python/tests/test_integration/test_docs_snippets.py`, which builds the
 * mirrored model and byte-compares against the same file. A cross-port divergence in
 * anything the guides show fails one side or the other.
 *
 * To re-take the oracles after a deliberate emitter change:
 *
 *     GHAGEN_DOCS_SNIPPETS_UPDATE=1 npm run build --prefix docs
 *
 * then re-run `uv run pytest` to confirm the Python port agrees with the new bytes.
 */
import { writeFileSync } from "node:fs";
import { resolve } from "node:path";

import {
  job,
  on,
  prTrigger,
  pushTrigger,
  step,
  toYaml,
  withComment,
  withEolComment,
  workflow,
} from "../../../packages/typescript/src/index.ts";
import type { Document } from "../../../packages/typescript/src/index.ts";

import commentBlockOracle from "../../../fixtures/expected/docs_comment_block.yml?raw";
import commentEolOracle from "../../../fixtures/expected/docs_comment_eol.yml?raw";
import commentFieldBlockOracle from "../../../fixtures/expected/docs_comment_field_block.yml?raw";
import commentFieldEolOracle from "../../../fixtures/expected/docs_comment_field_eol.yml?raw";
import commentFullOracle from "../../../fixtures/expected/docs_comment_full.yml?raw";
import extrasOracle from "../../../fixtures/expected/docs_extras.yml?raw";
import headerVerbatimOracle from "../../../fixtures/expected/docs_header_verbatim.yml?raw";
import quickstartOracle from "../../../fixtures/expected/docs_quickstart.yml?raw";

/**
 * Where the oracles live. Only read on the `GHAGEN_DOCS_SNIPPETS_UPDATE` path -- the
 * check path reads them through Vite's `?raw`, which resolves relative to this file.
 * `npm run build --prefix docs` runs with `docs/` as the working directory.
 */
const EXPECTED_DIR = resolve(process.cwd(), "../fixtures/expected");

const UPDATING = process.env.GHAGEN_DOCS_SNIPPETS_UPDATE === "1";

/**
 * Emit `doc`, hold the result against its committed oracle, and return the bytes.
 *
 * The throw is what makes this load-bearing: it runs during page rendering, so a
 * mismatch fails `astro build` and therefore `scripts/typecheck.sh docs`. It is the
 * same shape as `typeDocValidationGate` in `astro.config.mjs` -- the docs build has no
 * exit code of its own to pick, so failing means throwing.
 */
function emitted(
  name: string,
  doc: Document,
  oracle: string,
  header: string | null = null,
): string {
  const yaml = toYaml(doc, { header });
  if (UPDATING) {
    writeFileSync(resolve(EXPECTED_DIR, `${name}.yml`), yaml);
    return yaml;
  }
  if (yaml !== oracle) {
    throw new Error(
      `docs snippet '${name}' no longer matches fixtures/expected/${name}.yml.\n` +
        `The emitter's output changed. Re-take the oracle with\n` +
        `    GHAGEN_DOCS_SNIPPETS_UPDATE=1 npm run build --prefix docs\n` +
        `and re-run \`uv run pytest\` so the Python port is held to the new bytes too.\n` +
        `--- emitted ---\n${yaml}--- fixtures/expected/${name}.yml ---\n${oracle}`,
    );
  }
  return yaml;
}

// --- Slicing emitted documents down to the fragment a section is about ---------
//
// Only `Workflow` and `Action` are Documents, so a guide section about a `Job` or a
// `Step` cannot emit its subject on its own. The honest alternative to hand-writing
// the fragment is to emit a real document and show part of the result, which is what
// `region` / `regionBody` do: they address a fragment by its key path, so the slice
// tracks whatever the emitter lays down rather than freezing a copy of it.

/** Indent width of a line. The emitter never emits tabs. */
function indentOf(line: string): number {
  return line.length - line.trimStart().length;
}

/** The smallest indent among the non-blank lines, i.e. how far a block can dedent. */
function commonIndent(lines: string[]): number {
  const widths = lines.filter((l) => l.trim() !== "").map(indentOf);
  return widths.length === 0 ? 0 : Math.min(...widths);
}

interface Located {
  /** Index of the addressed key's own line. */
  key: number;
  /** Index of the first line above `key` that belongs to it (its block comment). */
  start: number;
  /** Index one past the last line of the key's value. */
  end: number;
  /** Column the key sits at. */
  indent: number;
}

/** Resolve a dot-separated map key path to its line span in an emitted document. */
function locate(lines: string[], path: string): Located {
  let indent = 0;
  let from = 0;
  let to = lines.length;
  let key = -1;

  for (const segment of path.split(".")) {
    const head = " ".repeat(indent) + segment + ":";
    key = -1;
    for (let i = from; i < to; i++) {
      if (lines[i] === head || lines[i].startsWith(`${head} `)) {
        key = i;
        break;
      }
    }
    if (key === -1) {
      throw new Error(`docs snippet: no key path '${path}' in:\n${lines.join("\n")}`);
    }

    // The value ends at the first later line that is back out at or above the key's
    // own column -- except for a sequence item, which ruamel/`yaml` render at exactly
    // the key's column rather than indented under it.
    to = lines.length;
    for (let i = key + 1; i < lines.length; i++) {
      const line = lines[i];
      if (line.trim() === "") {
        continue;
      }
      if (indentOf(line) > indent) {
        continue;
      }
      if (indentOf(line) === indent && line.trimStart().startsWith("- ")) {
        continue;
      }
      to = i;
      break;
    }
    from = key + 1;
    indent += 2;
  }

  // A block comment is emitted above the key it annotates, at the key's own column.
  const keyIndent = indent - 2;
  let start = key;
  while (start > 0) {
    const above = lines[start - 1];
    if (indentOf(above) !== keyIndent || !above.trimStart().startsWith("#")) {
      break;
    }
    start -= 1;
  }

  return { key, start, end: to, indent: keyIndent };
}

/** The whole `path` entry -- its block comment, its key line, and its value. */
function region(yaml: string, path: string): string {
  const lines = yaml.split("\n");
  const { start, end, indent } = locate(lines, path);
  return lines
    .slice(start, end)
    .map((l) => l.slice(indent))
    .join("\n")
    .trimEnd();
}

/** Just the value under `path`, dedented -- the key line itself dropped. */
function regionBody(yaml: string, path: string): string {
  const lines = yaml.split("\n");
  const { key, end } = locate(lines, path);
  const body = lines.slice(key + 1, end);
  const indent = commonIndent(body);
  return body
    .map((l) => l.slice(indent))
    .join("\n")
    .trimEnd();
}

// --- The documented models -----------------------------------------------------
//
// Each model here is the one the neighbouring `.mdx` prints as its Python/TypeScript
// snippet. Keep the two in step: the snippet is a claim about what produces the YAML
// below it, and only the YAML half is machine-checked.

/** The landing page's "ghagen generates clean, readable YAML". */
const quickstart = emitted(
  "docs_quickstart",
  workflow({
    name: "CI",
    on: on({
      push: pushTrigger({ branches: ["main"] }),
      pullRequest: prTrigger({ branches: ["main"] }),
    }),
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
  quickstartOracle,
);

/** guides/comments -- "Block comments". */
const commentBlock = emitted(
  "docs_comment_block",
  workflow({
    name: "CI",
    on: on({ push: pushTrigger({ branches: ["main"] }) }),
    jobs: {
      test: job({
        name: "Test",
        runsOn: "ubuntu-latest",
        comment: "Run the full test suite against all supported Python versions",
        steps: [step({ run: "pytest" })],
      }),
    },
  }),
  commentBlockOracle,
);

/** guides/comments -- "End-of-line comments". */
const commentEol = emitted(
  "docs_comment_eol",
  workflow({
    name: "CI",
    on: on({ push: pushTrigger({ branches: ["main"] }) }),
    jobs: {
      lint: job({
        runsOn: "ubuntu-latest",
        steps: [step({ name: "Ruff", run: "ruff check .", eolComment: "fast Python linter" })],
      }),
    },
  }),
  commentEolOracle,
);

/** guides/comments -- "Field-level block comments". */
const commentFieldBlock = emitted(
  "docs_comment_field_block",
  workflow({
    name: withComment("CI", "The name shown in the GitHub UI"),
    on: on({ push: pushTrigger({ branches: ["main"] }) }),
    jobs: { build: job({ runsOn: "ubuntu-latest", steps: [step({ run: "make" })] }) },
  }),
  commentFieldBlockOracle,
);

/** guides/comments -- "Field-level EOL comments". */
const commentFieldEol = emitted(
  "docs_comment_field_eol",
  workflow({
    name: "CI",
    on: withEolComment(on({ push: pushTrigger({ branches: ["main"] }) }), "trigger configuration"),
    jobs: { build: job({ runsOn: "ubuntu-latest", steps: [step({ run: "make" })] }) },
  }),
  commentFieldEolOracle,
);

/** guides/comments -- "Full example", all four comment kinds at once. */
const commentFull = emitted(
  "docs_comment_full",
  workflow({
    name: withComment("Commented Workflow", "The name shown in the GitHub UI"),
    on: withEolComment(on({ push: pushTrigger({ branches: ["main"] }) }), "trigger configuration"),
    jobs: {
      lint: job({
        name: "Lint",
        runsOn: "ubuntu-latest",
        comment: "Run linters before tests",
        steps: [
          step({ uses: "actions/checkout@v4" }),
          step({ name: "Ruff", run: "ruff check .", eolComment: "fast Python linter" }),
        ],
      }),
    },
  }),
  commentFullOracle,
);

/** guides/comments -- a verbatim string header, sitting straight on the body. */
const headerVerbatim = emitted(
  "docs_header_verbatim",
  workflow({
    name: "CI",
    on: on({ push: pushTrigger({ branches: ["main"] }) }),
    jobs: { build: job({ runsOn: "ubuntu-latest", steps: [step({ run: "make" })] }) },
  }),
  headerVerbatimOracle,
  "Hand written",
);

/** guides/escape-hatches -- "extras". */
const extras = emitted(
  "docs_extras",
  workflow({
    name: "Extras",
    on: on({ push: pushTrigger({ branches: ["main"] }) }),
    jobs: {
      build: job({
        runsOn: "ubuntu-latest",
        extras: { "timeout-minutes": 30, "continue-on-error": true },
      }),
    },
  }),
  extrasOracle,
);

// --- What the pages render -----------------------------------------------------

/** `index.mdx`: the whole generated file. */
export const quickstartYaml = quickstart.trimEnd();

/** `guides/comments.mdx`: the commented job, as it renders under `jobs:`. */
export const commentBlockYaml = region(commentBlock, "jobs.test");

/** `guides/comments.mdx`: the commented step, as it renders in a `steps:` list. */
export const commentEolYaml = regionBody(commentEol, "jobs.lint.steps");

/** `guides/comments.mdx`: the commented `name` field. */
export const commentFieldBlockYaml = region(commentFieldBlock, "name");

/** `guides/comments.mdx`: the commented `on` field. */
export const commentFieldEolYaml = region(commentFieldEol, "on");

/** `guides/comments.mdx`: the whole four-comment file. */
export const commentFullYaml = commentFull.trimEnd();

/** `guides/comments.mdx`: header and body, with nothing between them. */
export const headerVerbatimYaml = headerVerbatim.trimEnd();

/** `guides/escape-hatches.mdx`: the job body the `extras` keys were merged into. */
export const extrasYaml = regionBody(extras, "jobs.build");
