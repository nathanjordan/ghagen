/**
 * The exit-code contract, driven from `fixtures/cli-exit-codes.yml`.
 *
 * This is the shared table both ports must satisfy: `0` success, `1` expected
 * failure, `2` usage error. Every row is project-independent -- none of them
 * loads a user config module -- so the driver only has to `chdir` into an empty
 * temp directory.
 *
 * This is a separate file from `main.test.ts` because that file mocks `jiti` at
 * module scope, which these rows must not be run under.
 *
 * `FIXTURES_DIR` is not usable here: the TypeScript export points one level
 * deeper than the Python one (`fixtures/expected` vs `fixtures`), so the table
 * is resolved off `REPO_ROOT` directly.
 */

import { describe, it, expect, beforeAll, beforeEach, afterEach, vi } from "vitest";
import { readFileSync, mkdtempSync, realpathSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { parse } from "yaml";
import { REPO_ROOT } from "../paths.js";
import { main } from "./main.js";

interface ExitCodeRow {
  id: string;
  argv: string[];
  exit: number;
}

const TABLE: ExitCodeRow[] = parse(
  readFileSync(resolve(REPO_ROOT, "fixtures", "cli-exit-codes.yml"), "utf8"),
) as ExitCodeRow[];

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
      await expect(main(row.argv)).resolves.toBe(row.exit);
    });
  }
});

describe("main() always returns, never exits the process", () => {
  it("resolves for every row rather than killing the process", async () => {
    const codes: number[] = [];
    for (const row of TABLE) {
      codes.push(await main(row.argv));
    }
    expect(codes).toHaveLength(TABLE.length);
  });
});
