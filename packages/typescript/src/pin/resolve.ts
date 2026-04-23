/**
 * Resolve GitHub Action refs to commit SHAs via the GitHub REST API.
 *
 * Uses native Node 20+ `fetch`. Supports both lightweight and annotated
 * tags (dereferences tag objects to their underlying commit).
 */

/** Raised when a ref cannot be resolved to a commit SHA. */
export class ResolveError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ResolveError";
  }
}

/** Parsed components of an `owner/repo[/path]@ref` string. */
export interface ParsedUses {
  readonly owner: string;
  readonly repo: string;
  readonly path: string | null;
  readonly ref: string;
}

/** Options applicable to all GitHub API requests. */
export interface ResolveOptions {
  /** Optional GitHub personal access token. */
  token?: string;
}

const API_TIMEOUT_MS = 30_000;

/** Parse an `owner/repo[/path]@ref` string into components. */
export function parseUses(uses: string): ParsedUses {
  if (!uses.includes("@")) {
    throw new Error(`No @ref in uses string: ${JSON.stringify(uses)}`);
  }
  const at = uses.lastIndexOf("@");
  const actionPart = uses.slice(0, at);
  const ref = uses.slice(at + 1);
  const parts = actionPart.split("/");
  if (parts.length < 2) {
    throw new Error(`Cannot parse owner/repo from: ${JSON.stringify(uses)}`);
  }
  const owner = parts[0]!;
  const repo = parts[1]!;
  const path = parts.length > 2 ? parts.slice(2).join("/") : null;
  return { owner, repo, path, ref };
}

/**
 * Resolve a git ref to a commit SHA via the GitHub API.
 *
 * Tries `tags/{ref}` first, then `heads/{ref}`. For annotated tags the
 * tag object is dereferenced to the underlying commit.
 */
export async function resolveRef(
  owner: string,
  repo: string,
  ref: string,
  options: ResolveOptions = {},
): Promise<string> {
  for (const prefix of ["tags", "heads"] as const) {
    const url = `https://api.github.com/repos/${owner}/${repo}/git/ref/${prefix}/${ref}`;
    let data: { object: { type: string; sha: string } } | null;
    try {
      data = (await apiGet(url, options)) as {
        object: { type: string; sha: string };
      };
    } catch (err) {
      if (err instanceof NotFoundError) {
        continue;
      }
      throw err;
    }

    let sha = data.object.sha;
    if (data.object.type === "tag") {
      sha = await dereferenceTag(owner, repo, sha, options);
    }
    return sha;
  }

  throw new ResolveError(
    `Could not resolve ref '${ref}' for ${owner}/${repo}. ` +
      "Tried tags/ and heads/ — neither exists.",
  );
}

/**
 * List all tags for a repository via the GitHub API.
 *
 * Uses paginated `GET /repos/{owner}/{repo}/git/refs/tags`. Returns
 * tag names with the `refs/tags/` prefix stripped.
 */
export async function listTags(
  owner: string,
  repo: string,
  options: ResolveOptions = {},
): Promise<string[]> {
  let url: string | null = `https://api.github.com/repos/${owner}/${repo}/git/refs/tags`;
  const tags: string[] = [];
  while (url !== null) {
    let body: unknown;
    let nextUrl: string | null;
    try {
      const page = await apiGetPage(url, options);
      body = page.body;
      nextUrl = page.next;
    } catch (err) {
      if (err instanceof NotFoundError) {
        return [];
      }
      throw err;
    }
    if (!Array.isArray(body)) {
      break;
    }
    for (const ref of body as Array<{ ref?: string }>) {
      const fullRef = ref.ref ?? "";
      if (fullRef.startsWith("refs/tags/")) {
        tags.push(fullRef.slice("refs/tags/".length));
      }
    }
    url = nextUrl;
  }
  return tags;
}

/** Internal: marker thrown on 404 so callers can attempt fallbacks. */
class NotFoundError extends Error {}

interface PageResult {
  body: unknown;
  next: string | null;
}

async function apiGet(url: string, options: ResolveOptions): Promise<unknown> {
  const { body } = await apiGetPage(url, options);
  return body;
}

async function apiGetPage(url: string, options: ResolveOptions): Promise<PageResult> {
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
    throw new ResolveError(`Network error reaching GitHub API: ${(err as Error).message}`);
  }

  if (response.status === 404) {
    // Drain the body so the connection can be reused.
    await response.text().catch(() => {});
    throw new NotFoundError();
  }
  if (response.status === 403) {
    warnRateLimit(response);
  }
  if (!response.ok) {
    const text = await response.text().catch(() => response.statusText);
    throw new ResolveError(
      `GitHub API error ${response.status} for ${url}: ${text || response.statusText}`,
    );
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch (err) {
    throw new ResolveError(`Failed to parse JSON response from ${url}: ${(err as Error).message}`);
  }
  const next = parseNextLink(response.headers.get("Link"));
  return { body, next };
}

async function dereferenceTag(
  owner: string,
  repo: string,
  tagSha: string,
  options: ResolveOptions,
): Promise<string> {
  const url = `https://api.github.com/repos/${owner}/${repo}/git/tags/${tagSha}`;
  const data = (await apiGet(url, options)) as {
    object?: { type?: string; sha?: string };
  };
  const obj = data.object ?? {};
  if (obj.type === "commit" && typeof obj.sha === "string") {
    return obj.sha;
  }
  throw new ResolveError(
    `Tag ${tagSha} in ${owner}/${repo} does not point to a commit (type=${JSON.stringify(
      obj.type ?? null,
    )})`,
  );
}

/**
 * Extract the `next` URL from a GitHub `Link` header.
 *
 * Example header value:
 *
 *     <https://api.github.com/repos/o/r/git/refs/tags?page=2>; rel="next",
 *     <https://api.github.com/repos/o/r/git/refs/tags?page=5>; rel="last"
 */
function parseNextLink(header: string | null): string | null {
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

function warnRateLimit(response: Response): void {
  const remaining = response.headers.get("X-RateLimit-Remaining") ?? "?";
  process.stderr.write(
    `warning: GitHub API rate limit hit (remaining=${remaining}). ` +
      "Set $GITHUB_TOKEN or use --token for higher limits.\n",
  );
}
