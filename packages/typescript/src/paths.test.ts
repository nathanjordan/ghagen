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
  it("returns the directory containing .ghagen.yml", () => {
    writeFileSync(join(tmp, ".ghagen.yml"), "");
    expect(findAppRoot(tmp)).toBe(tmp);
  });

  it("walks up to find the marker", () => {
    writeFileSync(join(tmp, ".ghagen.yml"), "");
    const sub = join(tmp, "a", "b", "c");
    mkdirSync(sub, { recursive: true });
    expect(findAppRoot(sub)).toBe(tmp);
  });

  it("returns null when no marker exists", () => {
    expect(findAppRoot(tmp)).toBeNull();
  });

  it("starts at the file's parent when given a file", () => {
    writeFileSync(join(tmp, ".ghagen.yml"), "");
    const file = join(tmp, "workflows.ts");
    writeFileSync(file, "");
    expect(findAppRoot(file)).toBe(tmp);
  });
});
