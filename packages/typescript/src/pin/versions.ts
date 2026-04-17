/**
 * Version comparison utilities for GitHub Action tags.
 *
 * Hand-rolls the tag regex (`semver.coerce` discards prefixes like
 * `prefix-v1.0.0`, which we need to preserve). Numeric segments are
 * padded to a.b.c and fed into `semver.SemVer`.
 */

import { SemVer } from "semver";

// Matches an optional prefix (delimited by `-` or `/`) followed by an
// optional `v` and a numeric version.
//   group 1 = prefix (including delimiter), or undefined
//   group 2 = the version digits (e.g. "4", "4.1", "4.1.2")
const TAG_RE = /^(?:(.+)[/-])?v?(\d+(?:\.\d+)*)$/;

/** A parsed tag — wraps a SemVer plus the optional human prefix. */
export interface ParsedTag {
  /** The original tag string (e.g. `"v4"`, `"prefix-v1.0.0"`). */
  readonly tag: string;
  /** Prefix (without delimiter), or null when there is no prefix. */
  readonly prefix: string | null;
  /** Comparable semantic version. */
  readonly version: SemVer;
}

/** Parse a GitHub Action tag into a `ParsedTag`, or `null` if non-version. */
export function parseTag(tag: string): ParsedTag | null {
  const m = tag.match(TAG_RE);
  if (!m) return null;
  const prefix = m[1] ?? null;
  const versionStr = m[2]!;
  const segments = versionStr.split(".");

  // When a prefix is present (e.g. release/v1), require at least two
  // version segments so branch-like refs are rejected.
  if (prefix !== null && segments.length < 2) return null;

  // Pad to three segments so v4 → 4.0.0, v4.1 → 4.1.0.
  while (segments.length < 3) segments.push("0");

  try {
    const version = new SemVer(segments.join("."));
    return { tag, prefix, version };
  } catch {
    return null;
  }
}

/** Severity of a version bump. */
export type BumpSeverity = "major" | "minor" | "patch";

/** Classify the severity of a bump from `current` to `latest`. */
export function classifyBump(current: SemVer, latest: SemVer): BumpSeverity {
  if (latest.major !== current.major) return "major";
  if (latest.minor !== current.minor) return "minor";
  return "patch";
}

/**
 * Find the latest tag in `availableTags` that is newer than `currentRef`.
 *
 * Filters candidates to the same prefix as `currentRef`, parses them as
 * versions, and returns the original tag string for the highest version
 * — or `null` if `currentRef` is already up to date or unparseable.
 */
export function findLatestTag(
  currentRef: string,
  availableTags: readonly string[],
): string | null {
  const current = parseTag(currentRef);
  if (current === null) return null;

  let bestTag: string | null = null;
  let bestVersion: SemVer | null = null;

  for (const tag of availableTags) {
    const parsed = parseTag(tag);
    if (parsed === null) continue;
    if (parsed.prefix !== current.prefix) continue;
    if (parsed.version.compare(current.version) <= 0) continue;
    if (bestVersion === null || parsed.version.compare(bestVersion) > 0) {
      bestVersion = parsed.version;
      bestTag = tag;
    }
  }

  return bestTag;
}
