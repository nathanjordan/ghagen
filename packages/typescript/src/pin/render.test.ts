/**
 * Unit tests for `pin/render.ts` — no command invocation, no `vi.mock`.
 *
 * These assertions used to live in `src/cli/deps.test.ts`. The renderer is a
 * pure function from a typed report to a string, so it is tested as one. See
 * docs/specs/0005-typed-engine-report-seam.md Part A.
 *
 * The four format goldens in `fixtures/expected/` are byte-compared by both
 * ports; `upgrade_text.txt` is new in proposal 17 and is the first cross-port
 * oracle the default human-readable format has ever had.
 */

import { describe, expect, test } from "vitest";
import type { LockfileStaleEntry, UpgradeReport, VersionBump } from "./engine.js";
import { renderUpgradeReport, type UpgradeFormat } from "./render.js";
import { loadFixture } from "../integration/test-utils.js";

/** The shared golden's version bumps (the second has no source files). */
const BUMPS: VersionBump[] = [
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
    source_files: [],
  },
];

/** The shared golden's stale lockfile entry. */
const STALE: LockfileStaleEntry[] = [
  {
    uses: "actions/setup-python@v6",
    current_sha: "ece7cb06caefa5fff74198d8649806c4678c61a1",
    latest_sha: "aaaa1111bbbb2222cccc3333dddd4444eeee5555",
    source_files: [".github/ghagen_workflows.py"],
  },
];

function report(overrides: Partial<UpgradeReport> = {}): UpgradeReport {
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

/** A report carrying the shared golden data, both stages asked for. */
function fullReport(overrides: Partial<UpgradeReport> = {}): UpgradeReport {
  return report({
    versionBumps: BUMPS,
    lockfileStale: STALE,
    checkedVersions: true,
    checkedLockfile: true,
    ...overrides,
  });
}

const ALL_FORMATS: UpgradeFormat[] = ["text", "json", "pr-body", "issue-body"];

// ---- goldens ----

describe("renderUpgradeReport() golden fixtures", () => {
  test("json matches the shared golden fixture", () => {
    const rendered = renderUpgradeReport(fullReport(), "json");

    expect(JSON.parse(rendered)).toEqual(JSON.parse(loadFixture("upgrade_report.json")));

    // The phantom `helper_provided` field must never appear.
    expect(rendered).not.toContain("helper_provided");
  });

  test("pr-body matches the shared golden fixture", () => {
    expect(renderUpgradeReport(fullReport(), "pr-body")).toEqual(loadFixture("upgrade_pr_body.md"));
  });

  test("issue-body matches the shared golden fixture", () => {
    expect(renderUpgradeReport(fullReport(), "issue-body")).toEqual(
      loadFixture("upgrade_issue_body.md"),
    );
  });

  // The default format's first direct test in either port.
  test("text matches the shared golden fixture", () => {
    expect(renderUpgradeReport(fullReport(), "text")).toEqual(loadFixture("upgrade_text.txt"));
  });

  test("text is the default format", () => {
    const r = fullReport();
    expect(renderUpgradeReport(r)).toEqual(renderUpgradeReport(r, "text"));
  });
});

// ---- the JSON key set ----

describe("renderUpgradeReport() json key set", () => {
  test("source_files is omitted when empty", () => {
    const rendered = renderUpgradeReport(
      report({
        versionBumps: [
          {
            uses: "actions/setup-node@v3",
            current: "v3",
            latest: "v4",
            severity: "major",
            source_files: [],
          },
        ],
        lockfileStale: [
          {
            uses: "actions/setup-python@v6",
            current_sha: "a".repeat(40),
            latest_sha: "b".repeat(40),
            source_files: [],
          },
        ],
        checkedVersions: true,
        checkedLockfile: true,
      }),
      "json",
    );

    const data = JSON.parse(rendered);
    expect(data.version_bumps[0]).not.toHaveProperty("source_files");
    expect(data.lockfile_stale[0]).not.toHaveProperty("source_files");
  });

  test("checkedVersions only omits the lockfile_stale key", () => {
    const data = JSON.parse(
      renderUpgradeReport(fullReport({ checkedLockfile: false }), "json") as string,
    );
    expect(data).toHaveProperty("version_bumps");
    expect(data).not.toHaveProperty("lockfile_stale");
  });

  test("checkedLockfile only omits the version_bumps key", () => {
    const data = JSON.parse(
      renderUpgradeReport(fullReport({ checkedVersions: false }), "json") as string,
    );
    expect(data).toHaveProperty("lockfile_stale");
    expect(data).not.toHaveProperty("version_bumps");
  });

  // An *empty* report obeys the same rule as a non-empty one. This inverts the
  // behaviour deps.test.ts used to pin, and resolves the open choice recorded
  // in docs/specs/0005-typed-engine-report-seam.md §2.2: the empty case no
  // longer hard-codes both keys. The key set now depends only on --mode, which
  // the caller chose, instead of on data the caller cannot predict.
  const emptyCases = [
    { checkedVersions: true, checkedLockfile: false, expected: { version_bumps: [] } },
    { checkedVersions: false, checkedLockfile: true, expected: { lockfile_stale: [] } },
    {
      checkedVersions: true,
      checkedLockfile: true,
      expected: { version_bumps: [], lockfile_stale: [] },
    },
  ];

  for (const { checkedVersions, checkedLockfile, expected } of emptyCases) {
    test(`an empty report emits only the keys it checked (${checkedVersions}/${checkedLockfile})`, () => {
      const rendered = renderUpgradeReport(report({ checkedVersions, checkedLockfile }), "json");

      expect(JSON.parse(rendered)).toEqual(expected);
      expect(rendered).not.toContain("helper_provided");
    });
  }

  test("no keys checked renders an empty object", () => {
    expect(renderUpgradeReport(report(), "json")).toBe("{}\n");
  });
});

// ---- the empty report, per format ----

describe("renderUpgradeReport() empty report", () => {
  test("text says everything is up to date", () => {
    expect(renderUpgradeReport(report(), "text")).toBe("Everything is up to date.\n");
  });

  test("pr-body is the bare header", () => {
    expect(renderUpgradeReport(report(), "pr-body")).toBe("## ghagen dependency update\n");
  });

  test("issue-body is empty", () => {
    expect(renderUpgradeReport(report(), "issue-body")).toBe("");
  });
});

// ---- the interface ----

describe("renderUpgradeReport() interface", () => {
  // The caller writes the result verbatim, so it must self-terminate.
  test("every format is terminated as it must be written", () => {
    const r = fullReport();
    for (const format of ALL_FORMATS) {
      const rendered = renderUpgradeReport(r, format);
      expect(rendered.endsWith("\n"), format).toBe(true);
      expect(rendered.endsWith("\n\n\n"), format).toBe(false);
    }
  });

  test("an unknown format is a programmer error", () => {
    expect(() => renderUpgradeReport(report(), "yaml" as UpgradeFormat)).toThrow(
      /unknown output format/,
    );
  });

  // Pure: rendering must not mutate its input.
  test("renders without touching the report", () => {
    const r = fullReport();
    const before = [r.versionBumps.length, r.lockfileStale.length];

    for (const format of ALL_FORMATS) {
      renderUpgradeReport(r, format);
    }

    expect([r.versionBumps.length, r.lockfileStale.length]).toEqual(before);
  });
});
