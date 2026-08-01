# 15 — Single-home the Lockfile's on-disk encoding and error mode

**Status:** proposed | **Ports:** both | **Effort:** M | **Depends on:** **20** (delete caller-less pin/spec surface) — an **ordering** edge, not a source dependency. 20's `merge`→constructor rewrite at `lockfile.test.ts:142-145` sits _inside_ `:139-152`, the byte-identity test this proposal marks **Kept**; if 15 landed first, 20 would have to hand-apply that rewrite to a block 15 has frozen. **20 goes first**, and 15 inherits its constructor rewrites

## Files involved

### Modified

| Path                                              | Lines | Role in this proposal                                                                                                                                                                                                                                                                |
| ------------------------------------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `packages/python/src/ghagen/pin/lockfile.py`      | 167   | Module docstring becomes the normative on-disk grammar; `write_lockfile` states every scalar style explicitly and encodes the timestamp at second precision; `read_lockfile` wraps ruamel's parse errors in `LockfileError` and routes `resolved_at` through a stated decode grammar |
| `packages/typescript/src/pin/lockfile.ts`         | 182   | Mirror: `stringify` is fed double-quoted `Scalar`s, the timestamp encoder loses the lossy `.replace(…)`, `readLockfile` gains the top-level-shape check and the same decode grammar, the unreachable `instanceof Date` branch is deleted                                             |
| `packages/python/tests/test_pin/test_lockfile.py` | 254   | Golden-fixture conformance (write **and** read); malformed top-level and YAML-syntax cases; timestamp encode **and decode** cases                                                                                                                                                    |
| `packages/typescript/src/pin/lockfile.test.ts`    | 171   | Mirror; the hand-written "Python-written lockfile" literal is replaced by the golden, the missing reverse direction is added, and the header assertion follows the corrected literal                                                                                                 |
| `packages/python/tests/test_cli/test_deps.py`     | 911   | **Staleness only.** `_LOCKFILE:43` and `_UPGRADE_LOCKFILE:140` embed the old `ghagen pin` header literal in test _input_. Nothing breaks (they are fed to `read_lockfile`, which skips comments), but they must be refreshed or the repo carries two spellings of its own header     |
| `.ghagen.lock.yml`                                | 30    | Re-encoded to the canonical form: 9 `sha` values gain quotes, 9 `resolved_at` values lose `.131322`, header literal corrected                                                                                                                                                        |
| `packages/python/CONTEXT.md`                      | 114   | One appended **Example dialogue** exchange at end-of-file (implementation phase; see last section)                                                                                                                                                                                   |
| `packages/typescript/CONTEXT.md`                  | 119   | Mirror, same anchor (implementation phase; see last section)                                                                                                                                                                                                                         |
| `CONTEXT-MAP.md`                                  | 26    | `:17-18` calls the lockfile "snake_case keys for cross-language interop" — the same key-only understatement this proposal corrects in ADR-0006 (implementation phase; see last section)                                                                                              |
| `docs/adr/0006-pin-collects-parsed-refs.md`       | 20    | Amend _Consequences_: the boundary fixes **values** as well as keys (implementation phase; see last section)                                                                                                                                                                         |

### New

| Path                                    | Lines    | Role in this proposal                                                                                    |
| --------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------- |
| `fixtures/expected/lockfile_golden.yml` | new (12) | The shared byte oracle: the exact bytes both ports must write, and must read back to the same `Lockfile` |

Deliberately **not** in the table, to keep the conflict graph small:

- `packages/python/src/ghagen/pin/__init__.py`, `packages/typescript/src/pin/index.ts`,
  `packages/typescript/src/index.ts` — the encoder/decoder pair stays module-private, and every
  name this proposal touches is **already** exported: `LockfileError` at `pin/__init__.py:24,:37`,
  `pin/index.ts:6` and `src/index.ts:170`, alongside `Lockfile`, `PinEntry`,
  `read_lockfile`/`readLockfile` and `write_lockfile`/`writeLockfile`
  (`pin/__init__.py:22-28,36-41`, `pin/index.ts:3-10`, `src/index.ts:167-173`). **No barrel edit.**
- `packages/python/tests/test_integration/test_snapshots.py` and
  `packages/typescript/src/integration/snapshots.test.ts` — the golden lands in the **pin** tests,
  not the emitter snapshot suites.
- `packages/typescript/src/paths.ts` / `scripts/ghagen_schema/paths.py` — see _Test impact_; this
  proposal routes around their asymmetry rather than fixing it.
- `packages/python/src/ghagen/pin/transform.py` — carries the same stale command literal
  (`:47` says ``Run `ghagen pin` `` where the TS peer at `transform.ts:42` correctly says
  `ghagen deps pin`). Adjacent, unowned, and out of scope; flagged for the orchestrator.

## Problem

`.ghagen.lock.yml` is the one file both ports read and write. ADR-0006 nailed down its _keys_ and
said nothing about its _values_:

> **The Lockfile boundary stays string-keyed** — `uses` strings → SHAs, snake_case keys, identical
> across both ports. Do not "simplify" the Lockfile to store structured refs; the on-disk format is
> cross-language interop surface. Only the in-memory pin flow is typed.
> — `docs/adr/0006-pin-collects-parsed-refs.md:18-20`

"`snake_case` keys, identical across both ports" is a statement about key _spelling_. It is silent on
scalar style, timestamp precision, the timestamp grammar a reader accepts, and what a reader does
with input it cannot understand. Those decisions are, today, **not made by ghagen at all** — they
are delegated to two different YAML libraries' emitter heuristics, two independently hand-rolled
timestamp expressions, and two different date parsers. The result is that the two ports do not write
the same file, and do not accept the same file.

`CONTEXT-MAP.md:17-18` repeats the same key-only framing ("the same `.ghagen.lock.yml` lockfile
(snake_case keys for cross-language interop)"), as does the TypeScript module docstring
(`lockfile.ts:14-16`). The understatement is three-deep.

### 1. The two ports write different bytes for every entry — **LIVE**

Same input, both ports run:

```python
# packages/python/src/ghagen/pin/lockfile.py:154-159
pins_dict[uses] = {
    "sha": entry.sha,
    "resolved_at": DoubleQuotedScalarString(
        entry.resolved_at.astimezone(UTC).isoformat()
    ),
}
```

```ts
// packages/typescript/src/pin/lockfile.ts:171-174
pinsObj[uses] = {
  sha: entry.sha,
  resolved_at: entry.resolvedAt.toISOString().replace(/\.\d{3}Z$/, "+00:00"),
};
```

Feeding both ports the same three entries — `actions/checkout@v4` at microsecond precision,
`docker://alpine:3.19` with an all-digit SHA, and `pypa/gh-action-pypi-publish@release/v1` — and
diffing the two files:

```diff
--- py.lock.yml
+++ ts.lock.yml
@@ -6 +6 @@
-    resolved_at: "2026-04-09T14:30:00.123456+00:00"
+    resolved_at: 2026-04-09T14:30:00+00:00
@@ -8,9 +8,9 @@
-    sha: '1234567890123456789012345678901234567890'
-    resolved_at: "2026-04-09T14:30:00+00:00"
+    sha: "1234567890123456789012345678901234567890"
+    resolved_at: 2026-04-09T14:30:00+00:00
@@ -12 +12 @@
-    resolved_at: "2026-04-08T00:00:00+00:00"
+    resolved_at: 2026-04-08T00:00:00+00:00
```

Read the second hunk carefully — it is the load-bearing one. **Even at whole-second precision the
two ports disagree, because of quoting.** Precision is the divergence that _looks_ obvious; quoting
is the divergence that fires on **every** `resolved_at` line of **every** lockfile, unconditionally.
Any framing of this problem as "a precision mismatch" is too weak: truncating Python to seconds
would fix nothing on its own.

Two independent scalar-style divergences, both LIVE:

- **`resolved_at` quoting.** Python emits it double-quoted (`DoubleQuotedScalarString`,
  `lockfile.py:156`); TypeScript hands `stringify` a plain string and `yaml` emits it bare
  (confirmed against `yaml@2.8.3`: `stringify({x: "2026-04-09T14:30:00+00:00"})` →
  `x: 2026-04-09T14:30:00+00:00\n`).
- **All-digit SHA quoting — LIVE, not latent.** A 40-character hex SHA that happens to contain only
  decimal digits must be quoted or YAML resolves it to an integer. Both libraries notice, and pick
  different quotes: ruamel emits `sha: '1234…7890'`, `yaml` emits `sha: "1234…7890"` — reproduced in
  the diff above. The _input_ is improbable (P ≈ 1e-9 for a random SHA); the _code path_ is fully
  live and fires on every write. It is labelled LIVE here because reachability, not likelihood, is
  what the label means. It is also the cleanest proof of the thesis: **today the YAML library
  decides the encoding, not ghagen.**

Everything else agrees, verified rather than assumed: keys are emitted plain and ASCII-sorted in
both (including `docker://alpine:3.19` and `pypa/gh-action-pypi-publish@release/v1`), indentation is
two spaces in both, both emit exactly `pins: {}` for an empty lockfile (`cmp`-identical), and both
end with a single trailing newline.

**Both docstrings advertise a third form that neither port writes:**

- `packages/python/src/ghagen/pin/lockfile.py:4-11`
- `packages/typescript/src/pin/lockfile.ts:7-12`

Both show `resolved_at: "2026-04-09T14:30:00+00:00"` — quoted, second-precision — which Python
misses on precision and TypeScript misses on quoting. And both show `sha:` **unquoted**, which the
grammar proposed below (rule 4) breaks: the docstring blocks are not merely stale on one line, they
are wrong on two, and step 2 of the migration must rewrite both lines in both ports.

This is not hypothetical for this repo. `.ghagen.lock.yml` was written by the Python port and every
one of its nine entries carries microseconds (`.ghagen.lock.yml:6,9,12,…` —
`resolved_at: "2026-07-20T20:25:22.131322+00:00"`) with unquoted SHAs. Running the TypeScript
`ghagen deps pin` (`packages/typescript/src/cli/deps.ts:349`) here rewrites all nine, because `pin`
re-encodes the whole map whenever the run is not a no-op (`engine.ts:103-105`; Python
`engine.py:111-113` has the same guard). Adding one new action to a polyglot repo produces a
nine-line diff plus the one intended line.

Worse, the rewrite is **lossy in one direction only**: `Date` cannot hold microseconds, so
TypeScript reading Python's `"2026-04-09T14:30:00.123456+00:00"` truncates to `…:00.123Z` on parse
and then to `…:00+00:00` on write. Python reading TypeScript's output loses nothing. The format is
not representable in one of the two ports that owns it.

### 2. Malformed top-level input: Python raises, TypeScript reads an empty lockfile — **LIVE**

```python
# packages/python/src/ghagen/pin/lockfile.py:110-111
if not isinstance(raw, Mapping):
    raise LockfileError(f"{path}: lockfile must be a mapping")
```

```ts
// packages/typescript/src/pin/lockfile.ts:123-125
if (!raw) {
  return new Lockfile();
}
```

TypeScript has no top-level shape check at all: `raw` is _declared_ `Record<string, unknown>` at
`:115` but `parse` returns whatever the document is, and a non-object simply misses on
`raw["pins"]` at `:127` and falls into the "no pins" early return at `:128-130`. Reproduced against
both ports:

| on-disk document | Python `read_lockfile`                         | TypeScript `readLockfile`        |
| ---------------- | ---------------------------------------------- | -------------------------------- |
| `just-a-string`  | `LockfileError: …: lockfile must be a mapping` | returns `Lockfile`, `size === 0` |
| `- a\n- b`       | `LockfileError: …: lockfile must be a mapping` | returns `Lockfile`, `size === 0` |
| `0`              | `LockfileError: …: lockfile must be a mapping` | returns `Lockfile`, `size === 0` |
| `""`             | `LockfileError: …: lockfile must be a mapping` | returns `Lockfile`, `size === 0` |
| `false`          | `LockfileError: …: lockfile must be a mapping` | returns `Lockfile`, `size === 0` |

`!raw` is also the wrong test for "empty document": `0`, `""` and `false` die at `lockfile.ts:123`
alongside the `null` it means to catch, while truthy non-objects fall through to the `pins`-missing
early return at `:128-130`. Two different wrong paths, one identical wrong outcome.

The user-visible consequence in TypeScript is a **misdirecting** error, not a silent one.
`readLockfile` hands `pinTransform` an empty map, so `synth` throws
`PinError: No lockfile entry for 'actions/checkout@v4'. Run \`ghagen deps pin\` to resolve it.`
(`transform.ts:41-43`) — telling the user to re-pin when their lockfile is corrupt. If they follow
that advice, `deps pin`re-resolves everything and`writeLockfile` **overwrites the corrupt file**
(`engine.ts:103-105`), destroying whatever they had mangled. Python's contract is the correct one
and is the one both class docstrings already claim: "a lockfile only ever holds valid entries"
(`lockfile.py:47-53`, `lockfile.ts:44-50`). That invariant only holds if the reader refuses input it
cannot interpret instead of inventing an empty file.

### 3. Python leaks a third-party exception where TypeScript raises `LockfileError` — **LIVE**

The divergence runs the other way too. The module docstring promises, without qualification, that
`read_lockfile` "validates every on-disk entry and raises `LockfileError` on malformed input"
(`lockfile.py:13-15`), but `yaml.load(path)` at `:107` is unguarded:

| on-disk document       | Python                                                   | TypeScript                                                                   |
| ---------------------- | -------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `pins:\n  - [unclosed` | `ruamel.yaml.parser.ParserError` escapes `read_lockfile` | `LockfileError: …: failed to parse lockfile YAML: …` (`lockfile.ts:118-122`) |

The function's own docstring (`lockfile.py:96-102`) is a _closed_ enumeration — "when the `pins`
value is not a mapping, an entry is not a mapping, `sha` is missing or not a string, or
`resolved_at` is missing or unparseable" — and a YAML syntax error appears nowhere in it. So the
module docstring over-promises and the function docstring under-enumerates; neither one describes
what the code does.

Neither the Python CLI package nor `pin/engine.py` catches anything — there is no `except` anywhere
in `packages/python/src/ghagen/cli/`. End to end, `ghagen deps check-synced` on a repo whose
lockfile is `pins:\n  - actions/checkout@v4` prints a full Rich traceback ending in
`LockfileError: .ghagen.lock.yml: 'pins' must be a mapping`, where the TypeScript peer's `main()`
catch-all (`cli/main.ts:130-139`) prints one line. _How_ a CLI renders and exits belongs to
[19](./19-main-owns-exit-codes.md); _which type the module raises_ is this proposal's, and
`read_lockfile` raising `ruamel.yaml.parser.ParserError` violates its own documented error mode
regardless of what any caller does with it.

### 4. The two readers accept different `resolved_at` grammars — **LIVE**

Encoding is only half of an interop format. The _decoder_ grammar is currently delegated whole to
`ruamel.yaml` + `datetime.fromisoformat` on one side and `yaml` + `new Date()` on the other, and
they do not agree. Nine on-disk shapes, both ports, run under `TZ=America/Chicago`:

| on-disk `resolved_at`               | Python `read_lockfile`                                                         | TypeScript `readLockfile`                              |
| ----------------------------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------ |
| `2026-04-09` (bare)                 | **`LockfileError`** — ruamel yields `datetime.date`, which is not a `datetime` | accepted → `2026-04-09T00:00:00.000Z`                  |
| `"2026-04-09"`                      | accepted, **tz-naive** `datetime(2026, 4, 9, 0, 0)`                            | accepted → `2026-04-09T00:00:00.000Z` (UTC)            |
| `"April 9, 2026"`                   | **`LockfileError`**                                                            | accepted → `2026-04-09T05:00:00.000Z` — **host-local** |
| `"2026/04/09"`                      | **`LockfileError`**                                                            | accepted → `2026-04-09T05:00:00.000Z` — **host-local** |
| `"2026-04-09T14:30:00"` (naive)     | accepted, **tz-naive**                                                         | accepted → `2026-04-09T19:30:00.000Z` — **host-local** |
| `2026-04-09T14:30:00` (bare, naive) | accepted, `TimeStamp`, **tz-naive**                                            | accepted → **host-local**                              |
| `2026-04-09T14:30:00+00:00` (bare)  | accepted, `TimeStamp`, UTC                                                     | accepted, UTC                                          |
| `"2026-04-09T14:30:00+00:00"`       | accepted, UTC                                                                  | accepted, UTC                                          |
| `"2026-04-09T14:30:00Z"`            | accepted, UTC                                                                  | accepted, UTC                                          |

**Six of nine shapes diverge.** Only the three explicit-UTC forms agree — which is to say, the two
readers agree on exactly the shapes ghagen itself writes and on nothing else.

Two of those rows are sharper than "different error behaviour":

- **`"April 9, 2026"` and `"2026/04/09"` are accepted by TypeScript with a host-dependent result.**
  Two developers on the same repo in different timezones read different instants out of the same
  bytes. That is a correctness bug in a file whose entire purpose is cross-machine reproducibility.
- **The naive shapes put a tz-naive `datetime` into a `PinEntry` whose field docstring says "UTC
  timestamp"** (`lockfile.py:42-43`). This is not cosmetic: the encoder proposed in (b) below calls
  `.astimezone(UTC)`, and `.astimezone()` on a _naive_ datetime interprets it as **host-local**. So
  a naive value that entered from disk would make the **encoder's output** host-dependent too — the
  bug would leak from the read path into the write path. The grammar (rule 7) and the encoder guard
  in (b) exist to close exactly that.

### 5. One latent consequence of delegating scalar style to the YAML libraries — **LATENT**

**`resolvedAt instanceof Date` at `lockfile.ts:148-149` is unreachable.** The `yaml` package's YAML
1.2 core schema has no timestamp tag; confirmed against `yaml@2.8.3`, `parse("a: 2026-04-09T14:30:00+00:00")`,
`parse("a: 2026-04-09T14:30:00Z")` and `parse("a: 2026-04-09")` all return a **string**. The branch
exists as a mirror of Python's `isinstance(resolved_at, datetime)` at `:129-130`, which _is_
reachable — ruamel resolves an unquoted timestamp to `ruamel.yaml.timestamp.TimeStamp`. That
asymmetry is exactly why quoting matters: unquoted, the **type** of `resolved_at` after parsing
depends on which port reads the file.

### 6. The interop test runs one direction, and its input is fictional

There is exactly one cross-port lockfile test in the tree — `lockfile.test.ts`'s
`it("reads a Python-written lockfile (string-typed resolved_at)")` (`:154-170` on `main`):

```ts
'    resolved_at: "2026-04-09T14:30:00+00:00"',
```

Two problems. First, the fixture is hand-written to the _docstring's_ form, not to what Python
actually writes — the real Python output carries microseconds, which this test never exercises.
Second, there is no reverse direction: `test_lockfile.py` has no peer at all (`TestReadValidation`
`:140-195` and `TestRoundTrip` `:198-254` are entirely port-local), so nothing in the suite has ever
observed that TypeScript emits `resolved_at` unquoted. Both ports' byte-identity tests
(`test_lockfile.py::TestRoundTrip::test_round_trip_byte_identical` `:240-254`,
`lockfile.test.ts`'s `it("read -> write is byte-identical")` `:139-152`) compare a port against
_itself_, which is exactly the check that cannot see a cross-port divergence.

## Current interface

`read_lockfile` / `readLockfile` and `write_lockfile` / `writeLockfile` are the seam between the
in-memory `Lockfile` and `.ghagen.lock.yml`. Everything a caller must know about that seam is
currently split across four places and agrees in none of them:

| Interface element              | Python                                                                   | TypeScript                                                            | Documented as                                                             |
| ------------------------------ | ------------------------------------------------------------------------ | --------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| `resolved_at` scalar style     | double-quoted (`lockfile.py:156`)                                        | plain (`lockfile.ts:173`, via `stringify`'s default)                  | quoted (`lockfile.py:11`, `lockfile.ts:12`)                               |
| `resolved_at` precision        | microseconds (`isoformat()`, `:157`)                                     | milliseconds truncated to seconds (`.replace(/\.\d{3}Z$/,…)`, `:173`) | seconds (both docstrings)                                                 |
| `sha` scalar style             | whatever ruamel picks (`'…'` when all-digit, bare otherwise)             | whatever `stringify` picks (`"…"` when all-digit, bare otherwise)     | bare (`lockfile.py:10`, `lockfile.ts:11`) — which neither port guarantees |
| `resolved_at` accepted grammar | ISO-8601 via `fromisoformat`, plus ruamel `TimeStamp`; tz-naive accepted | anything `new Date(string)` accepts, incl. non-ISO and host-local     | not stated in either port                                                 |
| top-level not a mapping        | `LockfileError` (`:110-111`)                                             | empty `Lockfile` (`:123-130`)                                         | not stated in TS; "raises on malformed input" in Python (`:13-15`)        |
| YAML syntax error              | `ruamel…ParserError` escapes (`:107`)                                    | `LockfileError` (`:118-122`)                                          | absent from the closed list at `:96-102`                                  |
| round-trip contract            | port-local byte identity (`test_lockfile.py:240-254`)                    | port-local byte identity (`lockfile.test.ts:139-152`)                 | —                                                                         |

A maintainer changing anything here has to know which of two YAML libraries' scalar heuristics will
fire and which of two date parsers will shrug, and there is nothing anywhere that says what the file
is _supposed_ to look like. The "interface" of this module is a docstring that neither implementation
satisfies.

## Proposed interface

**One module per port owns the on-disk encoding _and_ the accepted decoding, states both as a
grammar, and is bound to a single golden file that both ports must reproduce byte-for-byte.**

### (a) The grammar, stated normatively in the module docstring

`.ghagen.lock.yml` is:

1. The header line ``# Auto-generated by `ghagen deps pin`. Do not edit manually.`` followed by a
   blank line. (Today's literal names `ghagen pin`, `lockfile.py:28` / `lockfile.ts:26` — a
   command that does not exist. The Python CLI registers the `deps` sub-app plus `synth`,
   `check-synced` and `init` only (`cli/main.py:18,21,38,61`); the pin command is `deps pin`,
   `cli/deps.py:56` / `cli/deps.ts:349`.)
2. A single top-level `pins:` mapping, block style, two-space indent. Empty is `pins: {}`.
3. Keys are the authored `uses:` strings, ASCII-sorted, emitted plain. (Both ports already agree,
   including on `docker://alpine:3.19` — verified.)
4. **Every value ghagen writes is a double-quoted scalar.** Not "quoted when the library thinks it
   needs to be" — always, so the style is ghagen's decision and not ruamel's or `yaml`'s. This
   covers `sha` as well as `resolved_at`; both docstring examples currently show `sha:` bare and
   must be corrected.
5. `resolved_at` is written as UTC, ISO-8601, **whole seconds**, explicit `+00:00` offset:
   `"2026-04-09T14:30:00+00:00"`.
6. Trailing newline; no other trailing whitespace.
7. **`resolved_at` is _read_ under one grammar in both ports:** an ISO-8601 date-time with an
   explicit UTC designator — `+00:00` or `Z` — quoted or unquoted, with optional fractional seconds
   (accepted and truncated). Everything else is a `LockfileError` in **both** ports: a bare date, a
   quoted date, a naive date-time, a non-ISO string such as `"April 9, 2026"` or `"2026/04/09"`, and
   a non-UTC offset such as `+02:00`. Nothing ghagen has ever written is rejected — both ports'
   existing encoders emit `+00:00` unconditionally — so this narrows only hand-edited input, which
   is the input the "always holds valid entries" invariant is about.

Second precision is the only choice both ports can _represent_: `Date` has millisecond resolution,
so a microsecond format is structurally unwritable in TypeScript. Nothing reads `resolved_at` to
make a decision — `rg` over both `src/` trees outside `pin/lockfile.*` returns exactly two hits,
`engine.py:105` and `engine.ts:95`, and both are _constructions_ (`lockfile.set(ref.uses,
PinEntry(sha=sha, resolved_at=now))` / `lockfile.set(ref.uses, { sha, resolvedAt: now })`) fed by a
single clock read at `engine.py:98` / `engine.ts:83`. It is never compared, sorted on, or
thresholded — so truncating provenance to seconds costs nothing.

### (b) The encoders and decoders, single-homed and explicit

Both ports get a private pair on each side of the seam, and the I/O paths stop relying on library
defaults:

```python
# packages/python/src/ghagen/pin/lockfile.py
def _encode_timestamp(dt: datetime) -> str:
    """The one on-disk timestamp form: UTC, whole seconds, explicit offset."""
    if dt.tzinfo is None:
        raise LockfileError("resolved_at must be timezone-aware")
    return dt.astimezone(UTC).replace(microsecond=0).isoformat()


def _decode_timestamp(raw: object, path: Path, uses: str) -> datetime:
    """The one accepted on-disk timestamp grammar (rule 7)."""
    if isinstance(raw, datetime):  # ruamel TimeStamp, from an unquoted scalar
        dt = raw
    elif isinstance(raw, str):
        try:
            dt = datetime.fromisoformat(raw)
        except ValueError as exc:
            raise LockfileError(
                f"{path}: pin {uses}: invalid 'resolved_at' timestamp: {raw!r}"
            ) from exc
    else:
        raise LockfileError(
            f"{path}: pin {uses}: 'resolved_at' must be a string or datetime"
        )
    if dt.utcoffset() != timedelta(0):  # None (naive) or non-UTC both fail
        raise LockfileError(
            f"{path}: pin {uses}: 'resolved_at' must carry an explicit UTC "
            f"offset (+00:00 or Z)"
        )
    return dt.astimezone(UTC)


# in write_lockfile:
pins_dict[uses] = {
    "sha": DoubleQuotedScalarString(entry.sha),
    "resolved_at": DoubleQuotedScalarString(_encode_timestamp(entry.resolved_at)),
}
```

```ts
// packages/typescript/src/pin/lockfile.ts
import { parse, stringify, Scalar } from "yaml";

const TIMESTAMP_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)$/;

/** The one on-disk timestamp form: UTC, whole seconds, explicit offset. */
function encodeTimestamp(d: Date): string {
  return `${d.toISOString().slice(0, 19)}+00:00`;
}
/** The one accepted on-disk timestamp grammar (rule 7). */
function decodeTimestamp(raw: unknown, path: string, uses: string): Date {
  if (typeof raw !== "string" || !TIMESTAMP_RE.test(raw)) {
    throw new LockfileError(
      `${path}: pin ${uses}: 'resolved_at' must be an ISO-8601 UTC timestamp`,
    );
  }
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) {
    throw new LockfileError(`${path}: pin ${uses}: invalid 'resolved_at' timestamp: ${raw}`);
  }
  return d;
}
function quoted(s: string): Scalar {
  const sc = new Scalar(s);
  sc.type = Scalar.QUOTE_DOUBLE; // ghagen decides the style, not `stringify`
  return sc;
}

// in writeLockfile:
pinsObj[uses] = { sha: quoted(entry.sha), resolved_at: quoted(encodeTimestamp(entry.resolvedAt)) };
```

`_encode_timestamp`'s naive guard has **no TypeScript peer, deliberately**: a `Date` is always an
absolute instant, so the "naive value makes the encoder host-dependent" failure is structurally
impossible in the TypeScript port. That is a language-idiom asymmetry, and belongs in the Python
CONTEXT.md surface notes, not in a mirrored no-op guard.

Both encoders were run against the same three-entry input (including an all-digit SHA and the
`docker://alpine:3.19` key) and produce **byte-identical** output, verified with `cmp`; the empty
form is `cmp`-identical too:

```yaml
# Auto-generated by `ghagen deps pin`. Do not edit manually.

pins:
  actions/checkout@v4:
    sha: "3df4ab11eba7bda6032a0b82a6bb43b11571feac"
    resolved_at: "2026-04-09T14:30:00+00:00"
  docker://alpine:3.19:
    sha: "1234567890123456789012345678901234567890"
    resolved_at: "2026-04-09T14:30:00+00:00"
  pypa/gh-action-pypi-publish@release/v1:
    sha: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    resolved_at: "2026-04-08T00:00:00+00:00"
```

That is `fixtures/expected/lockfile_golden.yml` verbatim — 12 lines, produced by running both
implementations, not written by hand.

### (c) One error mode: `LockfileError` for everything the reader cannot interpret

`read_lockfile` / `readLockfile` return an empty `Lockfile` for exactly two inputs — **the file is
absent**, and **the YAML document is empty (`null`)** — and raise `LockfileError` for everything
else, including:

- a YAML syntax error (Python wraps `ruamel.yaml.error.YAMLError` with `from exc`, matching
  `lockfile.ts:118-122`; the TypeScript side is already correct);
- a top-level document that is not a mapping (TypeScript adds the check Python has at `:110-111`,
  and `!raw` narrows to `raw === null || raw === undefined` so `0` / `""` / `false` reach it);
- a `resolved_at` outside grammar rule 7 — this is the **new** shared behaviour, and it is where the
  two readers currently disagree six ways out of nine;
- what the two readers already agree on: `pins` not a mapping, an entry that is not a mapping, a
  non-string `sha`, and a **missing** `resolved_at`.

The unreachable `resolvedAt instanceof Date` branch (`lockfile.ts:148-149`) is deleted; Python's
`isinstance(resolved_at, datetime)` branch (`:129-130`) **stays**, folded into `_decode_timestamp`,
because ruamel really does hand back a `TimeStamp` for the unquoted timestamps every
TypeScript-written lockfile in the wild currently contains. That is a decoder tolerance for data
that exists on disk — not a compatibility shim for a deprecated API, and so not a pre-1.0
clean-break violation. The encoder stays strict: **write one form, read the forms that exist.**

### (d) The golden is the interface

`fixtures/expected/lockfile_golden.yml` is the executable statement of (a). Each port asserts both
directions against it:

- `write_lockfile(<the fixture's entries>) == <the fixture's bytes>` — the encoder conforms.
- `read_lockfile(<the fixture>)` yields exactly those entries — the decoder conforms.

Two ports asserting against one file is what makes the encoding single-homed _across_ the ports, not
merely inside each. Nothing else in the suite can do that: port-local round-trip tests
(`test_lockfile.py:240-254`, `lockfile.test.ts:139-152`) are satisfied by any self-consistent
encoder, which is precisely how four divergences survived a fully green suite.

## What sits behind the seam

`pin/lockfile.*` already _was_ the module that owns `.ghagen.lock.yml`; what it did not own was the
encoding or the accepted decoding. Four decisions that a reader of the module could not find in it —
scalar style, timestamp precision, the timestamp grammar, and the malformed-input contract — move
from "whatever ruamel/`yaml` does" and "whatever this expression happens to produce" into a stated
grammar plus four named helpers and one shared fixture.

The leverage is unchanged (the callers are still the four read sites per port —
`engine.py:93,150,263` / `engine.ts:78,146,276` plus `app.py:152` / `app.ts:195` — and the single
write site, `engine.py:112` / `engine.ts:104`, all of which keep their signatures). The gain is
**locality**: today, "what does a lockfile look like" is answered by reading two YAML libraries'
scalar-style heuristics, "what is a valid timestamp" by reading two date parsers' documentation, and
"what happens on bad input" differently in each port. After this, all three are answered by one
docstring, one fixture, and one `LockfileError`.

**Deletion test.** Delete `_encode_timestamp`/`encodeTimestamp` and the two call sites re-inline the
format expression — that alone is a thin win. The load-bearing addition is the **golden plus its
four conformance assertions**: delete it and every divergence in _Problem_ becomes invisible again,
which is empirically what happened — the module has shipped with four of them and a full green
suite (pytest 562, vitest 515). Complexity does not vanish on deletion; it reappears as
cross-port drift that no port-local test can see. The fixture earns its keep.

Nothing new is exported. The encoders and decoders are module-private, and the public lockfile
surface is already complete (`pin/__init__.py:22-28,36-41`, `pin/index.ts:3-10`,
`src/index.ts:167-173`), so no barrel is touched.

## Migration plan

Pre-1.0; clean break. No compatibility shim — the decoder already accepts both the old and the new
_encodings_ (Python via its `datetime` branch, TypeScript via its `string` branch), so existing user
lockfiles read fine and are re-encoded to the canonical form on the next write. Rule 7 does newly
reject hand-written naive and non-ISO timestamps; that is the intended break, and nothing either
port has ever written is affected.

1. **Land after 20.** 20 rewrites `lockfile.test.ts`'s `merge` call at `:142-145`, inside the
   byte-identity test this proposal keeps verbatim; taking 20 first means that rewrite is inherited
   rather than hand-applied to a frozen block. No _source_ rebase is needed: 20 explicitly keeps
   `keys` and `get`, and `write_lockfile` / `writeLockfile` use only those two plus the constructor
   (`lockfile.py:151-152`, `lockfile.ts:167,170`) — none of the four members 20 deletes.
2. Add `_encode_timestamp` / `encodeTimestamp` and the double-quoting helper to each port; rewrite
   the two write bodies per (b). Correct the header literal in both (`lockfile.py:28`,
   `lockfile.ts:26`) and rewrite the two module docstring grammar blocks (`lockfile.py:4-11`,
   `lockfile.ts:7-12`) — both the `sha:` line and the `resolved_at:` line — into the normative
   grammar of (a), rules 1-7.
3. Add `_decode_timestamp` / `decodeTimestamp` per (b) and route both read paths through it
   (`lockfile.py:128-142`, `lockfile.ts:147-159`), deleting the unreachable `instanceof Date`
   branch (`lockfile.ts:148-149`).
4. Wrap `yaml.load` at `lockfile.py:107` in `try/except YAMLError` → `LockfileError(…) from exc`,
   and add the YAML-syntax case to the function docstring's enumeration (`lockfile.py:96-102`).
5. Add the top-level-mapping check to `readLockfile` and narrow `!raw` to an explicit null check
   (`lockfile.ts:123-130`).
6. Generate `fixtures/expected/lockfile_golden.yml` by running the Python encoder, then assert the
   TypeScript encoder reproduces it (this ordering makes the fixture a real oracle rather than a
   transcription).
7. Re-encode `.ghagen.lock.yml`: quote the nine `sha` values, truncate the nine `resolved_at` values
   to seconds, fix the header. Mechanical (`sed`), **not** a re-`pin` — the SHAs must not move.
8. Refresh the two stale header literals in test input (`test_cli/test_deps.py:43,140`).
9. Full suite, plus `uv run ghagen check-synced` and `uv run ghagen deps check-synced` (neither
   compares lockfile bytes, but both parse the re-encoded file).

## Test impact

Baseline pytest 562 / vitest 515, all green — and green is exactly the problem: no existing test
observes any of the four divergences.

### The golden, and exactly which bytes it pins

`fixtures/expected/lockfile_golden.yml` is one of the round's two designated byte oracles. It is the
**only** artefact in this proposal that proves the per-port byte divergence (H10) is fixed; every
other change here is a precondition for it. Its 12 lines pin, line by line:

| Golden line       | What it pins                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `:1`              | the header literal, including `ghagen deps pin`                                                                                                                                                                                                                                                                                                                                                                              |
| `:2`              | the blank line after the header                                                                                                                                                                                                                                                                                                                                                                                              |
| `:3`              | `pins:` as the sole top-level key, block style                                                                                                                                                                                                                                                                                                                                                                               |
| `:4`, `:7`, `:10` | keys emitted **plain** and ASCII-sorted, at two-space indent, including `docker://alpine:3.19`                                                                                                                                                                                                                                                                                                                               |
| `:5`, `:8`, `:11` | `sha` **double-quoted** — for an ordinary hex SHA (`:5`, `:11`) _and_ for an all-digit SHA (`:8`), the case where ruamel and `yaml` currently disagree with each other                                                                                                                                                                                                                                                       |
| `:6`, `:9`, `:12` | `resolved_at` **double-quoted** _and_ at **whole-second** precision with an explicit `+00:00` — the two independent halves of divergence #1, pinned separately by construction: `:6` and `:9` carry the same instant so quoting is the only thing distinguishing them from today's TypeScript output, and the microsecond-truncation case is pinned by the dedicated encode test below rather than by the golden's own bytes |
| trailing          | exactly one trailing newline, no other trailing whitespace                                                                                                                                                                                                                                                                                                                                                                   |

**Both suites read the same file**, in the shape the repo already uses for `fixtures/expected/`
goldens that are not pytest-snapshot artefacts:

- TypeScript: `loadFixture("lockfile_golden.yml")` from `src/integration/test-utils.ts:10-12` —
  identical to how `cli/deps.test.ts:11,104` consumes `upgrade_report.json`.
- Python: `(FIXTURES_DIR / "lockfile_golden.yml").read_text()` with the module-level alias
  `FIXTURES_DIR = _FIXTURES_ROOT / "expected"` — identical to `test_cli/test_deps.py:9,23`, which
  consumes `upgrade_report.json` at `:763` and the two body goldens at `:905,:910` the same way.

Using that idiom rather than a hand-rolled read is the point: it puts the golden on the same footing
as the three non-snapshot fixtures already living in that directory
(`upgrade_report.json`, `upgrade_pr_body.md`, `upgrade_issue_body.md`), none of which is a
pytest-snapshot artefact either. (`--snapshot-update` covers only the ten emitter YAML snapshots
managed through `pytest-snapshot` at `test_snapshots.py:5,39,44` — it never touched the other three,
and it will not touch this one.)

**The golden needs no clock seam and no scrubbing.** `write_lockfile` / `writeLockfile` read no
clock: the only `now()` in the pin subsystem is `datetime.now(UTC)` at `engine.py:98` and
`new Date()` at `engine.ts:83`, both **outside** the lockfile module, and both flow into the entry
via the `lockfile.set(...)` calls at `engine.py:105` / `engine.ts:95`. Feed the encoder fixed
`PinEntry`s and it is deterministic by construction.

**Fails on `main` in both ports, measured.** Encoding the golden's three entries through today's
encoders and diffing against the golden:

- **Python: 4 differing lines** — the header, and all three `sha` lines (two bare, one in ruamel's
  single quotes).
- **TypeScript: 6 differing lines** — the header, two bare `sha` lines (the all-digit one already
  matches, since `yaml` picks double quotes), and all three bare `resolved_at` lines.

### New, both ports

- Write conformance: `write_lockfile(<golden entries>)` equals the golden byte-for-byte.
- Read conformance: `read_lockfile(<the golden>)` yields the three expected `(sha, resolved_at)`
  pairs, with `resolved_at` tz-aware UTC.
- A microsecond-bearing input (`…:00.123456Z` in Python, `…:00.123Z` in TypeScript) encodes to the
  same whole-second bytes. Regression guard for the precision half of divergence #1.
- An all-digit SHA encodes to `sha: "1234…"` in both. Fails on `main` in Python (emits `'…'`).
- **Decode grammar, table-driven, one row per shape in _Problem_ §4**: the three explicit-UTC forms
  (bare `+00:00`, quoted `+00:00`, quoted `Z`) are accepted and yield the same instant in both
  ports; the bare date, the quoted date, both naive forms, `"April 9, 2026"`, `"2026/04/09"` and a
  `+02:00` offset all raise `LockfileError` in both. Six of these nine rows fail on `main` — in
  TypeScript because it accepts them, in Python because it accepts two of them tz-naive.
- **Error mode, table-driven**: top-level scalar, top-level sequence, top-level `0`, top-level `""`,
  top-level `false`, YAML syntax error, empty document, missing file — `LockfileError` for the first
  six, an empty `Lockfile` for the last two. Five fail on `main` in TypeScript (silently empty) and
  one fails in Python (leaks `ruamel.yaml.parser.ParserError`).
- **Naive-encoder guard, Python only**: `write_lockfile` of a `PinEntry` built with a naive
  `datetime` raises `LockfileError` rather than silently encoding a host-local instant. No
  TypeScript peer — see (b).

### Rewritten

`lockfile.test.ts`'s `it("reads a Python-written lockfile (string-typed resolved_at)")` loses its
fictional inline literal and reads the golden instead; **its missing peer is added** as a Python test
reading the same golden — the reverse direction that has never existed. The header assertion inside
`it("round-trips entries with sorted keys and snake_case on disk")` follows the corrected literal.

Both are named by `it(...)` title rather than by line, deliberately: they sit at `:154-170` and
`:120` on `main`, but 20 lands first and shifts them (20 rewrites `:19`, `:36`, `:100-115` and
`:142-145`, drops `:43`, and retitles `:16` and `:34`). The same applies on the Python side, where
20 rewrites `test_merge` (`:61-75`) and deletes `test_merge_overwrites` (`:77-86`).

### Kept

Both port-local byte-identity tests — `test_lockfile.py::TestRoundTrip::test_round_trip_byte_identical`
(`:240-254`) and `lockfile.test.ts`'s `it("read -> write is byte-identical")` (`:139-152`). They are
weaker than the golden but not redundant: they cover read→write idempotence over arbitrary entries,
whereas the golden covers one fixed document. **`lockfile.test.ts:139-152` is preserved verbatim by
this proposal**, which is precisely why 20 must land first.

### Unaffected, and one staleness

Every existing assertion survives: `test_lockfile.py:215` asserts the substring `"Auto-generated"`
(not the full header), `:238` uses `.index()` on key names, and `lockfile.test.ts:124` and `:136`
assert `toContain("sha:")` and `toISOString()` — none of which the encoding change moves. Every
in-memory `PinEntry` fixture (`test_engine.py:45`, `test_transform.py:28`, `app.test.ts:125`,
`synth.test.ts:43`, …) is untouched **by this proposal** — `app.test.ts:125` and `synth.test.ts:43`
are `merge` calls that 20 converts to constructor arguments, which 15 simply inherits.

`test_cli/test_deps.py`'s `_LOCKFILE:43` and `_UPGRADE_LOCKFILE:140` embed the old `ghagen pin`
header. They are **input** to `read_lockfile`, which skips comments, so nothing goes red — but they
would leave the repo carrying two spellings of its own header, so they are refreshed (migration step
8). Their `sha` and `resolved_at` literals (`:47-48`, `:102-103`, `:144-145`, `:147-148`) are
already in canonical quoted second-precision form and need no change. Verified: **no test in either
port asserts on written lockfile bytes** beyond the two byte-identity tests above and the header
assertion in `lockfile.test.ts`.

## Risks & alternatives

- **Alternative: keep microseconds and teach TypeScript to emit them.** Rejected — `Date` cannot
  hold them. Reaching microsecond precision in the TypeScript port means changing `PinEntry.resolvedAt`
  away from `Date`, which is a far larger interface change than the value justifies for a field
  nothing reads.
- **Alternative: keep both values unquoted and let each library decide.** Rejected — that is the
  status quo, and it is what makes the parsed _type_ of `resolved_at` depend on which port reads the
  file (`TimeStamp` under ruamel, `string` under `yaml`). Explicit quoting removes a
  library-version-dependent behaviour from a cross-language interop file.
- **Alternative: leave the decoder grammar delegated and fix only the encoder.** Rejected — it fixes
  the bytes ghagen writes while leaving `"April 9, 2026"` resolving to a different instant on two
  developers' machines (_Problem_ §4), and it leaves the encoder's own `.astimezone(UTC)` reachable
  with a naive input. A proposal titled "on-disk encoding **and error mode**" that states the writer's
  grammar and not the reader's has done half the job.
- **Alternative: make TypeScript's silently-empty behaviour the shared contract.** Rejected — it
  turns a corrupt lockfile into a `PinError` that tells the user to re-pin, and re-pinning
  overwrites the corruption (`engine.ts:103-105`). Refusing to guess is the only contract compatible
  with the "always holds valid entries" invariant both class docstrings already assert.
- **Risk: correcting the header literal changes the first line of every user lockfile.** Accepted —
  both readers skip comments entirely, so no lockfile becomes unreadable, and the literal currently
  names a command that does not exist. If a reviewer wants the smallest possible diff, this is the
  one separable sub-item: drop step 2's header edit and the golden simply keeps the old first line.
- **Risk: rule 7 rejects lockfiles that read today.** Accepted and bounded. Neither port has ever
  _written_ a shape rule 7 rejects — both encoders emit an explicit `+00:00` unconditionally — so
  only hand-edited files are affected, and for those the whole point is to stop guessing. Pre-1.0,
  clean break, no shim.
- **Effort: M, raised from S.** The _source_ diff really is S — the reviewer wrote and ran both
  proposed encoders and they reproduce the golden byte-for-byte. What is not S is everything around
  it: nine files, two ports, six function bodies, two docstrings promoted to normative grammar, two
  table-driven suites per port (error mode and decode grammar), two golden-conformance directions,
  the first-ever Python-reads-TypeScript interop test, a mechanical re-encode of the repo's own
  lockfile, an ADR amendment, and three shared-doc edits.

### Scope boundaries vs siblings

- **20 (delete caller-less pin/spec surface)** removes `Lockfile`'s collection facade — no
  production caller in either port. This proposal does **not** re-propose that deletion and does not
  touch the class body. The edge is **ordering only, and it runs 20 → 15 for a test-file reason**:
  20's `merge`→constructor rewrite at `lockfile.test.ts:142-145` falls inside `:139-152`, the
  byte-identity test 15 preserves verbatim, so 15 landing first would freeze a block 20 still needs
  to edit. There is no _source_ dependency in either direction: 20 keeps `keys` and `get`, and 15's
  two I/O functions use only those plus the constructor. 15's other `lockfile.test.ts` regions
  (`:120`, `:154-170`) and its Python regions are disjoint from 20's.
- **13 (unify `format_header`)** — **no edge.** 13's six `header_*.yml` fixtures and this
  proposal's one `lockfile_golden.yml` share the `fixtures/expected/` _directory_ and no filename;
  13 edits the two emitter snapshot suites and this proposal edits the two pin test files; and under
  the round's CONTEXT.md region assignment the two proposals hold disjoint regions. (13's "header"
  is the emitter's workflow-YAML header; this proposal's is the lockfile's first line. Same word,
  different artefacts.)
- **16 (lift transport policy into `HttpClient`)** — **no edge.** This proposal adds no export, and
  every name it touches is already on both barrels (`LockfileError` at `pin/__init__.py:24,:37`,
  `pin/index.ts:6`, `src/index.ts:170`), so there is no barrel edit to collide over; the CONTEXT.md
  regions are disjoint under the round assignment.
- **19 (`main()` owns exit codes)** owns how a `LockfileError` is rendered and what exit code it
  produces. This proposal owns only _which_ exception type crosses the module boundary. The Python
  traceback shown in _Problem_ §3 is cited as evidence that the error mode is unspecified, not as a
  request to fix the CLI.
- **`FIXTURES_DIR` asymmetry** — `packages/typescript/src/paths.ts:41` resolves it to
  `fixtures/expected` while `scripts/ghagen_schema/paths.py:35` resolves it to `fixtures`, so the
  same identifier names two different directories across the ports. This proposal is one of four
  dependents (with 12, 14 and 19) and does **not** own the fix.
  **Open — Phase 3 decision:** whether the asymmetry is corrected as a standalone hotfix on `main`
  after 12/14/15/19 land, or deferred to `docs/issues/08-fixtures-dir-name-collision.md` (raised
  formally by 23; review recommends defer). It also reaches `docs/specs/0005:127`, which documents
  the shared-fixture pattern in terms of the Python spelling.
  Either way this proposal routes **around** it and touches neither paths file: TypeScript uses
  `loadFixture()`, which already resolves `fixtures/expected`; Python aliases and joins, exactly as
  `test_cli/test_deps.py:9,23` already does for the same directory. (19 routes around the same
  asymmetry by keying off `REPO_ROOT`, `paths.ts:35` — a workable second precedent if the alias is
  ever considered too subtle.)

## ADR / CONTEXT.md impact

- **ADR-0006 is extended, not contradicted.** Its _Consequences_ (`:16-20`) fix the lockfile's keys
  and call the on-disk format "cross-language interop surface"; this proposal makes that claim true
  of the values as well. Intended amendment, one sentence: _the on-disk **encoding and accepted
  decoding** are fixed too — double-quoted scalars, UTC whole-second `resolved_at` with an explicit
  offset, and `LockfileError` for anything the reader cannot interpret;
  `fixtures/expected/lockfile_golden.yml` is the oracle._ The ADR's standing prohibition ("do not
  simplify the Lockfile to store structured refs") is untouched: `PinEntry` keeps `sha: str` and a
  `datetime`/`Date`, and the file keeps string keys.
- **`CONTEXT-MAP.md:17-18`** currently reads "both emit the same YAML and read/write the same
  `.ghagen.lock.yml` lockfile (snake_case keys for cross-language interop)". Intended amendment,
  same sentence: the shared thing is the whole **encoding**, not just the key spelling — canonical
  double-quoted scalars and one UTC whole-second timestamp grammar, pinned by
  `fixtures/expected/lockfile_golden.yml`. This is the identical key-only understatement corrected
  in ADR-0006; left uncorrected here, the repo's top-level map would be the last place still
  claiming the narrow version.
- **`packages/python/CONTEXT.md:114` and `packages/typescript/CONTEXT.md:119`** — the final line of
  each file, and this proposal's only CONTEXT.md region under the round's assignment. Intended
  amendment: **append one exchange to _Example dialogue_**, at end-of-file in both ports, mirrored —
  _"Dev: my lockfile diff shows nine changed lines and I only added one action. / Maintainer: both
  ports write one canonical encoding — every value double-quoted, `resolved_at` UTC at whole seconds
  — and a reader raises `LockfileError` rather than degrading to an empty **Lockfile**.
  `fixtures/expected/lockfile_golden.yml` is the byte oracle both suites assert against."_ The
  Python copy adds one clause the TypeScript copy does not need: a naive `datetime` in a **PinEntry**
  is rejected at write time, because `Date` makes the same mistake unrepresentable.
- **No new glossary terms, and no glossary edit.** **Lockfile** (`python:72-73` /
  `typescript:74-75`) and **PinEntry** (`python:75-76` / `typescript:77-78`) already exist and are
  the right words; sharpening them further would claim a region this proposal does not hold, so the
  on-disk contract is stated in the dialogue instead.
- **No ADR-0001 interaction.** The lockfile is not a Document and does not pass through the Emitter;
  `write_lockfile` dumps YAML directly. This proposal does not move it under the Emitter seam, and
  should not — see the deliberate non-goal in _Files involved_.
