/**
 * App class for multi-file synthesis of workflows and actions.
 *
 * CDK-inspired pattern: register items, then call `synth()` to write them all out. Use
 * `addWorkflow()` and `addAction()` for the common cases and `add()` as an escape hatch when you
 * need to write to a non-conventional path.
 */

import { existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname, isAbsolute, join, resolve } from "node:path";
import { loadOptions, setAutoDedent } from "./config.js";
import { cloneModel } from "./models/_base.js";
import type { ActionModel, WorkflowModel } from "./models/_base.js";
import { createTwoFilesPatch } from "diff";
import { toYaml } from "./emitter/yaml-writer.js";
import type { SynthContext, SynthItem, Transform } from "./transforms.js";
import { mkdir } from "node:fs/promises";

/** Conventional directory for GitHub Actions workflows inside a repository. */
export const DEFAULT_WORKFLOWS_DIR = ".github/workflows";

const DEFAULT_LOCKFILE_REL = ".ghagen.lock.yml";

interface RegisteredItem {
  readonly item: SynthItem;
  /** Output path relative to `root`. */
  readonly relPath: string;
}

export class App {
  readonly rootAbsPath: string;
  readonly headerTxt: string | null | undefined;
  readonly lockfilePath: string | null;

  /** @internal — registered items, exposed for transforms/lint. */
  readonly _items: RegisteredItem[] = [];
  readonly _userTransforms: readonly Transform[];

  constructor(options: {
    /**
     * Repository root directory. All registered output paths and the lockfile are resolved relative
     * to this. Defaults to `process.cwd()`.
     */
    root?: string;
    /**
     * Custom header comment template for generated files. May contain `{variable}` placeholders —
     * see the emitter's `HEADER_VARIABLES`. Set to `null` to keep the ghagen default; set to
     * `undefined` to use the default.
     */
    header?: string | null;
    /**
     * Path to the pin lockfile, relative to `root`. Set to `null` to disable lockfile auto-loading.
     * Defaults to `.ghagen.lock.yml`.
     */
    lockfile?: string | null;
    /**
     * Additional model transforms to apply during synthesis. The pin transform is auto-registered
     * when a lockfile is present; these are appended after it.
     */
    transforms?: readonly Transform[];
  } = {}) {
    const rootInput = options.root ?? ".";
    this.rootAbsPath = isAbsolute(rootInput) ? rootInput : resolve(rootInput);
    this.headerTxt = (options.header === null || options.header === undefined) ? options.header : options.header + "";
    this.lockfilePath =
      options.lockfile === null ? null : (options.lockfile ?? DEFAULT_LOCKFILE_REL);
    this._userTransforms = options.transforms ?? [];

    // Apply project-level options (e.g. auto_dedent) from .ghagen.yml. Mirrors the Python App's
    // behaviour.
    const opts = loadOptions(this.rootAbsPath);
    setAutoDedent(opts.auto_dedent);
  }

  /**
   * Register an item at an explicit path relative to `root`.
   *
   * Use this escape hatch when you need to write to a path that doesn't fit the standard
   * conventions. For the common cases, prefer `addWorkflow()` / `addAction()`.
   */
  add(item: SynthItem, path: string): void {
    this._items.push({ item, relPath: path });
  }

  /** Register a workflow at `.github/workflows/{filename}`. */
  addWorkflow(workflow: WorkflowModel, filename: string): void {
    this.add(workflow, join(DEFAULT_WORKFLOWS_DIR, filename));
  }

  /** Register an action, writing `{dir}/action.yml` (defaults to repo root). */
  addAction(action: ActionModel, dir: string = "."): void {
    this.add(action, join(dir, "action.yml"));
  }

  /**
   * Synthesize all registered items to YAML files.
   *
   * Returns the absolute paths of every file written. Asynchronous so we have room to add async
   * transforms in the future without breaking the API.
   */
  async synth(): Promise<string[]> {
    const transforms = await this._buildTransforms();
    const written: string[] = [];
    for (const { item, relPath } of this._items) {
      const full = resolve(this.rootAbsPath, relPath);
      const working = this._applyTransforms(item, relPath, transforms);
      await mkdir(dirname(full), { recursive: true });
      writeFileSync(full, toYaml(working, { header: this.headerTxt }));
      written.push(full);
    }
    return written;
  }

  /**
   * Check whether the on-disk YAML matches what `synth()` would write.
   *
   * Returns one `[path, diff]` tuple for each file that's stale or missing. An empty list means
   * everything is in sync.
   */
  async check(): Promise<Array<[string, string]>> {
    const transforms = await this._buildTransforms();
    const stale: Array<[string, string]> = [];

    for (const { item, relPath } of this._items) {
      const full = resolve(this.rootAbsPath, relPath);
      const working = this._applyTransforms(item, relPath, transforms);
      const expected = toYaml(working, { header: this.headerTxt });

      if (!existsSync(full) || !statSync(full).isFile()) {
        stale.push([full, `File does not exist: ${full}`]);
        continue;
      }

      const actual = readFileSync(full, "utf8");
      if (actual !== expected) {
        const diff = createTwoFilesPatch(`${full} (on disk)`, `${full} (generated)`, actual, expected);
        stale.push([full, diff]);
      }
    }

    return stale;
  }

  /** @internal */
  private async _buildTransforms(): Promise<Transform[]> {
    const transforms: Transform[] = [];

    if (this.lockfilePath !== null) {
      const fullLockfile = resolve(this.rootAbsPath, this.lockfilePath);
      if (existsSync(fullLockfile) && statSync(fullLockfile).isFile()) {
        // Dynamic import keeps the pin module out of the cold-path when no lockfile is present.
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
      root: this.rootAbsPath,
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
