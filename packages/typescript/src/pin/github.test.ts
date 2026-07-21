import { describe, it, expect, vi, afterEach } from "vitest";
import {
  GitHubClient,
  ResolveError,
  TransportError,
  type HttpClient,
  type HttpResponse,
  type RequestOptions,
  commitSha,
  isAnnotatedTag,
  parseNextLink,
  refUrls,
} from "./github.js";
const SHA = "a".repeat(40);
const TAG_SHA = "b".repeat(40);

interface CannedInit {
  status?: number;
  body?: unknown;
  headers?: Record<string, string>;
}

/** Build a canned `HttpResponse`. */
function jsonResponse(init: CannedInit): HttpResponse {
  const headers = new Headers(init.headers ?? {});
  return {
    status: init.status ?? 200,
    statusText: "",
    json: async () => init.body,
    header: (name: string) => headers.get(name),
  };
}

type Canned = HttpResponse | HttpResponse[] | Error;

/**
 * Canned `HttpClient` keyed by URL substring. Each entry maps a URL substring
 * to a response, a list of responses (consumed in order, for pagination), or
 * an error to throw. Unmatched URLs return a 404. Tokens are recorded.
 */
class FakeTransport implements HttpClient {
  readonly calls: string[] = [];
  readonly tokens: Array<string | undefined> = [];

  constructor(private readonly responses: Record<string, Canned>) {}

  async get(url: string, options: RequestOptions = {}): Promise<HttpResponse> {
    this.calls.push(url);
    this.tokens.push(options.token);
    for (const [pattern, value] of Object.entries(this.responses)) {
      if (url.includes(pattern)) {
        if (Array.isArray(value)) {
          return value.shift()!;
        }
        if (value instanceof Error) {
          throw value;
        }
        return value;
      }
    }
    return jsonResponse({ status: 404, body: {} });
  }
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("GitHubClient.resolveRef()", () => {
  it("returns the SHA from a lightweight tag ref", async () => {
    const transport = new FakeTransport({
      "tags/v4": jsonResponse({ body: { object: { type: "commit", sha: SHA } } }),
    });
    const client = new GitHubClient(transport);
    expect(await client.resolveRef("actions", "checkout", "v4")).toBe(SHA);
    expect(transport.calls[0]).toBe(
      "https://api.github.com/repos/actions/checkout/git/ref/tags/v4",
    );
  });

  it("falls back to heads/ when tags/ returns 404", async () => {
    const transport = new FakeTransport({
      "heads/main": jsonResponse({ body: { object: { type: "commit", sha: SHA } } }),
    });
    const client = new GitHubClient(transport);
    expect(await client.resolveRef("o", "r", "main")).toBe(SHA);
    expect(transport.calls[0]).toContain("/tags/main");
    expect(transport.calls[1]).toContain("/heads/main");
  });

  it("dereferences annotated tags via /git/tags/{sha}", async () => {
    const transport = new FakeTransport({
      "git/ref/tags/v1": jsonResponse({ body: { object: { type: "tag", sha: TAG_SHA } } }),
      [`git/tags/${TAG_SHA}`]: jsonResponse({ body: { object: { type: "commit", sha: SHA } } }),
    });
    const client = new GitHubClient(transport);
    expect(await client.resolveRef("o", "r", "v1")).toBe(SHA);
  });

  it("throws when an annotated tag does not point to a commit", async () => {
    const transport = new FakeTransport({
      "git/ref/tags/v1": jsonResponse({ body: { object: { type: "tag", sha: TAG_SHA } } }),
      [`git/tags/${TAG_SHA}`]: jsonResponse({ body: { object: { type: "tree", sha: SHA } } }),
    });
    const client = new GitHubClient(transport);
    await expect(client.resolveRef("o", "r", "v1")).rejects.toThrow(/does not point to a commit/);
  });

  it("sends the token to the transport", async () => {
    const transport = new FakeTransport({
      "tags/v1": jsonResponse({ body: { object: { type: "commit", sha: SHA } } }),
    });
    const client = new GitHubClient(transport, "abc");
    await client.resolveRef("o", "r", "v1");
    expect(transport.tokens[0]).toBe("abc");
  });

  it("throws ResolveError on non-404 errors", async () => {
    const transport = new FakeTransport({
      "tags/v1": jsonResponse({ status: 500, body: { message: "boom" } }),
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
      "git/refs/tags": jsonResponse({ body: refs("v1", "v2", "v3.0.0") }),
    });
    const client = new GitHubClient(transport);
    expect(await client.listTags("actions", "checkout")).toEqual(["v1", "v2", "v3.0.0"]);
  });

  it("paginates via the Link header", async () => {
    const next = "https://api.github.com/repos/o/r/git/refs/tags?page=2";
    const transport = new FakeTransport({
      "git/refs/tags?page=2": jsonResponse({ body: refs("v3") }),
      "git/refs/tags": [
        jsonResponse({ body: refs("v1", "v2"), headers: { Link: `<${next}>; rel="next"` } }),
      ],
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
      "git/refs/tags": jsonResponse({
        status: 403,
        body: { message: "rate limited" },
        headers: { "X-RateLimit-Remaining": "0" },
      }),
    });
    const client = new GitHubClient(transport);
    await expect(client.listTags("actions", "checkout")).rejects.toThrow(/403/);
    expect(stderr).toHaveBeenCalledWith(expect.stringContaining("rate limit hit"));
    expect(stderr).toHaveBeenCalledWith(expect.stringContaining("remaining=0"));
  });

  it("sends the token to the transport", async () => {
    const transport = new FakeTransport({ "git/refs/tags": jsonResponse({ body: [] }) });
    const client = new GitHubClient(transport, "secret");
    await client.listTags("o", "r");
    expect(transport.tokens[0]).toBe("secret");
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
