/**
 * App class for multi-file synthesis of workflows and actions.
 *
 * CDK-inspired pattern: register items, then call `synth()` to write them all out. Use
 * `addWorkflow()` and `addAction()` for the common cases and `add()` as an escape hatch when you
 * need to write to a non-conventional path.
 */

import { existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname, isAbsolute, join, resolve } from "node:path";
import { DEFAULT_LOCKFILE_PATH, type GhagenOptions, loadOptions } from "./config.js";
import type { ActionModel, Document, WorkflowModel } from "./models/_base.js";
import { createTwoFilesPatch } from "diff";
import type { HeaderVariables } from "./emitter/header.js";
import { readLockfile } from "./pin/lockfile.js";
import { pinTransform } from "./pin/transform.js";
import { render } from "./synth.js";
import type { Transform } from "./transforms.js";

/** Conventional directory for GitHub Actions workflows inside a repository. */
export const DEFAULT_WORKFLOWS_DIR = ".github/workflows";

interface RegisteredItem {
  readonly item: Document;
  /** Output path relative to `root`. */
  readonly relPath: string;
}

export class App {
  readonly rootAbsPath: string;
  readonly headerTxt: string | null | ((vars: HeaderVariables) => string) | undefined;
  readonly lockfilePath: string | null;

  /** @internal — registered items with their output paths. */
  readonly _items: RegisteredItem[] = [];
  readonly _userTransforms: readonly Transform[];
  /** @internal — auto-dedent flag from `.ghagen.yml`, threaded into emit. */
  private readonly autoDedent: boolean;

  constructor(
    options: {
      /**
       * Repository root directory. All registered output paths and the lockfile are resolved relative
       * to this. Defaults to `process.cwd()`.
       */
      root?: string;
      /**
       * Header comment for every generated file. Four shapes are accepted:
       *
       * - omit / `undefined` — emit ghagen's default header.
       * - `null`             — emit no header.
       * - `string`           — emit the string verbatim. No `{variable}`
       *   substitution; literal braces are preserved.
       * - `(vars) => string` — invoke the closure with a fully-populated
       *   `HeaderVariables` (see the emitter module for the typed shape) and
       *   emit the returned string.
       */
      header?: string | null | ((vars: HeaderVariables) => string);
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
      /**
       * Pre-loaded project options. When omitted, `App` reads them from
       * `.ghagen.yml` itself (standalone `new App()` works unchanged); pass a
       * value to avoid a redundant read when the config was already parsed.
       */
      options?: GhagenOptions;
    } = {},
  ) {
    const rootInput = options.root ?? ".";
    this.rootAbsPath = isAbsolute(rootInput) ? rootInput : resolve(rootInput);
    this.headerTxt = options.header;
    this.lockfilePath =
      options.lockfile === null ? null : (options.lockfile ?? DEFAULT_LOCKFILE_PATH);
    this._userTransforms = options.transforms ?? [];

    // Load project-level options (e.g. auto_dedent) from .ghagen.yml. Threaded into the emitter at
    // synth/check time rather than applied via a module-level global (ADR-0002). loadOptions is
    // total — a malformed `entrypoint:` never breaks it.
    const opts = options.options ?? loadOptions(this.rootAbsPath);
    this.autoDedent = opts.auto_dedent;
  }

  /**
   * Register an item at an explicit path relative to `root`.
   *
   * Use this escape hatch when you need to write to a path that doesn't fit the standard
   * conventions. For the common cases, prefer `addWorkflow()` / `addAction()`.
   */
  add(item: Document, path: string): void {
    this._items.push({ item, relPath: path });
  }

  /**
   * The registered Documents (Workflows and Actions), in registration order.
   *
   * The public accessor for pin and other read-only consumers; the
   * `{ item, relPath }` storage stays internal to `App`.
   */
  documents(): Document[] {
    return this._items.map(({ item }) => item);
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
   * Returns the absolute paths of every file written. Synchronous: `render` and every transform
   * are synchronous, and file writes use the sync `node:fs` API.
   */
  synth(): string[] {
    const written: string[] = [];
    for (const r of render(this._renderItems(), this._buildTransforms(), {
      header: this.headerTxt,
      autoDedent: this.autoDedent,
    })) {
      const full = resolve(this.rootAbsPath, r.path);
      mkdirSync(dirname(full), { recursive: true });
      writeFileSync(full, r.text);
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
  check(): Array<[string, string]> {
    const stale: Array<[string, string]> = [];

    for (const r of render(this._renderItems(), this._buildTransforms(), {
      header: this.headerTxt,
      autoDedent: this.autoDedent,
    })) {
      const full = resolve(this.rootAbsPath, r.path);

      if (!existsSync(full) || !statSync(full).isFile()) {
        stale.push([full, `File does not exist: ${full}`]);
        continue;
      }

      const actual = readFileSync(full, "utf8");
      if (actual !== r.text) {
        const diff = createTwoFilesPatch(
          `${full} (on disk)`,
          `${full} (generated)`,
          actual,
          r.text,
        );
        stale.push([full, diff]);
      }
    }

    return stale;
  }

  /** @internal — the registered items as `[document, relPath]` pairs for `render`. */
  private _renderItems(): Array<readonly [Document, string]> {
    return this._items.map(({ item, relPath }) => [item, relPath] as const);
  }

  /**
   * @internal
   *
   * Build the full transform list, auto-registering pin *last* if a lockfile is present. User
   * transforms run first so they see the authored `uses:` refs; the pin transform runs last so it
   * locks whatever refs survive to the end of the pipeline, including refs a user transform
   * injected.
   */
  private _buildTransforms(): Transform[] {
    const transforms: Transform[] = [...this._userTransforms];

    if (this.lockfilePath !== null) {
      const fullLockfile = resolve(this.rootAbsPath, this.lockfilePath);
      if (existsSync(fullLockfile) && statSync(fullLockfile).isFile()) {
        const lockfile = readLockfile(fullLockfile);
        transforms.push(pinTransform(lockfile));
      }
    }

    return transforms;
  }
}
