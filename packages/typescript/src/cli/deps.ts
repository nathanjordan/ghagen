/** ghagen deps — manage action dependencies. */

import { Command } from "commander";
import { resolve } from "node:path";
import type { App } from "../app.js";
import {
  collectUsesRefs,
  classifyBump,
  findLatestTag,
  listTags,
  parseTag,
  parseUses,
  readLockfile,
  ResolveError,
  resolveRef,
  trackUserFiles,
  locateUsesRefs,
  applyUpdates,
  writeLockfile,
} from "../pin/index.js";
import { CliError, findConfig, loadApp } from "./_common.js";

function resolveToken(flag?: string): string | undefined {
  return flag ?? process.env["GITHUB_TOKEN"] ?? process.env["GH_TOKEN"];
}

function ensureLockfilePath(app: App): string {
  if (app.lockfilePath === null) {
    throw new CliError(
      "Error: lockfile is disabled (lockfile: null on App)",
    );
  }
  return resolve(app.root, app.lockfilePath);
}

interface PinOpts {
  config?: string;
  update?: boolean;
  prune?: boolean;
  token?: string;
}

async function depsPin(opts: PinOpts): Promise<void> {
  const configPath = findConfig(opts.config);
  const app = await loadApp(configPath);

  const lockfilePath = ensureLockfilePath(app);
  const refs = collectUsesRefs(app);
  const lockfile = readLockfile(lockfilePath);

  const token = resolveToken(opts.token);
  if (!token) {
    process.stderr.write(
      "warning: no GitHub token found. Using unauthenticated requests " +
        "(60 req/hr limit). Set $GITHUB_TOKEN or use --token.\n",
    );
  }

  const toResolve = opts.update
    ? new Set(refs)
    : new Set([...refs].filter((r) => !lockfile.pins.has(r)));

  const now = new Date();
  let resolved = 0;
  let errors = 0;

  for (const uses of [...toResolve].sort()) {
    let parsed;
    try {
      parsed = parseUses(uses);
    } catch (err) {
      process.stderr.write(`warning: skipping ${JSON.stringify(uses)}: ${(err as Error).message}\n`);
      continue;
    }
    let sha: string;
    try {
      sha = await resolveRef(parsed.owner, parsed.repo, parsed.ref, { token });
    } catch (err) {
      if (err instanceof ResolveError) {
        process.stderr.write(`error: ${uses}: ${err.message}\n`);
        errors++;
        continue;
      }
      throw err;
    }
    lockfile.pins.set(uses, { sha, resolvedAt: now });
    resolved++;
    process.stdout.write(`  ${uses} → ${sha.slice(0, 12)}\n`);
  }

  let pruned = 0;
  if (opts.prune) {
    pruned = lockfile.prune(refs);
    if (pruned > 0) process.stdout.write(`Pruned ${pruned} stale entry/entries.\n`);
  }

  if (resolved > 0 || pruned > 0) {
    writeLockfile(lockfile, lockfilePath);
    process.stdout.write(`Wrote ${lockfilePath}\n`);
  }

  if (toResolve.size === 0 && pruned === 0) {
    process.stdout.write("Lockfile is already up to date.\n");
  }

  if (errors > 0) {
    throw new CliError(`${errors} ref(s) failed to resolve.`, 1);
  }
}

interface CheckSyncedOpts {
  config?: string;
  prune?: boolean;
}

async function depsCheckSynced(opts: CheckSyncedOpts): Promise<void> {
  const configPath = findConfig(opts.config);
  const app = await loadApp(configPath);

  const lockfilePath = ensureLockfilePath(app);
  const refs = collectUsesRefs(app);
  const lockfile = readLockfile(lockfilePath);

  const missing = [...refs].filter((r) => !lockfile.pins.has(r));
  const extra = opts.prune
    ? [...lockfile.pins.keys()].filter((r) => !refs.has(r))
    : [];

  if (missing.length === 0 && extra.length === 0) {
    process.stdout.write("Lockfile is in sync.\n");
    return;
  }

  if (missing.length > 0) {
    process.stderr.write("Missing lockfile entries:\n");
    for (const r of missing.sort()) process.stderr.write(`  ${r}\n`);
  }
  if (extra.length > 0) {
    process.stderr.write("Stale lockfile entries:\n");
    for (const r of extra.sort()) process.stderr.write(`  ${r}\n`);
  }
  throw new CliError("", 1);
}

interface UpgradeOpts {
  config?: string;
  check?: boolean;
  json?: boolean;
  mode?: "versions" | "lockfile" | "all";
  token?: string;
}

interface VersionBump {
  uses: string;
  current: string;
  latest: string;
  severity: "major" | "minor" | "patch";
  origin: "user";
  source_files?: string[];
}

interface LockfileStale {
  uses: string;
  current_sha: string;
  latest_sha: string;
  origin: "user";
  source_files?: string[];
}

async function depsUpgrade(opts: UpgradeOpts): Promise<void> {
  const mode = opts.mode ?? "all";
  if (mode !== "versions" && mode !== "lockfile" && mode !== "all") {
    throw new CliError(
      `Error: unknown --mode value '${mode}' (valid: versions, lockfile, all)`,
      2,
    );
  }
  const apply = !opts.check;

  const configPath = findConfig(opts.config);
  const { app, files: userFiles } = await trackUserFiles(configPath);

  const token = resolveToken(opts.token);
  if (!token) {
    process.stderr.write(
      "warning: no GitHub token found. Using unauthenticated requests " +
        "(60 req/hr limit). Set $GITHUB_TOKEN or use --token.\n",
    );
  }

  const refs = collectUsesRefs(app);

  if (refs.size === 0) {
    if (opts.json) {
      process.stdout.write(
        JSON.stringify(
          { version_bumps: [], lockfile_stale: [] },
          null,
          2,
        ) + "\n",
      );
    } else {
      process.stdout.write("Everything is up to date.\n");
    }
    return;
  }

  const refLocations = locateUsesRefs(refs, userFiles);

  // ---- version bump detection ----
  const versionBumps: VersionBump[] = [];

  const checkVersions = mode === "versions" || mode === "all";
  const checkLockfile = mode === "lockfile" || mode === "all";

  if (checkVersions) {
    const repoRefs = new Map<string, Array<{ uses: string; ref: string }>>();
    for (const uses of [...refs].sort()) {
      let parsed;
      try {
        parsed = parseUses(uses);
      } catch {
        continue;
      }
      const key = `${parsed.owner}/${parsed.repo}`;
      const list = repoRefs.get(key) ?? [];
      list.push({ uses, ref: parsed.ref });
      repoRefs.set(key, list);
    }

    const tagsCache = new Map<string, string[]>();
    for (const [key, usesList] of [...repoRefs.entries()].sort(([a], [b]) =>
      a.localeCompare(b),
    )) {
      const [owner, repo] = key.split("/", 2) as [string, string];
      let tags = tagsCache.get(key);
      if (tags === undefined) {
        try {
          tags = await listTags(owner, repo, { token });
        } catch (err) {
          if (err instanceof ResolveError) {
            process.stderr.write(
              `warning: failed to list tags for ${key}: ${err.message}\n`,
            );
            continue;
          }
          throw err;
        }
        tagsCache.set(key, tags);
      }

      for (const { uses, ref } of usesList) {
        const latestTag = findLatestTag(ref, tags);
        if (latestTag === null) continue;
        const currentParsed = parseTag(ref);
        const latestParsed = parseTag(latestTag);
        if (currentParsed === null || latestParsed === null) continue;
        const severity = classifyBump(currentParsed.version, latestParsed.version);
        const entry: VersionBump = {
          uses,
          current: ref,
          latest: latestTag,
          severity,
          origin: "user",
        };
        const sources = refLocations.get(uses);
        if (sources && sources.length > 0) entry.source_files = [...sources];
        versionBumps.push(entry);
      }
    }
  }

  // ---- lockfile staleness detection ----
  const lockfileStale: LockfileStale[] = [];

  if (checkLockfile && app.lockfilePath !== null) {
    const lockfile = readLockfile(resolve(app.root, app.lockfilePath));
    for (const uses of [...refs].sort()) {
      const entry = lockfile.get(uses);
      if (entry === undefined) continue;
      let parsed;
      try {
        parsed = parseUses(uses);
      } catch {
        continue;
      }
      let currentSha: string;
      try {
        currentSha = await resolveRef(parsed.owner, parsed.repo, parsed.ref, { token });
      } catch (err) {
        if (err instanceof ResolveError) {
          process.stderr.write(
            `warning: failed to resolve ${uses}: ${err.message}\n`,
          );
          continue;
        }
        throw err;
      }
      if (currentSha !== entry.sha) {
        const staleEntry: LockfileStale = {
          uses,
          current_sha: entry.sha,
          latest_sha: currentSha,
          origin: "user",
        };
        const sources = refLocations.get(uses);
        if (sources && sources.length > 0) staleEntry.source_files = [...sources];
        lockfileStale.push(staleEntry);
      }
    }
  }

  // ---- apply ----
  if (apply && versionBumps.length > 0) {
    const updates = new Map<string, string>();
    for (const bump of versionBumps) {
      const at = bump.uses.lastIndexOf("@");
      const newUses = `${bump.uses.slice(0, at)}@${bump.latest}`;
      updates.set(bump.uses, newUses);
    }
    const refLocsObj = new Map<string, string[]>();
    for (const [k, v] of refLocations.entries()) refLocsObj.set(k, [...v]);
    const changed = applyUpdates(updates, refLocsObj);
    if (changed.length > 0) {
      process.stdout.write("Applied version bumps:\n");
      for (const f of changed) process.stdout.write(`  modified ${f}\n`);
    }
  }

  // ---- output ----
  if (versionBumps.length === 0 && lockfileStale.length === 0) {
    if (opts.json) {
      process.stdout.write(
        JSON.stringify({ version_bumps: [], lockfile_stale: [] }, null, 2) + "\n",
      );
    } else {
      process.stdout.write("Everything is up to date.\n");
    }
    return;
  }

  if (opts.json) {
    const result: { version_bumps?: VersionBump[]; lockfile_stale?: LockfileStale[] } = {};
    if (checkVersions) result.version_bumps = versionBumps;
    if (checkLockfile) result.lockfile_stale = lockfileStale;
    process.stdout.write(JSON.stringify(result, null, 2) + "\n");
  } else {
    printHumanReport(versionBumps, lockfileStale);
  }
}

function printHumanReport(
  versionBumps: VersionBump[],
  lockfileStale: LockfileStale[],
): void {
  if (versionBumps.length > 0) {
    process.stdout.write("Version updates available:\n\n");
    for (const bump of versionBumps) {
      process.stdout.write(
        `  ${bump.uses}  →  ${bump.latest}  [${bump.severity}]\n`,
      );
      for (const src of bump.source_files ?? []) {
        process.stdout.write(`    in ${src}\n`);
      }
    }
    process.stdout.write("\n");
  }
  if (lockfileStale.length > 0) {
    process.stdout.write("Stale lockfile entries:\n\n");
    for (const entry of lockfileStale) {
      process.stdout.write(`  ${entry.uses}\n`);
      process.stdout.write(`    current SHA: ${entry.current_sha.slice(0, 12)}...\n`);
      process.stdout.write(`    latest SHA:  ${entry.latest_sha.slice(0, 12)}...\n`);
    }
    process.stdout.write("\n");
  }
}

/** Build the `deps` sub-command for mounting on the top-level CLI. */
export function buildDepsCommand(): Command {
  const deps = new Command("deps")
    .description("Manage action dependencies.")
    .showHelpAfterError();

  deps
    .command("pin")
    .description("Pin action references to commit SHAs in a lockfile.")
    .option("-c, --config <path>", "Path to config file")
    .option("--update", "Re-resolve all entries to latest SHAs")
    .option("--prune", "Remove lockfile entries not referenced in code")
    .option("--token <token>", "GitHub token (default: $GITHUB_TOKEN)")
    .action(async (opts: PinOpts) => depsPin(opts));

  deps
    .command("check-synced")
    .description("Verify lockfile is in sync with code (exit 1 if stale).")
    .option("-c, --config <path>", "Path to config file")
    .option("--prune", "Also flag stale lockfile entries not referenced in code")
    .action(async (opts: CheckSyncedOpts) => depsCheckSynced(opts));

  deps
    .command("upgrade")
    .description("Upgrade action dependencies to latest versions.")
    .option("-c, --config <path>", "Path to config file")
    .option("--check", "Check for available upgrades without applying")
    .option("--json", "Output in machine-readable JSON format")
    .option("--mode <mode>", "Detection mode: versions, lockfile, or all", "all")
    .option("--token <token>", "GitHub token (default: $GITHUB_TOKEN)")
    .action(async (opts: UpgradeOpts) => depsUpgrade(opts));

  return deps;
}

/** Public re-exports useful for testing. */
export { depsPin, depsCheckSynced, depsUpgrade };
