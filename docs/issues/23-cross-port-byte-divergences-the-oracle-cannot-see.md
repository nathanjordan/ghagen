# Cross-port byte divergences the shared oracle cannot see

**Status:** open — from round 2. Found by the whole-branch adversarial review

The shared byte oracle (`fixtures/expected/`) is the round's strongest instrument — nine shared files
were each corrupted by one byte during review and each failed both suites. But it only binds bytes
the fixtures actually exercise. The divergences below are all outside that set: both ports pass every
gate, and a polyglot repo would see the two ports rewrite each other's output.

Each is LIVE in the sense that the code paths differ today; none is currently reached by a fixture.

## 1. Repo groups sort by locale in TypeScript and by code point in Python

TypeScript sorts repo groups with `localeCompare`, which is locale-dependent and therefore **not
reproducible across machines** — the same input can order differently on two developers' laptops,
which is a stronger defect than the parity break. Python sorts by code point.

Pick code-point ordering in both (`.sort()` with no comparator, or an explicit code-point compare),
and add a fixture with keys that order differently under a non-`en` locale.

## 2. `json.dumps` defaults to `ensure_ascii=True`; `JSON.stringify` does not

Any non-ASCII character in a JSON artifact is `\uXXXX`-escaped by Python and emitted literally by
TypeScript. Reaches `--format json`, the plan output, and anything the shipped action publishes.

## 3. `resolved_at` has two read grammars

Python's `datetime.fromisoformat` accepts four forms TypeScript's regex rejects. A lockfile written
by a tool that produces any of those four is readable by one port and not the other. ADR-0006 fixed
the lockfile _keys_ as strings and said nothing about _values_; proposal 15 aligned what is
**written** but not what is **accepted**.

## 4. Lockfile key quote style

LATENT. The two ports quote lockfile keys differently under inputs no fixture produces today.

## 5. `alphabetical` sort dialect

`nodes.py:69-71` uses Python `sorted()` (code point); the TypeScript peer uses `.sort()` (UTF-16 code
unit). These agree for the entire Basic Multilingual Plane and diverge for astral-plane keys — e.g.
`On(extras={...})` containing both `"\u{1F600}"` and `"＀"`. `on` is the only spec on
`alphabetical` mode, so this is reachable only through `extras`.

Same root cause as issue-24's integer-like-key problem: JavaScript's string ordering is not Python's.

## 6. `source_file` resolves symlinks in one port only

`header.py` uses `Path(...).resolve()`, which follows symlinks; `header.ts` uses `resolve()`, which
does not. LATENT and environmental — it needs the config module to be reached through a symlink — but
it puts a different path in the emitted header, which the byte oracle _does_ cover for every other
input.

## What a fix must do

These want one pass, not six. The common shape is that each port reached for its own standard
library's default, and the defaults differ. The fix is to name the intended semantics at the seam and
then make both ports satisfy it — the same move proposals 14 and 15 made for version comparison and
lockfile encoding.

Every item above needs a `fixtures/expected/` entry, otherwise the next round re-derives this list.
