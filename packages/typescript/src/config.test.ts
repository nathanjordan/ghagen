import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { loadOptions, loadYamlConfig } from "./config.js";

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

  it("ignores a malformed entrypoint key (regression: loadOptions must not parse entrypoint)", () => {
    // A bad `entrypoint:` value used to make loadOptions() throw a ZodError
    // because it parsed the whole ghagenYmlSchema (entrypoint + options).
    // loadOptions() now parses only the `options` key, so this must not
    // throw -- even though `entrypoint` here is the wrong type.
    writeFileSync(join(tmp, ".ghagen.yml"), "entrypoint: 42\noptions:\n  auto_dedent: false\n");
    expect(loadOptions(tmp)).toEqual({ auto_dedent: false });
  });
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
