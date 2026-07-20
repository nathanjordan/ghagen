import { describe, expect, it } from "vitest";
import { dedentScript } from "./_dedent.js";

// Parity port of packages/python/tests/test_dedent.py — both implementations
// must produce byte-identical output for the same inputs.
describe("dedentScript", () => {
  it("template-literal leading blank line", () => {
    const s = "\n        echo hello\n        echo world\n    ";
    expect(dedentScript(s)).toBe("echo hello\necho world");
  });

  it("content on first line", () => {
    const s = "echo hello\n        echo world";
    expect(dedentScript(s)).toBe("echo hello\necho world");
  });

  it("preserves relative indentation", () => {
    const s = "\n        if [ -f config ]; then\n            source config\n        fi\n    ";
    expect(dedentScript(s)).toBe("if [ -f config ]; then\n    source config\nfi");
  });

  it("single line noop", () => {
    expect(dedentScript("echo hello")).toBe("echo hello");
  });

  it("newline-concatenated noop", () => {
    expect(dedentScript("echo hello\necho world")).toBe("echo hello\necho world");
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

  it("blank lines in middle preserved", () => {
    const s = "\n        echo start\n\n        echo end\n    ";
    expect(dedentScript(s)).toBe("echo start\n\necho end");
  });

  it("strips leading/trailing blank lines only", () => {
    const s = "\n\n    echo hello\n\n    echo world\n\n";
    expect(dedentScript(s)).toBe("echo hello\n\necho world");
  });

  it("only whitespace lines", () => {
    expect(dedentScript("\n  \n\n")).toBe("");
  });

  it("no common indent", () => {
    expect(dedentScript("line1\nline2\nline3")).toBe("line1\nline2\nline3");
  });

  it("single indented line", () => {
    expect(dedentScript("\n        single line\n    ")).toBe("single line");
  });

  it("preserves intentional trailing newline", () => {
    expect(dedentScript("echo hello\necho world\n")).toBe("echo hello\necho world\n");
  });

  it("strips artifact trailing newline from template literal", () => {
    const s = "\n        echo hello\n        echo world\n    ";
    const result = dedentScript(s);
    expect(result).toBe("echo hello\necho world");
    expect(result.endsWith("\n")).toBe(false);
  });
});
