/**
 * Turn an {@link UpgradeReport} into the bytes to write.
 *
 * Pure: no console I/O, no CLI types, no exceptions on well-formed input. The
 * CLI keeps sole ownership of *which stream* each piece of output goes to and
 * of exit codes (ADR-0007); this module owns *what the bytes are*.
 *
 * Everything a caller used to have to know about producing `deps upgrade`
 * output lives here now: the four formats and their exact bytes, the
 * trailing-newline discipline, the empty-report shape per format, and the
 * mapping from "what the engine looked for" to "which JSON keys appear".
 */

import type { LockfileStaleEntry, UpgradeReport, VersionBump } from "./engine.js";

/** The output shapes {@link renderUpgradeReport} can produce. */
export type UpgradeFormat = "text" | "json" | "pr-body" | "issue-body";

/**
 * Render an upgrade report, returning the exact bytes to write.
 *
 * Pure: no console I/O, no CLI types. The returned string is already
 * terminated as it should be written — the caller writes it verbatim and
 * neither adds nor suppresses a trailing newline.
 *
 * Which JSON keys appear is decided by `report.checkedVersions` /
 * `report.checkedLockfile`, never re-derived from the CLI's `--mode`. That
 * holds for empty reports too: a run asked only for version tags emits only
 * `version_bumps`, whether or not it found any.
 *
 * @param report - The typed outcome of an {@link upgrade} run.
 * @param outputFormat - One of {@link UpgradeFormat}. An unrecognised value is
 *   a programmer error — the CLI validates `--format` before calling.
 * @throws Error if `outputFormat` is not a known format.
 */
export function renderUpgradeReport(
  report: UpgradeReport,
  outputFormat: UpgradeFormat = "text",
): string {
  switch (outputFormat) {
    case "json":
      return renderJson(report);
    case "pr-body":
      return renderPrBody(report.versionBumps, report.lockfileStale);
    case "issue-body":
      return renderIssueBody(report.versionBumps, report.lockfileStale);
    case "text":
      return renderText(report.versionBumps, report.lockfileStale);
    default: {
      const unknown: never = outputFormat;
      throw new Error(`unknown output format ${JSON.stringify(unknown)}`);
    }
  }
}

/**
 * Render `--format json`, keyed by what the run was asked to check.
 *
 * Key presence follows `checkedVersions` / `checkedLockfile` in *all* cases,
 * empty included. This resolves the open choice recorded in
 * `docs/specs/0005-typed-engine-report-seam.md` §2.2 the other way: the key set
 * now depends only on `--mode`, which the caller chose, and not on whether the
 * run happened to find anything.
 */
function renderJson(report: UpgradeReport): string {
  const result: {
    version_bumps?: Array<Record<string, unknown>>;
    lockfile_stale?: Array<Record<string, unknown>>;
  } = {};
  if (report.checkedVersions) {
    result.version_bumps = report.versionBumps.map(bumpToJson);
  }
  if (report.checkedLockfile) {
    result.lockfile_stale = report.lockfileStale.map(staleToJson);
  }
  return JSON.stringify(result, null, 2) + "\n";
}

/** Serialize a version bump for `--format json` (omitting empty `source_files`). */
function bumpToJson(bump: VersionBump): Record<string, unknown> {
  const entry: Record<string, unknown> = {
    uses: bump.uses,
    current: bump.current,
    latest: bump.latest,
    severity: bump.severity,
  };
  if (bump.source_files.length > 0) {
    entry.source_files = [...bump.source_files];
  }
  return entry;
}

/** Serialize a stale entry for `--format json` (omitting empty `source_files`). */
function staleToJson(stale: LockfileStaleEntry): Record<string, unknown> {
  const entry: Record<string, unknown> = {
    uses: stale.uses,
    current_sha: stale.current_sha,
    latest_sha: stale.latest_sha,
  };
  if (stale.source_files.length > 0) {
    entry.source_files = [...stale.source_files];
  }
  return entry;
}

/**
 * Render the pull-request body markdown for an upgrade report.
 *
 * Golden-file tested against `fixtures/expected/upgrade_pr_body.md` and kept
 * byte-identical with the Python port's `_render_pr_body`. An empty report
 * yields the bare header.
 */
function renderPrBody(versionBumps: VersionBump[], lockfileStale: LockfileStaleEntry[]): string {
  const lines: string[] = ["## ghagen dependency update", ""];

  if (versionBumps.length > 0) {
    lines.push("### Version bumps", "");
    for (const bump of versionBumps) {
      lines.push(`- \`${bump.uses}\` -> \`${bump.latest}\` [${bump.severity}]`);
    }
    lines.push("");
  }

  if (lockfileStale.length > 0) {
    lines.push("### Lockfile maintenance", "");
    for (const entry of lockfileStale) {
      lines.push(`- \`${entry.uses}\` SHA refreshed`);
    }
    lines.push("");
  }

  return lines.join("\n");
}

/**
 * Render the issue body markdown for an upgrade report.
 *
 * Golden-file tested against `fixtures/expected/upgrade_issue_body.md` and kept
 * byte-identical with the Python port's `_render_issue_body`. An empty report
 * yields the empty string.
 */
function renderIssueBody(versionBumps: VersionBump[], lockfileStale: LockfileStaleEntry[]): string {
  const lines: string[] = [];

  if (versionBumps.length > 0) {
    lines.push("## Version updates available", "");
    for (const bump of versionBumps) {
      let line = `- [ ] \`${bump.uses}\` -> \`${bump.latest}\` [${bump.severity}]`;
      if (bump.source_files.length > 0) {
        const files = bump.source_files.map((f) => `\`${f}\``).join(", ");
        line += `  in ${files}`;
      }
      lines.push(line);
    }
    lines.push("");
  }

  if (lockfileStale.length > 0) {
    lines.push("## Stale lockfile entries", "");
    lines.push("Run `ghagen deps pin --update` to refresh.", "");
    for (const entry of lockfileStale) {
      lines.push(`- [ ] \`${entry.uses}\` — SHA changed`);
    }
    lines.push("");
  }

  return lines.join("\n");
}

/**
 * Render the default human-readable report.
 *
 * Golden-file tested against `fixtures/expected/upgrade_text.txt` and kept
 * byte-identical with the Python port's `_render_text`. A report with nothing
 * to say yields the up-to-date line rather than the empty string — this is the
 * one format whose empty case has words in it.
 */
function renderText(versionBumps: VersionBump[], lockfileStale: LockfileStaleEntry[]): string {
  const lines: string[] = [];

  if (versionBumps.length > 0) {
    lines.push("Version updates available:", "");
    for (const bump of versionBumps) {
      lines.push(`  ${bump.uses}  →  ${bump.latest}  [${bump.severity}]`);
      for (const src of bump.source_files) {
        lines.push(`    in ${src}`);
      }
    }
    lines.push("");
  }

  if (lockfileStale.length > 0) {
    lines.push("Stale lockfile entries:", "");
    for (const entry of lockfileStale) {
      lines.push(`  ${entry.uses}`);
      lines.push(`    current SHA: ${entry.current_sha.slice(0, 12)}...`);
      lines.push(`    latest SHA:  ${entry.latest_sha.slice(0, 12)}...`);
    }
    lines.push("");
  }

  if (lines.length === 0) {
    return "Everything is up to date.\n";
  }

  return lines.map((line) => `${line}\n`).join("");
}
