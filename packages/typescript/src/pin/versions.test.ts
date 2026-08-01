/**
 * Tests for pin/versions — a driver over the shared tag grammar table.
 *
 * The accept-set, the canonical release, the total order, the prefix filter
 * and the severity classification are declared once in
 * `schema/tag-grammar.yml` and read here *and* by the Python suite
 * (`packages/python/tests/test_pin/test_versions.py`). Both ports held to the
 * same table means both implement the same grammar — cross-port behaviour
 * agreement, structurally.
 *
 * Each section carries a consumed-every-key guard, mirroring the scope-key
 * parity assertion the conformance sweeps already use: a row this driver does
 * not run fails a test, so a case added for one port cannot silently skip the
 * other.
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { parse } from "yaml";
import { SCHEMA_DIR } from "../paths.js";
import { latestBump, parseTag } from "./versions.js";

/** One row of the shared `parse` map: the expected `ParsedTag`, or null. */
interface ParseRow {
  readonly prefix: string | null;
  readonly release: readonly number[];
}

/** One row of the shared `compare` list: inputs plus the expected `Bump`. */
interface CompareRow {
  readonly current: string;
  readonly available: readonly string[];
  readonly latest: string | null;
  readonly severity?: "major" | "minor" | "patch";
}

interface Table {
  readonly parse: Record<string, ParseRow | null>;
  readonly compare: readonly CompareRow[];
}

const TABLE_PATH = resolve(SCHEMA_DIR, "tag-grammar.yml");
const TABLE = parse(readFileSync(TABLE_PATH, "utf8")) as Table;

const PARSE_CASES: readonly (readonly [string, ParseRow | null])[] = Object.entries(
  TABLE.parse,
).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0));

const COMPARE_CASES: readonly (readonly [number, CompareRow])[] = TABLE.compare.map(
  (row, i) => [i, row] as const,
);

describe("parseTag() — the shared tag grammar", () => {
  for (const [tag, expected] of PARSE_CASES) {
    it(`parses ${JSON.stringify(tag)}`, () => {
      const parsed = parseTag(tag);
      if (expected === null) {
        expect(parsed).toBeNull();
      } else {
        expect(parsed).not.toBeNull();
        expect(parsed!.tag).toBe(tag);
        expect(parsed!.prefix).toBe(expected.prefix);
        expect([...parsed!.release]).toEqual([...expected.release]);
      }
    });
  }

  it("drives every row of the shared parse map", () => {
    expect(PARSE_CASES.map(([tag]) => tag).sort()).toEqual(Object.keys(TABLE.parse).sort());
  });
});

describe("latestBump() — the shared tag grammar", () => {
  for (const [i, row] of COMPARE_CASES) {
    it(`compare row ${i} (${row.current})`, () => {
      const bump = latestBump(row.current, row.available);
      if (row.latest === null) {
        expect(bump).toBeNull();
      } else {
        expect(bump).not.toBeNull();
        expect(bump!.current.tag).toBe(row.current);
        expect(bump!.latest.tag).toBe(row.latest);
        expect(bump!.severity).toBe(row.severity);
      }
    });
  }

  it("drives every row of the shared compare list", () => {
    expect(COMPARE_CASES.map(([, row]) => row)).toEqual([...TABLE.compare]);
  });
});
