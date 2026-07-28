# 03 — One synthesis pipeline behind App

**Status:** proposed | **Ports:** both | **Depends on:** —

## Problem

`App.synth` and `App.check` are two spellings of the same pipeline — clone each
registered Document, fold the transforms over the clone, emit YAML — that
diverge only in the last step (write to disk vs. diff against disk). Today that
shared prefix is copy-pasted, and the shared behaviour it encodes has no seam of
its own to test.

Python (`packages/python/src/ghagen/app.py`):

- `synth` (156-171) and `check` (173-204) both open with the identical three
  lines: `transforms = self._build_transforms()`, loop `self._items`, `working =
self._apply_transforms(item, transforms)`. From there `synth` calls
  `working.to_yaml_file(...)` (167-169) and `check` calls `working.to_yaml(...)`
  then compares (186-202).
- `_apply_transforms` (146-154) is the clone-then-fold core: `working =
item.model_copy(deep=True)` then `for transform in transforms: working =
transform(working)`.
- `_build_transforms` (130-144) hardcodes the transform order: it `append`s the
  `PinTransform` first (141), then `extend`s the user transforms (143). That
  ordering is load-bearing — a user Transform running after Pin sees `uses:`
  values that are already 40-char SHAs, not the authored refs — but it is
  implicit in the append/extend sequence and has no test.

TypeScript (`packages/typescript/src/app.ts`):

- `synth` (122-133) and `check` (141-171) duplicate the same prefix
  (`_buildTransforms`, loop `_items`, `_applyTransforms`).
- The emit-option object `{ header: this.headerTxt, autoDedent: this.autoDedent }`
  is written twice, verbatim (129 and 148-151).
- `synth` is `async` and `await`s `mkdir(...)` (128) but then writes with the
  **sync** `writeFileSync` (129). The asyncness is aspirational: the doc comment
  (119-121) says "Asynchronous so we have room to add async transforms in the
  future," but the `Transform` type is synchronous (`transforms.ts:22`:
  `(item: Document) => Document`) and `toYaml` is synchronous. The only genuinely
  async calls are `mkdir` (which has a sync twin already used in
  `yaml-writer.ts:283`) and the lazy `import()` in `_buildTransforms` (181-182).
- `_buildTransforms` (173-190) and `_applyTransforms` (192-203) are marked
  `@internal` and have **no direct test** — `app.test.ts` exercises them only
  end-to-end through `synth()`-to-disk. The pin-transform-under-App path
  (`_buildTransforms` 177-185, reading a lockfile via dynamic import and pushing
  `pinTransform`) is not covered at all in `app.test.ts`.

The net friction: every fact about the pipeline — transform ordering, clone
isolation, header threading, `auto_dedent` threading, what the emitted text
looks like — is only observable by writing files to a temp directory and reading
them back. There is no place to hand a Document plus transforms and get the YAML
string.

## Current interface

Python — the pipeline is inlined into two `App` methods and three private
helpers; nothing exposes "Document + transforms → text":

```python
class App:
    def _build_transforms(self) -> list[Transform]: ...      # pin first, then user
    def _apply_transforms(self, item, transforms) -> _Item:  # clone + fold
    def synth(self) -> list[Path]: ...                        # loop → to_yaml_file
    def check(self) -> list[tuple[Path, str]]: ...            # loop → to_yaml + diff
```

TypeScript — same shape, plus the aspirational `async`:

```ts
class App {
  private async _buildTransforms(): Promise<Transform[]>; // pin first, then user
  private _applyTransforms(item, transforms): Document; // clone + fold
  async synth(): Promise<string[]>; // loop → writeFileSync
  async check(): Promise<Array<[string, string]>>; // loop → toYaml + diff
}
```

## Proposed interface

Introduce one **synthesis pipeline** module per port whose whole job is
`Document in → transformed clone → emitted YAML text out`. It is filesystem-free
and root-free: it carries each Document's registered path through untouched so
the caller knows where the text goes, but it never joins a root, creates a
directory, or reads/writes a file. `synth` and `check` become thin consumers
that differ only in what they do with each `(path, text)` pair.

### Result shape

One value per Document: the path it was registered at, plus the rendered text.

```python
# packages/python/src/ghagen/synth.py
@dataclass(frozen=True)
class Rendered:
    """One Document rendered to YAML, tagged with its registered path."""
    path: Path   # the rel path as registered on App; opaque to the pipeline
    text: str    # the complete emitted YAML
```

```ts
// packages/typescript/src/synth.ts
export interface Rendered {
  /** The registered path, relative to App.root; opaque to the pipeline. */
  readonly path: string;
  /** The complete emitted YAML. */
  readonly text: string;
}
```

Return a **list** (not a lazy generator): the element count is the number of
registered files (small), both consumers iterate the whole thing once, and a
materialized list is indexable and `len`-able in tests.

### The pipeline

```python
# packages/python/src/ghagen/synth.py
def apply_transforms(document: Document, transforms: Sequence[Transform]) -> Document:
    """Deep-copy *document* and fold *transforms* over the copy, in order.

    The input is never mutated. With no transforms the copy is skipped and the
    original is returned (callers must treat the result as read-only).
    """
    if not transforms:
        return document
    working = document.model_copy(deep=True)
    for transform in transforms:
        working = transform(working)
    return working


def render(
    items: Sequence[tuple[Document, Path]],
    transforms: Sequence[Transform],
    *,
    header: HeaderInput,
    auto_dedent: bool,
) -> list[Rendered]:
    """Render every (document, path) pair to YAML.

    Invariants:
      * Transforms apply in list order: index 0 first, last index last. This is
        the whole ordering contract — the pipeline does not sort or reorder.
      * Each document is rendered from an independent deep copy; the caller's
        models are never mutated.
      * `header` and `auto_dedent` are threaded straight into `emit` on every
        document (ADR-0002: no global carries them).
    """
    return [
        Rendered(
            path=path,
            text=emit(
                apply_transforms(document, transforms),
                header=header,
                auto_dedent=auto_dedent,
            ),
        )
        for document, path in items
    ]
```

```ts
// packages/typescript/src/synth.ts
export function applyTransforms(document: Document, transforms: readonly Transform[]): Document {
  if (transforms.length === 0) return document;
  let working = cloneModel(document);
  for (const transform of transforms) working = transform(working);
  return working;
}

export function render(
  items: ReadonlyArray<readonly [Document, string]>,
  transforms: readonly Transform[],
  opts: { header: HeaderInput; autoDedent: boolean },
): Rendered[] {
  return items.map(([document, path]) => ({
    path,
    text: toYaml(applyTransforms(document, transforms), {
      header: opts.header,
      autoDedent: opts.autoDedent,
    }),
  }));
}
```

### Transform ordering: explicit, and pin runs last

The ordering contract is now a stated invariant of `render` (list order) plus a
single composition site in `App`. **Recommendation: user transforms first, pin
transform last** — the reverse of today's pin-first order (Python `app.py:141`
vs `143`; TS `app.ts:184` vs `188`). Rationale:

- User transforms should operate on the authored, human-readable `uses:` refs,
  not on 40-char SHAs. Under pin-first they see SHAs.
- Pin should lock _whatever refs survive to the end of the pipeline_, including
  refs a user transform injected. Under pin-first, a `uses:` added by a later
  user transform is emitted unpinned, because Pin already ran.

This is a behaviour change and is called out under _Risks_ and _ADR / CONTEXT
impact_. `App` composes the order in one place:

```python
# App._build_transforms(): user first, pin last
transforms: list[Transform] = list(self._transforms)
if pin_transform is not None:
    transforms.append(pin_transform)
return transforms
```

### Sync vs. async for TypeScript: sync

Make the whole path synchronous — drop `async`/`Promise` from `synth`, `check`,
and `_buildTransforms`. Honest reasons:

- `Transform` is synchronous (`transforms.ts:22`) and no async transform exists
  or is concretely planned; the "room for async transforms" comment is
  speculative.
- `toYaml` is synchronous; `render` is synchronous.
- The two async touch-points both have sync answers: `mkdir(...)` → `mkdirSync`
  (already used in `yaml-writer.ts:283`), and the lazy `import()` for the pin
  module becomes a static `import`. The pin module pulls in `lockfile`/`sites`;
  it does not form an import cycle back into `app.ts` (`pin/collect.ts`'s only
  `App` reference is type-only), so a static import is safe.

`App.synth` returns `string[]`, `App.check` returns `Array<[string, string]>`,
both without `Promise`. Callers drop `await` (see _Test impact_).

### App after the extraction

```python
def synth(self) -> list[Path]:
    written: list[Path] = []
    for r in render(self._items, self._build_transforms(),
                    header=self.header, auto_dedent=self._auto_dedent):
        full = self.root / r.path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(r.text)
        written.append(full)
    return written

def check(self) -> list[tuple[Path, str]]:
    stale: list[tuple[Path, str]] = []
    for r in render(self._items, self._build_transforms(),
                    header=self.header, auto_dedent=self._auto_dedent):
        full = self.root / r.path
        if not full.exists():
            stale.append((full, f"File does not exist: {full}"))
            continue
        actual = full.read_text()
        if actual != r.text:
            stale.append((full, _unified_diff(full, actual, r.text)))
    return stale
```

`synth` and `check` now share the render call verbatim and diverge only on the
write-vs-compare tail — the divergence is real (deletion test passes: the shared
render logic reappears in both), the duplication is gone.

## What sits behind the seam

The `render` interface is small — `(items, transforms, header, auto_dedent) →
list[Rendered]` — but the depth behind it is everything that today only shows up
after a round-trip through the filesystem:

- **Clone isolation** — the caller's Documents are deep-copied before any
  transform touches them.
- **Transform ordering and folding** — left-to-right application, the pin-last
  contract, and the fold that threads each transform's output into the next.
- **Header and `auto_dedent` threading** — one call site each, ADR-0002 clean
  (no global), instead of the two duplicated emit-option objects today.
- **Emission** — delegating to `emit` / `toYaml` per document.

`App` keeps only what genuinely needs the filesystem and the root: resolving
`root / rel_path`, `mkdir`, `write`, `read`, and diffing. Building the pin
transform from the lockfile stays in `App` (it owns `lockfile_path` and `root`);
composing it into the ordered transform list is its one ordering responsibility.

## Migration plan

Pre-1.0, clean breaks are fine; no compat shims.

1. **Python — add `ghagen/synth.py`** with `Rendered`, `apply_transforms`,
   `render`. Move the clone-and-fold body out of `App._apply_transforms` into
   `apply_transforms`; delete `App._apply_transforms`.
2. **Python — rewrite `App.synth` / `App.check`** to call `render` and keep only
   the write / compare tail. Flip `_build_transforms` to append user transforms
   first and the pin transform last.
3. **TypeScript — add `src/synth.ts`** with `Rendered`, `applyTransforms`,
   `render`. Move the clone-and-fold body out of `App._applyTransforms`.
4. **TypeScript — de-async.** Replace the dynamic `import()` in
   `_buildTransforms` with static imports, make `_buildTransforms` sync, rewrite
   `synth` / `check` to sync using `render` + `mkdirSync`/`writeFileSync`. Flip
   the composition to user-first, pin-last. Return non-`Promise` types.
5. **Update callers** — CLI `synth`/`check` handlers and any docs API drop
   `await` on the TS side. (Python already sync.)
6. **Export** `render` / `applyTransforms` / `Rendered` from each port's barrel
   if the pin/CLI layers or docs want them; otherwise keep module-local.

Lockstep: each numbered pair (1-2 Python, 3-4 TS) lands together to keep the
parity mandate — the invariants (clone isolation, pin-last ordering, header /
auto_dedent threading) must move in step even though the surface differs
(Python free functions + methods vs. TS free functions, sync both).

## Test impact

**New tests at the render seam** (pure strings, no temp dir, no disk):

```python
def test_pin_runs_after_user_transforms():
    # user transform renames a job; pin then locks the surviving uses ref
    items = [(wf_with_checkout_v4, Path("ci.yml"))]
    text = render(items, [rename_transform, pin_transform],
                  header=None, auto_dedent=True)[0].text
    assert "actions/checkout@" + "a" * 40 in text   # pinned
    assert "RENAMED" in text                         # user edit survived

def test_render_does_not_mutate_input():
    original = wf_with_checkout_v4
    render([(original, Path("ci.yml"))], [rename_transform],
           header=None, auto_dedent=True)
    assert original.jobs["build"].name != "RENAMED"  # clone was edited

def test_header_none_emits_no_header():
    text = render([(wf, Path("ci.yml"))], [], header=None, auto_dedent=True)[0].text
    assert not text.startswith("#")

def test_auto_dedent_false_passes_run_through():
    text = render([(wf_with_indented_run, Path("ci.yml"))], [],
                  header=DEFAULT, auto_dedent=False)[0].text
    assert "        echo hi" in text
```

TS mirrors these against `render(...)` with `toYaml`-level string assertions.

**Rewritten:**

- `app.test.ts` (`packages/typescript/src/app.test.ts`) — the ordering /
  clone-isolation / dedent / header cases (currently 90-144, all going through
  `mkdtemp` + `synth()` + `readFileSync`) move to `synth.test.ts` as string
  assertions. `app.test.ts` keeps only the genuinely filesystem cases: `synth`
  writes to the right resolved path, `check` flags missing files, `check`
  produces a diff for tampered files. All `await`s on `synth()` / `check()` are
  removed (now sync). Example: `expect(await app.check()).toEqual([])` becomes
  `expect(app.check()).toEqual([])`.
- Python has no dedicated `app` unit test today; the pipeline behaviours it
  lacked coverage for (ordering, clone isolation, header/dedent threading) are
  _added_ at the `synth.py` seam rather than through the CLI/integration suite.

**Deleted:** the untested-and-now-impossible-to-reach `@internal`
`_applyTransforms` on both ports (folded into `apply_transforms`). The pin path
that `app.test.ts` never covered (`app.ts:177-185`) is now covered by a render
test that passes a real `pinTransform` last.

## Risks & alternatives

- **Pin-last is a behaviour change.** A user transform that rewrites a `uses:`
  ref to a value absent from the lockfile now raises `PinError` at synth (Pin
  runs after and cannot find the new ref), where pin-first would have silently
  emitted the transform's output against an already-pinned SHA. This is the
  correct failure — "you introduced a ref, run `ghagen pin`" — and matches how
  refs added in source already behave. _Alternative:_ keep pin-first and only
  make the existing order explicit/tested. Rejected: it bakes in the surprising
  "user transforms see SHAs" semantics.
- **De-asyncing TS is a public API break** (`synth`/`check` no longer return
  Promises). Pre-1.0 this is acceptable and removes a false affordance.
  _Alternative:_ keep `async` for future-proofing. Rejected as speculative
  generality — there is no async transform, and `render` can be re-introduced as
  async in a single place if one ever arrives.
- **`Rendered` carries the registered rel path, not an absolute path.** Keeping
  the pipeline root-agnostic is deliberate (it stays testable without a root); if
  a future consumer wants absolute paths it resolves `root / path` itself, as
  `App` does. _Alternative:_ have the pipeline resolve against root. Rejected:
  drags filesystem/root knowledge into the pure seam.

## ADR / CONTEXT.md impact

- **ADR-0002 (no construction-time config globals):** strengthened, not
  amended. `header` and `auto_dedent` are still threaded at serialization time,
  now through a single `render(..., header=, auto_dedent=)` call site per port
  instead of two duplicated emit-option objects. Worth a one-line note that the
  threading site is now `synth.render`.
- **ADR-0001 (Emitter owns serialization; Document gates file serialization):**
  unaffected. `render` calls `emit` / `toYaml`; it does not serialize anything
  itself, and file writing stays in `App`. The Document-gated `to_yaml` /
  `to_yaml_file` methods remain the standalone entry point.
- **New ADR (recommended): "Synthesis pipeline and transform ordering."**
  Records that `render` is the single Document→text pipeline, that transforms
  apply in list order, that the pin transform runs **last**, and that the TS
  path is synchronous. This is where the pin-last decision and its `PinError`
  consequence are documented.
- **CONTEXT.md (both ports):** add a **Pipeline** / **render** term under a
  Synthesis heading — "the single Document → transformed clone → YAML-text
  pipeline; `synth` writes each result, `check` diffs it" — and note under
  **Transform** that transforms apply in registration order with the pin
  transform appended last.
