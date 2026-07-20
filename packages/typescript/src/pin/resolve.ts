/**
 * Error type for GitHub Action ref resolution.
 *
 * The networked resolution logic lives in `./github.ts` (`GitHubClient`).
 * `ResolveError` stays here as a dependency-free leaf so both the client and
 * its transports can import it without a cycle.
 */

/** Raised when a ref cannot be resolved to a commit SHA. */
export class ResolveError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ResolveError";
  }
}
