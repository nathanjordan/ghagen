/**
 * Coarse schema-conformance sweep for the hand-written TypeScript models.
 *
 * The Pydantic port validates hand-written models against the canonical
 * Snapshots at runtime; TypeScript's authoring conformance is compile-time (the
 * generated types are imported into the models, so `tsc` fails on divergence --
 * see ADR-0003). This sweep adds the *coverage* half of that story: it walks
 * **both** Snapshots (workflow + action) against the {@link ModelSpec} fieldMaps
 * -- the machine-readable model surface -- and asserts every upstream property
 * is emitted by some model, or is listed in the shared allow-list.
 *
 * The allow-list (`schema/conformance-gaps.yml`) and the scope table below are
 * mirrored exactly by the Python sweep
 * (`packages/python/tests/test_schema/test_conformance.py`). Both ports held to
 * the same allow-list means both model the same property set -- cross-port
 * surface agreement, structurally.
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { parse } from "yaml";
import { SCHEMA_DIR } from "../paths.js";
import type { ModelSpec } from "./_base.js";
import {
  ACTION_INPUT_SPEC,
  ACTION_OUTPUT_SPEC,
  ACTION_SPEC,
  BRANDING_SPEC,
  COMPOSITE_RUNS_SPEC,
  DOCKER_RUNS_SPEC,
  NODE_RUNS_SPEC,
} from "./action.js";
import { JOB_SPEC } from "./job.js";
import { STEP_SPEC } from "./step.js";
import { WORKFLOW_SPEC } from "./workflow.js";

const GAPS_PATH = resolve(SCHEMA_DIR, "conformance-gaps.yml");
const SCOPES_PATH = resolve(SCHEMA_DIR, "conformance-scopes.yml");

/** A JSON path into a loaded schema: the keys to walk before reading props. */
type SchemaPath = readonly string[];

interface Scope {
  readonly spec: ModelSpec;
  /** Schema location(s) whose unioned property set the spec must cover. */
  readonly paths: readonly SchemaPath[];
}

// snapshot filename -> { scope name -> covering spec }. The schema path(s) for
// each scope live in the shared schema/conformance-scopes.yml (read identically
// by the Python sweep); only the spec binding stays here (a ModelSpec cannot be
// serialized into the shared file). A parity guard asserts the two key sets
// match, so a scope added to one port and not the other fails a test.
const SPECS: Record<string, Record<string, ModelSpec>> = {
  "workflow_schema.json": {
    workflow: WORKFLOW_SPEC,
    // ghagen's single job model covers both the regular-job and the
    // reusable-workflow-call-job shapes.
    job: JOB_SPEC,
    step: STEP_SPEC,
  },
  "action_schema.json": {
    action: ACTION_SPEC,
    compositeRuns: COMPOSITE_RUNS_SPEC,
    dockerRuns: DOCKER_RUNS_SPEC,
    nodeRuns: NODE_RUNS_SPEC,
    actionInput: ACTION_INPUT_SPEC,
    actionOutput: ACTION_OUTPUT_SPEC,
    branding: BRANDING_SPEC,
  },
};

type ScopePaths = Record<string, Record<string, SchemaPath[]>>;

function loadScopePaths(): ScopePaths {
  return parse(readFileSync(SCOPES_PATH, "utf8")) as ScopePaths;
}

// Bind each shared scope's path(s) to this port's covering spec. Built over the
// intersection so a divergence never throws at load; the parity guard is the
// failure surface.
const SCOPE_PATHS = loadScopePaths();
const SWEEP: Record<string, Record<string, Scope>> = Object.fromEntries(
  Object.entries(SCOPE_PATHS).map(([snapshot, scopes]) => [
    snapshot,
    Object.fromEntries(
      Object.entries(scopes)
        .filter(([name]) => SPECS[snapshot]?.[name] !== undefined)
        .map(([name, paths]) => [name, { spec: SPECS[snapshot][name], paths } as Scope]),
    ),
  ]),
);

type Gaps = Record<string, Record<string, string[]>>;

function loadSchema(filename: string): Record<string, unknown> {
  return JSON.parse(readFileSync(resolve(SCHEMA_DIR, filename), "utf8"));
}

function loadGaps(): Gaps {
  return parse(readFileSync(GAPS_PATH, "utf8")) as Gaps;
}

function resolvePath(schema: Record<string, unknown>, path: SchemaPath): Record<string, unknown> {
  let node: unknown = schema;
  for (const key of path) {
    node = (node as Record<string, unknown>)[key];
  }
  return node as Record<string, unknown>;
}

/** Property names a schema node declares, direct or via patternProperties. */
function nodeProperties(node: Record<string, unknown>): Set<string> {
  const names = new Set<string>(Object.keys((node.properties as object | undefined) ?? {}));
  const pattern = (node.patternProperties as Record<string, unknown> | undefined) ?? {};
  for (const sub of Object.values(pattern)) {
    if (sub && typeof sub === "object") {
      for (const key of Object.keys((sub as Record<string, unknown>).properties ?? {})) {
        names.add(key);
      }
    }
  }
  return names;
}

function schemaProperties(schema: Record<string, unknown>, s: Scope): Set<string> {
  const props = new Set<string>();
  for (const path of s.paths) {
    for (const name of nodeProperties(resolvePath(schema, path))) {
      props.add(name);
    }
  }
  return props;
}

/** Emitted YAML keys a spec exposes -- the machine-readable model surface. */
function modelPropertyNames(spec: ModelSpec): Set<string> {
  return new Set(Object.values(spec.fieldMap));
}

describe("schema conformance sweep", () => {
  const gaps = loadGaps();

  for (const [snapshot, scopes] of Object.entries(SWEEP)) {
    const snapshotKey = snapshot.replace(/\.json$/, "");
    const schema = loadSchema(snapshot);

    for (const [scopeName, s] of Object.entries(scopes)) {
      it(`${snapshot}:${scopeName} model covers every schema property`, () => {
        const props = schemaProperties(schema, s);
        expect(props.size, `${snapshot}:${scopeName} exposes no schema properties`).toBeGreaterThan(
          0,
        );

        const allow = new Set(gaps[snapshotKey]?.[scopeName] ?? []);
        const covered = modelPropertyNames(s.spec);

        const missing = [...props].filter((p) => !covered.has(p) && !allow.has(p)).sort();
        expect(
          missing,
          `${snapshot}:${scopeName} is missing schema properties ${JSON.stringify(missing)}. ` +
            `Add fields to the ModelSpec, or list them in conformance-gaps.yml if intentional.`,
        ).toEqual([]);

        // Keep the allow-list honest: every allowed name must still exist upstream.
        const stale = [...allow].filter((a) => !props.has(a)).sort();
        expect(
          stale,
          `${snapshot}:${scopeName} allow-list has stale entries ${JSON.stringify(stale)} ` +
            `no longer in the schema. Remove them from conformance-gaps.yml.`,
        ).toEqual([]);
      });
    }
  }

  it("scope set matches the shared scope table", () => {
    // Mirrors the Python guard (test_scope_set_matches_shared_table): this
    // port's spec bindings must match the shared scope table exactly, so a
    // scope added to one port and not the other -- or a snapshot/scope typo --
    // fails here instead of degrading coverage silently.
    const shared = loadScopePaths();
    expect(Object.keys(SPECS).sort()).toEqual(Object.keys(shared).sort());
    for (const snapshot of Object.keys(shared)) {
      expect(
        Object.keys(SPECS[snapshot]).sort(),
        `${snapshot} scopes diverge from conformance-scopes.yml`,
      ).toEqual(Object.keys(shared[snapshot]).sort());
    }
  });
});
