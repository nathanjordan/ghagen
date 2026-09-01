/**
 * The one TypeScript repo-root / test-path resolver (dev/test-only).
 *
 * Replaces the duplicated `../../../../` constants in the test helpers and the
 * codegen's private two-hop `resolve(ROOT, "../..")` math with a single walk-up
 * that *asserts* it found the root (the directory containing `schema/`), so no
 * move of a caller can silently retarget it.
 *
 * This module is excluded from the published build (see tsconfig `exclude`); it
 * exists only for the test suites and `scripts/generate-types.ts`.
 */

import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";

function findRepoRoot(): string {
  // Key on the canonical Snapshot's `schema/manifest.json`, not a bare `schema/`
  // directory: this file starts under `packages/typescript/src`, which has its
  // own generated `schema/` folder (the reference types) that must not be
  // mistaken for the repo-root Snapshot.
  let dir = import.meta.dirname;
  while (true) {
    if (existsSync(resolve(dir, "schema", "manifest.json"))) {
      return dir;
    }
    const parent = dirname(dir);
    if (parent === dir) {
      throw new Error("Cannot find repo root (directory containing schema/manifest.json)");
    }
    dir = parent;
  }
}

/** Repo root: the ancestor directory containing `schema/`. */
export const REPO_ROOT = findRepoRoot();

/** Canonical schema Snapshot directory (single source of truth). */
export const SCHEMA_DIR = resolve(REPO_ROOT, "schema");

/**
 * The fixtures directory (holds `expected/` plus other fixture data such as
 * `cli-exit-codes.yml` and `cli-exit-code-projects/`).
 */
export const FIXTURES_ROOT = resolve(REPO_ROOT, "fixtures");

/** Shared golden fixtures consumed by both ports' test suites. */
export const EXPECTED_DIR = resolve(FIXTURES_ROOT, "expected");
