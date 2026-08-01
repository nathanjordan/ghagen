/**
 * Pin engine — pin / check-sync / upgrade orchestration returning typed reports.
 *
 * Lifts the pin/upgrade/check-synced logic out of the commander handlers so it
 * is unit-testable without the CLI. Each function takes the loaded {@link App}
 * (and, for the networked operations, an injected {@link GitHubClient}) and
 * returns a typed report. The engine performs its own side effects — writing
 * the lockfile in {@link pin}, mutating source files in {@link upgrade} when
 * `apply` is set — but does no console I/O: messages are collected into
 * `report.warnings` / `report.errors` for the CLI to render.
 */

import { resolve } from "node:path";
import type { App } from "../app.js";
import { collectUsesRefs } from "./collect.js";
import { ResolveError, type GitHubClient } from "./github.js";
import { readLockfile, writeLockfile } from "./lockfile.js";
import { locateUsesRefs } from "./sources.js";
import { applyUpdates } from "./update.js";
import type { UsesRef } from "./uses.js";
import { type BumpSeverity, latestBump } from "./versions.js";

// ---- pin ----

/** A single `uses:` ref newly resolved to a commit SHA. */
export interface ResolvedPin {
  uses: string;
  sha: string;
}

/** Outcome of a {@link pin} run. */
export interface PinReport {
  /** Refs newly resolved to SHAs (in sorted processing order). */
  resolved: ResolvedPin[];
  /** Human messages for refs that failed to resolve (`"uses: reason"`). */
  errors: string[];
  /** Non-fatal warnings (e.g. a ref skipped as unpinnable). */
  warnings: string[];
  /** Number of stale entries removed from the lockfile. */
  pruned: number;
  /** Whether the lockfile was written to disk. */
  written: boolean;
  /** Absolute path of the lockfile the report targets. */
  lockfilePath: string;
  /** True when nothing needed resolving and nothing was pruned. */
  upToDate: boolean;
}

export interface PinOptions {
  update: boolean;
  prune: boolean;
}

/**
 * Resolve `uses:` refs to commit SHAs and merge them into the lockfile.
 *
 * By default only unpinned refs are resolved; `update` re-resolves all of
 * them. Stale entries no longer referenced in code are pruned when `prune`
 * is set. The lockfile is written when anything changed.
 */
export async function pin(app: App, client: GitHubClient, opts: PinOptions): Promise<PinReport> {
  if (app.lockfilePath === null) {
    throw new Error("pin(): app has no lockfile (lockfilePath: null)");
  }
  const lockfilePath = resolve(app.rootAbsPath, app.lockfilePath);

  const report: PinReport = {
    resolved: [],
    errors: [],
    warnings: [],
    pruned: 0,
    written: false,
    lockfilePath,
    upToDate: false,
  };

  const refs = collectUsesRefs(app);
  const lockfile = readLockfile(lockfilePath);

  // `refs` is already sorted and parsed by `collectUsesRefs`; iterate directly.
  const toResolve = opts.update ? refs : refs.filter((r) => !lockfile.has(r.uses));

  const now = new Date();
  for (const ref of toResolve) {
    let sha: string;
    try {
      sha = await client.resolveRef(ref.owner, ref.repo, ref.ref);
    } catch (err) {
      if (err instanceof ResolveError) {
        report.errors.push(`${ref.uses}: ${err.message}`);
        continue;
      }
      throw err;
    }
    lockfile.set(ref.uses, { sha, resolvedAt: now });
    report.resolved.push({ uses: ref.uses, sha });
  }

  if (opts.prune) {
    report.pruned = lockfile.prune(new Set(refs.map((r) => r.uses)));
  }

  if (report.resolved.length > 0 || report.pruned > 0) {
    writeLockfile(lockfile, lockfilePath);
    report.written = true;
  }

  report.upToDate = toResolve.length === 0 && report.pruned === 0;
  return report;
}

// ---- check-sync ----

/** Outcome of a {@link checkSync} run (sorted lists). */
export class SyncReport {
  constructor(
    /** Refs referenced in code but absent from the lockfile. */
    readonly missing: string[],
    /** Lockfile entries no longer referenced in code (empty when not pruning). */
    readonly extra: string[],
  ) {}

  /** True when there is nothing missing and nothing extra. */
  get inSync(): boolean {
    return this.missing.length === 0 && this.extra.length === 0;
  }
}

export interface CheckSyncOptions {
  prune: boolean;
}

/**
 * Compare the lockfile against the app's refs — pure, no network.
 *
 * Returns the sorted `missing` / `extra` sets. `extra` is only computed when
 * `prune` is set (matching the CLI's `--no-prune`).
 */
export function checkSync(app: App, opts: CheckSyncOptions): SyncReport {
  if (app.lockfilePath === null) {
    throw new Error("checkSync(): app has no lockfile (lockfilePath: null)");
  }
  const lockfilePath = resolve(app.rootAbsPath, app.lockfilePath);

  const refs = collectUsesRefs(app);
  const lockfile = readLockfile(lockfilePath);
  const usesSet = new Set(refs.map((r) => r.uses));

  const missing = refs
    .map((r) => r.uses)
    .filter((uses) => !lockfile.has(uses))
    .sort();
  const extra = opts.prune ? [...lockfile.keys()].filter((r) => !usesSet.has(r)).sort() : [];
  return new SyncReport(missing, extra);
}

// ---- upgrade ----

/** A newer version tag available for a `uses:` ref. */
export interface VersionBump {
  uses: string;
  current: string;
  latest: string;
  severity: BumpSeverity;
  /** User source files the ref appears in (empty when none were found). */
  source_files: string[];
}

/** A pinned ref whose lockfile SHA no longer matches its ref. */
export interface LockfileStaleEntry {
  uses: string;
  current_sha: string;
  latest_sha: string;
  /** User source files the ref appears in (empty when none were found). */
  source_files: string[];
}

/** Outcome of an {@link upgrade} run. */
export interface UpgradeReport {
  versionBumps: VersionBump[];
  lockfileStale: LockfileStaleEntry[];
  changedFiles: string[];
  warnings: string[];
}

export interface UpgradeOptions {
  mode: "versions" | "lockfile" | "all";
  apply: boolean;
}

/**
 * Detect available upgrades and optionally apply version bumps.
 *
 * Depending on `mode`, detects newer version tags (`versions`), stale lockfile
 * SHAs (`lockfile`), or both (`all`). When `apply` is set, version bumps are
 * written back into the user source files identified by `userFiles`; the
 * changed files are recorded on the report.
 */
export async function upgrade(
  app: App,
  client: GitHubClient,
  userFiles: ReadonlySet<string>,
  opts: UpgradeOptions,
): Promise<UpgradeReport> {
  const report: UpgradeReport = {
    versionBumps: [],
    lockfileStale: [],
    changedFiles: [],
    warnings: [],
  };

  const refs = collectUsesRefs(app);
  if (refs.length === 0) {
    return report;
  }

  const refLocations = locateUsesRefs(new Set(refs.map((r) => r.uses)), userFiles);

  const checkVersions = opts.mode === "versions" || opts.mode === "all";
  const checkLockfile = opts.mode === "lockfile" || opts.mode === "all";

  if (checkVersions) {
    // Group refs by owner/repo for efficient API calls — parsing is free, so
    // grouping is a cheap local step over the already-parsed refs.
    const repoRefs = new Map<string, UsesRef[]>();
    for (const ref of refs) {
      const key = `${ref.owner}/${ref.repo}`;
      const list = repoRefs.get(key) ?? [];
      list.push(ref);
      repoRefs.set(key, list);
    }

    // One `listTags` call per repo — the grouping above is what deduplicates,
    // so no cache is involved.
    for (const [key, repoRefList] of [...repoRefs.entries()].sort(([a], [b]) =>
      a.localeCompare(b),
    )) {
      const [owner, repo] = key.split("/", 2) as [string, string];
      let tags: string[];
      try {
        tags = await client.listTags(owner, repo);
      } catch (err) {
        if (err instanceof ResolveError) {
          report.warnings.push(`failed to list tags for ${key}: ${err.message}`);
          continue;
        }
        throw err;
      }

      for (const ref of repoRefList) {
        const bump = latestBump(ref.ref, tags);
        if (bump === null) {
          continue; // not a version tag, or already the latest
        }
        report.versionBumps.push({
          uses: ref.uses,
          current: ref.ref,
          latest: bump.latest.tag,
          severity: bump.severity,
          source_files: [...(refLocations.get(ref.uses) ?? [])],
        });
      }
    }
  }

  if (checkLockfile && app.lockfilePath !== null) {
    const lockfile = readLockfile(resolve(app.rootAbsPath, app.lockfilePath));
    for (const ref of refs) {
      const entry = lockfile.get(ref.uses);
      if (entry === undefined) {
        continue;
      }
      let currentSha: string;
      try {
        currentSha = await client.resolveRef(ref.owner, ref.repo, ref.ref);
      } catch (err) {
        if (err instanceof ResolveError) {
          report.warnings.push(`failed to resolve ${ref.uses}: ${err.message}`);
          continue;
        }
        throw err;
      }
      if (currentSha !== entry.sha) {
        report.lockfileStale.push({
          uses: ref.uses,
          current_sha: entry.sha,
          latest_sha: currentSha,
          source_files: [...(refLocations.get(ref.uses) ?? [])],
        });
      }
    }
  }

  if (opts.apply && report.versionBumps.length > 0) {
    const refsByUses = new Map(refs.map((r) => [r.uses, r] as const));
    const updates = new Map<string, string>();
    for (const bump of report.versionBumps) {
      const ref = refsByUses.get(bump.uses)!;
      updates.set(bump.uses, ref.withSha(bump.latest));
    }
    const refLocsObj = new Map<string, string[]>();
    for (const [k, v] of refLocations.entries()) {
      refLocsObj.set(k, [...v]);
    }
    report.changedFiles = applyUpdates(updates, refLocsObj);
  }

  return report;
}
