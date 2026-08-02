import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, it, expect } from "vitest";
import { Document, parse, type Pair, type YAMLMap } from "yaml";
import { withComment } from "../models/_base.js";
import { job } from "../models/job.js";
import { step } from "../models/step.js";
import { workflow } from "../models/workflow.js";
import { SCHEMA_DIR } from "../paths.js";
import { attachFieldComment } from "./comments.js";
import { toYaml } from "./yaml-writer.js";
import {
  EOL_GUTTER,
  commentString,
  renderBlockComment,
  renderEolComment,
} from "./comment-geometry.js";

/**
 * The shared comment-geometry oracle, read by the Python peer
 * (`tests/test_emitter/test_comment_geometry.py`) too.
 *
 * Both ports used to state the gutter and the EOL vectors as their OWN
 * literals. Two mirrors are not a binding: changing one port's renderer and its
 * own literal together left the other port green while the emitted comment
 * column silently diverged.
 */
const GEOMETRY_PATH = resolve(SCHEMA_DIR, "comment-geometry.yml");

interface Geometry {
  readonly eol_gutter: number;
  readonly eol_comment: readonly { readonly payload: string; readonly rendered: string | null }[];
}

function loadGeometry(): Geometry {
  return parse(readFileSync(GEOMETRY_PATH, "utf8")) as Geometry;
}

describe("EOL_GUTTER", () => {
  it("matches the shared comment-geometry table", () => {
    expect(EOL_GUTTER).toBe(loadGeometry().eol_gutter);
  });
});

describe("renderBlockComment()", () => {
  it("prefixes a single line", () => {
    expect(renderBlockComment("hello")).toBe("# hello");
  });

  it("prefixes every line of a multi-line payload", () => {
    expect(renderBlockComment("one\ntwo")).toBe("# one\n# two");
  });

  it("renders a blank line as a bare `#`", () => {
    expect(renderBlockComment("")).toBe("#");
    expect(renderBlockComment("a\n\nb")).toBe("# a\n#\n# b");
  });

  it("leaves a `#` inside the payload alone", () => {
    expect(renderBlockComment("see issue # 42")).toBe("# see issue # 42");
  });
});

describe("renderEolComment()", () => {
  // The one function both ports have with the same signature and the same
  // contract, so it is what the shared table binds: the gutter, the `#`
  // pass-through that keeps the Python peer's gutter pass idempotent over its
  // own output, an inner `#` (content, not a marker), and the newline payload
  // that cannot sit at end of line at all.
  it.each(loadGeometry().eol_comment)(
    "renders $payload per the shared table",
    ({ payload, rendered }) => {
      expect(renderEolComment(payload)).toBe(rendered);
    },
  );

  it("contributes EOL_GUTTER - 1 columns", () => {
    // The `yaml` backend contributes the last column: `lineComment`'s third
    // branch (`dist/stringify/stringifyComment.js:16-20`) prepends one space
    // when the line does not already end in one. The other two branches are
    // unreachable — `comments.ts` never puts an EOL comment on a collection
    // value, and a newline payload returns null above.
    expect(renderEolComment("x")).toBe(`${" ".repeat(EOL_GUTTER - 1)}# x`);
  });
});

describe("commentString", () => {
  // Asserting `commentString(x) === x` against `(rendered) => rendered` proves
  // nothing — it restates the definition, and it stays green however the hook
  // is used. The load-bearing property is what the hook does to a real dump:
  // `yaml`'s DEFAULT comment stringifier prefixes `#` to every line, which
  // would double the marker this module already wrote. So assert the emitted
  // bytes, through `attachFieldComment` and through the real `toYaml` path.
  function commentedDoc(): Document {
    const doc = new Document({ name: "Lint" });
    const pair = (doc.contents as YAMLMap).items[0] as Pair;
    attachFieldComment(pair, "see issue # 42", "eol note");
    return doc;
  }

  it("leaves a rendered payload alone through Document.toString", () => {
    expect(commentedDoc().toString({ lineWidth: 0, commentString })).toBe(
      "# see issue # 42\nname: Lint  # eol note\n",
    );
  });

  it("is what stops the backend doubling the marker", () => {
    // Without the hook the same tree emits `## see issue # 42`. This is the
    // reason the hook exists, and it is why the identity is not vacuous.
    expect(commentedDoc().toString({ lineWidth: 0 })).toContain("##");
  });

  it("is wired into toYaml, so emitted comments carry one marker", () => {
    const yaml = toYaml(
      workflow({
        name: withComment("CI", "see issue # 42"),
        on: { push: {} },
        jobs: { lint: job({ runsOn: "ubuntu-latest", steps: [step({ run: "x" })] }) },
      }),
      { header: null },
    );
    expect(yaml).toContain("# see issue # 42\nname: CI\n");
    expect(yaml).not.toContain("##");
  });
});
