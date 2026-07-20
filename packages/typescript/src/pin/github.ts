/**
 * GitHub REST API client for resolving Action refs to commit SHAs.
 *
 * The HTTP transport is injected (`HttpClient`) so the GitHub logic — URL
 * building, error mapping, pagination, annotated-tag dereferencing — is
 * testable without network access. `FetchTransport` is the default adapter
 * (global `fetch`); tests supply a fake transport with canned responses.
 *
 * Pure decisions (Link-header parsing, the tag-vs-head fallback order, and the
 * annotated-tag "is this a commit" check) stay free functions so they can be
 * unit-tested directly.
 */

import { ResolveError } from "./resolve.js";

const API_BASE = "https://api.github.com";
const API_TIMEOUT_MS = 30_000;

/**
 * Raised by a transport when a request fails at the network level.
 *
 * Signals that no HTTP response was received (connection refused, DNS
 * failure, timeout). HTTP responses with error status codes are *not*
 * transport errors — they are returned as `HttpResponse` objects for
 * `GitHubClient` to map.
 */
export class TransportError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "TransportError";
  }
}

/** Options applicable to a transport request. */
export interface RequestOptions {
  /** Optional GitHub personal access token. */
  token?: string;
}

/** An HTTP response returned by a transport. */
export interface HttpResponse {
  /** HTTP status code. */
  readonly status: number;
  /** HTTP reason phrase (used in error messages). */
  readonly statusText: string;
  /** Parse and return the JSON body. */
  json(): Promise<unknown>;
  /** Return a header value by name (case-insensitive), or `null`. */
  header(name: string): string | null;
}

/** Transport seam: a single authenticated GET returning an `HttpResponse`. */
export interface HttpClient {
  /** GET `url`; reject with `TransportError` on network failure. */
  get(url: string, options?: RequestOptions): Promise<HttpResponse>;
}

/** Wraps a native `fetch` `Response` as an `HttpResponse`. */
class FetchResponse implements HttpResponse {
  constructor(private readonly raw: Response) {}

  get status(): number {
    return this.raw.status;
  }

  get statusText(): string {
    return this.raw.statusText;
  }

  json(): Promise<unknown> {
    return this.raw.json();
  }

  header(name: string): string | null {
    return this.raw.headers.get(name);
  }
}

/**
 * Default `HttpClient` backed by the global `fetch`.
 *
 * Holds the raw `fetch` call and header building. HTTP error responses
 * (4xx/5xx) are returned as `HttpResponse` objects rather than thrown, so the
 * client owns all status-based error mapping; genuine network failures reject
 * with `TransportError`.
 */
export class FetchTransport implements HttpClient {
  async get(url: string, options: RequestOptions = {}): Promise<HttpResponse> {
    const headers: Record<string, string> = {
      Accept: "application/vnd.github.v3+json",
      "User-Agent": "ghagen-pin",
    };
    if (options.token) {
      headers["Authorization"] = `Bearer ${options.token}`;
    }

    let response: Response;
    try {
      response = await fetch(url, {
        headers,
        signal: AbortSignal.timeout(API_TIMEOUT_MS),
      });
    } catch (err) {
      throw new TransportError((err as Error).message);
    }
    return new FetchResponse(response);
  }
}

/**
 * Resolve GitHub Action refs to commit SHAs via the REST API.
 *
 * URL building, error mapping, pagination, and annotated-tag dereferencing
 * live here. The HTTP transport and the token are injected once at
 * construction (the token moved off the per-call signature).
 */
export class GitHubClient {
  private readonly transport: HttpClient;
  private readonly token?: string;

  constructor(transport?: HttpClient, token?: string) {
    this.transport = transport ?? new FetchTransport();
    this.token = token;
  }

  /**
   * Resolve a git ref to a commit SHA.
   *
   * Tries `tags/{ref}` first, then `heads/{ref}`. Annotated tags are
   * dereferenced to their underlying commit.
   */
  async resolveRef(owner: string, repo: string, ref: string): Promise<string> {
    for (const url of refUrls(owner, repo, ref)) {
      const data = await this.getJson(url);
      if (data === null) {
        continue; // 404 for this prefix — try the next.
      }
      const obj = (data as { object: { type: string; sha: string } }).object;
      let sha = obj.sha;
      if (isAnnotatedTag(obj)) {
        sha = await this.dereferenceTag(owner, repo, sha);
      }
      return sha;
    }

    throw new ResolveError(
      `Could not resolve ref '${ref}' for ${owner}/${repo}. ` +
        "Tried tags/ and heads/ — neither exists.",
    );
  }

  /** Dereference an annotated tag object to its underlying commit SHA. */
  async dereferenceTag(owner: string, repo: string, tagSha: string): Promise<string> {
    const url = `${API_BASE}/repos/${owner}/${repo}/git/tags/${tagSha}`;
    const data = await this.getJson(url);
    const obj = (data as { object?: { type?: string; sha?: string } } | null)?.object ?? {};
    const sha = commitSha(obj);
    if (sha !== null) {
      return sha;
    }
    throw new ResolveError(
      `Tag ${tagSha} in ${owner}/${repo} does not point to a commit (type=${JSON.stringify(
        obj.type ?? null,
      )})`,
    );
  }

  /**
   * List all tags for a repository (paginated via the `Link` header).
   *
   * Returns tag names with the `refs/tags/` prefix stripped, or an empty list
   * when the repo has no tags (the API returns 404).
   */
  async listTags(owner: string, repo: string): Promise<string[]> {
    let url: string | null = `${API_BASE}/repos/${owner}/${repo}/git/refs/tags`;
    const tags: string[] = [];
    while (url !== null) {
      const page = await this.getPage(url);
      if (page === null) {
        return []; // 404 — no tags.
      }
      const { body, next } = page;
      if (!Array.isArray(body)) {
        break;
      }
      for (const ref of body as Array<{ ref?: string }>) {
        const fullRef = ref.ref ?? "";
        if (fullRef.startsWith("refs/tags/")) {
          tags.push(fullRef.slice("refs/tags/".length));
        }
      }
      url = next;
    }
    return tags;
  }

  // -- internal request helpers ------------------------------------------

  /**
   * GET `url` and map status codes to errors.
   *
   * Returns the response for 2xx and 404 (the caller distinguishes 404);
   * warns on 403 and throws `ResolveError` for any other non-2xx.
   */
  private async fetch(url: string): Promise<HttpResponse> {
    let resp: HttpResponse;
    try {
      resp = await this.transport.get(url, { token: this.token });
    } catch (err) {
      if (err instanceof TransportError) {
        throw new ResolveError(`Network error reaching GitHub API: ${err.message}`);
      }
      throw err;
    }

    if (resp.status === 404) {
      return resp;
    }
    if (resp.status === 403) {
      warnRateLimit(resp);
    }
    if (resp.status < 200 || resp.status >= 300) {
      throw new ResolveError(`GitHub API error ${resp.status} for ${url}: ${resp.statusText}`);
    }
    return resp;
  }

  /** Fetch and parse JSON, or `null` on 404. */
  private async getJson(url: string): Promise<unknown | null> {
    const resp = await this.fetch(url);
    if (resp.status === 404) {
      return null;
    }
    try {
      return await resp.json();
    } catch (err) {
      throw new ResolveError(
        `Failed to parse JSON response from ${url}: ${(err as Error).message}`,
      );
    }
  }

  /** Fetch one page: `{ body, next }`, or `null` on 404. */
  private async getPage(url: string): Promise<{ body: unknown; next: string | null } | null> {
    const resp = await this.fetch(url);
    if (resp.status === 404) {
      return null;
    }
    let body: unknown;
    try {
      body = await resp.json();
    } catch (err) {
      throw new ResolveError(
        `Failed to parse JSON response from ${url}: ${(err as Error).message}`,
      );
    }
    return { body, next: parseNextLink(resp.header("Link")) };
  }
}

// -- pure helpers (unit-testable without a transport) ----------------------

/** Return the candidate ref-lookup URLs in tag-then-head fallback order. */
export function refUrls(owner: string, repo: string, ref: string): string[] {
  return (["tags", "heads"] as const).map(
    (prefix) => `${API_BASE}/repos/${owner}/${repo}/git/ref/${prefix}/${ref}`,
  );
}

/** Whether a ref object points to an annotated tag (needs dereferencing). */
export function isAnnotatedTag(obj: { type?: string }): boolean {
  return obj.type === "tag";
}

/** Return the SHA if `obj` is a commit object, else `null`. */
export function commitSha(obj: { type?: string; sha?: string }): string | null {
  return obj.type === "commit" && typeof obj.sha === "string" ? obj.sha : null;
}

/**
 * Extract the `next` URL from a GitHub `Link` header.
 *
 * Example header value:
 *
 *     <https://api.github.com/repos/o/r/git/refs/tags?page=2>; rel="next",
 *     <https://api.github.com/repos/o/r/git/refs/tags?page=5>; rel="last"
 */
export function parseNextLink(header: string | null): string | null {
  if (!header) {
    return null;
  }
  for (const part of header.split(",")) {
    const m = part.match(/<([^>]+)>;\s*rel="next"/);
    if (m) {
      return m[1]!;
    }
  }
  return null;
}

function warnRateLimit(resp: HttpResponse): void {
  const remaining = resp.header("X-RateLimit-Remaining") ?? "?";
  process.stderr.write(
    `warning: GitHub API rate limit hit (remaining=${remaining}). ` +
      "Set $GITHUB_TOKEN or use --token for higher limits.\n",
  );
}
