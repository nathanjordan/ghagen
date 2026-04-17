import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { findAppRoot } from "./paths.js";

let tmp: string;
beforeEach(() => {
  tmp = mkdtempSync(join(tmpdir(), "ghagen-paths-"));
});
afterEach(() => {
  rmSync(tmp, { recursive: true, force: true });
});

describe("findAppRoot()", () => {
  it("returns the directory containing .github/ghagen.toml", () => {
    mkdirSync(join(tmp, ".github"), { recursive: true });
    writeFileSync(join(tmp, ".github", "ghagen.toml"), "");
    expect(findAppRoot(tmp)).toBe(tmp);
  });

  it("walks up to find the marker", () => {
    mkdirSync(join(tmp, ".github"), { recursive: true });
    writeFileSync(join(tmp, ".github", "ghagen.toml"), "");
    const sub = join(tmp, "a", "b", "c");
    mkdirSync(sub, { recursive: true });
    expect(findAppRoot(sub)).toBe(tmp);
  });

  it("returns null when no marker exists", () => {
    expect(findAppRoot(tmp)).toBeNull();
  });

  it("starts at the file's parent when given a file", () => {
    mkdirSync(join(tmp, ".github"), { recursive: true });
    writeFileSync(join(tmp, ".github", "ghagen.toml"), "");
    const file = join(tmp, "workflows.ts");
    writeFileSync(file, "");
    expect(findAppRoot(file)).toBe(tmp);
  });
});
