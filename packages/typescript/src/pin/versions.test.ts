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
 * Each section carries a consumed-every-row guard, mirroring the scope-key
 * parity assertion the conformance sweeps already use: a row this driver does
 * not *execute* fails a test, so a case added for one port cannot silently
 * skip the other. The guards compare the ids the test bodies recorded against
 * the file read fresh from disk — never two views of the same in-memory
 * object, which is a comparison that cannot fail.
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

/**
 * Row ids the drivers below actually ran, recorded by the test bodies.
 *
 * The guards at the end of each block compare these against the table read
 * fresh from disk. Comparing the collected-cases list against `TABLE` instead
 * would be a tautology — both sides come from the same object, so a driver
 * that is handed every row and quietly declines to check some of them (an
 * early `return`, a body that ignores its argument, a case list that was
 * sliced) still looks complete. Only what a body executed counts as driven.
 */
const drivenParse = new Set<string>();
const drivenCompare = new Set<number>();

/** The table as it is on disk right now, read independently of `TABLE`. */
function tableOnDisk(): Table {
  return parse(readFileSync(TABLE_PATH, "utf8")) as Table;
}

describe("parseTag() — the shared tag grammar", () => {
  for (const [tag, expected] of PARSE_CASES) {
    it(`parses ${JSON.stringify(tag)}`, () => {
      drivenParse.add(tag);
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

  // Registered last, so it runs after the drivers above; it is meaningful
  // only in a whole-file run.
  it("checks every row of the shared parse map", () => {
    expect([...drivenParse].sort()).toEqual(Object.keys(tableOnDisk().parse).sort());
  });
});

describe("latestBump() — the shared tag grammar", () => {
  for (const [i, row] of COMPARE_CASES) {
    it(`compare row ${i} (${row.current})`, () => {
      drivenCompare.add(i);
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

  it("checks every row of the shared compare list", () => {
    expect([...drivenCompare].sort((a, b) => a - b)).toEqual(
      tableOnDisk().compare.map((_, i) => i),
    );
  });
});
