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
import { join, resolve } from "node:path";
import { describe, expect, test, vi, afterEach } from "vitest";
import { parse as parseYaml } from "yaml";
import type { App } from "../app.js";
import { SCHEMA_DIR } from "../paths.js";
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

const loadAppMock = vi.fn<(...args: unknown[]) => Promise<App>>();

vi.mock("./_common.js", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./_common.js")>();
  return {
    ...actual,
    findConfig: vi.fn(() => "/fake/ghagen.workflows.ts"),
    loadApp: loadAppMock,
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

/**
 * A stand-in {@link App} carrying the surface `deps update` actually touches.
 *
 * `synth` is a real (empty) method rather than absent: the command
 * re-synthesizes after it has written to the tree, so a bare `{} as App` would
 * die on `app.synth is not a function` for reasons that have nothing to do with
 * what the test is asserting.
 */
function fakeApp(overrides: Record<string, unknown> = {}): App {
  return { synth: () => [], ...overrides } as unknown as App;
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
  loadAppMock.mockReset();
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
    trackUserFilesMock.mockResolvedValue({ app: fakeApp(), files: new Set<string>() });
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
    trackUserFilesMock.mockResolvedValue({ app: fakeApp(), files: new Set<string>() });
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
    trackUserFilesMock.mockResolvedValue({ app: fakeApp(), files: new Set<string>() });

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

/**
 * The field set `--format github` and `--format json` both carry, shared with
 * the Python suite through `schema/update-plan-fields.yml` — see
 * docs/issues/21-update-plan-is-not-under-the-shared-oracle.md.
 */
const PLAN_FIELDS: string[] = (
  parseYaml(readFileSync(resolve(SCHEMA_DIR, "update-plan-fields.yml"), "utf8")) as {
    keys: string[];
  }
).keys
  .slice()
  .sort();

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
      app: fakeApp({ lockfilePath: null }),
      files: new Set<string>(),
    });
    // The bump was applied, so the command re-reads the config. The reload of
    // a `lockfile: null` project is still a `lockfile: null` project.
    loadAppMock.mockResolvedValue(fakeApp({ lockfilePath: null }));
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
      app: fakeApp({ lockfilePath: ".ghagen.lock.yml" }),
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

  /**
   * Loading the config *executes* it, and it does not own stdout.
   *
   * Same stream, one step earlier. The config is arbitrary user TypeScript
   * that runs before the plan is printed, so a `console.log` with no `=` fails
   * the action's `>> "$GITHUB_OUTPUT"` step outright, and one *with* an `=` —
   * `console.log("action=create-issue")` — forges an action-level output the
   * workflow then acts on. Re-routed, not suppressed.
   */
  test("a chatty config module cannot reach the plan stream", async () => {
    trackUserFilesMock.mockImplementation(async () => {
      process.stdout.write("action=create-issue\n");
      process.stdout.write("loading workflows...\n");
      return { app: fakeApp({ lockfilePath: null }), files: new Set<string>() };
    });
    upgradeMock.mockResolvedValue(emptyReport(bumpOnLocklessProject()));

    const out = captureStdout();
    const err = captureStderr();
    await depsUpdate({ ...UPDATE_DEFAULTS, dryRun: true });
    out.restore();
    err.restore();

    const lines = out.text().split("\n").filter(Boolean);
    expect(lines.every((line) => /^[a-z_]+=/.test(line))).toBe(true);
    // Exactly one `action=`: the plan's own, and it is a PR, not the issue the
    // config module tried to forge.
    expect(lines.filter((line) => line.startsWith("action="))).toEqual(["action=create-pr"]);
    expect(err.text()).toContain("loading workflows...");
  });

  test("--format json and --format github carry the same fields", async () => {
    trackUserFilesMock.mockResolvedValue({
      app: fakeApp({ lockfilePath: null }),
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
      app: fakeApp({ lockfilePath: null }),
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
   * Issue 20's deliverable: `--output issue` writes nothing, even without
   * `--dry-run`.
   *
   * Before this fix, `--output issue` applied the version bump exactly like
   * `--output pr` — an issue mode leaves the tree untouched, since the
   * shipped action never commits on that path and those writes would
   * otherwise be stranded in a runner's checkout nothing will ever commit.
   */
  test("--output issue asks the engine not to apply, without --dry-run", async () => {
    trackUserFilesMock.mockResolvedValue({
      app: fakeApp({ lockfilePath: null }),
      files: new Set<string>(),
    });
    upgradeMock.mockResolvedValue(bumpOnLocklessProject());

    const out = captureStdout();
    await depsUpdate({ ...UPDATE_DEFAULTS, output: "issue", format: "json" });
    out.restore();

    expect(upgradeMock).toHaveBeenCalledWith(
      expect.anything(),
      expect.anything(),
      expect.anything(),
      expect.objectContaining({ apply: false }),
    );
    expect(pinMock).not.toHaveBeenCalled();
    const plan = JSON.parse(out.text());
    expect(plan.action).toBe("create-issue");
    expect(plan.apply_version_bumps).toBe(false);
    expect(plan.refresh_lockfile).toBe(false);
    expect(plan.changed).toBe(false);
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
      app: fakeApp({ lockfilePath: null }),
      files: new Set<string>(),
    });
    upgradeMock.mockResolvedValue(bumpOnLocklessProject());
    const dir = mkdtempSync(join(tmpdir(), "ghagen-update-"));
    const bodyFile = join(dir, "body.md");

    const out = captureStdout();
    await depsUpdate({ ...UPDATE_DEFAULTS, format: "json", bodyFile });
    out.restore();

    expect(JSON.parse(out.text()).body_format).toBe("pr-body");
    const body = readFileSync(bodyFile, "utf8");
    expect(body.startsWith("## ghagen dependency update")).toBe(true);
    expect(body).toContain("actions/checkout@v4");
    rmSync(dir, { recursive: true, force: true });
  });

  /**
   * `--dry-run` writes nothing, and the body file is a write.
   *
   * Both `cli.md` pages document "no source edits, no lockfile write, no body
   * file". The two sibling effects were guarded and this one was not, so the
   * contract was true of two thirds of itself. "Write nothing" is the stronger
   * contract, so the write moved under the guard rather than the sentence out
   * of the docs. The plan still *decides* a `bodyFormat`: a decision is not a
   * write.
   */
  test("--dry-run writes no body file", async () => {
    trackUserFilesMock.mockResolvedValue({
      app: fakeApp({ lockfilePath: null }),
      files: new Set<string>(),
    });
    upgradeMock.mockResolvedValue(bumpOnLocklessProject());
    const dir = mkdtempSync(join(tmpdir(), "ghagen-update-"));
    const bodyFile = join(dir, "body.md");

    const out = captureStdout();
    await depsUpdate({ ...UPDATE_DEFAULTS, dryRun: true, format: "json", bodyFile });
    out.restore();

    expect(JSON.parse(out.text()).body_format).toBe("pr-body");
    expect(existsSync(bodyFile)).toBe(false);
    rmSync(dir, { recursive: true, force: true });
  });

  test("no body file is written when there is nothing to raise", async () => {
    trackUserFilesMock.mockResolvedValue({
      app: fakeApp({ lockfilePath: null }),
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
 * `deps update` performs *every* write the update needs.
 *
 * Its whole reason to exist is that a caller reads the plan and raises a PR
 * without re-deriving anything. A PR whose generated workflows still carry the
 * pre-update SHAs is red by construction on the consumer repo's own
 * `check-synced` gate.
 */
describe("deps update leaves a synthesizable tree", () => {
  /** A project with a lockfile, whose `synth` and reload are observable. */
  function lockfileProject(): { stale: App; reloaded: App; synth: ReturnType<typeof vi.fn> } {
    const synth = vi.fn(() => [".github/workflows/ci.yml"]);
    const stale = { lockfilePath: ".ghagen.lock.yml", synth: vi.fn(() => []) } as unknown as App;
    const reloaded = { lockfilePath: ".ghagen.lock.yml", synth } as unknown as App;
    return { stale, reloaded, synth };
  }

  test("the workflows are regenerated from the re-read tree", async () => {
    const { stale, reloaded, synth } = lockfileProject();
    trackUserFilesMock.mockResolvedValue({ app: stale, files: new Set<string>() });
    loadAppMock.mockResolvedValue(reloaded);
    upgradeMock.mockResolvedValue(
      emptyReport({ ...bumpOnLocklessProject(), changedFiles: ["ghagen.workflows.ts"] }),
    );
    pinMock.mockResolvedValue({
      warnings: [],
      errors: [],
      written: true,
      lockfilePath: ".ghagen.lock.yml",
    });

    const out = captureStdout();
    const err = captureStderr();
    await depsUpdate({ ...UPDATE_DEFAULTS, format: "json" });
    out.restore();
    err.restore();

    // The bumps were written to *source*; the app in hand predates them, so
    // both the pin and the synth have to run against a re-read tree.
    expect(loadAppMock).toHaveBeenCalled();
    expect(synth).toHaveBeenCalled();
    expect(pinMock).toHaveBeenCalledWith(reloaded, expect.anything(), expect.anything());
    expect(err.text()).toContain("modified .github/workflows/ci.yml");
    expect(JSON.parse(out.text()).changed).toBe(true);
  });

  test("--dry-run synthesizes nothing", async () => {
    const { stale, reloaded, synth } = lockfileProject();
    trackUserFilesMock.mockResolvedValue({ app: stale, files: new Set<string>() });
    loadAppMock.mockResolvedValue(reloaded);
    upgradeMock.mockResolvedValue(bumpOnLocklessProject());

    const out = captureStdout();
    await depsUpdate({ ...UPDATE_DEFAULTS, dryRun: true, format: "json" });
    out.restore();

    expect(synth).not.toHaveBeenCalled();
    expect(JSON.parse(out.text()).changed).toBe(false);
  });

  test("--output issue synthesizes nothing", async () => {
    const { stale } = lockfileProject();
    trackUserFilesMock.mockResolvedValue({ app: stale, files: new Set<string>() });
    upgradeMock.mockResolvedValue(bumpOnLocklessProject());

    const out = captureStdout();
    await depsUpdate({ ...UPDATE_DEFAULTS, output: "issue", format: "json" });
    out.restore();

    // Never applied, so the app is never re-read from disk either -- `stale`
    // is what `synth()` would run against if it ran at all.
    expect(loadAppMock).not.toHaveBeenCalled();
    expect((stale as unknown as { synth: ReturnType<typeof vi.fn> }).synth).not.toHaveBeenCalled();
    expect(JSON.parse(out.text()).changed).toBe(false);
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

/**
 * `--check` is read-only.
 *
 * The sibling assertion for `deps update --dry-run` exists above; this one,
 * for `deps upgrade --check`, existed in neither port. Two independent
 * reviewers mutated `apply = !opts.check` to `const apply = true` and both
 * suites stayed green, because `pin/engine.test.ts` passes `apply` explicitly
 * and so can never observe the CLI's wiring.
 */
describe("deps upgrade --check", () => {
  test("asks the engine not to apply", async () => {
    trackUserFilesMock.mockResolvedValue({ app: fakeApp(), files: new Set<string>() });
    upgradeMock.mockResolvedValue(emptyReport({ checkedVersions: true }));

    const out = captureStdout();
    await depsUpgrade({ mode: "versions", check: true, token: "fake" });
    out.restore();

    expect(upgradeMock).toHaveBeenCalledWith(
      expect.anything(),
      expect.anything(),
      expect.anything(),
      expect.objectContaining({ apply: false }),
    );
  });

  test("without --check the engine is asked to apply", async () => {
    trackUserFilesMock.mockResolvedValue({ app: fakeApp(), files: new Set<string>() });
    upgradeMock.mockResolvedValue(emptyReport({ checkedVersions: true }));

    const out = captureStdout();
    await depsUpgrade({ mode: "versions", token: "fake" });
    out.restore();

    expect(upgradeMock).toHaveBeenCalledWith(
      expect.anything(),
      expect.anything(),
      expect.anything(),
      expect.objectContaining({ apply: true }),
    );
  });
});

/**
 * `--prune` must parse, not just `--no-prune`.
 *
 * Commander does not synthesise the positive form from a `--no-x` option, so
 * declaring only `--no-prune` left `--prune` an unknown-option error (exit 2)
 * — while Python's `"--prune/--no-prune"` accepted it and both `cli.md` pages
 * hand out a copy-pasteable CI step that uses it.
 */
describe("deps --prune parity", () => {
  /**
   * Parse `argv` against the real subcommand and report the `prune` it
   * resolved, without running the command's real body. The action handler is
   * replaced rather than stubbed around it, so what is under test is exactly
   * the option declarations `buildDepsCommand` ships.
   */
  async function parsePrune(sub: string, argv: string[]): Promise<boolean> {
    const { buildDepsCommand } = await import("./deps.js");
    const command = buildDepsCommand().commands.find((c) => c.name() === sub);
    if (command === undefined) {
      throw new Error(`no such subcommand: ${sub}`);
    }

    let seen: Record<string, unknown> = {};
    command
      .exitOverride()
      .configureOutput({ writeErr: () => {}, writeOut: () => {} })
      .action((opts: Record<string, unknown>) => {
        seen = opts;
      });

    await command.parseAsync(argv, { from: "user" });
    return seen["prune"] as boolean;
  }

  test.each(["pin", "check-synced"])("%s accepts --prune", async (sub) => {
    expect(await parsePrune(sub, ["--prune"])).toBe(true);
  });

  test.each(["pin", "check-synced"])("%s accepts --no-prune", async (sub) => {
    expect(await parsePrune(sub, ["--no-prune"])).toBe(false);
  });

  test.each(["pin", "check-synced"])("%s defaults prune ON", async (sub) => {
    expect(await parsePrune(sub, [])).toBe(true);
  });
});
