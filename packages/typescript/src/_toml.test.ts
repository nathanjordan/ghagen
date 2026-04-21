import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { dumpsToml, loadToml } from "./_toml.js";

let tmp: string;
beforeEach(() => {
  tmp = mkdtempSync(join(tmpdir(), "ghagen-toml-"));
});
afterEach(() => {
  rmSync(tmp, { recursive: true, force: true });
});

describe("loadToml()", () => {
  it("parses a basic TOML file", () => {
    const path = join(tmp, "x.toml");
    writeFileSync(path, "name = 'ci'\n[options]\nauto_dedent = true\n");
    expect(loadToml(path)).toEqual({
      name: "ci",
      options: { auto_dedent: true },
    });
  });

  it("throws on parse errors with the file path", () => {
    const path = join(tmp, "bad.toml");
    writeFileSync(path, "not = valid = toml");
    expect(() => loadToml(path)).toThrow(/bad\.toml.*failed to parse/);
  });

  it("throws on missing files with the file path", () => {
    expect(() => loadToml(join(tmp, "missing.toml"))).toThrow(/missing\.toml.*failed to read/);
  });
});

describe("dumpsToml()", () => {
  it("round-trips a quoted-key table", () => {
    const data = {
      pins: {
        "actions/checkout@v4": {
          sha: "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        },
      },
    };
    const str = dumpsToml(data);
    expect(str).toContain('"actions/checkout@v4"');
    expect(str).toContain("sha");
  });
});
