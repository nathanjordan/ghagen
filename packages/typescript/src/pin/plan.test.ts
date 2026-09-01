/**
 * Decision-table tests for `pin/plan.ts` — the mirror of the Python
 * `tests/test_pin/test_plan.py`, driven by the same table in the same order.
 *
 * Offline and hermetic: every case hand-builds an app-shaped object and an
 * `UpgradeReport` literal, so nothing here reaches the network or the
 * filesystem. `planUpdate` reads exactly one field off the app, so a structural
 * stand-in is honest here — it is the whole of the contract.
 */

import { describe, expect, test } from "vitest";
import type { App } from "../app.js";
import type { LockfileStaleEntry, UpgradeReport, VersionBump } from "./engine.js";
import { type UpdatePlan, planUpdate, parseLabels } from "./plan.js";

const TODAY = new Date(Date.UTC(2026, 6, 31));

function app(lockfilePath: string | null): App {
  return { lockfilePath } as App;
}

function bump(): VersionBump {
  return {
    uses: "actions/checkout@v4",
    current: "v4",
    latest: "v6",
    severity: "major",
    source_files: [],
  };
}

function stale(): LockfileStaleEntry {
  return {
    uses: "actions/checkout@v4",
    current_sha: "0".repeat(40),
    latest_sha: "1".repeat(40),
    source_files: [],
  };
}

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

/** Call `planUpdate` with the shipped action's defaults for anything unnamed. */
function plan(
  a: App,
  r: UpgradeReport,
  overrides: Partial<Parameters<typeof planUpdate>[2]> = {},
): UpdatePlan {
  return planUpdate(a, r, {
    output: "pr",
    branchPrefix: "ghagen-update/",
    commitMessagePrefix: "",
    labels: "",
    today: TODAY,
    ...overrides,
  });
}

/**
 * H7 — the live defect: `lockfile: null` is a supported configuration.
 *
 * The shipped action reconstructs "refresh the lockfile?" from a serialized
 * report that deliberately does not carry `app.lockfilePath`, so it fires
 * `deps pin --update` on a project that has no lockfile and the command exits
 * 1. `planUpdate` holds the app, so it is the one place the question can be
 * answered.
 */
describe("planUpdate with the lockfile disabled", () => {
  test("a version bump does not cascade into a lockfile refresh", () => {
    const p = plan(
      app(null),
      report({ versionBumps: [bump()], checkedVersions: true, checkedLockfile: true }),
    );

    expect(p.refreshLockfile).toBe(false);
    expect(p.applyVersionBumps).toBe(true);
    expect(p.action).toBe("create-pr");
    expect(p.totalUpdates).toBe(1);
  });

  test("an empty report is still nothing to do", () => {
    const p = plan(app(null), report({ checkedVersions: true, checkedLockfile: true }));

    expect(p.action).toBe("none");
    expect(p.totalUpdates).toBe(0);
    expect(p.refreshLockfile).toBe(false);
  });
});

/** The cascade is correct when there *is* a lockfile to refresh. */
describe("planUpdate with a lockfile present", () => {
  // The inverse of what this used to assert, and the reason it changed.
  //
  // `--mode versions` skips the lockfile stage but still rewrites `@v4` to
  // `@v7` in user source. Declining to refresh there leaves a lockfile that
  // only knows `@v4` against source that says `@v7`, and the very next
  // `ghagen synth` raises `PinError: No lockfile entry`. `mode` is a
  // documented `check-deps` input with `versions` among its values, so that
  // tree is reachable by any consumer: the bump has to carry the refresh with
  // it, whichever stage found it.
  test("a bump refreshes even when the lockfile stage was skipped", () => {
    const p = plan(
      app(".ghagen.lock.yml"),
      report({ versionBumps: [bump()], checkedVersions: true, checkedLockfile: false }),
    );

    expect(p.refreshLockfile).toBe(true);
    expect(p.applyVersionBumps).toBe(true);
  });

  // The companion that keeps `checkedLockfile` load-bearing. With no bump to
  // cascade, an unexamined lockfile is still not a reason to re-resolve — an
  // empty `lockfileStale` cannot distinguish "ran, found nothing" from "was
  // not asked for", so dropping the flag from the predicate would fail here.
  test("a skipped lockfile stage alone never refreshes", () => {
    const p = plan(app(".ghagen.lock.yml"), report({ checkedVersions: true }));

    expect(p.refreshLockfile).toBe(false);
    expect(p.applyVersionBumps).toBe(false);
  });

  test("a version bump cascades when the stage ran", () => {
    const p = plan(
      app(".ghagen.lock.yml"),
      report({ versionBumps: [bump()], checkedVersions: true, checkedLockfile: true }),
    );

    expect(p.refreshLockfile).toBe(true);
    expect(p.applyVersionBumps).toBe(true);
  });

  test("a stale entry alone refreshes without applying bumps", () => {
    const p = plan(
      app(".ghagen.lock.yml"),
      report({ lockfileStale: [stale()], checkedVersions: true, checkedLockfile: true }),
    );

    expect(p.applyVersionBumps).toBe(false);
    expect(p.refreshLockfile).toBe(true);
    expect(p.totalUpdates).toBe(1);
  });
});

/** The stage-to-action mapping and the fields it gates. */
describe("planUpdate action mapping", () => {
  test("an empty report plans nothing", () => {
    const p = plan(
      app(".ghagen.lock.yml"),
      report({ checkedVersions: true, checkedLockfile: true }),
    );

    expect(p.action).toBe("none");
    expect(p.branch).toBe("");
    expect(p.bodyFormat).toBeNull();
  });

  test("a PR carries the dated branch and the pr-body format", () => {
    const p = plan(
      app(".ghagen.lock.yml"),
      report({ versionBumps: [bump()], checkedVersions: true }),
    );

    expect(p.action).toBe("create-pr");
    expect(p.branch).toBe("ghagen-update/20260731");
    expect(p.bodyFormat).toBe("pr-body");
    expect(p.title).toBe(p.commitMessage);
  });

  test("an issue has no branch and carries the injected date", () => {
    const p = plan(
      app(".ghagen.lock.yml"),
      report({ versionBumps: [bump()], checkedVersions: true }),
      { output: "issue" },
    );

    expect(p.action).toBe("create-issue");
    expect(p.branch).toBe("");
    expect(p.bodyFormat).toBe("issue-body");
    expect(p.title).toBe("ghagen dependency updates available (2026-07-31)");
  });

  test("totalUpdates sums both stages", () => {
    const p = plan(
      app(".ghagen.lock.yml"),
      report({
        versionBumps: [bump()],
        lockfileStale: [stale()],
        checkedVersions: true,
        checkedLockfile: true,
      }),
    );

    expect(p.totalUpdates).toBe(2);
  });
});

/**
 * Issue 20: `--output issue` writes nothing, even with plenty to report.
 *
 * `applyVersionBumps` and `refreshLockfile` gate the CLI's actual writes, so
 * they must be `false` for `output: "issue"` regardless of what the report
 * found — otherwise the plan would tell a caller "these were applied" for a
 * run that applied nothing.
 */
describe("planUpdate with output issue", () => {
  test("a version bump is not applied under issue output", () => {
    const p = plan(
      app(".ghagen.lock.yml"),
      report({ versionBumps: [bump()], checkedVersions: true, checkedLockfile: true }),
      { output: "issue" },
    );

    expect(p.applyVersionBumps).toBe(false);
    expect(p.refreshLockfile).toBe(false);
    expect(p.action).toBe("create-issue");
    expect(p.totalUpdates).toBe(1);
  });

  test("a stale lockfile entry is not refreshed under issue output", () => {
    const p = plan(
      app(".ghagen.lock.yml"),
      report({ lockfileStale: [stale()], checkedVersions: true, checkedLockfile: true }),
      { output: "issue" },
    );

    expect(p.applyVersionBumps).toBe(false);
    expect(p.refreshLockfile).toBe(false);
    expect(p.action).toBe("create-issue");
  });
});

/** The nine-line bash label loop, turned into assertions. */
describe("planUpdate label parsing", () => {
  const nonEmpty = () => report({ versionBumps: [bump()], checkedVersions: true });

  test("labels are split, trimmed, and blanks dropped", () => {
    expect(plan(app(null), nonEmpty(), { labels: " a , b ,, c " }).labels).toEqual(["a", "b", "c"]);
  });

  test("an empty label input yields no labels", () => {
    expect(plan(app(null), nonEmpty(), { labels: "" }).labels).toEqual([]);
    expect(plan(app(null), nonEmpty(), { labels: "  ,  " }).labels).toEqual([]);
  });

  test("parseLabels is the exported half of the same rule", () => {
    expect(parseLabels(" a , b ,, c ")).toEqual(["a", "b", "c"]);
    expect(parseLabels("")).toEqual([]);
  });
});

/** Prefixing, including the empty-prefix case the bash gets right. */
describe("planUpdate commit message", () => {
  const nonEmpty = () => report({ versionBumps: [bump()], checkedVersions: true });

  test("an empty prefix leaves no leading space", () => {
    expect(plan(app(null), nonEmpty(), { commitMessagePrefix: "" }).commitMessage).toBe(
      "update ghagen action dependencies",
    );
  });

  test("a prefix is separated by one space", () => {
    expect(plan(app(null), nonEmpty(), { commitMessagePrefix: "chore(deps):" }).commitMessage).toBe(
      "chore(deps): update ghagen action dependencies",
    );
  });

  test("a prefix is trimmed before joining", () => {
    expect(
      plan(app(null), nonEmpty(), { commitMessagePrefix: "  chore(deps):  " }).commitMessage,
    ).toBe("chore(deps): update ghagen action dependencies");
  });
});
