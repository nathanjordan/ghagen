import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
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
    expect(loadOptions(tmp)).toEqual({ auto_dedent: true });
  });

  it("reads options from .ghagen.yml", () => {
    writeFileSync(join(tmp, ".ghagen.yml"), "options:\n  auto_dedent: false\n");
    expect(loadOptions(tmp)).toEqual({ auto_dedent: false });
  });

  it("rejects non-boolean auto_dedent in .ghagen.yml", () => {
    writeFileSync(join(tmp, ".ghagen.yml"), "options:\n  auto_dedent: 'yes'\n");
    expect(() => loadOptions(tmp)).toThrow();
  });

  it("strips unknown keys in options", () => {
    writeFileSync(join(tmp, ".ghagen.yml"), "options:\n  auto_dedent: false\n  unknown_key: 42\n");
    expect(loadOptions(tmp)).toEqual({ auto_dedent: false });
  });
});
