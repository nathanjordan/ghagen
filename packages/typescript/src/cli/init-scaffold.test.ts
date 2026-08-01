/**
 * `ghagen init` scaffolds the workflow both ports agree on.
 *
 * The two templates are hand-written source strings that nothing compared, and
 * they drifted: this one set `timeoutMinutes: 10` and the Python one set no
 * timeout at all. This drives the real scaffold through `main()`, loads the
 * file it wrote, and compares its emission byte-for-byte against the shared
 * oracle in `fixtures/expected/` -- the same oracle, and the same
 * `header: null` shape, that the snapshot suite uses. The Python mirror is
 * `packages/python/tests/test_cli/test_init_scaffold.py`, asserting against the
 * *same* fixture file; that is what makes this a parity test.
 *
 * Two details are not obvious:
 *
 * 1. The scaffolded file imports `"@ghagen/ghagen"`, and nothing links that
 *    into a temp directory -- `package.json`'s `exports` points at `dist/`,
 *    which the test suite must not require a build for. So the single import
 *    specifier is rewritten to an absolute path to `src/index.ts`.
 * 2. The scaffolded module *and* the emitter must come from **one** `jiti`
 *    instance with the module cache **on**. Mixing the two graphs -- either by
 *    using `moduleCache: false` (what `loadApp` uses), or by calling this
 *    file's own statically imported `toYaml` on a jiti-loaded object graph --
 *    yields a second copy of the model classes, and the emitter throws `Tag not
 *    resolved for Function value`. This is the same module-identity hazard
 *    `main.test.ts` documents, and it is why `toYaml` is imported through
 *    `jiti` below rather than at the top of the file.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { createJiti } from "jiti";
import { mkdtempSync, readFileSync, realpathSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import type { App } from "../app.js";
import type { toYaml as ToYaml } from "../emitter/yaml-writer.js";
import { FIXTURES_DIR } from "../paths.js";
import { main } from "./main.js";

const SRC_DIR = resolve(fileURLToPath(import.meta.url), "..", "..");
const SRC_INDEX = resolve(SRC_DIR, "index.ts");
const SRC_YAML_WRITER = resolve(SRC_DIR, "emitter", "yaml-writer.ts");
const FIXTURE = readFileSync(resolve(FIXTURES_DIR, "init_scaffold.yml"), "utf8");

let tmp: string;
let originalCwd: string;

beforeEach(() => {
  tmp = realpathSync(mkdtempSync(join(tmpdir(), "ghagen-init-scaffold-")));
  originalCwd = process.cwd();
  process.chdir(tmp);
  vi.spyOn(process.stdout, "write").mockReturnValue(true);
});

afterEach(() => {
  vi.restoreAllMocks();
  process.chdir(originalCwd);
  rmSync(tmp, { recursive: true, force: true });
});

describe("ghagen init scaffold", () => {
  it("emits exactly fixtures/expected/init_scaffold.yml", async () => {
    expect(await main(["init", "--outdir", tmp])).toBe(0);

    const configPath = join(tmp, "ghagen.workflows.ts");
    const source = readFileSync(configPath, "utf8");
    expect(source).toContain('"@ghagen/ghagen"');
    writeFileSync(configPath, source.replace('"@ghagen/ghagen"', JSON.stringify(SRC_INDEX)));

    const jiti = createJiti(import.meta.url);
    const mod = (await jiti.import(configPath)) as { app: App };
    const { toYaml } = (await jiti.import(SRC_YAML_WRITER)) as { toYaml: typeof ToYaml };

    const documents = mod.app.documents();
    expect(documents).toHaveLength(1);
    expect(toYaml(documents[0]!, { header: null })).toBe(FIXTURE);
  });
});
