/**
 * Decide what a caller should *do* about an {@link UpgradeReport}.
 *
 * Sibling of `pin/render.ts`, and the same shape of module: pure, no network,
 * no filesystem, no console I/O. `render` answers "what bytes do I write?";
 * `plan` answers "what do I do next?".
 *
 * The distinction matters because the two questions need different inputs. A
 * renderer needs only the report. A decision needs the report **and** the
 * {@link App}, because one of the three rules turns on a fact the serialized
 * report deliberately does not carry: whether the project has a lockfile at
 * all. Any consumer that reconstructs these decisions from
 * `deps upgrade --format json` is missing that fact and will get the lockfile
 * rule wrong — which is exactly what the shipped `check-deps` action did.
 */

import type { App } from "../app.js";
import type { UpgradeReport } from "./engine.js";

/** The commit subject (and PR title) an update run produces, before prefixing. */
const BASE_MESSAGE = "update ghagen action dependencies";

/** What the caller should raise, if anything. */
export type UpdateAction = "none" | "create-pr" | "create-issue";

/** Which of the two the caller asked for when there *is* something to raise. */
export type UpdateOutput = "pr" | "issue";

/**
 * What a caller should do about an {@link UpgradeReport}.
 *
 * Every field is a decision, not data: a caller reads them and acts, and never
 * re-derives one from another. In particular `refreshLockfile` is **not**
 * `report.lockfileStale.length > 0` and cannot be computed from the report
 * alone.
 */
export interface UpdatePlan {
  /** `none` when there is nothing to do; otherwise what to raise. */
  action: UpdateAction;

  /** Version bumps plus stale lockfile entries. */
  totalUpdates: number;

  /**
   * Whether to write newer version tags back into the user source files.
   *
   * `false` whenever `output === "issue"`: an issue reports pending work, it
   * does not perform it, so no write happens for either output. See
   * `refreshLockfile` for the same rule applied to the lockfile.
   */
  applyVersionBumps: boolean;

  /**
   * Whether to re-resolve the lockfile.
   *
   * `false` when the app has no lockfile configured, whatever the report says
   * — `ghagen deps pin` exits 1 on such a project, and the report's
   * `checkedLockfile` stays `true` there because it records what the run was
   * *asked* for, not what it ran. Also `false` whenever `output === "issue"`,
   * for the same reason as `applyVersionBumps`.
   */
  refreshLockfile: boolean;

  /** The dated branch to push, or `""` unless `action === "create-pr"`. */
  branch: string;

  /** The PR or issue title. */
  title: string;

  /** The commit subject, with the caller's prefix already applied. */
  commitMessage: string;

  /** Labels, already split on commas and trimmed; blanks dropped. */
  labels: string[];

  /**
   * Which `pin/render.ts` format to render the body in.
   *
   * `null` when `action === "none"`, i.e. when there is no body to render.
   * The plan carries the *format*, not the body: rendering needs the report,
   * which the caller already holds, and keeping bytes off the plan is what
   * lets a GitHub Actions consumer pass the body by file path rather than
   * through the multiline-output delimiter dance.
   */
  bodyFormat: "pr-body" | "issue-body" | null;
}

/** Everything the caller chose, as opposed to everything the run found. */
export interface PlanUpdateOptions {
  /**
   * What the caller wants raised when there is something to raise.
   *
   * Also decides whether anything gets written: `"issue"` implies
   * `applyVersionBumps` and `refreshLockfile` are both `false`, since an
   * issue reports pending work rather than performing it.
   */
  output: UpdateOutput;
  /** Prefix for the dated PR branch, e.g. `ghagen-update/`. */
  branchPrefix: string;
  /**
   * Optional prefix for the commit subject, e.g. `chore(deps):`. Trimmed; an
   * empty prefix leaves no leading space.
   */
  commitMessagePrefix: string;
  /**
   * Comma-separated labels, exactly as a GitHub Actions input hands them over.
   * Split and trimmed here so no caller has to.
   */
  labels: string;
  /** The date to stamp the branch name and issue title with. */
  today: Date;
}

/**
 * Decide what to do about `report`, given `app`'s configuration.
 *
 * Pure. No network, no filesystem, no clock: `today` is injected so the dated
 * branch name and issue title are testable without freezing time, the same
 * reasoning ADR-0002 applies to construction-time config globals.
 *
 * `app` is read for exactly one fact — `app.lockfilePath` — which is the fact
 * a serialized report cannot supply.
 */
export function planUpdate(
  app: App,
  report: UpgradeReport,
  options: PlanUpdateOptions,
): UpdatePlan {
  const totalUpdates = report.versionBumps.length + report.lockfileStale.length;

  // No `mode` reference anywhere in this function. `upgrade()` guarantees
  // `versionBumps` is empty unless the versions stage ran, so the flag adds
  // nothing here — reading it would make this a fresh derivation site for a
  // fact the report already encodes structurally.
  //
  // Gated on `output === "pr"`: an issue *describes* pending work, it does
  // not perform it, so `--output issue` writes nothing — no version bumps,
  // no lockfile refresh. This is a decision, computed the same way whether or
  // not the caller passed `--dry-run`; the CLI is what turns "would apply"
  // into "did apply" by additionally gating on `!dryRun`.
  const applyVersionBumps = options.output === "pr" && report.versionBumps.length > 0;

  const refreshLockfile =
    options.output === "pr" &&
    // The fact the payload drops: `deps pin` exits 1 on a project with no
    // lockfile, so a cascade into it is not "harmless extra work".
    app.lockfilePath !== null &&
    // A new version tag needs a lockfile entry whichever stage found it. This
    // clause is deliberately *not* gated on `checkedLockfile`: `--mode
    // versions` skips the lockfile stage, but it still rewrites `@v4` to `@v7`
    // in user source, and a lockfile that only knows `@v4` makes the very next
    // `ghagen synth` raise `PinError: No lockfile entry`. `mode` is a
    // documented action input with `versions` among its values, so that tree
    // is reachable by any consumer.
    (report.versionBumps.length > 0 ||
      // Read, never re-derived from `--mode`. Load-bearing only here: an empty
      // `lockfileStale` cannot distinguish "the stage ran and found nothing"
      // from "the stage was not asked for", so without this the rule could not
      // tell a clean lockfile from an unexamined one.
      (report.checkedLockfile && report.lockfileStale.length > 0));

  const action: UpdateAction =
    totalUpdates === 0 ? "none" : options.output === "pr" ? "create-pr" : "create-issue";

  const prefix = options.commitMessagePrefix.trim();
  const commitMessage = prefix ? `${prefix} ${BASE_MESSAGE}` : BASE_MESSAGE;

  const title =
    options.output === "pr"
      ? commitMessage
      : `ghagen dependency updates available (${isoDate(options.today)})`;

  const bodyFormat =
    action === "create-pr" ? "pr-body" : action === "create-issue" ? "issue-body" : null;

  return {
    action,
    totalUpdates,
    applyVersionBumps,
    refreshLockfile,
    branch: action === "create-pr" ? `${options.branchPrefix}${compactDate(options.today)}` : "",
    title,
    commitMessage,
    labels: parseLabels(options.labels),
    bodyFormat,
  };
}

/**
 * Split a comma-separated label input, trimming and dropping blanks.
 *
 * Exported because it is the whole of what a caller would otherwise reproduce
 * in shell, and because {@link UpdatePlan.labels} is the only place the result
 * is observable.
 */
export function parseLabels(labels: string): string[] {
  return labels
    .split(",")
    .map((part) => part.trim())
    .filter((part) => part.length > 0);
}

/** The wire shapes {@link renderUpdatePlan} can produce. */
export type PlanFormat = "json" | "github";

/** One field of a serialized plan, before it is encoded. */
type PlanValue = string | number | boolean | string[] | null;

/**
 * Render an {@link UpdatePlan} as the exact bytes to write.
 *
 * Two encodings of one shape, built from a single mapping so a field can never
 * appear in one and not the other. As in `pin/render.ts`, the result is already
 * terminated as it should be written: the caller writes it verbatim and neither
 * adds nor suppresses a trailing newline.
 *
 * `github` is the `key=value` form appended to `$GITHUB_OUTPUT`. It is
 * single-line per field by construction — every value is a boolean, a number,
 * or a string the CLI has already rejected newlines in — so it needs none of
 * the heredoc-delimiter machinery multiline outputs require.
 *
 * Keys are snake_case in both encodings, unlike the camelCase interface: they
 * are a cross-port wire contract shared byte for byte with the Python
 * `render_update_plan`, and the composite action's `outputs:` block names them.
 *
 * @param plan - The decision to serialize.
 * @param changed - Whether the run actually wrote to the working tree. Not a
 *   field of the plan: the plan is what to do, this is what happened, and only
 *   the caller that did it knows.
 * @param outputFormat - Positional, matching `renderUpgradeReport`. An
 *   unrecognised value is a programmer error — the CLI validates `--format`
 *   before calling.
 * @throws Error if `outputFormat` is not a known format.
 */
export function renderUpdatePlan(
  plan: UpdatePlan,
  changed: boolean,
  outputFormat: PlanFormat = "github",
): string {
  const fields = planFields(plan, changed);
  if (outputFormat === "json") {
    return `${JSON.stringify(Object.fromEntries(fields), null, 2)}\n`;
  }
  if (outputFormat === "github") {
    return fields.map(([key, value]) => `${key}=${githubValue(value)}\n`).join("");
  }
  throw new Error(`unknown output format ${JSON.stringify(outputFormat)}`);
}

/** The one field list both encodings walk, in one order. */
function planFields(plan: UpdatePlan, changed: boolean): [string, PlanValue][] {
  return [
    ["action", plan.action],
    ["total_updates", plan.totalUpdates],
    ["apply_version_bumps", plan.applyVersionBumps],
    ["refresh_lockfile", plan.refreshLockfile],
    ["branch", plan.branch],
    ["title", plan.title],
    ["commit_message", plan.commitMessage],
    ["labels", plan.labels],
    ["body_format", plan.bodyFormat],
    ["changed", changed],
  ];
}

/**
 * Scalarize one field for a `key=value` line.
 *
 * `null` becomes empty, which is the only thing a composite output can be when
 * there is no value.
 */
function githubValue(value: PlanValue): string {
  if (value === null) {
    return "";
  }
  if (Array.isArray(value)) {
    return value.join(",");
  }
  return String(value);
}

/**
 * `YYYY-MM-DD` in UTC.
 *
 * UTC rather than local time on purpose: the branch name and the issue title
 * are compared across runs and across machines, and a runner in a negative
 * offset must not disagree with one in a positive offset about what day it is.
 */
function isoDate(day: Date): string {
  return day.toISOString().slice(0, 10);
}

/** `YYYYMMDD` in UTC — the branch-name spelling of {@link isoDate}. */
function compactDate(day: Date): string {
  return isoDate(day).replaceAll("-", "");
}
