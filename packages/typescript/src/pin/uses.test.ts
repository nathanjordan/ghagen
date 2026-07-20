import { describe, it, expect } from "vitest";
import { UsesRef } from "./uses.js";

// Cases kept in lockstep with packages/python/tests/test_pin/test_uses.py.

const SHA = "a".repeat(40);

describe("UsesRef.parse()", () => {
  it("parses owner/repo@ref", () => {
    const parsed = UsesRef.parse("actions/checkout@v4");
    expect(parsed).not.toBeNull();
    expect({
      owner: parsed!.owner,
      repo: parsed!.repo,
      path: parsed!.path,
      ref: parsed!.ref,
    }).toEqual({ owner: "actions", repo: "checkout", path: null, ref: "v4" });
  });

  it("parses owner/repo/path/sub@ref (path may contain slashes)", () => {
    const parsed = UsesRef.parse("owner/repo/path/sub@ref");
    expect(parsed).not.toBeNull();
    expect({
      owner: parsed!.owner,
      repo: parsed!.repo,
      path: parsed!.path,
      ref: parsed!.ref,
    }).toEqual({ owner: "owner", repo: "repo", path: "path/sub", ref: "ref" });
  });

  it("parses a reusable-workflow path", () => {
    const parsed = UsesRef.parse("octo-org/repo/.github/workflows/ci.yml@v1");
    expect(parsed?.path).toBe(".github/workflows/ci.yml");
    expect(parsed?.ref).toBe("v1");
  });

  it("returns null for a local ref", () => {
    expect(UsesRef.parse("./local-action")).toBeNull();
  });

  it("returns null for a docker ref", () => {
    expect(UsesRef.parse("docker://node:18")).toBeNull();
  });

  it("returns null when there is no @ref", () => {
    expect(UsesRef.parse("actions/checkout")).toBeNull();
  });

  it("returns null when there is no owner/repo slash", () => {
    expect(UsesRef.parse("checkout@v4")).toBeNull();
  });
});

describe("UsesRef pinnability", () => {
  it("a version ref is pinnable", () => {
    const parsed = UsesRef.parse("actions/checkout@v4");
    expect(parsed?.refIsSha).toBe(false);
    expect(parsed?.isPinnable).toBe(true);
  });

  it("a SHA ref is not pinnable", () => {
    const parsed = UsesRef.parse(`actions/checkout@${SHA}`);
    expect(parsed?.refIsSha).toBe(true);
    expect(parsed?.isPinnable).toBe(false);
  });

  it("an uppercase-hex ref is not treated as a SHA", () => {
    const parsed = UsesRef.parse(`actions/checkout@${"A".repeat(40)}`);
    expect(parsed?.refIsSha).toBe(false);
    expect(parsed?.isPinnable).toBe(true);
  });
});

describe("UsesRef.actionPart / withSha()", () => {
  it("actionPart omits the ref (no path)", () => {
    expect(UsesRef.parse("actions/checkout@v4")?.actionPart).toBe("actions/checkout");
  });

  it("actionPart includes the path", () => {
    expect(UsesRef.parse("octo-org/repo/.github/workflows/ci.yml@v1")?.actionPart).toBe(
      "octo-org/repo/.github/workflows/ci.yml",
    );
  });

  it("withSha rebuilds owner/repo@sha", () => {
    expect(UsesRef.parse("actions/checkout@v4")?.withSha(SHA)).toBe(`actions/checkout@${SHA}`);
  });

  it("withSha rebuilds owner/repo/path@sha", () => {
    expect(UsesRef.parse("octo-org/repo/.github/workflows/ci.yml@v1")?.withSha(SHA)).toBe(
      `octo-org/repo/.github/workflows/ci.yml@${SHA}`,
    );
  });
});
