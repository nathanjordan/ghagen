import { describe, it, expect, vi, afterEach } from "vitest";
import {
  API_TIMEOUT_MS,
  FetchTransport,
  GitHubClient,
  ResolveError,
  TransportError,
  commitSha,
  isAnnotatedTag,
  parseNextLink,
  refUrls,
} from "./github.js";
import { FakeTransport, LoopbackOrigin, canned, cannedRaw } from "./transport-contract.js";
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

/**
 * A 200 that parses but has the wrong *shape* must also be a `ResolveError`.
 *
 * Peer of Python's `TestMalformedShape`. The block above covers a body that is
 * not JSON; this covers a body that is JSON and is not what the GitHub API
 * documents — the case that used to make `resolveRef` return `undefined` while
 * its signature promised `string`, so an unquoted `sha: null` reached the
 * lockfile that this same port then refuses to read back, and `listTags`
 * return `[]`, which reads as "this repo has no tags" and silently suppresses
 * every update for it.
 */
describe("a shape-malformed 200 surfaces as ResolveError", () => {
  const resolveRefCases: ReadonlyArray<readonly [string, unknown]> = [
    ["no-object-key", { unexpected: "shape" }],
    ["object-not-a-mapping", { object: "not-a-mapping" }],
    ["object-null", { object: null }],
    ["no-sha-key", { object: { type: "commit" } }],
    ["sha-null", { object: { type: "commit", sha: null } }],
    ["sha-number", { object: { type: "commit", sha: 12345 } }],
    ["body-is-a-list", []],
    ["body-is-a-string", "a string"],
  ];

  for (const [id, body] of resolveRefCases) {
    it(`from resolveRef() — ${id}`, async () => {
      const transport = new FakeTransport({ "git/ref/tags/v4": canned(body) });
      const client = new GitHubClient(transport);
      await expect(client.resolveRef("actions", "checkout", "v4")).rejects.toThrow(
        /Unexpected response shape/,
      );
    });
  }

  const listTagsCases: ReadonlyArray<readonly [string, unknown]> = [
    ["not-a-list", { unexpected: "shape" }],
    ["list-of-strings", ["refs/tags/v1"]],
    ["ref-not-a-string", [{ ref: 12345 }]],
    ["list-of-nulls", [null]],
  ];

  for (const [id, body] of listTagsCases) {
    it(`from listTags() — ${id}`, async () => {
      const transport = new FakeTransport({ "git/refs/tags": canned(body) });
      const client = new GitHubClient(transport);
      await expect(client.listTags("actions", "checkout")).rejects.toThrow(
        /Unexpected response shape/,
      );
    });
  }

  const messageCases: ReadonlyArray<readonly [unknown, string]> = [
    [{ object: { type: "commit", sha: 1 } }, "'object.sha' must be a string, got number"],
    [{ object: null }, "'object' must be an object, got null"],
    [[], "expected an object, got array"],
  ];

  for (const [body, detail] of messageCases) {
    it(`says the same thing as the Python port — ${detail}`, async () => {
      // The exact text its Python peer asserts, character for character; see
      // `TestMalformedShape.test_message_shape_matches_the_typescript_port`.
      const url = "https://api.github.com/repos/actions/checkout/git/ref/tags/v4";
      const transport = new FakeTransport({ "git/ref/tags/v4": canned(body) });
      await expect(
        new GitHubClient(transport).resolveRef("actions", "checkout", "v4"),
      ).rejects.toThrow(`Unexpected response shape from ${url}: ${detail}`);
    });
  }

  it("from dereferenceTag()", async () => {
    const transport = new FakeTransport({ [`git/tags/${TAG_SHA}`]: canned({ nope: 1 }) });
    const client = new GitHubClient(transport);
    await expect(client.dereferenceTag("actions", "checkout", TAG_SHA)).rejects.toThrow(
      /does not point to a commit/,
    );
  });

  it("but a repo with no tags is still an empty list", async () => {
    // The 404 path must keep meaning "no tags"; only a *malformed* 200 is the
    // error. Without this, tightening listTags could turn every tagless repo
    // into a failed run.
    expect(await new GitHubClient(new FakeTransport({})).listTags("o", "r")).toEqual([]);
  });

  it("and an empty page is still an empty list", async () => {
    const transport = new FakeTransport({ "git/refs/tags": canned([]) });
    expect(await new GitHubClient(transport).listTags("o", "r")).toEqual([]);
  });
});

/**
 * The production adapter's *default* deadline, which nothing else observes.
 *
 * The conformance table always builds the adapter with an explicit deadline
 * (`loopbackAdapter`'s `build`), so deleting the default — or dropping the
 * `signal` from the `fetch` call altogether — would leave the whole suite green
 * while shipping a transport that can hang forever. These tests observe the
 * deadline the default-constructed adapter actually arms.
 *
 * Peer of Python's `TestDefaultDeadline`.
 */
describe("FetchTransport's default deadline", () => {
  /** Run one GET against a loopback origin, returning the armed deadlines. */
  async function armedDeadlines(transport: FetchTransport): Promise<number[]> {
    const spy = vi.spyOn(AbortSignal, "timeout");
    const origin = new LoopbackOrigin((socket) => {
      socket.write("HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\n{}");
    });
    await origin.start();
    try {
      await transport.get(origin.url);
    } finally {
      await origin.stop();
    }
    return spy.mock.calls.map(([ms]) => ms);
  }

  it("arms the declared deadline when constructed with no argument", async () => {
    expect(await armedDeadlines(new FetchTransport())).toEqual([API_TIMEOUT_MS]);
  });

  it("arms an explicit deadline instead, so the constant is the default", async () => {
    expect(await armedDeadlines(new FetchTransport(1_500))).toEqual([1_500]);
  });

  it("declares the same deadline as the Python port", () => {
    // `API_TIMEOUT_SECONDS = 30.0` in packages/python/src/ghagen/pin/github.py.
    expect(API_TIMEOUT_MS).toBe(30_000);
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
