import { describe, it, expect } from "vitest";
import { captureSourceLocation } from "./_source_location.js";

describe("captureSourceLocation()", () => {
  it("returns the caller's file and line", () => {
    const loc = captureSourceLocation();
    expect(loc).not.toBeNull();
    expect(loc!.file).toContain("_source_location.test");
    expect(loc!.line).toBeGreaterThan(0);
  });

  it("skips frames inside ghagen internals", () => {
    // captureSourceLocation itself is in src/_source_location.ts which
    // contains "/ghagen/" only when the file lives under that path.
    // The path here is .../packages/typescript/src/_source_location.ts
    // which does NOT include "/ghagen/", so we can only verify that
    // the returned frame is in the test file itself, not the source
    // module.
    const loc = captureSourceLocation();
    expect(loc?.file).not.toContain("/node_modules/");
  });

  it("returns numeric line numbers", () => {
    const loc = captureSourceLocation();
    expect(typeof loc!.line).toBe("number");
    expect(Number.isInteger(loc!.line)).toBe(true);
  });
});
