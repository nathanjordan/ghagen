import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    globals: false,
    environment: "node",
    restoreMocks: true,
    // Headroom over the *tests'* own deadlines, not a blanket "things are
    // slow" allowance.
    //
    // `src/pin/transport-contract.ts` builds the adapter under test with
    // `RESPONSE_DEADLINE_MS = 5000` for every response row, which tied exactly
    // with vitest's default `testTimeout` of 5000. A stalled response row then
    // raced the runner against the transport's own deadline, and the runner
    // winning reported `Test timed out in 5000ms` -- destroying the failure
    // the harness exists to produce (a `TransportError` at the deadline) and
    // pointing at the runner instead of at the transport.
    //
    // 15s is 3x the longest deadline any test builds, so the test-owned
    // deadline always fires first and stays the thing under assertion. This
    // cannot mask a hang: the transport rows are bounded by their own 5000ms
    // deadline, and no other test in the suite runs longer than ~250ms.
    testTimeout: 15_000,
  },
});
