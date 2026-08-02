/**
 * The exit-code contract, driven from `fixtures/cli-exit-codes.yml`.
 *
 * This is the shared table both ports must satisfy: `0` success, `1` expected
 * failure, `2` usage error.
 *
 * Most rows are project-independent -- they load no user config module -- so
 * the driver only has to `chdir` into an empty temp directory. A row may
 * instead carry `project:`, naming a directory under
 * `fixtures/cli-exit-code-projects/` that is copied into the temp dir first
 * (see `rowCwd`). That key exists because the codes that depend on *user code
 * running* cannot be reached from an empty directory, and that is precisely
 * where the two ports had drifted.
 *
 * This is a separate file from `main.test.ts` because that file mocks `jiti` at
 * module scope, which these rows must not be run under.
 *
 * `FIXTURES_DIR` is not usable here: the TypeScript export points one level
 * deeper than the Python one (`fixtures/expected` vs `fixtures`), so the table
 * is resolved off `REPO_ROOT` directly.
 */

import { describe, it, expect, beforeAll, beforeEach, afterEach, vi } from "vitest";
import {
  cpSync,
  existsSync,
  readFileSync,
  mkdirSync,
  mkdtempSync,
  realpathSync,
  rmSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { parse } from "yaml";
import { REPO_ROOT } from "../paths.js";
import { main } from "./main.js";

interface ExitCodeRow {
  id: string;
  argv: string[];
  exit: number;
  /** Optional fixture project under `fixtures/cli-exit-code-projects/`. */
  project?: string;
}

const TABLE: ExitCodeRow[] = parse(
  readFileSync(resolve(REPO_ROOT, "fixtures", "cli-exit-codes.yml"), "utf8"),
) as ExitCodeRow[];

const PROJECTS_DIR = resolve(REPO_ROOT, "fixtures", "cli-exit-code-projects");

/**
 * The directory a row runs in, materialising its fixture project if it has one.
 *
 * Rows without `project` run in the empty temp dir, exactly as before. Rows
 * with it get a *copy*, so a command that writes (`synth`) cannot mutate the
 * checked-in fixture.
 */
function rowCwd(row: ExitCodeRow, root: string): string {
  if (row.project === undefined) {
    return root;
  }
  const source = join(PROJECTS_DIR, row.project);
  expect(existsSync(source), `${row.id}: no fixture project at ${source}`).toBe(true);
  const dest = join(root, row.project);
  cpSync(source, dest, { recursive: true });
  return dest;
}

let tmp: string;
let originalCwd: string;

beforeAll(() => {
  // Guard against the fixture silently emptying out: a zero-row table would
  // make every assertion below vacuous.
  expect(TABLE.length).toBeGreaterThan(0);
});

beforeEach(() => {
  tmp = realpathSync(mkdtempSync(join(tmpdir(), "ghagen-exit-codes-")));
  originalCwd = process.cwd();
  process.chdir(tmp);
  // commander writes help and usage errors to the real streams; swallow them
  // so the table's output does not drown the test report.
  vi.spyOn(process.stdout, "write").mockReturnValue(true);
  vi.spyOn(process.stderr, "write").mockReturnValue(true);
});

afterEach(() => {
  vi.restoreAllMocks();
  process.chdir(originalCwd);
  rmSync(tmp, { recursive: true, force: true });
});

describe("exit-code contract (fixtures/cli-exit-codes.yml)", () => {
  for (const row of TABLE) {
    it(`${row.id}: ghagen ${row.argv.join(" ")} -> ${row.exit}`, async () => {
      process.chdir(rowCwd(row, tmp));
      await expect(main(row.argv)).resolves.toBe(row.exit);
    });
  }
});

describe("main() always returns, never exits the process", () => {
  it("resolves for every row rather than killing the process", async () => {
    const codes: number[] = [];
    for (const [index, row] of TABLE.entries()) {
      // A fresh subdirectory per row: `rowCwd` copies into it, and two rows
      // naming the same project must not collide.
      const rowRoot = join(tmp, String(index));
      mkdirSync(rowRoot);
      process.chdir(rowCwd(row, rowRoot));
      codes.push(await main(row.argv));
    }
    expect(codes).toHaveLength(TABLE.length);
  });
});
