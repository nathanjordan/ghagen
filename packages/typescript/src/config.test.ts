import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { loadOptions } from "./config.js";

let tmp: string;
beforeEach(() => {
  tmp = mkdtempSync(join(tmpdir(), "ghagen-config-"));
});
afterEach(() => {
  rmSync(tmp, { recursive: true, force: true });
});

describe("loadOptions()", () => {
  it("returns defaults when no config files exist", () => {
    expect(loadOptions(tmp)).toEqual({ autoDedent: true });
  });

  it("reads [options] from .github/ghagen.toml", () => {
    mkdirSync(join(tmp, ".github"), { recursive: true });
    writeFileSync(join(tmp, ".github", "ghagen.toml"), "[options]\nauto_dedent = false\n");
    expect(loadOptions(tmp)).toEqual({ autoDedent: false });
  });

  it("reads ghagen.options from package.json", () => {
    writeFileSync(
      join(tmp, "package.json"),
      JSON.stringify({ name: "x", ghagen: { options: { autoDedent: false } } }),
    );
    expect(loadOptions(tmp)).toEqual({ autoDedent: false });
  });

  it("ghagen.toml takes precedence over package.json", () => {
    mkdirSync(join(tmp, ".github"), { recursive: true });
    writeFileSync(join(tmp, ".github", "ghagen.toml"), "[options]\nauto_dedent = false\n");
    writeFileSync(
      join(tmp, "package.json"),
      JSON.stringify({ ghagen: { options: { autoDedent: true } } }),
    );
    expect(loadOptions(tmp)).toEqual({ autoDedent: false });
  });

  it("rejects non-boolean auto_dedent in ghagen.toml", () => {
    mkdirSync(join(tmp, ".github"), { recursive: true });
    writeFileSync(join(tmp, ".github", "ghagen.toml"), "[options]\nauto_dedent = 'yes'\n");
    expect(() => loadOptions(tmp)).toThrow(/must be a boolean/);
  });

  it("accepts auto_dedent (snake_case) in package.json too", () => {
    writeFileSync(
      join(tmp, "package.json"),
      JSON.stringify({ ghagen: { options: { auto_dedent: false } } }),
    );
    expect(loadOptions(tmp)).toEqual({ autoDedent: false });
  });
});
