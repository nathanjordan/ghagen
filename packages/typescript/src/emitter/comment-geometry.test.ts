import { describe, it, expect } from "vitest";
import {
  EOL_GUTTER,
  commentString,
  renderBlockComment,
  renderEolComment,
} from "./comment-geometry.js";

describe("EOL_GUTTER", () => {
  it("is two columns, matching ruamel.yaml and therefore the Python port", () => {
    expect(EOL_GUTTER).toBe(2);
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
  it("contributes EOL_GUTTER - 1 columns", () => {
    // The `yaml` backend contributes the last column: `lineComment`'s third
    // branch (`dist/stringify/stringifyComment.js:16-20`) prepends one space
    // when the line does not already end in one. The other two branches are
    // unreachable — `comments.ts` never puts an EOL comment on a collection
    // value, and a newline payload returns null below.
    expect(renderEolComment("x")).toBe(`${" ".repeat(EOL_GUTTER - 1)}# x`);
    expect(renderEolComment("x")).toBe(" # x");
  });

  it("returns null for a payload that cannot sit at end of line", () => {
    expect(renderEolComment("line one\nline two")).toBeNull();
  });

  it("passes through a payload that already carries its own `#`", () => {
    // ruamel's `yaml_add_eol_comment` contract; keeps the Python peer's pass
    // idempotent over its own output.
    expect(renderEolComment("# already")).toBe(" # already");
  });

  it("leaves a `#` inside the payload alone", () => {
    expect(renderEolComment("see issue # 42")).toBe(" # see issue # 42");
  });
});

describe("commentString", () => {
  it("is the identity — every payload is already rendered", () => {
    expect(commentString("# already rendered")).toBe("# already rendered");
  });
});
