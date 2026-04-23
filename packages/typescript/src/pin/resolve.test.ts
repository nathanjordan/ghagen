import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { ResolveError, listTags, parseUses, resolveRef } from "./resolve.js";

interface MockResponseInit {
  status?: number;
  body?: unknown;
  headers?: Record<string, string>;
}

function jsonResponse(init: MockResponseInit): Response {
  const body = init.body === undefined ? "" : JSON.stringify(init.body);
  const headers = new Headers(init.headers ?? {});
  if (!headers.has("content-type")) {
    headers.set("content-type", "application/json");
  }
  return new Response(body, { status: init.status ?? 200, headers });
}

let calls: Array<{ url: string; headers: Record<string, string> }>;
let queue: Response[];

beforeEach(() => {
  calls = [];
  queue = [];
  vi.stubGlobal("fetch", async (url: string, init?: RequestInit) => {
    const headers: Record<string, string> = {};
    if (init?.headers) {
      const h = new Headers(init.headers);
      h.forEach((v, k) => {
        headers[k] = v;
      });
    }
    calls.push({ url, headers });
    const next = queue.shift();
    if (!next) {
      throw new Error(`unexpected fetch: ${url}`);
    }
    return next;
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("parseUses()", () => {
  it("parses owner/repo@ref", () => {
    expect(parseUses("actions/checkout@v4")).toEqual({
      owner: "actions",
      repo: "checkout",
      path: null,
      ref: "v4",
    });
  });

  it("parses owner/repo/path@ref", () => {
    expect(parseUses("owner/repo/path/to/action@main")).toEqual({
      owner: "owner",
      repo: "repo",
      path: "path/to/action",
      ref: "main",
    });
  });

  it("throws when no @ref is present", () => {
    expect(() => parseUses("actions/checkout")).toThrow(/No @ref/);
  });
});

describe("resolveRef()", () => {
  it("returns the SHA from a tag ref", async () => {
    queue.push(
      jsonResponse({
        body: { object: { type: "commit", sha: "a".repeat(40) } },
      }),
    );
    const sha = await resolveRef("actions", "checkout", "v4");
    expect(sha).toBe("a".repeat(40));
    expect(calls[0]!.url).toBe("https://api.github.com/repos/actions/checkout/git/ref/tags/v4");
    expect(calls[0]!.headers["accept"]).toBe("application/vnd.github.v3+json");
    expect(calls[0]!.headers["user-agent"]).toBe("ghagen-pin");
  });

  it("falls back to heads/ when tags/ returns 404", async () => {
    queue.push(jsonResponse({ status: 404, body: {} }));
    queue.push(
      jsonResponse({
        body: { object: { type: "commit", sha: "b".repeat(40) } },
      }),
    );
    const sha = await resolveRef("o", "r", "main");
    expect(sha).toBe("b".repeat(40));
    expect(calls[1]!.url).toContain("/heads/main");
  });

  it("dereferences annotated tags via /git/tags/{sha}", async () => {
    queue.push(
      jsonResponse({
        body: { object: { type: "tag", sha: "tagsha".padEnd(40, "0") } },
      }),
    );
    queue.push(
      jsonResponse({
        body: { object: { type: "commit", sha: "c".repeat(40) } },
      }),
    );
    const sha = await resolveRef("o", "r", "v1");
    expect(sha).toBe("c".repeat(40));
    expect(calls[1]!.url).toContain("/git/tags/");
  });

  it("sends Authorization when token is provided", async () => {
    queue.push(
      jsonResponse({
        body: { object: { type: "commit", sha: "d".repeat(40) } },
      }),
    );
    await resolveRef("o", "r", "v1", { token: "abc" });
    expect(calls[0]!.headers["authorization"]).toBe("Bearer abc");
  });

  it("throws ResolveError on non-404 errors", async () => {
    queue.push(jsonResponse({ status: 500, body: { message: "boom" } }));
    await expect(resolveRef("o", "r", "v1")).rejects.toBeInstanceOf(ResolveError);
  });

  it("throws ResolveError when both tags and heads 404", async () => {
    queue.push(jsonResponse({ status: 404, body: {} }));
    queue.push(jsonResponse({ status: 404, body: {} }));
    await expect(resolveRef("o", "r", "v1")).rejects.toThrow(/Could not resolve/);
  });
});

describe("listTags()", () => {
  it("paginates via the Link header", async () => {
    queue.push(
      jsonResponse({
        body: [{ ref: "refs/tags/v1" }, { ref: "refs/tags/v2" }],
        headers: {
          Link: '<https://api.github.com/repos/o/r/git/refs/tags?page=2>; rel="next"',
        },
      }),
    );
    queue.push(
      jsonResponse({
        body: [{ ref: "refs/tags/v3" }],
      }),
    );
    const tags = await listTags("o", "r");
    expect(tags).toEqual(["v1", "v2", "v3"]);
  });

  it("returns [] on 404 (e.g. repo without tags)", async () => {
    queue.push(jsonResponse({ status: 404, body: {} }));
    expect(await listTags("o", "r")).toEqual([]);
  });
});
