# Comment attachment module

**Status:** implemented

## Implementation notes / deviations from the as-written spec

Reconciled against the actually-landed 0001, which differs from what this spec's
"after" code assumed:

1. **0001 landed as three helpers, not one `serialize.py`.** The single-pass
   serializer is `to_yaml_node` (recursive value serializer) + `_to_yaml_seq`
   (list branch), both in `emitter/yaml_writer.py`, plus `to_commented_map` (a
   model's own field walk) still in `models/_base.py`. The call sites landed
   accordingly: field comment inline in `to_commented_map`; list item in
   `_to_yaml_seq`; nested map-value model in `to_yaml_node`'s `GhagenModel`
   branch; root in `emit.py`.
2. **Python `attach_field_comments` was deleted, not "moved to comments.py".**
   The collect-then-reattach two-pass is eliminated in favor of inline `attach`
   at the point of emission (§2 call-site-1 intent: "no collect-then-reattach
   two-pass"). TS likewise inlines `attachFieldComment` per pair in `toYamlMap`.
3. **Seq-item models bypass the map-value branch (both ports).** To avoid a
   list-entry model being attached twice (once as a map value on its first key,
   once on the seq index), `_to_yaml_seq` / the array branch build the item map
   directly (`to_commented_map()` / `item.toYamlMap()`) and attach once as a seq
   item. This is §2's binding "call site 2 is not reached for seq items"; the
   §3 illustrative `node = toYamlValue(item)` snippet would double-attach, so
   §2's intent was followed.
4. **EOL placement is container-dependent** (a detail the unified
   `attachModelComment` in §2 glossed): a seq-item model's EOL renders on the
   **first** value (the dash/entry-point line — the TS peer of ruamel's
   seq-index EOL redirect to the item's first key), while a map-value / root
   model's EOL renders on the **last** value. This also fixed a latent TS
   inconsistency where the old nested-Model branch put a map-value model's EOL
   on the first value; it is now the last value, matching the root path and the
   Python side.
5. **`attachModelComment` block (atSeqItem:false) merges** ahead of any existing
   first-key comment (adopting the root path's `${comment}\n${existing}` merge),
   rather than overwriting as the old nested-Model branch did.

The one intended output change (§4) landed: `fixtures/expected/comments.yml` now
shows the `lint` job's `# Run linters before tests`, and the TS snapshot input
gained the matching `comment`. Both ports produce byte-identical output.


One deep module per port, living inside the Emitter, that owns every path by which a
YAML comment lands on a node. Today that logic is smeared across three files per port and
runs down three near-duplicate code paths; this spec collapses it behind one small
interface.

## Dependency (read first)

This spec **applies on top of spec 0001** (Emitter seam / single-pass Python serializer),
which is being written concurrently and **lands first**. 0001 rewrites Python's
`GhagenModel.to_commented_map` god-method into a single recursive Emitter free helper that
mirrors TypeScript's `toYamlValue` (`_serialize_value`, `_restore_nested_models`,
`_collect_commented_fields`, the dual alias resolution, the ×3 Raw-unwrap and ×5 Commented
handling all consolidate into emitter free helpers). Throughout this document:

- **"before"** = the real current code (pre-0001), quoted verbatim for context.
- **"after"** = the comment module as it fits the **post-0001** world: a single recursive
  Python serializer, and TypeScript's current `toYamlValue`.

The Python "after" call sites named below are points **inside 0001's single-pass helper**,
not inside today's `to_commented_map`. Implementing 0003 before 0001 lands would mean
hooking into code that is about to be deleted — do not.

---

## 1. Problem

### The smear

"Attach a comment to a YAML node" is one idea. It is currently implemented three times, in
three files, per port.

**Python** (3 files):

| Path | Site | What it does |
|------|------|--------------|
| field comment | `models/_base.py::_collect_commented_fields` → `emitter/yaml_writer.py::attach_field_comments` → `attach_comment` | walks `model_fields`, pulls `comment`/`eol_comment` off `Commented` wrappers into two dicts, re-walks the map to attach them by key |
| list-item comment | `models/_base.py::_serialize_list` (lines 253–259) → `attach_comment` | second loop over the same items; for each `GhagenModel` item attaches its own `.comment`/`.eol_comment` on the seq index |
| Document-root comment | `emitter/emit.py::to_yaml` (lines 57–58) → `attach_comment` | attaches the root model's `.comment` before the first key |

**TypeScript** (2 files):

| Path | Site | What it does |
|------|------|--------------|
| field comment | `models/_base.ts::toYamlMap` collects into `fieldComments`/`fieldEolComments` → `attachFieldComments` (same file) | mirror of the Python field path |
| nested-model comment | `models/_base.ts::toYamlValue` nested-Model branch (lines 716–730) | sets `commentBefore` on the child map's first key + `comment` on the first value |
| list-item comment | `models/_base.ts::toYamlValue` array branch (lines 742–752) | **re-does** the nested-model attach at a different target, then **undoes** the first one |
| Document-root comment | `emitter/yaml-writer.ts::toYaml` → `attachBlockComment` / `attachEolComment` (same file) | attaches the root model's `comment`/`eolComment` |

Three conceptual operations, six-plus implementations, four files touched to trace one
behavior. `attach_comment` (Python) and the placement logic (TS) each encode a pile of
node-shape-specific ruamel/`yaml`-lib quirks (seq-index vs map-key dispatch, the map-item
EOL redirect, block-comment column rewriting) with no single owner.

### The TypeScript duplicate-comment workaround (symptom)

`toYamlValue` has two branches that both attach a nested model's block comment, at
**different targets**, because a model renders differently depending on its container:

- **map value** — `key:` then the child map indented under it. The comment belongs on the
  child's **first key** (`key.commentBefore`). This is what the nested-Model branch
  (lines 716–722) does.
- **seq item** — `- ` then the child map inline after the dash. The comment belongs on the
  **map node itself** (`node.commentBefore`) so it renders above the dash.

The array branch calls `toYamlValue(item)`, which runs the nested-Model branch and wrongly
stamps the comment on the first key; the array branch then has to overwrite it in the right
place *and* null out the wrong one:

```ts
// _base.ts, toYamlValue array branch — lines 742–752 (verbatim)
// If the item is a Model with a comment, attach it to the seq entry
if (item instanceof Model && item.meta.comment && node instanceof YAMLMap) {
  // Comment is already attached to the first key inside toYamlMap's caller above.
  // For sequence items, we need to set commentBefore on the map node itself.
  (node as YAMLMap).commentBefore = item.meta.comment;
  // Remove the duplicate from the first key if it was set
  const firstPair = (node as YAMLMap).items[0] as Pair | undefined;
  if (firstPair && firstPair.key instanceof Scalar) {
    firstPair.key.commentBefore = null;
  }
}
```

**Root cause:** the nested-Model branch attaches the model's own comment *before knowing
what container the model sits in*. Placement depends on container, so a second call site
must reverse the first. Two paths compute one attachment with opposite placement
conventions; one clobbers the other. The workaround is the smear made visible.

### The parity gap (symptom)

The two ports disagree on **nested map-value models**. In TypeScript, `toYamlValue`'s
nested-Model branch attaches a nested model's own comment regardless of container, so a
`job` inside the `jobs` object renders its comment. In Python, a model's own comment is
attached **only** for the Document root (`emit.py`) and for **list** items
(`_serialize_list`) — a map-value model (a `Job` under the `jobs` dict) is silently
dropped, because `to_commented_map` never attaches `self.comment`.

This is observable in the shared snapshot `fixtures/expected/comments.yml`: the Python test
`test_comments` constructs the `lint` job with `comment="Run linters before tests"`
(`tests/test_integration/test_snapshots.py:129`), yet the comment is **absent from the
fixture** — Python drops it. The TypeScript snapshot test omits that comment from its input
entirely, because including it would render in TS and break the shared fixture. The fixture
is pinned to the two ports' intersection precisely because the behavior diverges. One
comment owner per port erases the divergence.

### Cost

Any change to comment behavior means reading `_commented.py`, `_base.py`,
`yaml_writer.py`, and `emit.py` (Python) or `_base.ts` and `yaml-writer.ts` (TS), holding
three interacting code paths in your head, and reasoning about a self-cancelling
double-attach. There is no single place to add a test, fix a quirk, or answer "how does a
comment get onto a node".

---

## 2. Design

One new file per port, inside the Emitter, that owns **all** comment placement and **all**
node-shape/quirk knowledge. The serializer decides *what* comment goes *where* (which node,
which key/index); the module decides *how* to make the underlying library render it.

### Python — `emitter/comments.py`

```python
"""Comment attachment: the single owner of how a comment lands on a ruamel node."""

from __future__ import annotations
from ruamel.yaml.comments import CommentedMap, CommentedSeq


def attach(
    parent: CommentedMap | CommentedSeq,
    key: str | int,
    *,
    comment: str | None = None,
    eol_comment: str | None = None,
) -> None:
    """Low-level primitive. Attach a block and/or EOL comment to a map key or a
    seq index. Owns the map-vs-seq dispatch, the seq-item map EOL-redirect quirk,
    and the block-comment placeholder column (rewritten later by dump_yaml)."""


def attach_model_comment(
    node: CommentedMap,
    *,
    comment: str | None = None,
    eol_comment: str | None = None,
) -> None:
    """A model's OWN comment, rendered on the map as a whole: block before the
    first key, EOL after the last value. Used for the Document root AND every
    nested map-value model (closing the parity gap)."""
```

- `attach` is today's `attach_comment` (yaml_writer.py:65–110) **relocated verbatim** — it
  already owns the map/seq dispatch and the map-item EOL redirect.
- `attach_model_comment` generalizes emit.py's root-comment logic to any map node and adds
  EOL support (parity with TS's `attachEolComment`).

**Call sites** (inside 0001's single-pass serializer helper, `emitter/serialize.py` or
wherever 0001 lands the recursive `to_commented_map(value)`):

1. **Field comment** — when a mapping value is a `Commented` wrapper, after writing
   `cm[key] = serialize(wrapper.value)`:
   `attach(cm, key, comment=wrapper.comment, eol_comment=wrapper.eol_comment)`.
   Subsumes `_collect_commented_fields` + `attach_field_comments` (no collect-then-reattach
   two-pass; attach at the point of emission).
2. **List item** — in the list branch, for each `GhagenModel` item:
   `attach(seq, idx, comment=item.comment, eol_comment=item.eol_comment)`.
   Replaces `_serialize_list`'s second loop.
3. **Nested / root model** — when the recursive helper produces the `CommentedMap` for a
   `GhagenModel` (root or nested map value):
   `attach_model_comment(child, comment=model.comment, eol_comment=model.eol_comment)`.
   Replaces emit.py:57–58 **and** closes the map-value gap.

**What dies:**

- `models/_base.py`: `_collect_commented_fields` (whole method, 192–224); the comment loop
  in `_serialize_list` (253–259); the extras comment-collection branch (313–319 → routes
  through call site 1); the `attach_field_comments` call (324–328). (Most of the surrounding
  `to_commented_map` body is already being deleted by 0001; 0003 owns the comment slice.)
- `emitter/yaml_writer.py`: `attach_comment` and `attach_field_comments` **move out** to
  `comments.py`. yaml_writer keeps `dump_yaml`, `unwrap_raw`, `to_ordered_commented_map`,
  `_apply_block_scalar_style`, `_apply_pre_comment_columns` (emission/formatting, not
  attachment).
- `emitter/emit.py`: the inline root-comment attach (57–58) becomes a call to
  `attach_model_comment` (or, better, 0001's single pass already invokes call site 3 for the
  root, and emit.py stops touching comments entirely).
- `_commented.py`: **unchanged** — it is the public `Commented` wrapper data type
  (`with_comment` / `with_eol_comment` / `is_commented` / `unwrap_commented`), not
  attachment logic. It stays as the input to the module.

### TypeScript — `emitter/comments.ts`

```ts
import { YAMLMap, YAMLSeq, Scalar, Pair } from "yaml";

/** Path 1: block/EOL comment from a Commented wrapper on one mapping field. */
export function attachFieldComment(pair: Pair, comment?: string, eolComment?: string): void;

/**
 * Paths 2+3: a model's OWN block/EOL comment. `atSeqItem` is the ONE decision
 * the old duplicate workaround hacked around:
 *   - false → map is a field value or the document root: comment on the first
 *     key (block) / last value (EOL).
 *   - true  → map is a `- ` list entry: block comment on the map node itself
 *     (`commentBefore`), so it renders above the dash.
 */
export function attachModelComment(
  map: YAMLMap,
  comment: string | undefined,
  eolComment: string | undefined,
  opts: { atSeqItem: boolean },
): void;
```

- `attachFieldComment` is the per-pair core extracted from `attachFieldComments`
  (`_base.ts:812–849`); the collect loop in `toYamlMap` calls it per field (or a thin
  `attachFieldComments(map, ...)` wrapper stays in the module).
- `attachModelComment` unifies `attachBlockComment` + `attachEolComment`
  (`yaml-writer.ts:55–83`) **and** the nested-Model branch's placement
  (`_base.ts:716–730`), with the container decision made **once** by the caller via
  `atSeqItem`.

**Call sites** (in `toYamlValue`, `_base.ts`):

1. **Field comment** — the `toYamlMap` collect loop calls `attachFieldComment` per pair
   (or one `attachFieldComments`).
2. **Nested model as map value** — nested-Model branch:
   `attachModelComment(childMap, model.meta.comment, model.meta.eolComment, { atSeqItem: false })`.
   The branch **no longer** hand-sets `commentBefore`/`comment` inline.
3. **Nested model as seq item** — array branch:
   `attachModelComment(node, item.meta.comment, item.meta.eolComment, { atSeqItem: true })`.
   The self-cancelling "remove the duplicate" block is **deleted** — the wrong attach never
   happens, because call site 2 is not reached for seq items (the array branch owns its
   items' model comments).
4. **Document root** — `toYaml` (`yaml-writer.ts`):
   `attachModelComment(doc.contents, meta.comment, meta.eolComment, { atSeqItem: false })`.

**What dies:**

- `models/_base.ts`: `attachFieldComments` **moves** to `comments.ts`; the nested-Model
  branch's inline `commentBefore`/`comment` writes (716–730) and the entire array-branch
  duplicate workaround (742–752) are **replaced** by two `attachModelComment` calls.
- `emitter/yaml-writer.ts`: `attachBlockComment` and `attachEolComment` **move** to
  `comments.ts` (fold into `attachModelComment`). `fixInlineCommentSpacing` **stays** — it
  is string-level output normalization on the final dump, not node attachment.

### One note on the ports not being byte-identical

ruamel stores a seq item's pre-comment on the **parent seq**'s `.ca`, so Python's seq path
is `attach(seq, idx, ...)`; the `yaml` library stores it on the **child node**'s
`commentBefore`, so TS's seq path is `attachModelComment(node, …, {atSeqItem:true})`. That
library difference is exactly the node-shape knowledge each module is meant to encapsulate;
the two modules play the identical role while differing in internals. Parity is at the
interface's *responsibility*, not its literal signature.

---

## 3. Before / After

### Path 1 — field comment

**Python before** (`_base.py:192–224`, `310–328` + `yaml_writer.py:113–133`) — collect into
two dicts, then re-walk the map:

```python
def _collect_commented_fields(self) -> tuple[dict[str, str], dict[str, str]]:
    field_comments: dict[str, str] = {}
    field_eol_comments: dict[str, str] = {}
    for field_name, field_info in type(self).model_fields.items():
        value = getattr(self, field_name, None)
        if not is_commented(value):
            continue
        alias = field_info.alias or field_name
        ...  # dual alias resolution
        if value.comment:
            field_comments[ser_alias] = value.comment
        if value.eol_comment:
            field_eol_comments[ser_alias] = value.eol_comment
    return field_comments, field_eol_comments
# ... later, a second pass:
attach_field_comments(cm, field_comments=field_comments or None,
                      field_eol_comments=field_eol_comments or None)
```

**Python after** — inline at emission, in 0001's single pass (no collect, no re-walk, no
`_collect_commented_fields`, no `attach_field_comments`):

```python
# where the single-pass helper writes a mapping entry:
raw = self.data_for(key)                 # 0001's field iteration
if is_commented(raw):
    cm[key] = serialize(raw.value)
    attach(cm, key, comment=raw.comment, eol_comment=raw.eol_comment)
else:
    cm[key] = serialize(raw)
```

**TS before** (`_base.ts:812–849`, `attachFieldComments`, module-private). **TS after** —
same body, now `attachFieldComment(pair, comment?, eolComment?)` exported from
`comments.ts`, called per pair from `toYamlMap`'s collect loop.

### Path 2 — list-item comment

**Python before** (`_base.py:247–261`):

```python
def _serialize_list(self, items: list[Any]) -> CommentedSeq:
    seq = CommentedSeq()
    for item in items:
        seq.append(self._serialize_value(item))
    for idx, item in enumerate(items):
        if isinstance(item, GhagenModel):
            if item.comment:
                attach_comment(seq, idx, comment=item.comment)
            if item.eol_comment:
                attach_comment(seq, idx, eol_comment=item.eol_comment)
    return seq
```

**Python after** — single loop in 0001's list branch, one call:

```python
for idx, item in enumerate(items):
    seq.append(serialize(item))
    if isinstance(item, GhagenModel):
        attach(seq, idx, comment=item.comment, eol_comment=item.eol_comment)
```

**TS before** (`_base.ts:742–752`, the duplicate workaround quoted in §1). **TS after** —
the workaround is gone; the array branch attaches once:

```ts
for (let i = 0; i < value.length; i++) {
  const item = value[i];
  const node = toYamlValue(item);
  if (item instanceof Model && node instanceof YAMLMap) {
    attachModelComment(node, item.meta.comment, item.meta.eolComment, { atSeqItem: true });
  }
  seq.add(node);
}
```

### Path 3 — Document-root (and nested map-value) comment

**Python before** (`emit.py:57–58`) — root only; nested map-value models drop their comment:

```python
if model.comment and cm:
    attach_comment(cm, next(iter(cm.keys())), comment=model.comment)
```

**Python after** — one helper covers root *and* nested map value; EOL now supported; gap
closed. Called by 0001's single pass wherever a `GhagenModel` yields a map:

```python
child = serialize_model(model)   # produces the CommentedMap
attach_model_comment(child, comment=model.comment, eol_comment=model.eol_comment)
```

**TS before** (`_base.ts:716–730` inline + `yaml-writer.ts:55–83` + `toYaml` 123–130). **TS
after** — nested-model branch delegates:

```ts
// toYamlValue nested-Model branch:
const childMap = value.toYamlMap();
attachModelComment(childMap, value.meta.comment, value.meta.eolComment, { atSeqItem: false });
return childMap;
```
```ts
// toYaml (yaml-writer.ts), root:
if (doc.contents instanceof YAMLMap) {
  attachModelComment(doc.contents, target.meta.comment, target.meta.eolComment, { atSeqItem: false });
}
```

---

## 4. Test plan

The whole point is that comments become **directly unit-testable** on a plain node, without
constructing a Document or round-tripping to YAML.

**New: `test_emitter/test_comments.py` (Python) / `emitter/comments.test.ts` (TS)** — drive
the module on hand-built nodes:

- `attach` / `attachFieldComment`: block-only, EOL-only, both, on a `CommentedMap` /
  `Pair`; assert the comment token is present on the target key.
- `attach` on a `CommentedSeq` index whose item is a non-empty map → EOL redirects to the
  item's first key (the ruamel quirk); on a scalar item → EOL on the index; on an empty map
  item → falls back to the index. (These assertions exist today as behavioral tests in
  `test_yaml_writer.py:87–147`; **move** them onto the module's own primitive.)
- `attach_model_comment` / `attachModelComment`:
  - `atSeqItem:false` → block on first key, EOL on last value.
  - `atSeqItem:true` (TS) → block on the map node (`commentBefore`), **not** on the first
    key (regression guard for the deleted duplicate — assert the first key has no
    `commentBefore`).
  - Both take **plain node + wrapper inputs** only; no `Model`/`Document` construction.
- Idempotence / merge: attaching a block comment when one already exists (mirrors
  `attachBlockComment`'s existing `${comment}\n${existing}` merge, `yaml-writer.ts:62`).

**Existing tests stay green:**

- `test_yaml_writer.py` unit tests: those asserting `attach_comment` behavior follow the
  function into `comments.py` (update import); `dump_yaml` / block-scalar / ordering tests
  unchanged.
- Snapshot suites (`fixtures/expected/*.yml`, both ports) unchanged **except** the parity
  fix: closing the Python map-value gap makes the `lint` job's
  `comment="Run linters before tests"` render. Update `fixtures/expected/comments.yml` to
  include it **and** add the same `comment` to the TS `snapshots.test.ts` input so both
  ports match. This is the one intended output change; all other snapshots are byte-stable.
- TS `_base.test.ts` / `yaml-writer.test.ts` comment cases (block-before-field,
  EOL-on-value, model-level comment on first key, model-level EOL on last value) stay green
  through the module.

---

## 5. Acceptance criteria

1. A new `emitter/comments.py` and `emitter/comments.ts` are the **only** files that call
   ruamel comment APIs / set `commentBefore`/`comment` on `yaml` nodes. Grep confirms no
   comment-attachment remains in `_base`, `emit`/`yaml-writer` beyond call sites that
   *delegate* to the module.
2. All three paths (field, list-item, root/nested-model) route through the module; the
   TypeScript array-branch "remove the duplicate" workaround is deleted.
3. The Python parity gap is closed: a nested map-value model's own comment renders,
   matching TS; `fixtures/expected/comments.yml` shows the `lint` job comment and both port
   snapshot suites agree.
4. The module is unit-tested on plain nodes + wrappers with no Document round-trip; the
   seq-item quirk tests live on the module.
5. Full suites green in both ports (one intended fixture update, per §4).
6. No public API change: `Commented`, `with_comment`/`withComment`, `with_eol_comment`/
   `withEolComment` are untouched; the moved functions were all internal
   (`emitter/__init__.py` is empty; TS helpers were module-private).

---

## 6. Conflicts

- **Depends on spec 0001 (hard, same Python files).** 0001 rewrites
  `models/_base.py::to_commented_map` and `_serialize_value`/`_serialize_list`/
  `_restore_nested_models`/`_collect_commented_fields` into a single-pass Emitter helper.
  0003's Python call sites are points *inside that new helper*. **Implement 0003 after 0001
  merges, not in parallel** — the two would edit the same methods and 0003's "after" targets
  code 0001 has not yet produced.
- **TypeScript side is technically independent** of 0001 (no 0001 TS churn beyond narrowing
  `toYaml`), but it ships in this spec to keep the two ports in lockstep (per the deepening
  plan's "lockstep both languages" rule). Land Python and TS together.
- No conflict with the pin track (specs on `UsesRef`/transport/lockfile) or config/schema
  work; `pin/transform` uses `with_eol_comment` at construction time, upstream of and
  unaffected by attachment.
