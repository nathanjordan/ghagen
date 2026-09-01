/**
 * Snapshot tests: compare generated YAML against the stored expected output.
 *
 * The models are not written here — they live in `fixture-models.ts`, the one
 * binding from a fixture file to the model that produces it, so the walk sweep
 * in `to-data-sweep.test.ts` runs over exactly the documents this oracle
 * covers rather than over a second hand-built list.
 *
 * Peer: `packages/python/tests/test_integration/test_snapshots.py`.
 */
import { describe, it, expect } from "vitest";
import { loadFixture } from "./test-utils.js";
import { toYaml } from "../emitter/yaml-writer.js";
import { HEADER_GOLDENS, SNAPSHOT_DOCS } from "./fixture-models.js";

describe("snapshot tests", () => {
  for (const doc of SNAPSHOT_DOCS) {
    it(doc.fixture, () => {
      expect(toYaml(doc.build(), { header: doc.header })).toBe(loadFixture(doc.fixture));
    });
  }
});

// ---------------------------------------------------------------------------
// Header goldens — the cross-port byte oracle for `formatHeader`.
//
// The six files are generated from the Python port and read byte-for-byte by
// both suites; every byte that differs between them is header. Peer:
// `packages/python/tests/test_integration/test_snapshots.py`.
// ---------------------------------------------------------------------------
describe("header goldens", () => {
  for (const doc of HEADER_GOLDENS) {
    it(doc.fixture, () => {
      const out = toYaml(doc.build(), { header: doc.header });
      expect(out).toBe(loadFixture(doc.fixture));
      if (doc.fixture === "header_crlf.yml") {
        // CRLF and a bare CR are both line breaks: no CR may survive.
        expect(out).not.toContain("\r");
      }
    });
  }
});
