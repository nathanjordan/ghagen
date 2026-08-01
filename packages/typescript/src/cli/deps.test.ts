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

import { describe, expect, test, vi, afterEach } from "vitest";
import type { App } from "../app.js";
import type { UpgradeReport } from "../pin/index.js";

const upgradeMock = vi.fn<(...args: unknown[]) => Promise<UpgradeReport>>();
const trackUserFilesMock =
  vi.fn<(...args: unknown[]) => Promise<{ app: App; files: Set<string> }>>();

vi.mock("../pin/index.js", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../pin/index.js")>();
  return {
    ...actual,
    upgrade: upgradeMock,
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

const { depsUpgrade } = await import("./deps.js");

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
