/**
 * Decision-table tests for `pin/plan.ts` — the mirror of the Python
 * `tests/test_pin/test_plan.py`, driven by the same table in the same order.
 *
 * Offline and hermetic: every case hand-builds an app-shaped object and an
 * `UpgradeReport` literal, so nothing here reaches the network or the
 * filesystem. `planUpdate` reads exactly one field off the app, so a structural
 * stand-in is honest here — it is the whole of the contract.
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, test } from "vitest";
import { parse as parseYaml } from "yaml";
import type { App } from "../app.js";
import { EXPECTED_DIR, SCHEMA_DIR } from "../paths.js";
import type { LockfileStaleEntry, UpgradeReport, VersionBump } from "./engine.js";
import { type UpdatePlan, planUpdate, parseLabels, renderUpdatePlan } from "./plan.js";

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

// docs/issues/23 item 2 also names the plan output as reachable.
// `renderUpdatePlan`'s `json` branch was already correct here (JSON.stringify
// never \uXXXX-escapes non-ASCII); the Python peer's `render_update_plan`
// needed the same `ensure_ascii=False` fix as `render_upgrade_report` (see
// `pin/render.py`'s golden-fixture test for the primary oracle). This pins
// the same fact at its own call site with a direct, byte-exact assertion
// rather than a fixture file, since the two call sites share one line of
// code and one rationale.
describe("renderUpdatePlan json format non-ASCII", () => {
  test("does not escape non-ASCII", () => {
    const updatePlan: UpdatePlan = {
      action: "create-pr",
      totalUpdates: 1,
      applyVersionBumps: true,
      refreshLockfile: false,
      branch: "ghagen-update/2026-07-31",
      title: "update ghagen action dependencies",
      commitMessage: "update ghágen action dependencies",
      labels: [],
      bodyFormat: "pr-body",
    };

    const rendered = renderUpdatePlan(updatePlan, true, "json");

    expect(rendered).toContain("ghágen");
    expect(rendered).not.toContain("\\u");
  });
});

// ---------------------------------------------------------------------------
// The shared plan-field table: order, type, and encoding
// ---------------------------------------------------------------------------

/** One row of `schema/update-plan-fields.yml`. */
interface PlanFieldRow {
  name: string;
  json: "string" | "integer" | "boolean" | "string-array";
  github: "verbatim" | "decimal" | "lowercase-bool" | "comma-joined";
  null_when?: { field: string; equals: string };
}

/**
 * `schema/update-plan-fields.yml`, whole — names, order, JSON type, and
 * `$GITHUB_OUTPUT` encoding, one row per field.
 *
 * The name and order axes are also driven from `src/cli/deps.test.ts` against a
 * live invocation. The type and encoding axes are driven here instead, because
 * they need *two* plans — one with `action === "none"` and one without — to say
 * anything about `body_format`'s conditional null, and an `action === "none"`
 * run is not reachable from the CLI suite's fixtures without a second mocked
 * project. `planUpdate` is pure, so both are one line each here.
 *
 * The Python mirror is `tests/test_pin/test_plan.py`; corrupting one row of the
 * shared file fails both.
 */
const FIELD_TABLE: PlanFieldRow[] = (
  parseYaml(readFileSync(resolve(SCHEMA_DIR, "update-plan-fields.yml"), "utf8")) as {
    fields: PlanFieldRow[];
  }
).fields;

/** Whether `value` is the JSON type the table declares. */
function jsonTypeHolds(value: unknown, declared: PlanFieldRow["json"]): boolean {
  switch (declared) {
    case "string":
      return typeof value === "string";
    case "integer":
      return typeof value === "number" && Number.isInteger(value);
    case "boolean":
      return typeof value === "boolean";
    case "string-array":
      return Array.isArray(value) && value.every((x) => typeof x === "string");
  }
}

/** The `key=` right-hand side the table's encoding rule demands. */
function githubEncode(value: unknown, encoding: PlanFieldRow["github"]): string {
  if (value === null) {
    return "";
  }
  switch (encoding) {
    case "verbatim":
      return value as string;
    case "decimal":
      return String(value as number);
    case "lowercase-bool":
      return value ? "true" : "false";
    case "comma-joined":
      return (value as string[]).join(",");
  }
}

/** Parse a `--format github` render back into `key -> value`. */
function githubPairs(rendered: string): Record<string, string> {
  const entries = rendered
    .split("\n")
    .filter((line) => line.length > 0)
    .map((line) => {
      const at = line.indexOf("=");
      return [line.slice(0, at), line.slice(at + 1)] as const;
    });
  return Object.fromEntries(entries);
}

/** `[json document, github key=value mapping]` for one plan. */
function bothEncodings(
  p: UpdatePlan,
  changed: boolean,
): [Record<string, unknown>, Record<string, string>] {
  return [
    JSON.parse(renderUpdatePlan(p, changed, "json")) as Record<string, unknown>,
    githubPairs(renderUpdatePlan(p, changed, "github")),
  ];
}

/** A plan with every field at a non-degenerate value. */
function prPlan(): UpdatePlan {
  return plan(
    app(".ghagen.lock.yml"),
    report({
      versionBumps: [bump()],
      lockfileStale: [stale()],
      checkedVersions: true,
      checkedLockfile: true,
    }),
    { commitMessagePrefix: "chore(deps):", labels: " ci , deps ,, automated " },
  );
}

/** The one plan whose `body_format` is null. */
function nonePlan(): UpdatePlan {
  return plan(app(".ghagen.lock.yml"), report({ checkedVersions: true, checkedLockfile: true }));
}

/**
 * `schema/update-plan-fields.yml`, held to all three of its axes.
 *
 * Gap 1 of docs/issues/33: the shared file bound field *names* and nothing
 * else, so two ports emitting the same ten fields in two different orders, or
 * encoding `labels` as a list in one port and a comma-joined string in the
 * other, were both invisible to it.
 */
describe("the shared plan-field table", () => {
  test("the table is not empty", () => {
    // A zero-row table would make every case below vacuous.
    expect(FIELD_TABLE.length).toBeGreaterThan(0);
  });

  test("both encodings carry the table's fields in the table's order", () => {
    const names = FIELD_TABLE.map((field) => field.name);

    for (const p of [prPlan(), nonePlan()]) {
      const [asJson, asGithub] = bothEncodings(p, true);
      expect(Object.keys(asJson)).toEqual(names);
      expect(Object.keys(asGithub)).toEqual(names);
    }
  });

  test("every field has the declared JSON type", () => {
    for (const p of [prPlan(), nonePlan()]) {
      const [asJson] = bothEncodings(p, true);
      for (const field of FIELD_TABLE) {
        const value = asJson[field.name];
        // Legality of the null itself is the biconditional below.
        if (value === null) {
          continue;
        }
        expect(jsonTypeHolds(value, field.json), `${field.name}: ${String(value)}`).toBe(true);
      }
    }
  });

  test("every field encodes into github the declared way", () => {
    for (const p of [prPlan(), nonePlan()]) {
      const [asJson, asGithub] = bothEncodings(p, true);
      for (const field of FIELD_TABLE) {
        expect(asGithub[field.name], field.name).toBe(
          githubEncode(asJson[field.name], field.github),
        );
      }
    }
  });

  test("labels really does differ between the two encodings", () => {
    // The case above passes vacuously if no field exercises the difference.
    const [asJson, asGithub] = bothEncodings(prPlan(), true);

    expect(asJson["labels"]).toEqual(["ci", "deps", "automated"]);
    expect(asGithub["labels"]).toBe("ci,deps,automated");
  });

  test("null holds exactly where the table says it does", () => {
    // A biconditional, in both encodings, over both plans. `body_format`
    // carries `null_when: {field: action, equals: none}`; every other row
    // carries no `null_when` at all and is therefore never null. Asserting the
    // "only when" half is what stops a port from nulling `body_format` on some
    // other condition — say on `--output issue` — and still passing.
    for (const p of [prPlan(), nonePlan()]) {
      const [asJson, asGithub] = bothEncodings(p, true);
      for (const field of FIELD_TABLE) {
        const rule = field.null_when;
        const expectedNull = rule !== undefined && asJson[rule.field] === rule.equals;
        expect(asJson[field.name] === null, field.name).toBe(expectedNull);
        // A null renders as the empty string on the github side. Only the
        // forward direction: `branch` is legitimately `""` under
        // `action: none` without being null, so emptiness there is not
        // evidence of a null. The converse is covered by the encoding case
        // above, which pins every field's github form to its JSON value.
        if (expectedNull) {
          expect(asGithub[field.name], field.name).toBe("");
        }
      }
    }
  });
});

/**
 * `fixtures/expected/update_plan{.json,_github.txt}` — byte for byte.
 *
 * The table above binds the shape; these bind the bytes, and they are the
 * fixtures docs/issues/33 Gap 1 names. What they add over the table is the
 * serialization detail the table has no vocabulary for: the two-space JSON
 * indent, the one-element-per-line array, the trailing newline on both
 * renders, and the literal `key=value` line form — all of it shared with the
 * Python port, whose `tests/test_pin/test_plan.py` reads the same two files and
 * compares the same way.
 */
describe("renderUpdatePlan golden fixtures", () => {
  test("the json render matches the golden", () => {
    expect(renderUpdatePlan(prPlan(), true, "json")).toBe(
      readFileSync(resolve(EXPECTED_DIR, "update_plan.json"), "utf8"),
    );
  });

  test("the github render matches the golden", () => {
    expect(renderUpdatePlan(prPlan(), true, "github")).toBe(
      readFileSync(resolve(EXPECTED_DIR, "update_plan_github.txt"), "utf8"),
    );
  });
});
