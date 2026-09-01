/**
 * The walk oracle: `parse(toYaml(doc))` must equal `toData(doc)` for every
 * fixture document.
 *
 * `toData` and `toYaml` are two renderings of one collection stage
 * (`emitEntries`). This sweep is what makes that claim testable on real
 * documents: it runs over the same `fixture-models.ts` list the byte oracle in
 * `snapshots.test.ts` runs over, so any decision the shared stage owns —
 * membership, YAML keys, order, the extras merge, the Step `run` dedent,
 * present-null — that the two renderings resolve differently fails here.
 *
 * The cross-check it replaces was a single hand-built document: an existence
 * proof over the shapes its author happened to remember (docs/issues/01). That
 * document is kept, in `emitter/to-data.test.ts`, because it deliberately packs
 * shapes no fixture contains.
 *
 * Comments are dropped by a YAML parse, so the comparison runs with comments
 * off — the default. `autoDedent` is left at its default too, which is
 * `toYaml`'s.
 *
 * Peer: `packages/python/tests/test_integration/test_to_data_sweep.py`.
 */
import { readdirSync } from "node:fs";
import { describe, it, expect } from "vitest";
import { parse } from "yaml";
import { toData, toYaml } from "../emitter/yaml-writer.js";
import { EXPECTED_DIR } from "../paths.js";
import { ALL_FIXTURE_DOCS, UNBOUND_DOC_FIXTURES } from "./fixture-models.js";

/**
 * Fixture files under `fixtures/expected/` that are not emitter documents at
 * all, so no model produces them and the sweep is not shrinking by leaving them
 * out. The lockfile goldens come from the pin lockfile serializer, not the
 * model emitter; the rest are not YAML.
 */
const NON_DOCUMENT_FIXTURES = new Set([
  "lockfile_golden.yml",
  "lockfile_key_quoting.yml",
  "lockfile_space_separator_rejected.yml",
]);

describe("toData matches the emitted YAML for every fixture document", () => {
  for (const doc of ALL_FIXTURE_DOCS) {
    it(doc.fixture, () => {
      const model = doc.build();
      const parsed = parse(toYaml(model, { header: doc.header })) as Record<string, unknown>;
      // `postProcess` runs on the backend node, so it is in the YAML and, by
      // contract, never in `toData`. Subtract its effect — asserting it was
      // there, so the subtraction cannot hide a real difference.
      for (const key of doc.postProcessRootKeys ?? []) {
        expect(parsed).toHaveProperty(key);
        delete parsed[key];
      }
      expect(toData(model)).toEqual(parsed);
    });
  }

  // The sweep's edge, asserted rather than described: every `.yml` under
  // `fixtures/expected/` is either swept above, a known non-document, or
  // listed as unbound with a reason. A new fixture lands in none of the three
  // and fails here, so the set cannot quietly shrink.
  it("accounts for every .yml fixture", () => {
    const swept = new Set(ALL_FIXTURE_DOCS.map((d) => d.fixture));
    const unbound = new Set(UNBOUND_DOC_FIXTURES);
    const unaccounted = readdirSync(EXPECTED_DIR)
      .filter((name) => name.endsWith(".yml"))
      .filter((name) => !swept.has(name) && !unbound.has(name) && !NON_DOCUMENT_FIXTURES.has(name));
    expect(unaccounted).toEqual([]);
  });
});
