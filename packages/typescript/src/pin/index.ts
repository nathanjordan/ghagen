/** ghagen pin — SHA-based lockfile for GitHub Actions references. */

export {
  DEFAULT_LOCKFILE_PATH,
  Lockfile,
  LockfileError,
  type PinEntry,
  readLockfile,
  writeLockfile,
} from "./lockfile.js";
export {
  GitHubClient,
  FetchTransport,
  ResolveError,
  TransportError,
  type HttpClient,
  HttpResponse,
  type RequestOptions,
} from "./github.js";
export { UsesRef } from "./uses.js";
export { type BumpSeverity } from "./versions.js";
export { collectUsesRefs } from "./collect.js";
export { renderUpgradeReport, type UpgradeFormat } from "./render.js";
export {
  planUpdate,
  parseLabels,
  renderUpdatePlan,
  type PlanFormat,
  type UpdateAction,
  type UpdateOutput,
  type UpdatePlan,
  type PlanUpdateOptions,
} from "./plan.js";
export { UsesSite, iterUsesSites } from "./sites.js";
export { PinError, type PinTransform, pinTransform } from "./transform.js";
export { trackUserFiles, locateUsesRefs } from "./sources.js";
export { applyUpdates } from "./update.js";
export {
  pin,
  checkSync,
  upgrade,
  SyncReport,
  type PinReport,
  type PinOptions,
  type ResolvedPin,
  type CheckSyncOptions,
  type UpgradeReport,
  type UpgradeOptions,
  type VersionBump,
  type LockfileStaleEntry,
} from "./engine.js";
