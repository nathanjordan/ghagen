import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { CliError, findConfig } from "./_common.js";

let tmp: string;
beforeEach(() => {
  tmp = mkdtempSync(join(tmpdir(), "ghagen-common-"));
});
afterEach(() => {
  rmSync(tmp, { recursive: true, force: true });
});

describe("findConfig()", () => {
  it("resolves the entrypoint when cwd is the root (regression guard)", () => {
    mkdirSync(join(tmp, "workflows"));
    writeFileSync(join(tmp, "workflows", "ci.ts"), "// stub");
    writeFileSync(join(tmp, ".ghagen.yml"), "entrypoint: workflows/ci.ts\n");

    expect(findConfig(undefined, tmp)).toBe(join(tmp, "workflows", "ci.ts"));
  });

  it("resolves the entrypoint when cwd is a nested subdirectory (the fix)", () => {
    mkdirSync(join(tmp, "workflows"));
    writeFileSync(join(tmp, "workflows", "ci.ts"), "// stub");
    writeFileSync(join(tmp, ".ghagen.yml"), "entrypoint: workflows/ci.ts\n");

    const sub = join(tmp, "a", "b");
    mkdirSync(sub, { recursive: true });

    expect(findConfig(undefined, sub)).toBe(join(tmp, "workflows", "ci.ts"));
  });

  it("finds a CONFIG_SEARCH_PATHS candidate at the root when invoked from a subdirectory", () => {
    writeFileSync(join(tmp, ".ghagen.yml"), "");
    writeFileSync(join(tmp, "ghagen.config.ts"), "// stub");

    const sub = join(tmp, "sub");
    mkdirSync(sub);

    expect(findConfig(undefined, sub)).toBe(join(tmp, "ghagen.config.ts"));
  });

  it("probes CONFIG_SEARCH_PATHS against cwd only when no .ghagen.yml exists anywhere", () => {
    // A candidate at an ancestor of cwd (but not cwd itself) must NOT be
    // found -- there is no ancestor walk in this fallback branch.
    writeFileSync(join(tmp, "ghagen.config.ts"), "// stub");

    const sub = join(tmp, "sub");
    mkdirSync(sub);

    expect(() => findConfig(undefined, sub)).toThrow(CliError);
  });

  it("finds a CONFIG_SEARCH_PATHS candidate in cwd when no .ghagen.yml exists anywhere", () => {
    writeFileSync(join(tmp, "ghagen.config.ts"), "// stub");

    expect(findConfig(undefined, tmp)).toBe(join(tmp, "ghagen.config.ts"));
  });

  it("--config bypasses discovery entirely regardless of cwd", () => {
    writeFileSync(join(tmp, ".ghagen.yml"), "entrypoint: does_not_exist.ts\n");
    const flagTarget = join(tmp, "flag.ts");
    writeFileSync(flagTarget, "// stub");

    const sub = join(tmp, "sub");
    mkdirSync(sub);

    expect(findConfig(flagTarget, sub)).toBe(flagTarget);
  });
});
