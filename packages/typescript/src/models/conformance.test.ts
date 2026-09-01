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
 * surface agreement, structurally. Every entry is asserted three ways: a
 * listed name must still be upstream ("stale"), must still be uncovered by the
 * model ("closed" -- catching a gap that was fixed without deleting the row),
 * and the file's own top-level snapshot/scope keys must match the sweep
 * exactly ("gap set matches the sweep" -- catching a garbled key, which an
 * empty allow-list under it would otherwise hide).
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { parse } from "yaml";
import { SCHEMA_DIR } from "../paths.js";
import { withComment, type ModelKind, type ModelSpec } from "./_base.js";
import { imageSnapshot } from "./image-snapshot.js";
import { SPECS_BY_KIND } from "./registry.js";

const GAPS_PATH = resolve(SCHEMA_DIR, "conformance-gaps.yml");
const SCOPES_PATH = resolve(SCHEMA_DIR, "conformance-scopes.yml");
const VALUES_PATH = resolve(SCHEMA_DIR, "conformance-values.yml");
const KEY_ORDER_PATH = resolve(SCHEMA_DIR, "key-order.yml");

/**
 * A JSON path into a loaded schema: the keys to walk before reading props.
 *
 * Integer segments index into a list — ten of the workflow scopes name a
 * `oneOf` alternative positionally (`properties.on.oneOf[2]`,
 * `definitions.snapshot.oneOf[1]`), and there is no other way to reach either.
 */
type SchemaPath = readonly (string | number)[];

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
    workflow: SPECS_BY_KIND.workflow,
    // ghagen's single job model covers both the regular-job and the
    // reusable-workflow-call-job shapes.
    job: SPECS_BY_KIND.job,
    step: SPECS_BY_KIND.step,
    // --- the on: sub-tree ---
    on: SPECS_BY_KIND.on,
    pushTrigger: SPECS_BY_KIND.pushTrigger,
    // One spec covers both `pull_request` and `pull_request_target`.
    prTrigger: SPECS_BY_KIND.prTrigger,
    scheduleTrigger: SPECS_BY_KIND.scheduleTrigger,
    workflowDispatch: SPECS_BY_KIND.workflowDispatch,
    workflowDispatchInput: SPECS_BY_KIND.workflowDispatchInput,
    workflowCall: SPECS_BY_KIND.workflowCall,
    workflowCallInput: SPECS_BY_KIND.workflowCallInput,
    workflowCallOutput: SPECS_BY_KIND.workflowCallOutput,
    workflowCallSecret: SPECS_BY_KIND.workflowCallSecret,
    // --- job sub-shapes ---
    permissions: SPECS_BY_KIND.permissions,
    container: SPECS_BY_KIND.container,
    strategy: SPECS_BY_KIND.strategy,
    concurrency: SPECS_BY_KIND.concurrency,
    defaults: SPECS_BY_KIND.defaults,
    defaultsRun: SPECS_BY_KIND.defaultsRun,
    environment: SPECS_BY_KIND.environment,
    imageSnapshot: SPECS_BY_KIND.imageSnapshot,
  },
  "action_schema.json": {
    action: SPECS_BY_KIND.action,
    compositeRuns: SPECS_BY_KIND.compositeRuns,
    dockerRuns: SPECS_BY_KIND.dockerRuns,
    nodeRuns: SPECS_BY_KIND.nodeRuns,
    actionInput: SPECS_BY_KIND.actionInput,
    actionOutput: SPECS_BY_KIND.actionOutput,
    branding: SPECS_BY_KIND.branding,
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
    node = (node as Record<string | number, unknown>)[key];
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

        // A gap entry claims the model does NOT cover this name. If the model
        // now covers it, the gap has been closed and the row is stale in the
        // other direction -- this is what makes a recorded gap a *test that
        // the gap still exists*, so closing it forces the table to be updated.
        const closed = [...allow].filter((a) => covered.has(a)).sort();
        expect(
          closed,
          `${snapshot}:${scopeName} allow-list names ${JSON.stringify(closed)} that ` +
            `the model now covers -- the gap has been closed. Remove them from ` +
            `conformance-gaps.yml.`,
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

  it("gap set matches the sweep", () => {
    // Mirrors the Python guard (test_gap_set_matches_sweep). The per-scope
    // test above reads `gaps[snapshotKey]?.[scopeName] ?? []`, which silently
    // treats a garbled or missing key as "no gaps recorded" -- invisible when
    // that key's allow-list is empty anyway, which is exactly this file's
    // current state. This guard makes the file's shape itself load-bearing:
    // every snapshot and scope key the sweep binds must appear here and vice
    // versa, so renaming or dropping a top-level key (e.g. `workflow_schema`
    // -> `workflow_schemas`) fails here.
    const sweepKeys = Object.keys(SWEEP).map((snapshot) => snapshot.replace(/\.json$/, ""));
    expect(sweepKeys.sort()).toEqual(Object.keys(gaps).sort());
    for (const [snapshot, scopes] of Object.entries(SWEEP)) {
      const key = snapshot.replace(/\.json$/, "");
      expect(
        Object.keys(scopes).sort(),
        `${key} scope keys in conformance-gaps.yml diverge from the sweep`,
      ).toEqual(Object.keys(gaps[key] ?? {}).sort());
    }
  });
});

// ---------------------------------------------------------------------------
// Key-order sweep. The scope table above covers *which properties* a model
// exposes, as a SET -- `modelPropertyNames` returns a `Set`, so it never sees
// the sequence. Every order guard in either port is intra-port and compares a
// spec's emitted sequence to its own field map, which passes by construction.
// Permuting `DEFAULTS_RUN_SPEC.fieldMap` against `DefaultsRun.yaml_keys`
// therefore changed this port's emitted YAML with both suites entirely green.
//
// The shared table is schema/key-order.yml, read identically by the Python
// sweep; only the kind -> spec binding stays here. Together with
// `spec.test.ts`'s "emitted key sequence equals fieldMap declaration order",
// the chain is closed in both ports: shared table == fieldMap == emitted.
// ---------------------------------------------------------------------------

interface KeyOrderEntry {
  readonly order: "explicit" | "alphabetical";
  readonly keys: readonly string[];
}

function loadKeyOrder(): Record<string, KeyOrderEntry> {
  return parse(readFileSync(KEY_ORDER_PATH, "utf8")) as Record<string, KeyOrderEntry>;
}

describe("cross-port key order", () => {
  const table = loadKeyOrder();

  it("model-kind set matches the shared key-order table", () => {
    // Mirrored by the Python guard of the same name. The table covers all 30
    // kinds -- two more than the conformance scope table, which has no scope
    // for `matrix` or `service`.
    expect(Object.keys(SPECS_BY_KIND).sort()).toEqual(Object.keys(table).sort());
  });

  for (const [kind, entry] of Object.entries(table)) {
    it(`${kind} matches the shared key sequence`, () => {
      const spec = SPECS_BY_KIND[kind as ModelKind] as ModelSpec | undefined;
      expect(spec, `no spec bound to kind ${kind}`).toBeDefined();
      if (spec === undefined) {
        return;
      }
      expect(spec.order ?? "explicit", `${kind} OrderMode`).toBe(entry.order);
      // `alphabetical` leaves declaration order unread -- the Emitter sorts at
      // emit time -- so the table states the SORTED sequence for `on` and the
      // declared list is sorted to meet it. Asserting the raw declaration for
      // `on` would bind a sequence nothing observes.
      const declared = Object.values(spec.fieldMap);
      const emitted = entry.order === "alphabetical" ? [...declared].sort() : declared;
      expect(emitted, `${kind} key sequence`).toEqual([...entry.keys]);
    });
  }
});

// ---------------------------------------------------------------------------
// Value-grammar sweep. The scope table above covers *which properties* a model
// exposes; this covers *which values* a field accepts. The shared table is
// schema/conformance-values.yml, read identically by the Python sweep; only the
// spec + constructor binding stays here.
// ---------------------------------------------------------------------------

interface ValueEntry {
  /** Walks to a pattern *string*, so it ends one segment deeper than a scope path. */
  readonly path: SchemaPath;
  readonly accept: readonly string[];
  readonly reject: readonly string[];
  /** Values that must still be refused when wrapped in `withComment(...)`. */
  readonly reject_commented: readonly string[];
}

interface ValueBinding {
  readonly spec: ModelSpec;
  /** Construct the model with `value` in the bound field. Throws on reject. */
  readonly construct: (value: string) => unknown;
  /**
   * Construct with `withComment(value, …)` in the bound field. A comment
   * wrapper is presentation, not content, so it must not change what the
   * grammar accepts — the `reject_commented` vectors bind that in both ports.
   */
  readonly constructCommented: (value: string) => unknown;
}

// snapshot filename -> `<kind>.<field>` -> this port's spec + constructor. The
// key format is exactly `spec.kind` plus a `patterns` key, so the shared table
// *is* the spec data under one join.
const VALUE_BINDINGS: Record<string, Record<string, ValueBinding>> = {
  "workflow_schema.json": {
    "imageSnapshot.version": {
      spec: SPECS_BY_KIND.imageSnapshot,
      construct: (version) => imageSnapshot({ imageName: "img", version }),
      constructCommented: (version) =>
        imageSnapshot({ imageName: "img", version: withComment(version, "note") }),
    },
  },
};

function loadValues(): Record<string, Record<string, ValueEntry>> {
  return parse(readFileSync(VALUES_PATH, "utf8")) as Record<string, Record<string, ValueEntry>>;
}

function resolveValuePath(schema: Record<string, unknown>, path: SchemaPath): unknown {
  let node: unknown = schema;
  for (const key of path) {
    node = (node as Record<string | number, unknown>)[key];
  }
  return node;
}

/**
 * A bound pattern's source must start with `^` and end with `$`.
 *
 * TypeScript enforces value grammars with `pattern.test` (`models/_base.ts`),
 * which depends on the anchors entirely -- unlike Python's `fullmatch`
 * (`GhagenModel._enforce_spec_patterns`), for which they are redundant. The
 * two ports therefore agree today only by coincidence of every current
 * pattern happening to be anchored. The next grammar copied from a JSON
 * Schema `pattern` -- where *unanchored* is the norm -- would make
 * TypeScript accept a value Python rejects, with nothing catching the
 * divergence (issue 28 #3). This assertion is what closes that gap.
 */
function assertPatternAnchored(pattern: RegExp, key: string): void {
  const src = pattern.source;
  const anchored = src.startsWith("^") && src.endsWith("$");
  expect(
    anchored,
    `${key} pattern ${JSON.stringify(src)} is not anchored with ^ and $. ` +
      "TypeScript's pattern.test() depends on the anchors entirely, but " +
      "Python's fullmatch() (models/_base.py) does not need them -- " +
      "without them the two ports would validate this field differently. " +
      "Add ^ and $ to the pattern, or wrap the RegExp as ^(?:...)$ so the " +
      "anchors stop being load-bearing in either port.",
  ).toBe(true);
}

describe("value-grammar pattern anchoring", () => {
  // Direct proof `assertPatternAnchored` catches what it must. The sweep
  // below only ever sees today's real bindings, which are already anchored
  // -- so on its own it can never turn red. This constructs the exact input
  // the sweep cannot currently produce (an unanchored pattern) and confirms
  // the assertion actually fails it, rather than passing by construction.
  it("rejects an unanchored pattern", () => {
    expect(() => assertPatternAnchored(/\d+/, "synthetic.field")).toThrow(/not anchored/);
  });

  it("accepts an anchored pattern", () => {
    expect(() => assertPatternAnchored(/^\d+$/, "synthetic.field")).not.toThrow();
  });
});

describe("schema value-grammar sweep", () => {
  const values = loadValues();

  for (const [snapshot, entries] of Object.entries(values)) {
    const schema = loadSchema(snapshot);

    for (const [key, entry] of Object.entries(entries)) {
      const binding = VALUE_BINDINGS[snapshot]?.[key];
      if (binding === undefined) {
        continue; // the parity guard below is the failure surface
      }
      const field = key.slice(key.indexOf(".") + 1);

      it(`${snapshot}:${key} pattern matches the canonical Snapshot`, () => {
        const pattern = binding.spec.patterns?.[field];
        expect(pattern, `${key} declares no pattern in its ModelSpec`).toBeDefined();
        expect(pattern?.source).toBe(resolveValuePath(schema, entry.path));
        // A `/g` pattern makes `RegExp.test` stateful across calls.
        expect(pattern?.flags, `${key} pattern must carry no flags`).toBe("");
      });

      it(`${snapshot}:${key} pattern is anchored with ^ and $`, () => {
        const pattern = binding.spec.patterns?.[field];
        expect(pattern, `${key} declares no pattern in its ModelSpec`).toBeDefined();
        assertPatternAnchored(pattern as RegExp, key);
      });

      it(`${snapshot}:${key} accepts every schema-valid vector`, () => {
        for (const value of entry.accept) {
          expect(
            () => binding.construct(value),
            `${key} rejected ${JSON.stringify(value)}`,
          ).not.toThrow();
        }
      });

      it(`${snapshot}:${key} rejects every schema-invalid vector`, () => {
        for (const value of entry.reject) {
          expect(
            () => binding.construct(value),
            `${key} accepted ${JSON.stringify(value)}`,
          ).toThrow();
        }
      });

      it(`${snapshot}:${key} holds the grammar under a comment wrapper`, () => {
        // A comment wrapper changes presentation, never what the grammar
        // accepts. `buildYamlData` peels the wrapper before testing the
        // pattern; Python's `_enforce_spec_patterns` peels it too (it used not
        // to, and every one of these vectors constructed successfully there).
        for (const value of entry.accept) {
          expect(
            () => binding.constructCommented(value),
            `${key} rejected commented ${JSON.stringify(value)}`,
          ).not.toThrow();
        }
        for (const value of entry.reject_commented) {
          expect(
            () => binding.constructCommented(value),
            `${key} accepted commented ${JSON.stringify(value)}`,
          ).toThrow();
        }
      });
    }
  }

  it("value-grammar key set matches the shared value table", () => {
    // Mirrors the Python guard (test_value_key_set_matches_shared_table): a
    // grammar enforced in one port and not the other fails here.
    const shared = loadValues();
    expect(Object.keys(VALUE_BINDINGS).sort()).toEqual(Object.keys(shared).sort());
    for (const snapshot of Object.keys(shared)) {
      expect(
        Object.keys(VALUE_BINDINGS[snapshot]).sort(),
        `${snapshot} value grammars diverge from conformance-values.yml`,
      ).toEqual(Object.keys(shared[snapshot]).sort());
    }
  });
});
