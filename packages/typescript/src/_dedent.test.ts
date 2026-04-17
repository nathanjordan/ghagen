import { describe, it, expect } from "vitest";
import { dedentScript, getAutoDedent, setAutoDedent } from "./_dedent.js";

// These cases are ported line-for-line from
// `packages/python/tests/test_dedent.py` so the two packages stay in
// lockstep on dedent semantics.

describe("dedentScript()", () => {
  it("triple-quoted leading blank line", () => {
    const s = "\n        echo hello\n        echo world\n    ";
    expect(dedentScript(s)).toBe("echo hello\necho world");
  });

  it("triple-quoted content on first line", () => {
    const s = "echo hello\n        echo world";
    expect(dedentScript(s)).toBe("echo hello\necho world");
  });

  it("preserves relative indentation", () => {
    const s = "\n        if [ -f config ]; then\n            source config\n        fi\n    ";
    expect(dedentScript(s)).toBe("if [ -f config ]; then\n    source config\nfi");
  });

  it("single line is a no-op", () => {
    expect(dedentScript("echo hello")).toBe("echo hello");
  });

  it("newline-concatenated input is a no-op", () => {
    const s = "echo hello\necho world";
    expect(dedentScript(s)).toBe("echo hello\necho world");
  });

  it("empty string", () => {
    expect(dedentScript("")).toBe("");
  });

  it("preserves tabs (critical for <<- heredocs)", () => {
    const s = "\n        cat <<-EOF\n        \tindented with tab\n        EOF\n    ";
    expect(dedentScript(s)).toBe("cat <<-EOF\n\tindented with tab\nEOF");
  });

  it("mixed indent levels", () => {
    const s = "\n        level0\n          level1\n            level2\n    ";
    expect(dedentScript(s)).toBe("level0\n  level1\n    level2");
  });

  it("blank lines in middle are preserved", () => {
    const s = "\n        echo start\n\n        echo end\n    ";
    expect(dedentScript(s)).toBe("echo start\n\necho end");
  });

  it("strips leading and trailing blank lines only", () => {
    const s = "\n\n    echo hello\n\n    echo world\n\n";
    expect(dedentScript(s)).toBe("echo hello\n\necho world");
  });

  it("only-whitespace lines collapse to empty string", () => {
    const s = "\n  \n\n";
    expect(dedentScript(s)).toBe("");
  });

  it("input with no common indent is unchanged", () => {
    const s = "line1\nline2\nline3";
    expect(dedentScript(s)).toBe("line1\nline2\nline3");
  });

  it("single indented line", () => {
    const s = "\n        single line\n    ";
    expect(dedentScript(s)).toBe("single line");
  });

  it("preserves intentional trailing newline (\\n-concatenated input)", () => {
    const s = "echo hello\necho world\n";
    expect(dedentScript(s)).toBe("echo hello\necho world\n");
  });

  it("strips trailing newline artifact from triple-quoted input", () => {
    const s = "\n        echo hello\n        echo world\n    ";
    const result = dedentScript(s);
    expect(result).toBe("echo hello\necho world");
    expect(result.endsWith("\n")).toBe(false);
  });
});

describe("autoDedent flag", () => {
  it("defaults to true", () => {
    expect(getAutoDedent()).toBe(true);
  });

  it("can be toggled", () => {
    setAutoDedent(false);
    expect(getAutoDedent()).toBe(false);
    setAutoDedent(true);
    expect(getAutoDedent()).toBe(true);
  });
});
