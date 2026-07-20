/** ghagen pin — SHA-based lockfile for GitHub Actions references. */

export {
  DEFAULT_LOCKFILE_PATH,
  Lockfile,
  LockfileError,
  type PinEntry,
  readLockfile,
  writeLockfile,
} from "./lockfile.js";
export { ResolveError } from "./resolve.js";
export {
  GitHubClient,
  FetchTransport,
  TransportError,
  type HttpClient,
  type HttpResponse,
  type RequestOptions,
} from "./github.js";
export { UsesRef } from "./uses.js";
export {
  type BumpSeverity,
  type ParsedTag,
  parseTag,
  classifyBump,
  findLatestTag,
} from "./versions.js";
export { collectUsesRefs } from "./collect.js";
export { PinError, type PinTransform, pinTransform } from "./transform.js";
export { trackUserFiles, locateUsesRefs } from "./sources.js";
export { applyUpdates } from "./update.js";
