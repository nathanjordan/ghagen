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

const SCHEMA_DIR = resolve(import.meta.dirname, "../../../../schema");
const GAPS_PATH = resolve(SCHEMA_DIR, "conformance-gaps.yml");

/** A JSON path into a loaded schema: the keys to walk before reading props. */
type SchemaPath = readonly string[];

const ROOT: SchemaPath = [];

interface Scope {
  readonly spec: ModelSpec;
  /** Schema location(s) whose unioned property set the spec must cover. */
  readonly paths: readonly SchemaPath[];
}

function scope(spec: ModelSpec, ...paths: SchemaPath[]): Scope {
  return { spec, paths: paths.length > 0 ? paths : [ROOT] };
}

// snapshot filename -> { scope name -> Scope }. Mirrors the Python SWEEP table.
const SWEEP: Record<string, Record<string, Scope>> = {
  "workflow_schema.json": {
    workflow: scope(WORKFLOW_SPEC, ROOT),
    // ghagen's single job model covers both the regular-job and the
    // reusable-workflow-call-job shapes.
    job: scope(JOB_SPEC, ["definitions", "normalJob"], ["definitions", "reusableWorkflowCallJob"]),
    step: scope(STEP_SPEC, ["definitions", "step"]),
  },
  "action_schema.json": {
    action: scope(ACTION_SPEC, ROOT),
    compositeRuns: scope(COMPOSITE_RUNS_SPEC, ["definitions", "runs-composite"]),
    dockerRuns: scope(DOCKER_RUNS_SPEC, ["definitions", "runs-docker"]),
    nodeRuns: scope(NODE_RUNS_SPEC, ["definitions", "runs-javascript"]),
    actionInput: scope(ACTION_INPUT_SPEC, ["properties", "inputs"]),
    actionOutput: scope(ACTION_OUTPUT_SPEC, ["definitions", "outputs-composite"]),
    branding: scope(BRANDING_SPEC, ["properties", "branding"]),
  },
};

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
});
