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

  /** Whether to write newer version tags back into the user source files. */
  applyVersionBumps: boolean;

  /**
   * Whether to re-resolve the lockfile.
   *
   * `false` when the app has no lockfile configured, whatever the report says
   * — `ghagen deps pin` exits 1 on such a project, and the report's
   * `checkedLockfile` stays `true` there because it records what the run was
   * *asked* for, not what it ran.
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
  /** What the caller wants raised when there is something to raise. */
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
  const applyVersionBumps = report.versionBumps.length > 0;

  const refreshLockfile =
    // The fact the payload drops: `deps pin` exits 1 on a project with no
    // lockfile, so a cascade into it is not "harmless extra work".
    app.lockfilePath !== null &&
    // Read, never re-derived from `--mode`. Load-bearing only in this rule: an
    // empty `lockfileStale` cannot distinguish "the stage ran and found
    // nothing" from "the stage was not asked for", and the cascade clause
    // below fires on version bumps alone.
    report.checkedLockfile &&
    (report.lockfileStale.length > 0 || applyVersionBumps);

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
