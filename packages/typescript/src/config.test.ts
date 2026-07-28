import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { loadOptions, loadProjectConfig, loadYamlConfig } from "./config.js";

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

describe("loadProjectConfig()", () => {
  it("parses .ghagen.yml once for both options and entrypoint", () => {
    mkdirSync(join(tmp, "workflows"));
    writeFileSync(join(tmp, "workflows", "ci.ts"), "// stub");
    writeFileSync(
      join(tmp, ".ghagen.yml"),
      "entrypoint: workflows/ci.ts\noptions:\n  auto_dedent: false\n",
    );

    const config = loadProjectConfig(tmp);
    expect(config.root).toBe(tmp);
    expect(config.entrypoint).toBe("workflows/ci.ts");
    expect(config.configPath).toBe(join(tmp, "workflows", "ci.ts"));
    expect(config.options).toEqual({ auto_dedent: false });
    expect(config.errors).toEqual([]);
  });

  it("returns root=null and cwd-anchored search with no marker", () => {
    writeFileSync(join(tmp, "ghagen.config.ts"), "// stub");
    const config = loadProjectConfig(tmp);
    expect(config.root).toBeNull();
    expect(config.configPath).toBe(join(tmp, "ghagen.config.ts"));
    expect(config.options).toEqual({ auto_dedent: true });
    expect(config.errors).toEqual([]);
  });

  it("kind=parse on malformed YAML (does not throw)", () => {
    writeFileSync(join(tmp, ".ghagen.yml"), ":\n  - :\n  bad: [");
    const config = loadProjectConfig(tmp);
    expect(config.errors.map((e) => e.kind)).toContain("parse");
  });

  it("kind=not-a-mapping on a top-level list", () => {
    writeFileSync(join(tmp, ".ghagen.yml"), "- a\n- b\n");
    const config = loadProjectConfig(tmp);
    expect(config.errors.map((e) => e.kind)).toContain("not-a-mapping");
  });

  it("kind=bad-entrypoint-type when entrypoint is not a string", () => {
    writeFileSync(join(tmp, ".ghagen.yml"), "entrypoint: 42\n");
    const config = loadProjectConfig(tmp);
    expect(config.errors.map((e) => e.kind)).toContain("bad-entrypoint-type");
    expect(config.configPath).toBeNull();
  });

  it("kind=entrypoint-missing when the entrypoint file does not exist", () => {
    writeFileSync(join(tmp, ".ghagen.yml"), "entrypoint: nope.ts\n");
    const config = loadProjectConfig(tmp);
    expect(config.errors.map((e) => e.kind)).toContain("entrypoint-missing");
  });

  it("kind=bad-option-type when auto_dedent is not a boolean", () => {
    writeFileSync(join(tmp, ".ghagen.yml"), "options:\n  auto_dedent: 'yes'\n");
    const config = loadProjectConfig(tmp);
    expect(config.errors.map((e) => e.kind)).toContain("bad-option-type");
  });

  it("--config short-circuits discovery", () => {
    writeFileSync(join(tmp, ".ghagen.yml"), "entrypoint: does_not_exist.ts\n");
    const flag = join(tmp, "flag.ts");
    writeFileSync(flag, "// stub");
    const config = loadProjectConfig(join(tmp, "sub-does-not-matter"), flag);
    expect(config.configPath).toBe(flag);
    expect(config.errors).toEqual([]);
  });

  it("--config bypasses a malformed .ghagen.yml (regression vs main)", () => {
    // A bad `entrypoint:` type used to accumulate a `bad-entrypoint-type`
    // error that the flag path still returned, making resolveConfig exit 1 on
    // the very config the user overrode. The flag now short-circuits before any
    // `.ghagen.yml` read, so the override runs clean.
    writeFileSync(join(tmp, ".ghagen.yml"), "entrypoint: 123\n");
    const flag = join(tmp, "override.ts");
    writeFileSync(flag, "// stub");
    const config = loadProjectConfig(tmp, flag);
    expect(config.configPath).toBe(flag);
    expect(config.errors).toEqual([]);
  });

  it("--config bypasses unparseable .ghagen.yml", () => {
    writeFileSync(join(tmp, ".ghagen.yml"), ":\n  - :\n  bad: [");
    const flag = join(tmp, "override.ts");
    writeFileSync(flag, "// stub");
    const config = loadProjectConfig(tmp, flag);
    expect(config.configPath).toBe(flag);
    expect(config.errors).toEqual([]);
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
