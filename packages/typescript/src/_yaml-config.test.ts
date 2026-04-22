import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { loadYamlConfig } from "./_yaml-config.js";

let tmp: string;
beforeEach(() => {
  tmp = mkdtempSync(join(tmpdir(), "ghagen-yaml-config-"));
});
afterEach(() => {
  rmSync(tmp, { recursive: true, force: true });
});

describe("loadYamlConfig()", () => {
  it("parses a basic YAML file", () => {
    const path = join(tmp, "x.yml");
    writeFileSync(path, "entrypoint: workflows.ts\noptions:\n  auto_dedent: true\n");
    expect(loadYamlConfig(path)).toEqual({
      entrypoint: "workflows.ts",
      options: { auto_dedent: true },
    });
  });

  it("returns empty object for empty file", () => {
    const path = join(tmp, "empty.yml");
    writeFileSync(path, "");
    expect(loadYamlConfig(path)).toEqual({});
  });

  it("throws on parse errors with the file path", () => {
    const path = join(tmp, "bad.yml");
    writeFileSync(path, ":\n  - :\n  bad: [");
    expect(() => loadYamlConfig(path)).toThrow(/bad\.yml.*failed to parse/);
  });

  it("throws on missing files with the file path", () => {
    expect(() => loadYamlConfig(join(tmp, "missing.yml"))).toThrow(/missing\.yml.*failed to read/);
  });

  it("throws on non-mapping top-level value", () => {
    const path = join(tmp, "list.yml");
    writeFileSync(path, "- item1\n- item2\n");
    expect(() => loadYamlConfig(path)).toThrow(/expected a YAML mapping/);
  });
});
