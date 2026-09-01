/**
 * Code-point string ordering — the one sort dialect both ports use.
 *
 * Python's `sorted()` / `list.sort()` compare `str` values by Unicode code
 * point, with no locale involved, always. Neither of JavaScript's built-in
 * options matches that on its own: `Array.prototype.sort()` with no
 * comparator compares by UTF-16 code unit, which agrees with code-point
 * order across the Basic Multilingual Plane but diverges for astral-plane
 * characters (surrogate pairs sort as two high code units instead of one
 * larger code point); `String.prototype.localeCompare` sorts by locale
 * collation, which is not just astral-plane-sensitive but actively
 * machine-dependent — the same input can order differently across locales,
 * so it is never reproducible output for a tool that promises byte-identical
 * results across ports and machines.
 *
 * `codePointCompare` is the single comparator both call sites use so the
 * ordering is named once rather than re-derived per call site.
 */
export function codePointCompare(a: string, b: string): number {
  const ai = Array.from(a);
  const bi = Array.from(b);
  const len = Math.min(ai.length, bi.length);
  for (let i = 0; i < len; i++) {
    const ac = ai[i]!.codePointAt(0)!;
    const bc = bi[i]!.codePointAt(0)!;
    if (ac !== bc) {
      return ac - bc;
    }
  }
  return ai.length - bi.length;
}
