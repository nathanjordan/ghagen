/**
 * Canonical parsed `uses:` action reference.
 *
 * One type replaces the scattered `lastIndexOf("@")` splits and the
 * divergent pinnability predicate that used to live in `collect.ts`,
 * `transform.ts`, `resolve.ts`, and the deps CLI.
 */

// 40-character lowercase hex — already a commit SHA.
const SHA_RE = /^[0-9a-f]{40}$/;

/**
 * A parsed `owner/repo[/path]@ref` action reference.
 *
 * Knows whether it is **Pinnable** — remote (not `./` or `docker://`) and
 * not already written as a commit SHA.
 */
export class UsesRef {
  private constructor(
    readonly owner: string,
    readonly repo: string,
    readonly path: string | null,
    readonly ref: string,
  ) {}

  /**
   * Parse an `owner/repo[/path]@ref` string, or return `null`.
   *
   * Returns `null` for references that are unpinnable by *shape*: local
   * paths (`./…`), docker images (`docker://…`), or strings with no `@ref`
   * component. Otherwise splits into `owner/repo[/path]@ref` where `path`
   * is everything between the repo and the `@` (and may itself contain `/`).
   */
  static parse(uses: string): UsesRef | null {
    if (uses.startsWith("./") || uses.startsWith("docker://")) {
      return null;
    }
    if (!uses.includes("@")) {
      return null;
    }

    const at = uses.lastIndexOf("@");
    const actionPart = uses.slice(0, at);
    const ref = uses.slice(at + 1);
    const parts = actionPart.split("/");
    if (parts.length < 2) {
      return null;
    }

    const owner = parts[0]!;
    const repo = parts[1]!;
    const path = parts.length > 2 ? parts.slice(2).join("/") : null;
    return new UsesRef(owner, repo, path, ref);
  }

  /** Whether `ref` is a 40-character lowercase hex SHA. */
  get refIsSha(): boolean {
    return SHA_RE.test(this.ref);
  }

  /** Whether this ref can be pinned (parsed AND not already a SHA). */
  get isPinnable(): boolean {
    return !this.refIsSha;
  }

  /** The `owner/repo[/path]` portion (without `@ref`). */
  get actionPart(): string {
    return this.path !== null
      ? `${this.owner}/${this.repo}/${this.path}`
      : `${this.owner}/${this.repo}`;
  }

  /** Rebuild the reference as `owner/repo[/path]@sha`. */
  withSha(sha: string): string {
    return `${this.actionPart}@${sha}`;
  }
}
