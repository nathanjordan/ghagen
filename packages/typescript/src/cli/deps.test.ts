/**
 * Tests for the `ghagen deps` CLI command surface.
 *
 * Scope, deliberately narrow: what is genuinely CLI. **Which stream** each
 * piece of output goes to, and the end-to-end shape of the JSON payload.
 *
 * What is *not* here, and why:
 *
 * - Engine behaviour (bump detection, stale-lockfile detection, mode dispatch,
 *   warnings) is asserted directly in `src/pin/engine.test.ts`.
 * - Output rendering (all four formats, the golden fixtures, the JSON key set)
 *   is asserted directly against `pin/render.ts` in `src/pin/render.test.ts`.
 *
 * See docs/specs/0005-typed-engine-report-seam.md Part A.
 */

import { existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, test, vi, afterEach } from "vitest";
import type { App } from "../app.js";
import type { UpgradeReport } from "../pin/index.js";

const upgradeMock = vi.fn<(...args: unknown[]) => Promise<UpgradeReport>>();
const pinMock = vi.fn<(...args: unknown[]) => Promise<unknown>>();
const trackUserFilesMock =
  vi.fn<(...args: unknown[]) => Promise<{ app: App; files: Set<string> }>>();

vi.mock("../pin/index.js", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../pin/index.js")>();
  return {
    ...actual,
    upgrade: upgradeMock,
    pin: pinMock,
    trackUserFiles: trackUserFilesMock,
    // Never actually used (upgrade() is mocked), but must be a real
    // constructor: buildGitHubClient() in deps.ts does `new GitHubClient(...)`.
    GitHubClient: class FakeGitHubClient {
      readonly fake = true;
    },
  };
});

vi.mock("./_common.js", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./_common.js")>();
  return {
    ...actual,
    findConfig: vi.fn(() => "/fake/ghagen.workflows.ts"),
  };
});

const { depsUpgrade, depsUpdate } = await import("./deps.js");

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

afterEach(() => {
  vi.restoreAllMocks();
  upgradeMock.mockReset();
  pinMock.mockReset();
  trackUserFilesMock.mockReset();
});

/**
 * Where the apply-progress note lands — the `0cae9b1` hotfix, both halves.
 *
 * The renderer returns a string and writes nothing, so it cannot interleave
 * with the progress note; the command keeps sole ownership of destinations.
 * These tests pin that ownership, which is a routing fact, not a rendering
 * one — hence a CLI test rather than a renderer test.
 */
describe("deps upgrade output routing", () => {
  const bumpReport = () =>
    emptyReport({
      changedFiles: [".github/ghagen_workflows.ts"],
      checkedVersions: true,
      versionBumps: [
        {
          uses: "actions/checkout@v5",
          current: "v5",
          latest: "v6",
          severity: "major",
          source_files: [],
        },
      ],
    });

  test("apply mode keeps stdout parseable — the progress note goes to stderr", async () => {
    trackUserFilesMock.mockResolvedValue({ app: {} as App, files: new Set<string>() });
    upgradeMock.mockResolvedValue(bumpReport());

    const out = captureStdout();
    const err = captureStderr();
    // No `check` -> apply mode, so report.changedFiles is non-empty.
    await depsUpgrade({ mode: "versions", format: "json", token: "fake" });
    out.restore();
    err.restore();

    expect(out.text()).not.toContain("Applied version bumps");
    expect(JSON.parse(out.text())).toHaveProperty("version_bumps");
    expect(err.text()).toContain("Applied version bumps");
    expect(err.text()).toContain("modified .github/ghagen_workflows.ts");
  });

  // The other half of the same hotfix, and the branch TypeScript had never
  // asserted: without --format there is no machine-readable payload to
  // protect, so the progress note belongs on stdout with the report.
  test("without --format the progress note goes to stdout", async () => {
    trackUserFilesMock.mockResolvedValue({ app: {} as App, files: new Set<string>() });
    upgradeMock.mockResolvedValue(bumpReport());

    const out = captureStdout();
    const err = captureStderr();
    await depsUpgrade({ mode: "versions", token: "fake" });
    out.restore();
    err.restore();

    expect(out.text()).toContain("Applied version bumps");
    expect(out.text()).toContain("modified .github/ghagen_workflows.ts");
    expect(err.text()).not.toContain("Applied version bumps");
  });

  test("warnings are echoed to stderr, never to the payload", async () => {
    trackUserFilesMock.mockResolvedValue({ app: {} as App, files: new Set<string>() });
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

    expect(err.text()).toContain("warning: failed to list tags for actions/checkout");
    expect(out.text()).not.toContain("warning:");
    expect(JSON.parse(out.text())).toEqual({ version_bumps: [] });
  });
});

/**
 * The end-to-end key-set contract.
 *
 * The rule itself — key presence follows `checkedVersions` /
 * `checkedLockfile` — is asserted directly on the renderer in
 * `src/pin/render.test.ts`. This is the one place it is pinned through the
 * real command, because it is a user-visible payload change.
 */
describe("deps upgrade --format json key set", () => {
  // An empty report emits the same key set as a non-empty one: the key set
  // depends only on --mode, which the caller chose, and never on whether the
  // run happened to find anything. This inverts the behaviour the
  // "everything up to date" early return used to have, and resolves the open
  // choice recorded in docs/specs/0005-typed-engine-report-seam.md §2.2.
  test("an empty report emits only the keys the mode asked for", async () => {
    trackUserFilesMock.mockResolvedValue({ app: {} as App, files: new Set<string>() });

    const expectedPerMode = [
      { mode: "versions", expected: { version_bumps: [] } },
      { mode: "lockfile", expected: { lockfile_stale: [] } },
      { mode: "all", expected: { version_bumps: [], lockfile_stale: [] } },
    ] as const;

    for (const { mode, expected } of expectedPerMode) {
      upgradeMock.mockResolvedValue(
        emptyReport({
          checkedVersions: mode === "versions" || mode === "all",
          checkedLockfile: mode === "lockfile" || mode === "all",
        }),
      );

      const out = captureStdout();
      await depsUpgrade({ mode, format: "json", check: true, token: "fake" });
      out.restore();

      expect(JSON.parse(out.text()), mode).toEqual(expected);
      expect(out.text()).not.toContain("helper_provided");
    }
  });
});

// -- deps update -------------------------------------------------------------

/** The field set `--format github` and `--format json` both carry. */
const PLAN_FIELDS = [
  "action",
  "total_updates",
  "apply_version_bumps",
  "refresh_lockfile",
  "branch",
  "title",
  "commit_message",
  "labels",
  "body_format",
  "changed",
].sort();

/** Parse `--format github` back into the mapping a runner would build. */
function githubOutputs(stdout: string): Record<string, string> {
  const entries = stdout
    .split("\n")
    .filter((line) => line.length > 0)
    .map((line) => {
      const at = line.indexOf("=");
      return [line.slice(0, at), line.slice(at + 1)] as const;
    });
  return Object.fromEntries(entries);
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

/** The report a `lockfile: null` project with an outdated ref produces. */
function bumpOnLocklessProject(): UpgradeReport {
  return emptyReport({
    versionBumps: [bump()],
    checkedVersions: true,
    // True even though the stage cannot have run: it records what the run was
    // *asked* for. That is the distinction the shipped action could not make.
    checkedLockfile: true,
  });
}

const UPDATE_DEFAULTS = { token: "fake" } as const;

/**
 * The automation verb: one sweep, one plan, one answer.
 *
 * Decision rules themselves are asserted offline in `src/pin/plan.test.ts`;
 * body bytes in `src/pin/render.test.ts`. What is here is what is genuinely
 * CLI — flag validation, stream ownership, the two wire shapes, and the
 * end-to-end proof that the command does not do the thing the shipped
 * `check-deps` action's bash did.
 */
describe("deps update", () => {
  /**
   * H7, end to end: a bump on a `lockfile: null` project must not cascade.
   *
   * The shipped action's guard is `lockfile_stale != 0 || version_bumps != 0`,
   * which fires here — `lockfile_stale` is always `0` under `lockfile: null`
   * because the stage is skipped, but the bump is real. It then runs
   * `ghagen deps pin --update`, which exits 1 with "lockfile is disabled",
   * killing the step under `set -euo pipefail`. `planUpdate` holds the app, so
   * the command applies the bump and stops.
   */
  test("a lockfile-less project never reaches the pin engine", async () => {
    trackUserFilesMock.mockResolvedValue({
      app: { lockfilePath: null } as App,
      files: new Set<string>(),
    });
    upgradeMock.mockResolvedValue(
      emptyReport({ ...bumpOnLocklessProject(), changedFiles: ["ghagen.workflows.ts"] }),
    );

    const out = captureStdout();
    const err = captureStderr();
    await depsUpdate({ ...UPDATE_DEFAULTS, format: "json" });
    out.restore();
    err.restore();

    expect(pinMock).not.toHaveBeenCalled();
    expect(err.text()).not.toContain("lockfile is disabled");
    const plan = JSON.parse(out.text());
    expect(plan.refresh_lockfile).toBe(false);
    expect(plan.apply_version_bumps).toBe(true);
    expect(plan.action).toBe("create-pr");
    expect(plan.changed).toBe(true);
  });

  test("a lockfile-bearing project refreshes through the pin engine", async () => {
    trackUserFilesMock.mockResolvedValue({
      app: { lockfilePath: ".ghagen.lock.yml" } as App,
      files: new Set<string>(),
    });
    upgradeMock.mockResolvedValue(bumpOnLocklessProject());
    pinMock.mockResolvedValue({
      resolved: [],
      warnings: [],
      errors: [],
      pruned: 0,
      written: true,
      upToDate: false,
      lockfilePath: ".ghagen.lock.yml",
    });

    const out = captureStdout();
    const err = captureStderr();
    await depsUpdate({ ...UPDATE_DEFAULTS, format: "json" });
    out.restore();
    err.restore();

    expect(pinMock).toHaveBeenCalledTimes(1);
    const plan = JSON.parse(out.text());
    expect(plan.refresh_lockfile).toBe(true);
    expect(plan.changed).toBe(true);
  });

  /**
   * `--format github` appends straight to `$GITHUB_OUTPUT`.
   *
   * Nothing human may share that stream: the action's plan step is a single
   * `>> "$GITHUB_OUTPUT"` redirect, so a stray progress line would become a
   * malformed output entry.
   */
  test("--format github is $GITHUB_OUTPUT-shaped and owns stdout", async () => {
    trackUserFilesMock.mockResolvedValue({
      app: { lockfilePath: null } as App,
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
    await depsUpdate({ ...UPDATE_DEFAULTS, dryRun: true, labels: " a , b ,, c " });
    out.restore();
    err.restore();

    const outputs = githubOutputs(out.text());
    expect(Object.keys(outputs).sort()).toEqual(PLAN_FIELDS);
    expect(outputs["action"]).toBe("create-pr");
    expect(outputs["total_updates"]).toBe("1");
    expect(outputs["refresh_lockfile"]).toBe("false");
    expect(outputs["apply_version_bumps"]).toBe("true");
    expect(outputs["changed"]).toBe("false");
    expect(outputs["labels"]).toBe("a,b,c");
    expect(outputs["commit_message"]).toBe("update ghagen action dependencies");
    expect(err.text()).toContain("warning: failed to list tags");
    expect(out.text()).not.toContain("warning:");
  });

  test("--format json and --format github carry the same fields", async () => {
    trackUserFilesMock.mockResolvedValue({
      app: { lockfilePath: null } as App,
      files: new Set<string>(),
    });
    upgradeMock.mockResolvedValue(bumpOnLocklessProject());

    const asJson = captureStdout();
    await depsUpdate({ ...UPDATE_DEFAULTS, dryRun: true, format: "json" });
    asJson.restore();

    const asGithub = captureStdout();
    await depsUpdate({ ...UPDATE_DEFAULTS, dryRun: true, format: "github" });
    asGithub.restore();

    expect(Object.keys(JSON.parse(asJson.text())).sort()).toEqual(PLAN_FIELDS);
    expect(Object.keys(githubOutputs(asGithub.text())).sort()).toEqual(PLAN_FIELDS);
  });

  test("--dry-run asks the engine not to apply", async () => {
    trackUserFilesMock.mockResolvedValue({
      app: { lockfilePath: null } as App,
      files: new Set<string>(),
    });
    upgradeMock.mockResolvedValue(bumpOnLocklessProject());

    const out = captureStdout();
    await depsUpdate({ ...UPDATE_DEFAULTS, dryRun: true, format: "json" });
    out.restore();

    expect(upgradeMock).toHaveBeenCalledWith(
      expect.anything(),
      expect.anything(),
      expect.anything(),
      expect.objectContaining({ apply: false }),
    );
    expect(JSON.parse(out.text()).changed).toBe(false);
  });

  /**
   * The body is a file path, never an output value.
   *
   * Keeping bytes out of `$GITHUB_OUTPUT` sidesteps the multiline delimiter
   * dance entirely, which is why the plan carries `bodyFormat` rather than a
   * body.
   */
  test("--body-file receives the plan's rendering", async () => {
    trackUserFilesMock.mockResolvedValue({
      app: { lockfilePath: null } as App,
      files: new Set<string>(),
    });
    upgradeMock.mockResolvedValue(bumpOnLocklessProject());
    const dir = mkdtempSync(join(tmpdir(), "ghagen-update-"));
    const bodyFile = join(dir, "body.md");

    const out = captureStdout();
    await depsUpdate({ ...UPDATE_DEFAULTS, dryRun: true, format: "json", bodyFile });
    out.restore();

    expect(JSON.parse(out.text()).body_format).toBe("pr-body");
    const body = readFileSync(bodyFile, "utf8");
    expect(body.startsWith("## ghagen dependency update")).toBe(true);
    expect(body).toContain("actions/checkout@v4");
    rmSync(dir, { recursive: true, force: true });
  });

  test("no body file is written when there is nothing to raise", async () => {
    trackUserFilesMock.mockResolvedValue({
      app: { lockfilePath: null } as App,
      files: new Set<string>(),
    });
    upgradeMock.mockResolvedValue(emptyReport({ checkedVersions: true, checkedLockfile: true }));
    const dir = mkdtempSync(join(tmpdir(), "ghagen-update-"));
    const bodyFile = join(dir, "body.md");

    const out = captureStdout();
    await depsUpdate({ ...UPDATE_DEFAULTS, format: "json", bodyFile });
    out.restore();

    const plan = JSON.parse(out.text());
    expect(plan.action).toBe("none");
    expect(plan.body_format).toBeNull();
    expect(existsSync(bodyFile)).toBe(false);
    rmSync(dir, { recursive: true, force: true });
  });
});

/**
 * Bad flag values exit 2 with one line — never a stack trace.
 *
 * The construct being replaced turned every diagnosable CLI failure into
 * exit 1 plus a `JSONDecodeError` traceback from the *reader*, because the
 * detect step ended in `|| true` and the next line parsed the empty file it
 * was supposed to have written.
 */
describe("deps update flag validation", () => {
  async function expectUsageError(
    opts: Parameters<typeof depsUpdate>[0],
    fragment: string,
  ): Promise<void> {
    await expect(depsUpdate(opts)).rejects.toMatchObject({
      exitCode: 2,
      message: expect.stringContaining(fragment),
    });
  }

  test("an unknown --mode", async () => {
    await expectUsageError({ mode: "bogus" as "all" }, "unknown --mode value");
  });

  test("an unknown --output", async () => {
    await expectUsageError({ output: "bogus" as "pr" }, "unknown --output value");
  });

  test("an unknown --format", async () => {
    await expectUsageError({ format: "yaml" }, "unknown --format value");
  });

  /**
   * A newline would forge extra `$GITHUB_OUTPUT` entries.
   *
   * `commit-message-prefix` is a workflow-author-supplied action input that
   * lands verbatim in a `key=value` line, so an embedded newline is an
   * output-injection vector, not a formatting nit.
   */
  test("a newline in a prefix", async () => {
    await expectUsageError(
      { commitMessagePrefix: "x\naction=create-pr" },
      "must not contain a newline",
    );
  });
});
