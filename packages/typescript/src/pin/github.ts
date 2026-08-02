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

const API_BASE = "https://api.github.com";

/**
 * Wall-clock ceiling on a single `HttpClient` request, body read included.
 *
 * Part of the transport contract rather than an adapter's private business — a
 * third-party adapter is expected to honour it, so it is exported and mirrors
 * the Python port's `API_TIMEOUT_SECONDS` (`pin/github.py`).
 */
export const API_TIMEOUT_MS = 30_000;

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

/** Raised when a ref cannot be resolved to a commit SHA. */
export class ResolveError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ResolveError";
  }
}

/** Options applicable to a transport request. */
export interface RequestOptions {
  /** Optional GitHub personal access token. */
  token?: string;
}

/**
 * An HTTP response returned by a transport, carrying a body the transport has
 * already read.
 *
 * A class, not a structural interface: an adapter author *constructs* one
 * rather than implementing `json()`, so every double — including the canned
 * one — parses the same bytes the real adapter would hand over, and a
 * malformed 200 is expressible. Field order mirrors Python's `Response`
 * (`Response(status, body, reason, headers)`).
 */
export class HttpResponse {
  constructor(
    /** HTTP status code. */
    readonly status: number,
    /** The already-read body. Python's peer carries `bytes`; this is a `string`. */
    readonly body: string,
    /** HTTP reason phrase (used in error messages). Python calls it `reason`. */
    readonly statusText: string = "",
    private readonly headers: Readonly<Record<string, string>> = {},
  ) {}

  /** Parse and return the JSON body; throws the native decode error. */
  json(): unknown {
    return JSON.parse(this.body);
  }

  /** Return a header value by name (case-insensitive), or `null`. */
  header(name: string): string | null {
    const lowered = name.toLowerCase();
    for (const [key, value] of Object.entries(this.headers)) {
      if (key.toLowerCase() === lowered) {
        return value;
      }
    }
    return null;
  }
}

/**
 * Transport seam: a single authenticated GET returning an `HttpResponse`.
 *
 * The contract every adapter — production or canned — must satisfy, stated
 * here once rather than re-decided per adapter. It is executable: the
 * conformance table in `transport-contract.ts` runs it against each of them,
 * and its Python peer runs the identical table.
 *
 * **Deadline — wall clock, not per operation.** A `get` settles — resolving or
 * rejecting — within `API_TIMEOUT_MS` measured on the wall clock from the
 * moment it is called, *including reading the body*. The distinction is the
 * whole point: a per-socket-operation timeout is reset by every byte that
 * arrives, so a peer trickling one byte per interval holds the call open
 * indefinitely while never exceeding it. Row 12 of the conformance table
 * (`dribble-body`) is that peer, and it is what an adapter must survive.
 *
 * One phase is excluded, in both ports' wording though not in this port's
 * fact: the response **head**. Python's `UrllibTransport` delegates
 * connect-and-read-headers to `urlopen`, which admits only a per-operation
 * timeout, so an origin that trickles *header* bytes is bounded per operation
 * there; `AbortSignal.timeout` covers it here. The guarantee stated is the
 * intersection — wall-clock from the first body byte, per-operation before it
 * — so that the interface promises only what both ports deliver. This port
 * exceeds it; see `UrllibTransport._read_within` in `pin/github.py`.
 *
 * Production adapters take the deadline as one defaulted constructor argument
 * so the promise is testable rather than merely stated, and the default itself
 * is pinned by a test (`FetchTransport's default deadline` and its Python
 * peer) because the table always supplies an explicit one.
 *
 * **Error taxonomy — total.** `get` either resolves with an `HttpResponse` or
 * rejects with `TransportError`, and nothing else:
 *
 * - it resolves for **any** HTTP response it obtains, including 4xx, 5xx and a
 *   body that is not JSON. The transport never parses and never judges a
 *   status; `GitHubClient` owns that.
 * - it rejects with `TransportError` for **every** failure to obtain one —
 *   refusal, DNS, reset, mid-body abort, truncated body, deadline.
 * - it never lets the underlying library's error type escape.
 *
 * The totality is load-bearing: the pin engine recovers per ref on
 * `ResolveError` (`pin/engine.ts`), so an error outside the taxonomy turns one
 * unresolvable ref into an aborted run that writes nothing.
 *
 * **The body is read by the transport**, inside its own deadline and its own
 * failure mapping, so a caller may assume the network is done with once `get`
 * has resolved.
 */
export interface HttpClient {
  /** GET `url`, resolving with the response or rejecting with `TransportError`. */
  get(url: string, options?: RequestOptions): Promise<HttpResponse>;
}

/**
 * Default `HttpClient` backed by the global `fetch`.
 *
 * Holds the raw `fetch` call and header building; the policy it implements is
 * `HttpClient`'s, not its own.
 */
export class FetchTransport implements HttpClient {
  constructor(private readonly timeoutMs: number = API_TIMEOUT_MS) {}

  async get(url: string, options: RequestOptions = {}): Promise<HttpResponse> {
    const headers: Record<string, string> = {
      Accept: "application/vnd.github.v3+json",
      "User-Agent": "ghagen-pin",
    };
    if (options.token) {
      headers["Authorization"] = `Bearer ${options.token}`;
    }

    // Only the I/O sits under the handler — the body read included, which is
    // what puts a mid-body abort and a truncated payload inside the taxonomy —
    // and the HttpResponse is constructed after it.
    let status: number;
    let statusText: string;
    let body: string;
    let responseHeaders: Record<string, string>;
    try {
      const response = await fetch(url, {
        headers,
        signal: AbortSignal.timeout(this.timeoutMs),
      });
      status = response.status;
      statusText = response.statusText;
      responseHeaders = Object.fromEntries(response.headers.entries());
      body = await response.text();
    } catch (err) {
      throw new TransportError((err as Error).message);
    }
    return new HttpResponse(status, body, statusText, responseHeaders);
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
   *
   * @throws {ResolveError} If the ref cannot be resolved, or the API answers
   * 200 with a body that is not the documented shape.
   */
  async resolveRef(owner: string, repo: string, ref: string): Promise<string> {
    for (const url of refUrls(owner, repo, ref)) {
      const data = await this.getJson(url);
      if (data === null) {
        continue; // 404 for this prefix — try the next.
      }
      const obj = refObject(data, url);
      let sha = requireSha(obj, url);
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

  /**
   * Dereference an annotated tag object to its underlying commit SHA.
   *
   * @throws {ResolveError} If the tag does not point to a commit — which
   * includes a 200 whose body is not the documented shape, since such a body
   * evidences no commit either.
   */
  async dereferenceTag(owner: string, repo: string, tagSha: string): Promise<string> {
    const url = `${API_BASE}/repos/${owner}/${repo}/git/tags/${tagSha}`;
    const data = await this.getJson(url);
    const member = isJsonObject(data) ? data["object"] : undefined;
    const obj = isJsonObject(member) ? (member as { type?: string; sha?: string }) : {};
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
   *
   * "No tags" is the 404 alone. A 200 whose body is not an array of ref
   * objects throws rather than degrading to `[]`: an empty list here is
   * indistinguishable from a genuinely tagless repo, and it would suppress
   * every available update for that repo without a word.
   *
   * @throws {ResolveError} On non-404 API errors (e.g. rate limiting), or a
   * 200 whose body is not the documented shape.
   */
  async listTags(owner: string, repo: string): Promise<string[]> {
    let url: string | null = `${API_BASE}/repos/${owner}/${repo}/git/refs/tags`;
    const tags: string[] = [];
    while (url !== null) {
      const page = await this.getPage(url);
      if (page === null) {
        return []; // 404 — no tags.
      }
      tags.push(...refNames(page.body, url));
      url = page.next;
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

  /**
   * Parse a response body, mapping malformed JSON onto `ResolveError`.
   *
   * The module's documented error contract is `ResolveError`; a malformed 200
   * must not escape as a raw `SyntaxError`. Peer of Python's `_parse_json`.
   */
  private parseJson(resp: HttpResponse, url: string): unknown {
    try {
      return resp.json();
    } catch (err) {
      throw new ResolveError(
        `Failed to parse JSON response from ${url}: ${(err as Error).message}`,
      );
    }
  }

  /** Fetch and parse JSON, or `null` on 404. */
  private async getJson(url: string): Promise<unknown | null> {
    const resp = await this.fetch(url);
    if (resp.status === 404) {
      return null;
    }
    return this.parseJson(resp, url);
  }

  /** Fetch one page: `{ body, next }`, or `null` on 404. */
  private async getPage(url: string): Promise<{ body: unknown; next: string | null } | null> {
    const resp = await this.fetch(url);
    if (resp.status === 404) {
      return null;
    }
    return { body: this.parseJson(resp, url), next: parseNextLink(resp.header("Link")) };
  }
}

// -- response-shape validation ---------------------------------------------
//
// A 200 that parses as JSON has still told us nothing until its *shape* is
// checked. Skipping the check does not avoid the failure, it relocates it: to
// an `undefined` returned where the signature promises `string`, which reaches
// the lockfile as an unquoted `sha: null` this same package then refuses to
// read back, or to a `[]` from `listTags` that reads as "this repo has no
// tags". Both ports throw from here, with the same message shape.

/** Whether `value` is a JSON object (not null, not an array). */
function isJsonObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Name `value`'s JSON type the way both ports name it in messages. */
function jsonType(value: unknown): string {
  if (value === null || value === undefined) {
    return "null";
  }
  if (Array.isArray(value)) {
    return "array";
  }
  const primitive = typeof value;
  return primitive === "object" ? "object" : primitive;
}

/** The one message shape for a well-formed-JSON, wrong-shape 200. */
function shapeError(url: string, detail: string): ResolveError {
  return new ResolveError(`Unexpected response shape from ${url}: ${detail}`);
}

/** The `object` member of a ref response, or `ResolveError`. */
function refObject(data: unknown, url: string): { type?: string; sha?: unknown } {
  if (!isJsonObject(data)) {
    throw shapeError(url, `expected an object, got ${jsonType(data)}`);
  }
  const obj = data["object"];
  if (!isJsonObject(obj)) {
    throw shapeError(url, `'object' must be an object, got ${jsonType(obj)}`);
  }
  return obj;
}

/** `object.sha` as a string, or `ResolveError`. */
function requireSha(obj: { sha?: unknown }, url: string): string {
  if (typeof obj.sha !== "string") {
    throw shapeError(url, `'object.sha' must be a string, got ${jsonType(obj.sha)}`);
  }
  return obj.sha;
}

/** Tag names from one page of `git/refs/tags`, `refs/tags/` stripped. */
function refNames(data: unknown, url: string): string[] {
  if (!Array.isArray(data)) {
    throw shapeError(url, `expected an array, got ${jsonType(data)}`);
  }
  const names: string[] = [];
  for (const [index, entry] of data.entries()) {
    if (!isJsonObject(entry)) {
      throw shapeError(url, `[${index}] must be an object, got ${jsonType(entry)}`);
    }
    const fullRef = entry["ref"];
    if (typeof fullRef !== "string") {
      throw shapeError(url, `[${index}].ref must be a string, got ${jsonType(fullRef)}`);
    }
    if (fullRef.startsWith("refs/tags/")) {
      names.push(fullRef.slice("refs/tags/".length));
    }
  }
  return names;
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
