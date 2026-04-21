/**
 * App class for multi-file synthesis of workflows and actions.
 *
 * CDK-inspired pattern: register items, then call `synth()` to write
 * them all out. Use `addWorkflow()` and `addAction()` for the common
 * cases and `add()` as an escape hatch when you need to write to a
 * non-conventional path.
 */

import { existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname, isAbsolute, join, resolve } from "node:path";
import { loadOptions } from "./config.js";
import { setAutoDedent } from "./_dedent.js";
import { cloneModel } from "./models/_base.js";
import type { ActionModel, WorkflowModel } from "./models/_base.js";
import { toYaml } from "./emitter/yaml-writer.js";
import type { SynthContext, SynthItem, Transform } from "./transforms.js";

/** Conventional directory for GitHub Actions workflows inside a repository. */
export const WORKFLOWS_DIR = ".github/workflows";

/** Configuration for an `App`. */
export interface AppOptions {
  /**
   * Repository root directory. All registered output paths and the
   * lockfile are resolved relative to this. Defaults to
   * `process.cwd()`.
   */
  root?: string;
  /**
   * Custom header comment template for generated files. May contain
   * `{variable}` placeholders — see the emitter's `HEADER_VARIABLES`.
   * Set to `null` to keep the ghagen default; set to `undefined` to
   * use the default.
   */
  header?: string | null;
  /**
   * Path to the pin lockfile, relative to `root`. Set to `null` to
   * disable lockfile auto-loading. Defaults to
   * `.github/ghagen.lock.toml`.
   */
  lockfile?: string | null;
  /**
   * Additional model transforms to apply during synthesis. The pin
   * transform is auto-registered when a lockfile is present; these
   * are appended after it.
   */
  transforms?: readonly Transform[];
}

const DEFAULT_LOCKFILE_REL = ".github/ghagen.lock.toml";

interface RegisteredItem {
  readonly item: SynthItem;
  /** Output path relative to `root`. */
  readonly relPath: string;
}

export class App {
  readonly root: string;
  readonly header: string | null | undefined;
  readonly lockfilePath: string | null;
  /** @internal — registered items, exposed for transforms/lint. */
  readonly _items: RegisteredItem[] = [];
  private readonly _userTransforms: readonly Transform[];

  constructor(options: AppOptions = {}) {
    const rootInput = options.root ?? ".";
    this.root = isAbsolute(rootInput) ? rootInput : resolve(rootInput);
    this.header = options.header;
    this.lockfilePath =
      options.lockfile === null ? null : (options.lockfile ?? DEFAULT_LOCKFILE_REL);
    this._userTransforms = options.transforms ?? [];

    // Apply project-level options (e.g. autoDedent) from ghagen.toml /
    // package.json. Mirrors the Python App's behaviour.
    const opts = loadOptions(this.root);
    setAutoDedent(opts.autoDedent);
  }

  /**
   * Register an item at an explicit path relative to `root`.
   *
   * Use this escape hatch when you need to write to a path that
   * doesn't fit the standard conventions. For the common cases,
   * prefer `addWorkflow()` / `addAction()`.
   */
  add(item: SynthItem, path: string): void {
    this._items.push({ item, relPath: path });
  }

  /** Register a workflow at `.github/workflows/{filename}`. */
  addWorkflow(workflow: WorkflowModel, filename: string): void {
    this.add(workflow, join(WORKFLOWS_DIR, filename));
  }

  /** Register an action, writing `{dir}/action.yml` (defaults to repo root). */
  addAction(action: ActionModel, dir: string = "."): void {
    this.add(action, join(dir, "action.yml"));
  }

  /**
   * Synthesize all registered items to YAML files.
   *
   * Returns the absolute paths of every file written. Asynchronous so
   * we have room to add async transforms in the future without
   * breaking the API.
   */
  async synth(): Promise<string[]> {
    const transforms = await this._buildTransforms();
    const written: string[] = [];
    for (const { item, relPath } of this._items) {
      const full = resolve(this.root, relPath);
      const working = this._applyTransforms(item, relPath, transforms);
      mkdirSync(dirname(full), { recursive: true });
      writeFileSync(full, toYaml(working, { header: this.header }));
      written.push(full);
    }
    return written;
  }

  /**
   * Check whether the on-disk YAML matches what `synth()` would write.
   *
   * Returns one `[path, diff]` tuple for each file that's stale or
   * missing. An empty list means everything is in sync.
   */
  async check(): Promise<Array<[string, string]>> {
    const transforms = await this._buildTransforms();
    const stale: Array<[string, string]> = [];

    for (const { item, relPath } of this._items) {
      const full = resolve(this.root, relPath);
      const working = this._applyTransforms(item, relPath, transforms);
      const expected = toYaml(working, { header: this.header });

      if (!existsSync(full) || !statSync(full).isFile()) {
        stale.push([full, `File does not exist: ${full}`]);
        continue;
      }

      const actual = readFileSync(full, "utf8");
      if (actual !== expected) {
        const diff = unifiedDiff(actual, expected, `${full} (on disk)`, `${full} (generated)`);
        stale.push([full, diff]);
      }
    }

    return stale;
  }

  /** @internal */
  private async _buildTransforms(): Promise<Transform[]> {
    const transforms: Transform[] = [];

    if (this.lockfilePath !== null) {
      const fullLockfile = resolve(this.root, this.lockfilePath);
      if (existsSync(fullLockfile) && statSync(fullLockfile).isFile()) {
        // Dynamic import keeps the pin module out of the cold-path
        // when no lockfile is present.
        const { readLockfile } = await import("./pin/lockfile.js");
        const { pinTransform } = await import("./pin/transform.js");
        const lockfile = readLockfile(fullLockfile);
        transforms.push(pinTransform(lockfile));
      }
    }

    transforms.push(...this._userTransforms);
    return transforms;
  }

  /** @internal */
  private _applyTransforms(
    item: SynthItem,
    relPath: string,
    transforms: readonly Transform[],
  ): SynthItem {
    if (transforms.length === 0) return item;

    let working = cloneModel(item);
    const ctx: SynthContext = {
      workflowKey: stem(relPath),
      itemType: item._kind === "workflow" ? "workflow" : "action",
      root: this.root,
    };
    for (const transform of transforms) {
      working = transform(working, ctx);
    }
    return working;
  }
}

/** Return the basename of `path` without its final extension. */
function stem(path: string): string {
  const base = path.replace(/^.*[\\/]/, "");
  const dot = base.lastIndexOf(".");
  return dot > 0 ? base.slice(0, dot) : base;
}

/**
 * Minimal unified-diff implementation. Produces output similar to
 * Python's `difflib.unified_diff` for use in `App.check()`.
 *
 * Computes the longest-common-subsequence of lines and emits hunks
 * with 3 lines of context. Output is line-terminated when possible
 * to match Python's `keepends=True` style.
 */
function unifiedDiff(a: string, b: string, fromFile: string, toFile: string, context = 3): string {
  const aLines = splitLines(a);
  const bLines = splitLines(b);
  const ops = lineOps(aLines, bLines);

  if (ops.every((op) => op.tag === "equal")) return "";

  const out: string[] = [`--- ${fromFile}\n`, `+++ ${toFile}\n`];

  // Group ops into hunks separated by long stretches of equal lines.
  const hunks = groupHunks(ops, context);
  for (const hunk of hunks) {
    let aStart = -1;
    let bStart = -1;
    let aLen = 0;
    let bLen = 0;
    for (const op of hunk) {
      if (aStart < 0) aStart = op.aIndex;
      if (bStart < 0) bStart = op.bIndex;
      if (op.tag !== "insert") aLen++;
      if (op.tag !== "delete") bLen++;
    }
    out.push(`@@ -${aStart + 1},${aLen} +${bStart + 1},${bLen} @@\n`);
    for (const op of hunk) {
      const line = op.tag === "insert" ? bLines[op.bIndex]! : aLines[op.aIndex]!;
      const prefix = op.tag === "equal" ? " " : op.tag === "delete" ? "-" : "+";
      out.push(prefix + line);
      // Ensure the diff terminates with a newline for visual sanity.
      if (!line.endsWith("\n")) out.push("\n");
    }
  }

  return out.join("");
}

interface LineOp {
  tag: "equal" | "insert" | "delete";
  aIndex: number;
  bIndex: number;
}

function splitLines(s: string): string[] {
  if (!s) return [];
  const lines: string[] = [];
  let i = 0;
  while (i < s.length) {
    let j = i;
    while (j < s.length && s[j] !== "\n") j++;
    if (j < s.length) j++;
    lines.push(s.slice(i, j));
    i = j;
  }
  return lines;
}

/**
 * Compute a Myers-style ops list using LCS via dynamic programming.
 * Sufficient for App.check() output — the size of generated YAML is
 * small, so the O(n*m) memory is fine.
 */
function lineOps(a: string[], b: string[]): LineOp[] {
  const n = a.length;
  const m = b.length;
  // dp[i][j] = LCS length of a[0..i] and b[0..j].
  const dp: number[][] = Array.from({ length: n + 1 }, () => new Array<number>(m + 1).fill(0));
  for (let i = 1; i <= n; i++) {
    for (let j = 1; j <= m; j++) {
      if (a[i - 1] === b[j - 1]) dp[i]![j] = dp[i - 1]![j - 1]! + 1;
      else dp[i]![j] = Math.max(dp[i - 1]![j]!, dp[i]![j - 1]!);
    }
  }
  const ops: LineOp[] = [];
  let i = n;
  let j = m;
  while (i > 0 && j > 0) {
    if (a[i - 1] === b[j - 1]) {
      ops.push({ tag: "equal", aIndex: i - 1, bIndex: j - 1 });
      i--;
      j--;
    } else if (dp[i - 1]![j]! >= dp[i]![j - 1]!) {
      ops.push({ tag: "delete", aIndex: i - 1, bIndex: j });
      i--;
    } else {
      ops.push({ tag: "insert", aIndex: i, bIndex: j - 1 });
      j--;
    }
  }
  while (i > 0) {
    ops.push({ tag: "delete", aIndex: --i, bIndex: 0 });
  }
  while (j > 0) {
    ops.push({ tag: "insert", aIndex: 0, bIndex: --j });
  }
  ops.reverse();
  return ops;
}

function groupHunks(ops: LineOp[], context: number): LineOp[][] {
  const hunks: LineOp[][] = [];
  let cur: LineOp[] = [];
  let trailingEquals = 0;

  for (let i = 0; i < ops.length; i++) {
    const op = ops[i]!;
    if (op.tag === "equal") {
      cur.push(op);
      trailingEquals++;
      if (trailingEquals > context * 2 && cur.length > context) {
        // Trim trailing context to `context` lines, finalise hunk.
        const trimmed = cur.slice(0, cur.length - (trailingEquals - context));
        if (trimmed.some((o) => o.tag !== "equal")) hunks.push(trimmed);
        cur = [];
        trailingEquals = 0;
      }
    } else {
      // On a non-equal op: keep at most `context` leading equal lines.
      if (cur.length > 0 && trailingEquals > context) {
        cur = cur.slice(cur.length - context);
      }
      cur.push(op);
      trailingEquals = 0;
    }
  }
  if (cur.some((o) => o.tag !== "equal")) {
    // Trim trailing context.
    if (trailingEquals > context) {
      cur = cur.slice(0, cur.length - (trailingEquals - context));
    }
    hunks.push(cur);
  }
  return hunks;
}
