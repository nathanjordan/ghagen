import { describe, it, expect, vi, afterEach } from "vitest";
import {
  GitHubClient,
  ResolveError,
  TransportError,
  commitSha,
  isAnnotatedTag,
  parseNextLink,
  refUrls,
} from "./github.js";
import { FakeTransport, canned, cannedRaw } from "./transport-contract.js";
const SHA = "a".repeat(40);
const TAG_SHA = "b".repeat(40);

afterEach(() => {
  vi.restoreAllMocks();
});

describe("GitHubClient.resolveRef()", () => {
  it("returns the SHA from a lightweight tag ref", async () => {
    const transport = new FakeTransport({
      "tags/v4": canned({ object: { type: "commit", sha: SHA } }),
    });
    const client = new GitHubClient(transport);
    expect(await client.resolveRef("actions", "checkout", "v4")).toBe(SHA);
    expect(transport.calls[0]).toBe(
      "https://api.github.com/repos/actions/checkout/git/ref/tags/v4",
    );
  });

  it("falls back to heads/ when tags/ returns 404", async () => {
    const transport = new FakeTransport({
      "heads/main": canned({ object: { type: "commit", sha: SHA } }),
    });
    const client = new GitHubClient(transport);
    expect(await client.resolveRef("o", "r", "main")).toBe(SHA);
    expect(transport.calls[0]).toContain("/tags/main");
    expect(transport.calls[1]).toContain("/heads/main");
  });

  it("dereferences annotated tags via /git/tags/{sha}", async () => {
    const transport = new FakeTransport({
      "git/ref/tags/v1": canned({ object: { type: "tag", sha: TAG_SHA } }),
      [`git/tags/${TAG_SHA}`]: canned({ object: { type: "commit", sha: SHA } }),
    });
    const client = new GitHubClient(transport);
    expect(await client.resolveRef("o", "r", "v1")).toBe(SHA);
  });

  it("throws when an annotated tag does not point to a commit", async () => {
    const transport = new FakeTransport({
      "git/ref/tags/v1": canned({ object: { type: "tag", sha: TAG_SHA } }),
      [`git/tags/${TAG_SHA}`]: canned({ object: { type: "tree", sha: SHA } }),
    });
    const client = new GitHubClient(transport);
    await expect(client.resolveRef("o", "r", "v1")).rejects.toThrow(/does not point to a commit/);
  });

  it("sends the token to the transport", async () => {
    const transport = new FakeTransport({
      "tags/v1": canned({ object: { type: "commit", sha: SHA } }),
    });
    const client = new GitHubClient(transport, "abc");
    await client.resolveRef("o", "r", "v1");
    expect(transport.tokens[0]).toBe("abc");
  });

  it("throws ResolveError on non-404 errors", async () => {
    const transport = new FakeTransport({
      "tags/v1": canned({ message: "boom" }, { status: 500 }),
    });
    const client = new GitHubClient(transport);
    await expect(client.resolveRef("o", "r", "v1")).rejects.toBeInstanceOf(ResolveError);
  });

  it("throws ResolveError when both tags and heads 404", async () => {
    const client = new GitHubClient(new FakeTransport({}));
    await expect(client.resolveRef("o", "r", "v1")).rejects.toThrow(/Could not resolve/);
  });

  it("maps a transport network failure to ResolveError", async () => {
    const transport = new FakeTransport({ "tags/v1": new TransportError("boom") });
    const client = new GitHubClient(transport);
    await expect(client.resolveRef("o", "r", "v1")).rejects.toThrow(/Network error/);
  });
});

describe("GitHubClient.listTags()", () => {
  const refs = (...names: string[]) => names.map((n) => ({ ref: `refs/tags/${n}` }));

  it("returns stripped tag names from a single page", async () => {
    const transport = new FakeTransport({
      "git/refs/tags": canned(refs("v1", "v2", "v3.0.0")),
    });
    const client = new GitHubClient(transport);
    expect(await client.listTags("actions", "checkout")).toEqual(["v1", "v2", "v3.0.0"]);
  });

  it("paginates via the Link header", async () => {
    const next = "https://api.github.com/repos/o/r/git/refs/tags?page=2";
    const transport = new FakeTransport({
      "git/refs/tags?page=2": canned(refs("v3")),
      "git/refs/tags": [canned(refs("v1", "v2"), { headers: { Link: `<${next}>; rel="next"` } })],
    });
    const client = new GitHubClient(transport);
    expect(await client.listTags("o", "r")).toEqual(["v1", "v2", "v3"]);
  });

  it("returns [] on 404 (e.g. repo without tags)", async () => {
    const client = new GitHubClient(new FakeTransport({}));
    expect(await client.listTags("o", "r")).toEqual([]);
  });

  it("warns and throws ResolveError on a 403 rate limit", async () => {
    const stderr = vi.spyOn(process.stderr, "write").mockReturnValue(true);
    const transport = new FakeTransport({
      "git/refs/tags": canned(
        { message: "rate limited" },
        { status: 403, headers: { "X-RateLimit-Remaining": "0" } },
      ),
    });
    const client = new GitHubClient(transport);
    await expect(client.listTags("actions", "checkout")).rejects.toThrow(/403/);
    expect(stderr).toHaveBeenCalledWith(expect.stringContaining("rate limit hit"));
    expect(stderr).toHaveBeenCalledWith(expect.stringContaining("remaining=0"));
  });

  it("sends the token to the transport", async () => {
    const transport = new FakeTransport({ "git/refs/tags": canned([]) });
    const client = new GitHubClient(transport, "secret");
    await client.listTags("o", "r");
    expect(transport.tokens[0]).toBe("secret");
  });
});

// Peer of Python's TestMalformedJson. Impossible before `HttpResponse` became a
// class: every hand-written double implemented `json()` by returning an
// already-parsed value, so a canned body could not fail to parse.
describe("a malformed 200 surfaces as ResolveError", () => {
  it("from resolveRef()", async () => {
    const transport = new FakeTransport({ "tags/v4": cannedRaw("<html>not json</html>") });
    const client = new GitHubClient(transport);
    await expect(client.resolveRef("actions", "checkout", "v4")).rejects.toThrow(
      /Failed to parse JSON response/,
    );
  });

  it("from listTags()", async () => {
    const transport = new FakeTransport({
      "git/refs/tags": cannedRaw("<html>not json</html>"),
    });
    const client = new GitHubClient(transport);
    await expect(client.listTags("actions", "checkout")).rejects.toThrow(
      /Failed to parse JSON response/,
    );
  });
});

describe("pure helpers", () => {
  it("refUrls() returns tag-then-head fallback order", () => {
    expect(refUrls("actions", "checkout", "v4")).toEqual([
      "https://api.github.com/repos/actions/checkout/git/ref/tags/v4",
      "https://api.github.com/repos/actions/checkout/git/ref/heads/v4",
    ]);
  });

  it("isAnnotatedTag() detects tag objects", () => {
    expect(isAnnotatedTag({ type: "tag" })).toBe(true);
    expect(isAnnotatedTag({ type: "commit" })).toBe(false);
    expect(isAnnotatedTag({})).toBe(false);
  });

  it("commitSha() returns the sha only for commit objects", () => {
    expect(commitSha({ type: "commit", sha: SHA })).toBe(SHA);
    expect(commitSha({ type: "tag", sha: SHA })).toBeNull();
    expect(commitSha({ type: "commit" })).toBeNull();
    expect(commitSha({})).toBeNull();
  });

  it("parseNextLink() extracts the next relation", () => {
    const header =
      '<https://api.github.com/repos/o/r/git/refs/tags?page=2>; rel="next", ' +
      '<https://api.github.com/repos/o/r/git/refs/tags?page=5>; rel="last"';
    expect(parseNextLink(header)).toBe("https://api.github.com/repos/o/r/git/refs/tags?page=2");
  });

  it("parseNextLink() returns null without a next relation", () => {
    expect(parseNextLink(null)).toBeNull();
    expect(parseNextLink("")).toBeNull();
    expect(parseNextLink('<https://api.github.com/x?page=1>; rel="last"')).toBeNull();
  });
});
