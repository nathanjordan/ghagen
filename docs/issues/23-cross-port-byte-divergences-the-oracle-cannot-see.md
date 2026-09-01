# Cross-port byte divergences the shared oracle cannot see

**Status:** closed — all six items fixed, each with a `fixtures/expected/` oracle. From round 2.
Found by the whole-branch adversarial review

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

## Resolution

One pass, as proposed. Each seam now has a semantics named once (a comment or a shared regex/helper)
and a `fixtures/expected/` oracle; every fixture was corrupted by one byte and confirmed to fail both
`pytest` and `vitest` before being restored.

1. **Repo group sort.** `packages/typescript/src/pin/engine.ts` sorted the `listTags` sweep with
   `.sort((a, b) => a.localeCompare(b))` — locale-dependent, so not reproducible across machines.
   Both ports now sort by code point: Python's `sorted()` already did (unchanged, pinned by a
   regression test so it cannot drift); TypeScript gained `codePointCompare` in the new
   `packages/typescript/src/_codepoint.ts`, used at both call sites that need it (this one and item
   5). Oracle: `fixtures/expected/pin_repo_group_order.txt` (`Zulu/repo` before `apple/repo` — code
   point order, the reverse of locale/dictionary order).

2. **`ensure_ascii`.** `pin/render.py`'s `_render_json` and `pin/plan.py`'s `render_update_plan`
   both called `json.dumps(..., indent=2)` with the library default `ensure_ascii=True`;
   `JSON.stringify` never escapes non-ASCII. Both Python call sites now pass
   `ensure_ascii=False`, matching TypeScript (which needed no change here — `render.ts`/`plan.ts`
   were already correct, confirmed by reading both). A non-ASCII byte (`á`) was folded into the
   existing `source_files` fixture data shared by both ports (`_bumps()`/`_stale()` in
   `test_render.py`, `BUMPS` in `render.test.ts`), which also exposed and fixed a pre-existing,
   unrelated defect: `fixtures/expected/upgrade_report.json` was hand-written with single-line JSON
   arrays and was never actually byte-identical to real renderer output (`indent=2` /
   `JSON.stringify(..., null, 2)` both always expand arrays to multi-line); the fixture is now
   generated from real output and both golden tests assert byte-exactness, not just JSON-semantic
   equality. Plan-output JSON got its own direct non-ASCII test in both ports since it has no
   pre-existing file fixture to extend.

3. **`resolved_at` read grammar.** `pin/lockfile.py`'s `_decode_timestamp` delegated straight to
   `datetime.fromisoformat`, which (3.11+) accepts a space separator, a colonless or minuteless
   offset, a comma decimal, basic format (no separators), and non-`:00` UTC spellings like
   `+00:00:00`/`-00:00` — all of which TypeScript's `TIMESTAMP_RE` already rejected. Python now
   checks the same named regex (`_TIMESTAMP_RE`, byte-identical to TypeScript's `TIMESTAMP_RE`)
   before calling `fromisoformat`/before trusting a ruamel `TimeStamp`, closing the reader to
   exactly the grammar ADR-0006 already named but the code didn't fully enforce (see the ADR-0006
   amendment below). Both ports gained 7 new parametrized rejection cases for the newly-closed forms,
   plus a shared-file oracle for the flagship case:
   `fixtures/expected/lockfile_space_separator_rejected.yml`.

4. **Lockfile key quote style.** LATENT, as the issue said — no `uses:` string produced by normal
   usage is ambiguous (every real ref carries `/`, `@`, or a `docker://` prefix). Reachable by
   constructing a `Lockfile` directly through the public API with a key like `"123456"`, which
   ruamel and the TypeScript `yaml` package quote differently (single vs. double) when left to their
   own heuristics. Both ports now decide explicitly with a shared predicate
   (`_key_needs_quoting`/`needsQuoting`, same regex) covering YAML 1.1 bool/null keywords,
   int/float-shaped scalars, and structural characters — never delegated to the library. Oracle:
   `fixtures/expected/lockfile_key_quoting.yml`, constructed via the public `Lockfile` API (not the
   CLI, since the CLI can never produce an ambiguous key) and asserted both ways (write matches
   golden bytes; golden reads back to the right keys/values).

5. **`alphabetical` sort dialect.** `emitter/yaml-writer.ts`'s `orderedEntries` sorted with
   `.sort()` (UTF-16 code unit); `nodes.py`'s Python peer used `sorted()` (code point). These agree
   across the whole Basic Multilingual Plane and diverge only for astral-plane keys. `On(extras=...)`
   is the only reachable path, per the issue's own note that `on` is the sole spec on
   `order="alphabetical"`. TypeScript now sorts with the same `codePointCompare` used for item 1.
   Oracle: `fixtures/expected/on_extras_astral_order.txt`, built from the exact character pair named
   in this issue (U+FF00 `＀` and U+1F600 `😀`), exercised through the public `to_data`/`toData`
   surface rather than the internal (non-exported in TypeScript) ordering function.

6. **`source_file` symlink resolution.** `emitter/header.py` (via `config.py`'s `find_app_root`)
   called `Path(...).resolve()`, which follows symlinks and returns a realpath; `header.ts`'s
   `resolve()` from `node:path` is lexical only (string manipulation, no filesystem access, no way
   to opt out of following a symlink because it never has that capability). Python now uses
   `Path(os.path.abspath(...))` in both `config.py` and `header.py`: `.` and `..` collapsed, cwd
   joined for a relative path, but no symlink ever followed — matching TypeScript's actual
   capability instead of Python's. LATENT and environmental, as the issue said: it needs
   `.ghagen.yml`/the emitted file to be reached through a symlinked path. Oracle:
   `fixtures/expected/header_source_file_symlink.txt` (`link/workflows.py`, not the real path behind
   the link), built by exercising `build_header_variables` (Python) / `buildHeaderVariables`
   (TypeScript) against a `tmp_path`-created symlink directly, bypassing the CLI (which would need a
   real symlinked checkout to reach this at all).

**ADR:** ADR-0006 already stated the intended reader invariant for the lockfile boundary ("neither
delegates scalar style or timestamp tolerance to its YAML library") but the code hadn't fully lived
up to it for reading `resolved_at` or for key quoting — items 3 and 4 close that specific gap, and
ADR-0006 got a short amendment recording it (its original decision and rationale stand unchanged). No
new ADR: none of the other four items is a genuine trade-off — each is a straightforward case of two
ports reaching for two different standard-library defaults with no reasonable argument for either
default over the other (locale-dependent sort, ASCII-escaping, UTF-16-code-unit sort, and
symlink-following are not intentional choices anywhere in the codebase, just unexamined defaults), so
"pick one, make both do it" is not a decision worth a standing record.

**Nothing was unreachable.** All six, including the two the issue itself called LATENT (4 and 6),
got a fixture that actually exercises the code path — items 4 and 6 by going through each port's
public API directly (`Lockfile`/`build_header_variables`) rather than the CLI, since the CLI cannot
construct the triggering input (an ambiguous lockfile key; a symlinked source path) on its own.
