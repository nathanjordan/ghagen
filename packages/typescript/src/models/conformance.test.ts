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
import { raw, type ModelKind, type ModelSpec } from "./_base.js";
import { VALUE_BINDINGS } from "./conformance-values.js";
import { CONSTRAINT_BINDINGS, INPUT_BINDINGS } from "./conformance-inputs.js";
import { SPECS_BY_KIND } from "./registry.js";

const GAPS_PATH = resolve(SCHEMA_DIR, "conformance-gaps.yml");
const SCOPES_PATH = resolve(SCHEMA_DIR, "conformance-scopes.yml");
const VALUES_PATH = resolve(SCHEMA_DIR, "conformance-values.yml");
const INPUTS_PATH = resolve(SCHEMA_DIR, "conformance-inputs.yml");
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
    serviceContainer: SPECS_BY_KIND.service,
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

/**
 * Reserved top-level key in conformance-gaps.yml holding cross-field
 * constraint gaps rather than per-scope property gaps. It is not a snapshot,
 * so the property-gap sweep and its key-set guard must both skip it.
 */
const CONSTRAINTS_KEY = "constraints";

/**
 * Reserved top-level key in conformance-gaps.yml holding the gaps in the OTHER
 * direction -- emitted keys the Snapshot does not declare for their scope (see
 * "scope emits only declared keys"). Not a snapshot either, so the property-gap
 * sweep and its key-set guard skip it too.
 */
const UNDECLARED_KEY = "undeclared";

/** Every reserved (non-snapshot) top-level key in conformance-gaps.yml. */
const RESERVED_KEYS: readonly string[] = [CONSTRAINTS_KEY, UNDECLARED_KEY];

function loadSchema(filename: string): Record<string, unknown> {
  return JSON.parse(readFileSync(resolve(SCHEMA_DIR, filename), "utf8"));
}

/** The whole gaps document, reserved sections included. */
function loadGapsFile(): Record<string, unknown> {
  return parse(readFileSync(GAPS_PATH, "utf8")) as Record<string, unknown>;
}

/** Only the per-snapshot property-gap sections. */
function loadGaps(): Gaps {
  const doc = loadGapsFile();
  return Object.fromEntries(
    Object.entries(doc).filter(([key]) => !RESERVED_KEYS.includes(key)),
  ) as Gaps;
}

/** The `undeclared` section: snapshot -> scope -> emitted-but-unbacked. */
function loadUndeclared(): Gaps {
  return loadGapsFile()[UNDECLARED_KEY] as Gaps;
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
// The sweep in the other direction: model keys must be DECLARED upstream.
//
// The sweep above asserts upstream <= model -- every property the Snapshot
// declares is emitted by some model, or allow-listed. It says nothing about the
// reverse. This port has a compile-time answer to the reverse for SOME specs:
// `satisfies Record<keyof StepInput, keyof SchemaStep>` binds each emitted key
// to a property name the generated type declares, so a typo is TS2322 and an
// upstream rename is TS2724 -- which is exactly how the 2026-09-01 refresh's
// `definitions.container` -> `jobContainer`/`serviceContainer` split surfaced.
// But there are seven such clauses, covering eight of this sweep's twenty-nine
// scopes, and Python (whose `yaml_keys` values are free strings, ADR-0003 having deleted
// the generated models) had no peer for any of them: `"shell": "shel"` passed
// every check in the family while ghagen emitted a workflow the platform
// refuses. This is the peer, for every scope, in both ports. Mirrored by the
// Python sweep (`test_scope_emits_only_declared_keys`).
// ---------------------------------------------------------------------------

describe("undeclared-key sweep", () => {
  const undeclared = loadUndeclared();

  for (const [snapshot, scopes] of Object.entries(SWEEP)) {
    const snapshotKey = snapshot.replace(/\.json$/, "");
    const schema = loadSchema(snapshot);

    for (const [scopeName, s] of Object.entries(scopes)) {
      it(`${snapshot}:${scopeName} scope emits only declared keys`, () => {
        const props = schemaProperties(schema, s);
        const emitted = modelPropertyNames(s.spec);
        const allow = new Set(undeclared[snapshotKey]?.[scopeName] ?? []);

        const invented = [...emitted].filter((k) => !props.has(k) && !allow.has(k)).sort();
        expect(
          invented,
          `${snapshot}:${scopeName} spec emits keys the Snapshot does not declare for ` +
            `this scope: ${JSON.stringify(invented)}. Fix the fieldMap, or record them ` +
            `under \`undeclared\` in conformance-gaps.yml with the reason they are ` +
            `emitted anyway.`,
        ).toEqual([]);

        // Claim 1: the row is still needed -- the model still emits this key.
        const closed = [...allow].filter((a) => !emitted.has(a)).sort();
        expect(
          closed,
          `${snapshot}:${scopeName} \`undeclared\` names ${JSON.stringify(closed)} that ` +
            `the spec no longer emits. Remove them from conformance-gaps.yml.`,
        ).toEqual([]);

        // Claim 2: the key is still un-upstream. The day the Snapshot declares
        // it, the exception has become ordinary coverage and the row must go.
        const backed = [...allow].filter((a) => props.has(a)).sort();
        expect(
          backed,
          `${snapshot}:${scopeName} \`undeclared\` names ${JSON.stringify(backed)} that ` +
            `the Snapshot now declares -- the exception is no longer one. Remove them ` +
            `from conformance-gaps.yml.`,
        ).toEqual([]);
      });
    }
  }

  it("undeclared set matches the sweep", () => {
    // Claim 3, and the peer of "gap set matches the sweep": the test above
    // reads `undeclared[snapshotKey]?.[scopeName] ?? []`, so a garbled key
    // would read as "no exceptions recorded" -- which is this section's entire
    // current content, and therefore invisible.
    const sweepKeys = Object.keys(SWEEP).map((snapshot) => snapshot.replace(/\.json$/, ""));
    expect(sweepKeys.sort()).toEqual(Object.keys(undeclared).sort());
    for (const [snapshot, scopes] of Object.entries(SWEEP)) {
      const key = snapshot.replace(/\.json$/, "");
      expect(
        Object.keys(scopes).sort(),
        `${key} scope keys under \`undeclared\` in conformance-gaps.yml diverge from the sweep`,
      ).toEqual(Object.keys(undeclared[key] ?? {}).sort());
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

// `ValueBinding` and `VALUE_BINDINGS` live in `./conformance-values.ts`, a
// plain (non-`.test.ts`) source file, not here -- see that file's doc comment
// for why: `tsconfig.json` excludes `src/**/*.test.ts` from `tsc --noEmit`,
// so a binding defined in this file would never be type-checked, and the
// raw-hatch check below would pass regardless of whether the bound field's
// declared type actually admits `Raw`.

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

      it(`${snapshot}:${key} accepts a raw() value in place of the grammar`, () => {
        // A field carrying a spec pattern MUST admit `raw()` -- see issue 22.
        // `buildYamlData` skips the grammar check for a non-string value
        // specifically so `raw()` stays the escape hatch, and the
        // grammar-violation message (`models/_base.ts`) tells the caller
        // exactly that. That advice is only true if the field's declared
        // type actually accepts a `Raw`. TypeScript has no runtime type
        // information to inspect (unlike Python's
        // `model_fields[field].annotation`), so this executes the same path
        // a caller acting on the message would: every `reject` vector,
        // wrapped in `raw(...)` instead of passed bare, must still
        // construct. A field typed to exclude `Raw` fails this with a thrown
        // `ModelInputError` instead of silently shipping a false promise.
        for (const value of entry.reject) {
          expect(
            () => binding.construct(raw(value)),
            `${key} rejected raw(${JSON.stringify(value)})`,
          ).not.toThrow();
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

// ---------------------------------------------------------------------------
// Input-TYPE sweep. The scope table binds which properties a model exposes; the
// value table binds the grammar of the string fields that declare one. Neither
// binds a field's accepted TYPE UNION, which is the axis the two ports actually
// drifted on (issue 27). The shared table is schema/conformance-inputs.yml,
// read identically by the Python sweep; the spec + constructor + typed-literal
// binding lives in `./conformance-inputs.ts` -- a plain `src/` module, because
// `tsconfig.json` excludes `src/**/*.test.ts` from `tsc --noEmit` and the
// reject direction of this sweep IS the compiler. See that file's header.
// ---------------------------------------------------------------------------

interface InputRef {
  readonly path: SchemaPath;
  readonly value: string;
}

interface InputEntry {
  /** The key this field emits; each port asserts its own spec maps to it. */
  readonly yaml_key: string;
  /** Paths, each resolving to a JSON-Schema `type` token or a list of them. */
  readonly type_paths: readonly SchemaPath[];
  /** The sorted union of what `type_paths` resolve to. */
  readonly types: readonly string[];
  /** Optional: a path plus the exact `$ref` string it must hold. */
  readonly ref?: InputRef;
  readonly accept: readonly unknown[];
  readonly reject: readonly unknown[];
}

function loadInputs(): Record<string, Record<string, InputEntry>> {
  return parse(readFileSync(INPUTS_PATH, "utf8")) as Record<string, Record<string, InputEntry>>;
}

/** The sorted union of the JSON-Schema type tokens at `type_paths`. */
function snapshotTypeUnion(schema: Record<string, unknown>, entry: InputEntry): string[] {
  const types = new Set<string>();
  for (const path of entry.type_paths) {
    const node = resolveValuePath(schema, path);
    if (typeof node === "string") {
      types.add(node);
    } else {
      for (const token of node as string[]) {
        types.add(token);
      }
    }
  }
  return [...types].sort();
}

describe("schema input-type sweep", () => {
  const inputs = loadInputs();

  for (const [snapshot, entries] of Object.entries(inputs)) {
    const schema = loadSchema(snapshot);

    for (const [key, entry] of Object.entries(entries)) {
      const binding = INPUT_BINDINGS[snapshot]?.[key];
      if (binding === undefined) {
        continue; // the parity guard below is the failure surface
      }

      it(`${snapshot}:${key} declared types match the canonical Snapshot`, () => {
        // The type-union analogue of the value sweep's pattern-identity check,
        // and what stops the shared table from being a wish. An upstream
        // narrowing -- or a typo in `types` -- fails here, in both ports.
        expect(snapshotTypeUnion(schema, entry)).toEqual([...entry.types]);
      });

      it(`${snapshot}:${key} field emits the shared yaml_key`, () => {
        // The shared key (`job.continueOnError`) uses one spelling for a field
        // the two ports name differently. This is what makes that safe: each
        // port names its own field in its own binding, and both assert the
        // field lands on the same emitted key.
        expect(
          binding.spec.fieldMap[binding.field],
          `${key}: this port maps ${binding.field} elsewhere`,
        ).toBe(entry.yaml_key);
      });

      if (entry.ref !== undefined) {
        const ref = entry.ref;
        it(`${snapshot}:${key} is still a bare $ref to the shared node`, () => {
          // Only the two `permissions` rows carry a `ref`, and there it is the
          // entire justification for one `PermissionsValue` alias serving both
          // the workflow-level and the job-level field. If upstream inlines or
          // splits `definitions.permissions`, one alias stops being the right
          // shape and this fails.
          expect(resolveValuePath(schema, ref.path)).toBe(ref.value);
        });
      }

      it(`${snapshot}:${key} accept vectors match the shared table`, () => {
        // This is the join between the compiler and the shared file. The
        // literals in `conformance-inputs.ts` are `satisfies readonly
        // <FieldType>[]`, so tsc has already ruled they are all in the field's
        // union; this asserts they are the SAME list the Python sweep
        // executes. Edit a vector in the YAML and this comparison fails here
        // while the construction fails there -- one shared byte, both suites.
        expect(binding.accept).toEqual(entry.accept);
      });

      it(`${snapshot}:${key} reject vectors match the shared table`, () => {
        // Same join for the reject direction, which has no runtime form in
        // this port. Each literal in `conformance-inputs.ts` sits under an
        // `@ts-expect-error`, so tsc has already ruled each one is OUTSIDE the
        // field's union (and reports an unused directive the moment the field
        // widens to admit it). This asserts the compiler ruled on the same
        // list Python's `pytest.raises` executes.
        expect(binding.reject).toEqual(entry.reject);
      });

      it(`${snapshot}:${key} constructs with every accept vector`, () => {
        // Weaker than Python's peer and deliberately kept anyway: it catches
        // an accept vector the RUNTIME rejects (a value grammar, a metadata
        // check), which the compile-time `satisfies` cannot see.
        for (const value of entry.accept) {
          expect(
            () => binding.construct(value),
            `${key} rejected ${JSON.stringify(value)}`,
          ).not.toThrow();
        }
      });
    }
  }

  it("input-type key set matches the shared input table", () => {
    // Mirrors the Python guard (test_input_key_set_matches_shared_table): a
    // type union bound in one port and not the other fails here.
    const shared = loadInputs();
    expect(Object.keys(INPUT_BINDINGS).sort()).toEqual(Object.keys(shared).sort());
    for (const snapshot of Object.keys(shared)) {
      expect(
        Object.keys(INPUT_BINDINGS[snapshot]).sort(),
        `${snapshot} input types diverge from conformance-inputs.yml`,
      ).toEqual(Object.keys(shared[snapshot]).sort());
    }
  });
});

// ---------------------------------------------------------------------------
// Cross-field constraint gaps -- the `constraints` section of
// conformance-gaps.yml. A property gap proves itself by the property's absence
// from the spec, a set-membership test. A cross-field constraint has no such
// footprint (both fields are present and both are typed), so the only proof
// the limit still exists is to construct the schema-invalid combination and
// watch it succeed.
// ---------------------------------------------------------------------------

interface ConstraintRequirement {
  readonly path: SchemaPath;
  readonly value: unknown;
}

interface ConstraintRow {
  readonly kind: string;
  readonly requires: readonly ConstraintRequirement[];
  readonly requires_prose: string;
  readonly unenforced: string;
  readonly counterexample: Record<string, unknown>;
}

function loadConstraints(): Record<string, Record<string, ConstraintRow>> {
  return loadGapsFile()[CONSTRAINTS_KEY] as Record<string, Record<string, ConstraintRow>>;
}

describe("cross-field constraint gaps", () => {
  const constraints = loadConstraints();

  for (const [snapshot, rows] of Object.entries(constraints)) {
    const schema = loadSchema(`${snapshot}.json`);

    for (const [key, row] of Object.entries(rows)) {
      const binding = CONSTRAINT_BINDINGS[snapshot]?.[key];
      if (binding === undefined) {
        continue; // the parity guard below is the failure surface
      }

      it(`${snapshot}:${key} rule still exists upstream`, () => {
        // Claim 1, the peer of the property rows' `stale` check: the row
        // cannot outlive the upstream rule it describes.
        for (const req of row.requires) {
          expect(
            resolveValuePath(schema, req.path),
            `${key}: the Snapshot no longer holds ${JSON.stringify(req.value)} at ` +
              `${JSON.stringify(req.path)} -- update or remove the row`,
          ).toEqual(req.value);
        }
      });

      it(`${snapshot}:${key} counterexample still type-checks`, () => {
        // Claim 2 for this port. The runtime half below is nearly vacuous here
        // -- TypeScript validates no declared input type at runtime, so almost
        // anything "constructs". The meaningful claim is the compile-time one:
        // `conformance-inputs.ts` declares this same object `satisfies` the
        // model's input type with NO `@ts-expect-error`, so it must compile.
        // Enforce the conditional with a discriminated union and that stops
        // compiling, forcing the row out. This assertion binds that literal to
        // the YAML row so corrupting either is visible.
        expect(binding.counterexample).toEqual(row.counterexample);
      });

      it(`${snapshot}:${key} counterexample still constructs`, () => {
        expect(() => binding.construct()).not.toThrow();
      });

      it(`${snapshot}:${key} row states its claim`, () => {
        // A gap row is a claim, so it must actually say what is unenforced.
        // An empty or placeholder prose field turns the row back into the
        // shrug it exists to replace.
        expect(row.requires_prose.length).toBeGreaterThan(120);
        expect(row.unenforced.length).toBeGreaterThan(120);
      });
    }
  }

  it("constraint gap key set matches the sweep", () => {
    // Claim 3, mirrored in the Python sweep: a constraint recorded against one
    // port only -- or a garbled key -- fails a test.
    const shared = loadConstraints();
    expect(Object.keys(CONSTRAINT_BINDINGS).sort()).toEqual(Object.keys(shared).sort());
    for (const snapshot of Object.keys(shared)) {
      expect(
        Object.keys(CONSTRAINT_BINDINGS[snapshot]).sort(),
        `${snapshot} constraint rows in conformance-gaps.yml diverge from the sweep`,
      ).toEqual(Object.keys(shared[snapshot]).sort());
    }
  });
});
