/**
 * Pins the `ghagen deps upgrade --json` seam against the shared golden
 * fixture (`fixtures/expected/upgrade_report.json`), asserted identically in
 * the Python port (`tests/test_cli/test_deps.py`). See
 * docs/specs/0005-typed-engine-report-seam.md Part A.
 */

import { describe, expect, test, vi, afterEach } from "vitest";
import type { App } from "../app.js";
import type { UpgradeReport, VersionBump, LockfileStaleEntry } from "../pin/index.js";
import { loadFixture } from "../integration/test-utils.js";

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

const { bumpToJson, staleToJson, depsUpgrade } = await import("./deps.js");

function emptyReport(overrides: Partial<UpgradeReport> = {}): UpgradeReport {
  return { versionBumps: [], lockfileStale: [], changedFiles: [], warnings: [], ...overrides };
}

function captureStdout(): { text(): string; restore(): void } {
  let out = "";
  const spy = vi.spyOn(process.stdout, "write").mockImplementation((chunk: unknown) => {
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

describe("deps upgrade --json contract", () => {
  test("bumpToJson/staleToJson render exactly the shared golden fixture", () => {
    const bumps: VersionBump[] = [
      {
        uses: "actions/checkout@v5",
        current: "v5",
        latest: "v6",
        severity: "major",
        source_files: [".github/ghagen_workflows.py"],
      },
      {
        uses: "actions/setup-node@v3",
        current: "v3",
        latest: "v4",
        severity: "major",
        // No source_files -> key must be omitted entirely (not `[]`).
        source_files: [],
      },
    ];
    const stale: LockfileStaleEntry[] = [
      {
        uses: "actions/setup-python@v6",
        current_sha: "ece7cb06caefa5fff74198d8649806c4678c61a1",
        latest_sha: "aaaa1111bbbb2222cccc3333dddd4444eeee5555",
        source_files: [".github/ghagen_workflows.py"],
      },
    ];

    const rendered = {
      version_bumps: bumps.map(bumpToJson),
      lockfile_stale: stale.map(staleToJson),
    };
    const renderedText = JSON.stringify(rendered, null, 2);

    const fixtureText = loadFixture("upgrade_report.json");
    expect(JSON.parse(renderedText)).toEqual(JSON.parse(fixtureText));

    // The phantom `helper_provided` field must never appear.
    expect(renderedText).not.toContain("helper_provided");
    expect(rendered).not.toHaveProperty("helper_provided");
  });

  test("source_files is omitted when empty", () => {
    const bump: VersionBump = {
      uses: "actions/setup-node@v3",
      current: "v3",
      latest: "v4",
      severity: "major",
      source_files: [],
    };
    const stale: LockfileStaleEntry = {
      uses: "actions/setup-python@v6",
      current_sha: "a".repeat(40),
      latest_sha: "b".repeat(40),
      source_files: [],
    };
    expect(bumpToJson(bump)).not.toHaveProperty("source_files");
    expect(staleToJson(stale)).not.toHaveProperty("source_files");
  });
});

describe("deps upgrade CLI --json mode behavior", () => {
  test("--mode versions omits the lockfile_stale key", async () => {
    trackUserFilesMock.mockResolvedValue({ app: {} as App, files: new Set<string>() });
    upgradeMock.mockResolvedValue(
      emptyReport({
        versionBumps: [
          {
            uses: "actions/checkout@v5",
            current: "v5",
            latest: "v6",
            severity: "major",
            source_files: [],
          },
        ],
      }),
    );

    const out = captureStdout();
    await depsUpgrade({ mode: "versions", json: true, check: true, token: "fake" });
    out.restore();

    const data = JSON.parse(out.text());
    expect(data).toHaveProperty("version_bumps");
    expect(data).not.toHaveProperty("lockfile_stale");
    expect(out.text()).not.toContain("helper_provided");
  });

  test("--mode lockfile omits the version_bumps key", async () => {
    trackUserFilesMock.mockResolvedValue({ app: {} as App, files: new Set<string>() });
    upgradeMock.mockResolvedValue(
      emptyReport({
        lockfileStale: [
          {
            uses: "actions/setup-python@v6",
            current_sha: "a".repeat(40),
            latest_sha: "b".repeat(40),
            source_files: [],
          },
        ],
      }),
    );

    const out = captureStdout();
    await depsUpgrade({ mode: "lockfile", json: true, check: true, token: "fake" });
    out.restore();

    const data = JSON.parse(out.text());
    expect(data).toHaveProperty("lockfile_stale");
    expect(data).not.toHaveProperty("version_bumps");
    expect(out.text()).not.toContain("helper_provided");
  });

  test("the empty-report early return emits both keys as [] regardless of mode", async () => {
    trackUserFilesMock.mockResolvedValue({ app: {} as App, files: new Set<string>() });
    upgradeMock.mockResolvedValue(emptyReport());

    for (const mode of ["versions", "lockfile", "all"] as const) {
      const out = captureStdout();
      await depsUpgrade({ mode, json: true, check: true, token: "fake" });
      out.restore();

      expect(JSON.parse(out.text())).toEqual({ version_bumps: [], lockfile_stale: [] });
      expect(out.text()).not.toContain("helper_provided");
    }
  });
});
