/** ghagen deps — manage action dependencies.
 *
 * Each command is a thin shell: resolve the config/app, build a
 * {@link GitHubClient}, call the pin engine, and render the typed report.
 * All orchestration lives in `../pin/engine.ts`.
 */

import { Command } from "commander";
import { resolve } from "node:path";
import type { App } from "../app.js";
import {
  GitHubClient,
  trackUserFiles,
  pin,
  checkSync,
  upgrade,
  renderUpgradeReport,
} from "../pin/index.js";
import { findConfig, loadApp } from "./_common.js";
import { CliError } from "./_errors.js";

function resolveToken(flag?: string): string | undefined {
  return flag ?? process.env["GITHUB_TOKEN"] ?? process.env["GH_TOKEN"];
}

/**
 * Resolve the token (flag > $GITHUB_TOKEN > $GH_TOKEN) and build a client,
 * emitting the no-token warning once so commands stay free of duplication.
 */
function buildGitHubClient(tokenFlag?: string): GitHubClient {
  const token = resolveToken(tokenFlag);
  if (!token) {
    process.stderr.write(
      "warning: no GitHub token found. Using unauthenticated requests " +
        "(60 req/hr limit). Set $GITHUB_TOKEN or use --token.\n",
    );
  }
  return new GitHubClient(undefined, token);
}

function ensureLockfilePath(app: App): string {
  if (app.lockfilePath === null) {
    throw new CliError("Error: lockfile is disabled (lockfile: null on App)");
  }
  return resolve(app.rootAbsPath, app.lockfilePath);
}

interface PinOpts {
  config?: string;
  update?: boolean;
  prune: boolean;
  token?: string;
}

/**
 * Resolve action references to commit SHAs and write them to the lockfile.
 *
 * By default only new (unpinned) references are resolved. Pass `--update` to
 * re-resolve all entries. Stale entries no longer referenced in code are pruned
 * automatically; pass `--no-prune` to keep them.
 */
async function depsPin(opts: PinOpts): Promise<void> {
  const configPath = findConfig(opts.config);
  const app = await loadApp(configPath);
  ensureLockfilePath(app); // validate before doing any work

  const client = buildGitHubClient(opts.token);

  const report = await pin(app, client, {
    update: opts.update ?? false,
    prune: opts.prune,
  });

  for (const r of report.resolved) {
    process.stdout.write(`  ${r.uses} → ${r.sha.slice(0, 12)}\n`);
  }
  for (const w of report.warnings) {
    process.stderr.write(`warning: ${w}\n`);
  }
  for (const e of report.errors) {
    process.stderr.write(`error: ${e}\n`);
  }
  if (report.pruned > 0) {
    process.stdout.write(`Pruned ${report.pruned} stale entry/entries.\n`);
  }
  if (report.written) {
    process.stdout.write(`Wrote ${report.lockfilePath}\n`);
  }
  if (report.upToDate) {
    process.stdout.write("Lockfile is already up to date.\n");
  }

  if (report.errors.length > 0) {
    throw new CliError(`${report.errors.length} ref(s) failed to resolve.`, 1);
  }
}

interface CheckSyncedOpts {
  config?: string;
  prune: boolean;
}

/**
 * Verify the lockfile is in sync with the current action references.
 *
 * Exits with code 1 if any references are missing from the lockfile or
 * if the lockfile contains stale entries. Pass `--no-prune` to ignore stale
 * entries.
 */
async function depsCheckSynced(opts: CheckSyncedOpts): Promise<void> {
  const configPath = findConfig(opts.config);
  const app = await loadApp(configPath);
  ensureLockfilePath(app); // validate before doing any work

  const report = checkSync(app, { prune: opts.prune });

  if (report.inSync) {
    process.stdout.write("Lockfile is in sync.\n");
    return;
  }

  if (report.missing.length > 0) {
    process.stderr.write("Missing lockfile entries:\n");
    for (const r of report.missing) {
      process.stderr.write(`  ${r}\n`);
    }
  }
  if (report.extra.length > 0) {
    process.stderr.write("Stale lockfile entries:\n");
    for (const r of report.extra) {
      process.stderr.write(`  ${r}\n`);
    }
  }
  throw new CliError("", 1);
}

interface UpgradeOpts {
  config?: string;
  check?: boolean;
  format?: string;
  mode?: "versions" | "lockfile" | "all";
  token?: string;
}

/**
 * Detect and optionally apply upgrades to action dependencies.
 *
 * Checks for newer version tags (`--mode versions`), stale lockfile SHAs
 * (`--mode lockfile`), or both (`--mode all`). By default upgrades are
 * applied in-place; pass `--check` for a dry-run report.
 */
async function depsUpgrade(opts: UpgradeOpts): Promise<void> {
  const mode = opts.mode ?? "all";
  if (mode !== "versions" && mode !== "lockfile" && mode !== "all") {
    throw new CliError(`Error: unknown --mode value '${mode}' (valid: versions, lockfile, all)`, 2);
  }

  const format = opts.format;
  if (
    format !== undefined &&
    format !== "json" &&
    format !== "pr-body" &&
    format !== "issue-body"
  ) {
    throw new CliError(
      `Error: unknown --format value '${format}' (valid: json, pr-body, issue-body)`,
      2,
    );
  }
  const apply = !opts.check;

  const configPath = findConfig(opts.config);
  const { app, files: userFiles } = await trackUserFiles(configPath);

  const client = buildGitHubClient(opts.token);

  const report = await upgrade(app, client, userFiles, { mode, apply });

  for (const w of report.warnings) {
    process.stderr.write(`warning: ${w}\n`);
  }

  if (report.changedFiles.length > 0) {
    // Under --format the report itself owns stdout; this progress note goes to
    // stderr so `--format json` (without --check) stays machine-parseable.
    const progress = format !== undefined ? process.stderr : process.stdout;
    progress.write("Applied version bumps:\n");
    for (const f of report.changedFiles) {
      progress.write(`  modified ${f}\n`);
    }
  }

  process.stdout.write(renderUpgradeReport(report, format ?? "text"));
}

/** Build the `deps` sub-command for mounting on the top-level CLI. */
export function buildDepsCommand(): Command {
  const deps = new Command("deps").description("Manage action dependencies.").showHelpAfterError();

  deps
    .command("pin")
    .description("Pin action references to commit SHAs in a lockfile.")
    .option("-c, --config <path>", "Path to config file")
    .option("--update", "Re-resolve all entries to latest SHAs")
    .option("--no-prune", "Keep stale lockfile entries not referenced in code")
    .option("--token <token>", "GitHub token (default: $GITHUB_TOKEN)")
    .action(async (opts: PinOpts) => depsPin(opts));

  deps
    .command("check-synced")
    .description("Verify lockfile is in sync with code (exit 1 if stale).")
    .option("-c, --config <path>", "Path to config file")
    .option("--no-prune", "Ignore stale lockfile entries not referenced in code")
    .action(async (opts: CheckSyncedOpts) => depsCheckSynced(opts));

  deps
    .command("upgrade")
    .description("Upgrade action dependencies to latest versions.")
    .option("-c, --config <path>", "Path to config file")
    .option("--check", "Check for available upgrades without applying")
    .option(
      "--format <format>",
      "Output format: json, pr-body, or issue-body (default: human-readable text)",
    )
    .option("--mode <mode>", "Detection mode: versions, lockfile, or all", "all")
    .option("--token <token>", "GitHub token (default: $GITHUB_TOKEN)")
    .action(async (opts: UpgradeOpts) => depsUpgrade(opts));

  return deps;
}

/** Public re-exports useful for testing. */
export { depsPin, depsCheckSynced, depsUpgrade };
