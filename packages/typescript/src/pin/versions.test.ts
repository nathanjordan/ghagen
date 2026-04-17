import { describe, it, expect } from "vitest";
import { SemVer } from "semver";
import { classifyBump, findLatestTag, parseTag } from "./versions.js";

// Cases ported from packages/python/tests/test_pin/test_versions.py
// to keep the two implementations in lockstep on tag-parsing behaviour.

describe("parseTag()", () => {
  it("parses bare integer (v4 → 4.0.0)", () => {
    expect(parseTag("v4")?.version.format()).toBe("4.0.0");
  });

  it("parses two-part (v4.1 → 4.1.0)", () => {
    expect(parseTag("v4.1")?.version.format()).toBe("4.1.0");
  });

  it("parses three-part (v4.1.2)", () => {
    expect(parseTag("v4.1.2")?.version.format()).toBe("4.1.2");
  });

  it("parses without v prefix (4.1.2)", () => {
    expect(parseTag("4.1.2")?.version.format()).toBe("4.1.2");
  });

  it("rejects branch names like main/master", () => {
    expect(parseTag("main")).toBeNull();
    expect(parseTag("master")).toBeNull();
  });

  it("rejects refs without numbers", () => {
    expect(parseTag("latest")).toBeNull();
  });

  it("parses prefix-v1.0.0", () => {
    const p = parseTag("prefix-v1.0.0");
    expect(p?.prefix).toBe("prefix");
    expect(p?.version.format()).toBe("1.0.0");
  });

  it("parses prefix/v1.0.0", () => {
    const p = parseTag("prefix/v1.0.0");
    expect(p?.prefix).toBe("prefix");
    expect(p?.version.format()).toBe("1.0.0");
  });

  it("rejects prefix/v1 (single-segment with prefix is branch-like)", () => {
    expect(parseTag("release/v1")).toBeNull();
  });
});

describe("classifyBump()", () => {
  it("major", () => {
    expect(
      classifyBump(new SemVer("4.0.0"), new SemVer("5.0.0")),
    ).toBe("major");
  });
  it("minor", () => {
    expect(
      classifyBump(new SemVer("4.0.0"), new SemVer("4.1.0")),
    ).toBe("minor");
  });
  it("patch", () => {
    expect(
      classifyBump(new SemVer("4.1.0"), new SemVer("4.1.1")),
    ).toBe("patch");
  });
});

describe("findLatestTag()", () => {
  it("finds the newest tag in the same prefix family", () => {
    expect(findLatestTag("v4", ["v3", "v4", "v4.1", "v5"])).toBe("v5");
  });

  it("returns null if current is already latest", () => {
    expect(findLatestTag("v5", ["v3", "v4", "v5"])).toBeNull();
  });

  it("ignores tags with a different prefix", () => {
    expect(findLatestTag("v4", ["release-v5", "v4.1"])).toBe("v4.1");
  });

  it("considers prefixed tags that share the same prefix", () => {
    expect(
      findLatestTag("release-v1.0.0", ["release-v1.1.0", "release-v2.0.0"]),
    ).toBe("release-v2.0.0");
  });

  it("returns null when current is unparseable", () => {
    expect(findLatestTag("main", ["v1", "v2"])).toBeNull();
  });
});
