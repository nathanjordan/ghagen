/**
 * The version-tag grammar for GitHub Action refs — ghagen's own.
 *
 * This module alone answers: *is this ref a version tag, which of two tags is
 * newer, and how big is the jump?* It holds the tag regex, the prefix rule,
 * the canonical-release rule, the segment cap, the total order, the
 * same-prefix filter, and the severity classification.
 *
 * The grammar is declared once, in `schema/tag-grammar.yml`, and pinned by
 * both ports' suites. No third-party version library sits on this path — see
 * `docs/adr/0008-ghagen-owns-its-tag-grammar.md`.
 */

// Matches an optional prefix (delimited by `-` or `/`) followed by an
// optional `v` and a numeric version.
//   group 1 = prefix (including delimiter), or undefined
//   group 2 = the version digits (e.g. "4", "4.1", "4.1.2", "4.1.2.3")
const TAG_RE = /^(?:(.+)[/-])?v?(\d+(?:\.\d+)*)$/;

/**
 * Largest value a release segment may hold (10**15 - 1).
 *
 * The rule is on the integer **value**, not on the literal's length: a
 * zero-padded `v0000000000000001.0.0` is 16 characters but the value 1, and is
 * accepted, while `v9999999999999999.0.0` is rejected. The cap exists so both
 * ports can hold a release in a plain integer array — JS numbers are exact
 * below 2**53, and 999_999_999_999_999 < 9_007_199_254_740_991.
 */
const MAX_SEGMENT = 999_999_999_999_999;

/** Severity of a version bump. */
export type BumpSeverity = "major" | "minor" | "patch";

/** A parsed version tag: its prefix and its canonical release. */
export interface ParsedTag {
  /** The original tag string, preserved for rewriting the uses-site. */
  readonly tag: string;
  /** Prefix (without delimiter), or null when there is no prefix. */
  readonly prefix: string | null;
  /** Canonical release: length >= 3, no trailing zeros past index 2. */
  readonly release: readonly number[];
}

/** A newer tag for a ref, with everything the caller needs about it. */
export interface Bump {
  readonly current: ParsedTag;
  readonly latest: ParsedTag;
  readonly severity: BumpSeverity;
}

/**
 * Parse a GitHub Action tag into a `ParsedTag`, or `null` if it is not one.
 *
 * A ref is a version tag iff it matches the tag regex — an optional
 * `prefix-` / `prefix/`, an optional `v`, then dot-separated integers — and
 * every segment's value is at most {@link MAX_SEGMENT}. When a prefix is
 * present the numeric part needs at least two segments, which keeps
 * branch-like refs such as `release/v1` out.
 *
 * The canonical release parses each segment as an integer, pads with zeros to
 * length three, then drops trailing zeros beyond index 2: `v4` becomes
 * `[4, 0, 0]`, `v01.02.03` becomes `[1, 2, 3]`, and `v1.2.3.0` becomes
 * `[1, 2, 3]` — the same version as `v1.2.3`.
 */
export function parseTag(tag: string): ParsedTag | null {
  const m = tag.match(TAG_RE);
  if (!m) {
    return null;
  }
  const prefix = m[1] ?? null;
  const segments = m[2]!.split(".");

  // When a prefix is present (e.g. release/v1), require at least two
  // version segments so branch-like refs are rejected.
  if (prefix !== null && segments.length < 2) {
    return null;
  }

  const release = segments.map(Number);
  if (release.some((value) => value > MAX_SEGMENT)) {
    return null;
  }

  // Pad to three so v4 → [4, 0, 0], then strip trailing zeros beyond the
  // third so v1.2.3.0 compares equal to v1.2.3.
  while (release.length < 3) {
    release.push(0);
  }
  while (release.length > 3 && release[release.length - 1] === 0) {
    release.pop();
  }

  return { tag, prefix, release };
}

/** Total order on canonical releases: element-wise, then by length. */
function compareRelease(a: readonly number[], b: readonly number[]): number {
  const shared = Math.min(a.length, b.length);
  for (let i = 0; i < shared; i++) {
    if (a[i]! !== b[i]!) {
      return a[i]! < b[i]! ? -1 : 1;
    }
  }
  if (a.length === b.length) {
    return 0;
  }
  return a.length < b.length ? -1 : 1;
}

/** Severity of the jump from `current` to `latest` (both length >= 3). */
function classify(current: ParsedTag, latest: ParsedTag): BumpSeverity {
  if (latest.release[0]! !== current.release[0]!) {
    return "major";
  }
  if (latest.release[1]! !== current.release[1]!) {
    return "minor";
  }
  return "patch";
}

/**
 * The newest same-prefix tag strictly newer than `currentRef`, classified.
 *
 * `null` when `currentRef` is not a version tag, or when nothing in
 * `availableTags` is newer. Equal versions are not newer, so they produce no
 * `Bump` at all. Every returned `Bump` holds parsed values; no caller
 * re-parses (ADR-0006).
 */
export function latestBump(currentRef: string, availableTags: Iterable<string>): Bump | null {
  const current = parseTag(currentRef);
  if (current === null) {
    return null;
  }

  let best: ParsedTag | null = null;
  for (const tag of availableTags) {
    const parsed = parseTag(tag);
    if (parsed === null) {
      continue;
    }
    if (parsed.prefix !== current.prefix) {
      continue;
    }
    if (compareRelease(parsed.release, current.release) <= 0) {
      continue;
    }
    if (best === null || compareRelease(parsed.release, best.release) > 0) {
      best = parsed;
    }
  }

  if (best === null) {
    return null;
  }

  return { current, latest: best, severity: classify(current, best) };
}
