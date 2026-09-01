/**
 * The CLI stream contract, driven from `schema/cli-streams.yml`.
 *
 * This is the shared table both ports must satisfy: for a given command (and,
 * where the rule is conditional, a given flag combination) exactly one of
 * stdout/stderr carries the described output. The Python mirror is
 * `packages/python/tests/test_cli/test_streams.py`.
 *
 * Every case below invokes the real command (through `main()` for the
 * top-level commands, directly for the `deps` sub-commands, mirroring the
 * exported-for-testing seam `deps.test.ts` already uses) and asks the table
 * which stream the row's marker text belongs on, rather than hard-coding
 * "stdout" or "stderr" in the assertion. Corrupting a row in
 * `schema/cli-streams.yml` therefore fails the corresponding case here *and*
 * the Python mirror, which is the whole point of a shared oracle: see
 * docs/issues/24-conformance-gaps-is-inert.md for what happens to a table
 * nothing actually reads.
 */

import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { parse as parseYaml } from "yaml";
import type { App } from "../app.js";
import { SCHEMA_DIR } from "../paths.js";
import type { UpgradeReport } from "../pin/index.js";
import { CliError } from "./_errors.js";

interface StreamRow {
  id: string;
  command: string;
  condition?: string;
  stream: "stdout" | "stderr";
  note: string;
}

const _TABLE: Record<string, StreamRow> = Object.fromEntries(
  (parseYaml(readFileSync(resolve(SCHEMA_DIR, "cli-streams.yml"), "utf8")) as StreamRow[]).map(
    (row) => [row.id, row],
  ),
);

if (Object.keys(_TABLE).length === 0) {
  throw new Error("schema/cli-streams.yml is empty -- every case below would be vacuous");
}

/** The text of the stream `schema/cli-streams.yml` names for `rowId`. */
function streamText(out: string, err: string, rowId: string): string {
  return _TABLE[rowId]!.stream === "stdout" ? out : err;
}

/** The text of the *other* stream -- what the marker must be absent from. */
function otherStreamText(out: string, err: string, rowId: string): string {
  return _TABLE[rowId]!.stream === "stdout" ? err : out;
}

function captureStdout(): { text(): string; restore(): void } {
  let out = "";
  const spy = vi.spyOn(process.stdout, "write").mockImplementation((chunk: unknown) => {
    out += String(chunk);
    return true;
  });
  return { text: () => out, restore: () => spy.mockRestore() };
}

function captureStderr(): { text(): string; restore(): void } {
  let out = "";
  const spy = vi.spyOn(process.stderr, "write").mockImplementation((chunk: unknown) => {
    out += String(chunk);
    return true;
  });
  return { text: () => out, restore: () => spy.mockRestore() };
}

// -- mocks shared across the `deps` sub-commands -----------------------------

const upgradeMock = vi.fn<(...args: unknown[]) => Promise<UpgradeReport>>();
const pinMock = vi.fn<(...args: unknown[]) => Promise<unknown>>();
const checkSyncMock = vi.fn<(...args: unknown[]) => unknown>();
const trackUserFilesMock =
  vi.fn<(...args: unknown[]) => Promise<{ app: App; files: Set<string> }>>();

vi.mock("../pin/index.js", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../pin/index.js")>();
  return {
    ...actual,
    upgrade: upgradeMock,
    pin: pinMock,
    checkSync: checkSyncMock,
    trackUserFiles: trackUserFilesMock,
    // Never actually used (upgrade()/pin() are mocked), but must be a real
    // constructor: buildGitHubClient() in deps.ts does `new GitHubClient(...)`.
    GitHubClient: class FakeGitHubClient {
      readonly fake = true;
    },
  };
});

const findConfigMock = vi.fn<(...args: unknown[]) => string>(() => "/fake/ghagen.workflows.ts");
const loadAppMock = vi.fn<(...args: unknown[]) => Promise<App>>();

vi.mock("./_common.js", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./_common.js")>();
  return {
    ...actual,
    findConfig: findConfigMock,
    loadApp: loadAppMock,
  };
});

const { depsPin, depsCheckSynced, depsUpgrade, depsUpdate } = await import("./deps.js");
const { main } = await import("./main.js");

function emptyReport(overrides: Partial<UpgradeReport> = {}): UpgradeReport {
  return {
    versionBumps: [],
    lockfileStale: [],
    changedFiles: [],
    warnings: [],
    checkedVersions: false,
    checkedLockfile: false,
    ...overrides,
  };
}

function fakeApp(overrides: Record<string, unknown> = {}): App {
  return {
    synth: () => [],
    check: async () => [],
    lockfilePath: ".ghagen.lock.yml",
    rootAbsPath: "/fake",
    ...overrides,
  } as unknown as App;
}

function bump(): UpgradeReport["versionBumps"][number] {
  return {
    uses: "actions/checkout@v4",
    current: "v4",
    latest: "v6",
    severity: "major",
    source_files: [],
  };
}

const savedEnv: Record<string, string | undefined> = {};

function clearToken(): void {
  savedEnv["GITHUB_TOKEN"] = process.env["GITHUB_TOKEN"];
  savedEnv["GH_TOKEN"] = process.env["GH_TOKEN"];
  delete process.env["GITHUB_TOKEN"];
  delete process.env["GH_TOKEN"];
}

afterEach(() => {
  vi.restoreAllMocks();
  upgradeMock.mockReset();
  pinMock.mockReset();
  checkSyncMock.mockReset();
  trackUserFilesMock.mockReset();
  loadAppMock.mockReset();
  findConfigMock.mockReset();
  findConfigMock.mockReturnValue("/fake/ghagen.workflows.ts");
  if ("GITHUB_TOKEN" in savedEnv) {
    if (savedEnv["GITHUB_TOKEN"] === undefined) {
      delete process.env["GITHUB_TOKEN"];
    } else {
      process.env["GITHUB_TOKEN"] = savedEnv["GITHUB_TOKEN"];
    }
  }
  if ("GH_TOKEN" in savedEnv) {
    if (savedEnv["GH_TOKEN"] === undefined) {
      delete process.env["GH_TOKEN"];
    } else {
      process.env["GH_TOKEN"] = savedEnv["GH_TOKEN"];
    }
  }
});

// -- synth / check-synced / init (top-level) ---------------------------------

describe("top-level command streams", () => {
  test("synth-success", async () => {
    loadAppMock.mockResolvedValue(fakeApp({ synth: () => ["ci.yml"] }));

    const out = captureStdout();
    const err = captureStderr();
    const code = await main(["synth"]);
    out.restore();
    err.restore();

    expect(code).toBe(0);
    expect(streamText(out.text(), err.text(), "synth-success")).toContain("Synthesized 1");
    expect(otherStreamText(out.text(), err.text(), "synth-success")).not.toContain("Synthesized 1");
  });

  test("synth-config-not-found", async () => {
    findConfigMock.mockImplementation(() => {
      throw new CliError("Error: no config file found. Searched:\n  - ghagen.workflows.ts");
    });

    const out = captureStdout();
    const err = captureStderr();
    const code = await main(["synth"]);
    out.restore();
    err.restore();

    expect(code).toBe(1);
    expect(streamText(out.text(), err.text(), "synth-config-not-found")).toContain(
      "no config file found",
    );
    expect(otherStreamText(out.text(), err.text(), "synth-config-not-found")).not.toContain(
      "no config file found",
    );
  });

  test("check-synced-top-level-in-sync", async () => {
    loadAppMock.mockResolvedValue(fakeApp({ check: async () => [] }));

    const out = captureStdout();
    const err = captureStderr();
    const code = await main(["check-synced"]);
    out.restore();
    err.restore();

    expect(code).toBe(0);
    expect(streamText(out.text(), err.text(), "check-synced-top-level-in-sync")).toContain(
      "up-to-date",
    );
    expect(otherStreamText(out.text(), err.text(), "check-synced-top-level-in-sync")).not.toContain(
      "up-to-date",
    );
  });

  test("check-synced-top-level-stale", async () => {
    loadAppMock.mockResolvedValue(
      fakeApp({ check: async () => [["ci.yml", "stale diff"] as [string, string]] }),
    );

    const out = captureStdout();
    const err = captureStderr();
    const code = await main(["check-synced"]);
    out.restore();
    err.restore();

    expect(code).toBe(1);
    expect(streamText(out.text(), err.text(), "check-synced-top-level-stale")).toContain(
      "out of date",
    );
    expect(otherStreamText(out.text(), err.text(), "check-synced-top-level-stale")).not.toContain(
      "out of date",
    );
  });
});

describe("init command streams", () => {
  let tmp: string;
  let originalCwd: string;

  beforeEach(() => {
    tmp = mkdtempSync(join(tmpdir(), "ghagen-streams-init-"));
    originalCwd = process.cwd();
    process.chdir(tmp);
  });

  afterEach(() => {
    process.chdir(originalCwd);
    rmSync(tmp, { recursive: true, force: true });
  });

  test("init-success", async () => {
    const out = captureStdout();
    const err = captureStderr();
    const code = await main(["init"]);
    out.restore();
    err.restore();

    expect(code).toBe(0);
    expect(streamText(out.text(), err.text(), "init-success")).toContain("Created");
    expect(otherStreamText(out.text(), err.text(), "init-success")).not.toContain("Created");
  });

  test("init-already-exists", async () => {
    const target = join(tmp, ".github", "ghagen.workflows.ts");
    mkdirSync(join(tmp, ".github"), { recursive: true });
    writeFileSync(target, "// existing\n");

    const out = captureStdout();
    const err = captureStderr();
    const code = await main(["init"]);
    out.restore();
    err.restore();

    expect(code).toBe(1);
    expect(streamText(out.text(), err.text(), "init-already-exists")).toContain("already exists");
    expect(otherStreamText(out.text(), err.text(), "init-already-exists")).not.toContain(
      "already exists",
    );
  });
});

// -- deps check-synced ---------------------------------------------------------

describe("deps check-synced streams", () => {
  test("deps-check-synced-in-sync", async () => {
    loadAppMock.mockResolvedValue(fakeApp());
    checkSyncMock.mockReturnValue({ missing: [], extra: [], inSync: true });
    clearToken();

    const out = captureStdout();
    const err = captureStderr();
    await depsCheckSynced({ prune: true });
    out.restore();
    err.restore();

    expect(streamText(out.text(), err.text(), "deps-check-synced-in-sync")).toContain(
      "Lockfile is in sync.",
    );
    expect(otherStreamText(out.text(), err.text(), "deps-check-synced-in-sync")).not.toContain(
      "Lockfile is in sync.",
    );
  });

  test("deps-check-synced-missing", async () => {
    loadAppMock.mockResolvedValue(fakeApp());
    checkSyncMock.mockReturnValue({
      missing: ["actions/checkout@v4"],
      extra: [],
      inSync: false,
    });
    clearToken();

    const out = captureStdout();
    const err = captureStderr();
    await expect(depsCheckSynced({ prune: true })).rejects.toMatchObject({ exitCode: 1 });
    out.restore();
    err.restore();

    expect(streamText(out.text(), err.text(), "deps-check-synced-missing")).toContain(
      "Missing lockfile entries",
    );
    expect(otherStreamText(out.text(), err.text(), "deps-check-synced-missing")).not.toContain(
      "Missing lockfile entries",
    );
  });
});

// -- deps pin -------------------------------------------------------------------

describe("deps pin streams", () => {
  test("deps-pin-resolved", async () => {
    loadAppMock.mockResolvedValue(fakeApp());
    pinMock.mockResolvedValue({
      resolved: [{ uses: "actions/checkout@v4", sha: "0".repeat(40) }],
      errors: [],
      warnings: [],
      pruned: 0,
      written: true,
      upToDate: false,
      lockfilePath: "/fake/.ghagen.lock.yml",
    });

    const out = captureStdout();
    const err = captureStderr();
    await depsPin({ prune: true, token: "fake-token" });
    out.restore();
    err.restore();

    expect(streamText(out.text(), err.text(), "deps-pin-resolved")).toContain(
      "actions/checkout@v4",
    );
    expect(otherStreamText(out.text(), err.text(), "deps-pin-resolved")).not.toContain(
      "actions/checkout@v4",
    );
  });

  test("deps-pin-no-token-warning", async () => {
    loadAppMock.mockResolvedValue(fakeApp());
    pinMock.mockResolvedValue({
      resolved: [],
      errors: [],
      warnings: [],
      pruned: 0,
      written: false,
      upToDate: true,
      lockfilePath: "/fake/.ghagen.lock.yml",
    });
    clearToken();

    const out = captureStdout();
    const err = captureStderr();
    await depsPin({ prune: true });
    out.restore();
    err.restore();

    expect(streamText(out.text(), err.text(), "deps-pin-no-token-warning")).toContain(
      "no GitHub token found",
    );
    expect(otherStreamText(out.text(), err.text(), "deps-pin-no-token-warning")).not.toContain(
      "no GitHub token found",
    );
  });
});

// -- deps upgrade -----------------------------------------------------------

describe("deps upgrade streams", () => {
  const bumpReport = () =>
    emptyReport({
      changedFiles: [".github/ghagen_workflows.ts"],
      checkedVersions: true,
      versionBumps: [bump()],
    });

  test("deps-upgrade-report", async () => {
    trackUserFilesMock.mockResolvedValue({ app: fakeApp(), files: new Set<string>() });
    upgradeMock.mockResolvedValue(bumpReport());

    const out = captureStdout();
    const err = captureStderr();
    await depsUpgrade({ mode: "versions", format: "json", check: true, token: "fake" });
    out.restore();
    err.restore();

    expect(streamText(out.text(), err.text(), "deps-upgrade-report")).toContain('"version_bumps"');
    expect(otherStreamText(out.text(), err.text(), "deps-upgrade-report")).not.toContain(
      '"version_bumps"',
    );
  });

  test("deps-upgrade-warning", async () => {
    trackUserFilesMock.mockResolvedValue({ app: fakeApp(), files: new Set<string>() });
    upgradeMock.mockResolvedValue(
      emptyReport({
        checkedVersions: true,
        warnings: ["failed to list tags for actions/checkout: rate limited"],
      }),
    );

    const out = captureStdout();
    const err = captureStderr();
    await depsUpgrade({ mode: "versions", format: "json", check: true, token: "fake" });
    out.restore();
    err.restore();

    expect(streamText(out.text(), err.text(), "deps-upgrade-warning")).toContain("warning:");
    expect(otherStreamText(out.text(), err.text(), "deps-upgrade-warning")).not.toContain(
      "warning:",
    );
  });

  test("deps-upgrade-progress-note-no-format", async () => {
    trackUserFilesMock.mockResolvedValue({ app: fakeApp(), files: new Set<string>() });
    upgradeMock.mockResolvedValue(bumpReport());

    const out = captureStdout();
    const err = captureStderr();
    await depsUpgrade({ mode: "versions", token: "fake" });
    out.restore();
    err.restore();

    const row = "deps-upgrade-progress-note-no-format";
    expect(streamText(out.text(), err.text(), row)).toContain("Applied version bumps");
    expect(otherStreamText(out.text(), err.text(), row)).not.toContain("Applied version bumps");
  });

  test("deps-upgrade-progress-note-with-format", async () => {
    trackUserFilesMock.mockResolvedValue({ app: fakeApp(), files: new Set<string>() });
    upgradeMock.mockResolvedValue(bumpReport());

    const out = captureStdout();
    const err = captureStderr();
    await depsUpgrade({ mode: "versions", format: "json", token: "fake" });
    out.restore();
    err.restore();

    const row = "deps-upgrade-progress-note-with-format";
    expect(streamText(out.text(), err.text(), row)).toContain("Applied version bumps");
    expect(otherStreamText(out.text(), err.text(), row)).not.toContain("Applied version bumps");
  });
});

// -- deps update --------------------------------------------------------------

describe("deps update streams", () => {
  function bumpOnLocklessProject(): UpgradeReport {
    return emptyReport({
      versionBumps: [bump()],
      checkedVersions: true,
      checkedLockfile: true,
    });
  }

  test("deps-update-plan", async () => {
    trackUserFilesMock.mockResolvedValue({
      app: fakeApp({ lockfilePath: null }),
      files: new Set<string>(),
    });
    upgradeMock.mockResolvedValue(bumpOnLocklessProject());

    for (const format of ["github", "json"] as const) {
      const out = captureStdout();
      const err = captureStderr();
      await depsUpdate({ token: "fake", dryRun: true, format });
      out.restore();
      err.restore();

      const marker = format === "json" ? '"action"' : "action=";
      expect(streamText(out.text(), err.text(), "deps-update-plan")).toContain(marker);
      expect(otherStreamText(out.text(), err.text(), "deps-update-plan")).not.toContain(marker);
    }
  });

  test("deps-update-warning", async () => {
    trackUserFilesMock.mockResolvedValue({
      app: fakeApp({ lockfilePath: null }),
      files: new Set<string>(),
    });
    upgradeMock.mockResolvedValue(
      emptyReport({
        ...bumpOnLocklessProject(),
        warnings: ["failed to list tags for actions/checkout: rate limited"],
      }),
    );

    const out = captureStdout();
    const err = captureStderr();
    await depsUpdate({ token: "fake", dryRun: true, format: "json" });
    out.restore();
    err.restore();

    expect(streamText(out.text(), err.text(), "deps-update-warning")).toContain("warning:");
    expect(otherStreamText(out.text(), err.text(), "deps-update-warning")).not.toContain(
      "warning:",
    );
  });

  test("deps-update-modified-note", async () => {
    trackUserFilesMock.mockResolvedValue({
      app: fakeApp({ lockfilePath: null }),
      files: new Set<string>(),
    });
    loadAppMock.mockResolvedValue(fakeApp({ lockfilePath: null }));
    upgradeMock.mockResolvedValue(
      emptyReport({ ...bumpOnLocklessProject(), changedFiles: ["ghagen.workflows.ts"] }),
    );

    const out = captureStdout();
    const err = captureStderr();
    await depsUpdate({ token: "fake", format: "json" });
    out.restore();
    err.restore();

    const row = "deps-update-modified-note";
    expect(streamText(out.text(), err.text(), row)).toContain("modified");
    expect(otherStreamText(out.text(), err.text(), row)).not.toContain("modified");
  });
});
