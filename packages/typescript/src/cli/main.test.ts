/**
 * CLI-level regression tests exercising `main()` end to end, mirroring the
 * Python `test_cli/test_main.py` suite's `test_entrypoint_*` cases.
 *
 * These specifically cover the subdirectory case from
 * docs/specs/0004-unified-root-discovery.md: `findConfig`/`findAppRoot`
 * must resolve `.ghagen.yml`'s `entrypoint` via an ancestor walk, not just
 * a flat check against `process.cwd()`.
 *
 * `jiti`'s dynamic import is mocked out here (returning a real `App`
 * built from this file's own module graph) rather than dynamically
 * importing a written-to-disk fixture module: `jiti` loads modules
 * through its own transform/loader, which is a *different* module
 * instance of `App` than the one `resolveAppFromModule`'s `instanceof App`
 * check compares against under Vitest's module graph, so a genuine
 * dynamic import would spuriously fail the `instanceof` check. This
 * still exercises the real, unmocked `findConfig`/`entrypointFromGhagenYml`
 * ancestor-walk logic end to end through `main()` -- only the module
 * loading step is stubbed.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { existsSync, mkdirSync, mkdtempSync, realpathSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { App } from "../app.js";
import { job } from "../models/job.js";
import { pushTrigger } from "../models/trigger.js";
import { step } from "../models/step.js";
import { workflow } from "../models/workflow.js";

const importedPaths: string[] = [];

vi.mock("jiti", () => ({
  createJiti: () => ({
    import: async (path: string) => {
      importedPaths.push(path);
      const app = new App();
      const ci = workflow({
        name: "CI",
        on: { push: pushTrigger({ branches: ["main"] }) },
        jobs: {
          test: job({
            runsOn: "ubuntu-latest",
            steps: [step({ uses: "actions/checkout@v4" })],
          }),
        },
      });
      app.addWorkflow(ci, "ci.yml");
      return { app };
    },
  }),
}));

const { main } = await import("./main.js");

let tmp: string;
let originalCwd: string;

beforeEach(() => {
  // realpath: on macOS, process.cwd() (used internally by findConfig's
  // ancestor walk) always returns the symlink-resolved path, so tmp must
  // be normalized the same way for path assertions below to match.
  tmp = realpathSync(mkdtempSync(join(tmpdir(), "ghagen-cli-main-")));
  originalCwd = process.cwd();
  importedPaths.length = 0;
});
afterEach(() => {
  process.chdir(originalCwd);
  rmSync(tmp, { recursive: true, force: true });
});

describe("main() -- entrypoint resolution from a subdirectory", () => {
  it("resolves .ghagen.yml's entrypoint when invoked from the project root", async () => {
    mkdirSync(join(tmp, "workflows"));
    writeFileSync(
      join(tmp, "workflows", "ci.ts"),
      "// stub, never actually imported (jiti mocked)",
    );
    writeFileSync(join(tmp, ".ghagen.yml"), "entrypoint: workflows/ci.ts\n");

    process.chdir(tmp);
    const code = await main(["synth"]);

    expect(code).toBe(0);
    expect(importedPaths).toEqual([join(tmp, "workflows", "ci.ts")]);
    expect(existsSync(join(tmp, ".github", "workflows", "ci.yml"))).toBe(true);
  });

  it("resolves .ghagen.yml's entrypoint when invoked from a nested subdirectory", async () => {
    mkdirSync(join(tmp, "workflows"));
    writeFileSync(
      join(tmp, "workflows", "ci.ts"),
      "// stub, never actually imported (jiti mocked)",
    );
    writeFileSync(join(tmp, ".ghagen.yml"), "entrypoint: workflows/ci.ts\n");

    const subdir = join(tmp, "a", "b");
    mkdirSync(subdir, { recursive: true });
    process.chdir(subdir);

    const code = await main(["synth"]);

    expect(code).toBe(0);
    // The entrypoint resolves to the root-level workflows/ci.ts even though
    // the CLI ran two levels down -- this is the fix under test.
    expect(importedPaths).toEqual([join(tmp, "workflows", "ci.ts")]);
    // App() defaults root to process.cwd() at construction time (unaffected
    // by this spec) -- output lands under the subdirectory. What this test
    // guards is entrypoint *resolution*, not App's output location.
    expect(existsSync(join(subdir, ".github", "workflows", "ci.yml"))).toBe(true);
  });

  it("finds a CONFIG_SEARCH_PATHS candidate at the root from a subdirectory", async () => {
    writeFileSync(join(tmp, ".ghagen.yml"), "");
    writeFileSync(join(tmp, "ghagen.config.ts"), "// stub, never actually imported (jiti mocked)");

    const subdir = join(tmp, "subdir");
    mkdirSync(subdir);
    process.chdir(subdir);

    const code = await main(["synth"]);

    expect(code).toBe(0);
    expect(importedPaths).toEqual([join(tmp, "ghagen.config.ts")]);
  });

  it("fails from a subdirectory with no config anywhere in the ancestry", async () => {
    const subdir = join(tmp, "subdir");
    mkdirSync(subdir);
    process.chdir(subdir);

    const code = await main(["synth"]);

    expect(code).toBe(1);
    expect(importedPaths).toEqual([]);
  });

  it("--config bypasses discovery entirely regardless of cwd", async () => {
    writeFileSync(join(tmp, ".ghagen.yml"), "entrypoint: does_not_exist.ts\n");
    const flagTarget = join(tmp, "flag.ts");
    writeFileSync(flagTarget, "// stub, never actually imported (jiti mocked)");

    const subdir = join(tmp, "subdir");
    mkdirSync(subdir);
    process.chdir(subdir);

    const code = await main(["synth", "--config", flagTarget]);

    expect(code).toBe(0);
    expect(importedPaths).toEqual([flagTarget]);
  });
});
