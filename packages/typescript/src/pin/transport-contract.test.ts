/**
 * The transport conformance table, run against every adapter in the repo.
 *
 * `FetchTransport` runs the full table in front of a raw loopback socket — the
 * first coverage the production adapter has ever had. `FakeTransport` runs the
 * response rows, so the double cannot drift into a shape the real adapter is
 * unable to produce.
 */

import { describe, it } from "vitest";
import { FetchTransport } from "./github.js";
import {
  ALL_CASES,
  RESPONSE_CASES,
  cannedAdapter,
  caseId,
  loopbackAdapter,
  runTransportContract,
} from "./transport-contract.js";

describe("FetchTransport conforms to the transport contract", () => {
  for (const testCase of ALL_CASES) {
    it(caseId(testCase), async () => {
      await runTransportContract(
        loopbackAdapter((deadlineMs) => new FetchTransport(deadlineMs)),
        [testCase],
      );
    });
  }
});

describe("FakeTransport conforms to the transport contract", () => {
  for (const testCase of RESPONSE_CASES) {
    it(caseId(testCase), async () => {
      await runTransportContract(cannedAdapter(), [testCase]);
    });
  }
});
