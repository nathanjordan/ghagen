# 02 — A public Emitter observation surface

**Status:** proposed | **Ports:** both | **Depends on:** none (interacts with [01](./01-modelspec-key-authority.md) and [06](./06-close-modelspec-escape-hatches.md))

## Problem

Model behaviour is tested by reaching **through** the Emitter's public surface into private
internals. The Emitter has exactly one supported entry point per port — `emit`/`emit_file` (Python,
`packages/python/src/ghagen/emitter/__init__.py:22`) and `toYaml`/`toYamlFile` (TS,
`packages/typescript/src/emitter/yaml-writer.ts:229,282`) — but neither exposes a way to observe a
_single model's_ emitted structure. Tests want that, so they grab whatever is closest.

**Python — private `_model_to_map`.** Model tests import the emitter's leading-underscore recursion
core directly:

- `packages/python/tests/test_models/test_step.py:4`
- `packages/python/tests/test_models/test_workflow.py:6`
- `packages/python/tests/test_models/test_action.py:17`
- `packages/python/tests/test_models/test_image_snapshot.py:9`
- `packages/python/tests/test_models/test_serialize.py:10`
- `packages/python/tests/test_helpers/test_expressions.py:7`
- `packages/python/tests/test_emitter/test_yaml_writer.py:19`

Every one imports `from ghagen.emitter.nodes import _model_to_map` and asserts on the returned
`CommentedMap` — a private function returning a **ruamel** type. Renaming `_model_to_map`, changing
its signature, or (per ADR-0001's own goal) reworking the recursion breaks ~40 call sites across 7
files.

**Python — Commented wrapper internals.** Pin tests reach into the ghagen `Commented` wrapper on the
model to check comment attachment: `packages/python/tests/test_pin/test_transform.py:49-50`
(`step.uses.value`, `step.uses.eol_comment`), `:76-78`, `:93-97`, `:201-203`. These assert the
transform's effect by reading wrapper fields rather than by observing what the Emitter produces.

**TypeScript — `model.data["yaml-key"]` layout.** ~10 test files assert on the raw `data` bag:
`step.test.ts:11,20-56`, `permissions.test.ts:33-45`, `action.test.ts:87-109`, `workflow.test.ts:27`,
`job.test.ts`, `pin/transform.test.ts`, `pin/sites.test.ts:149-172` (with `as unknown as` brand
casts). These couple tests to the internal storage shape (`s.data["with"]`, `s.data.snapshot`),
not to emitted output.

**TypeScript — spec identity and inconsistent private export.** Tests assert `model.spec === JOB_SPEC`
(`job.test.ts:141-145`, `action.test.ts`, `image-snapshot.test.ts:12`) — an implementation detail of
how factories tag models. And `modelToYamlMap` is `export`ed from `yaml-writer.ts:66` (unlike
Python's `_model_to_map`) and reached directly by `image-snapshot.test.ts:5,55` and
`yaml-writer.test.ts:6,91,100` — an accidental public surface with no doc contract.

The result: the Emitter's interface is de-facto its entire implementation. ADR-0001 (amended) moved
all recursion into the Emitter precisely so the recursion could be reworked freely — but the tests
pin the private recursion in place, defeating the ADR's payoff.

## Current interface

To observe one model's emitted shape today a test must know:

- **Python:** that `ghagen.emitter.nodes._model_to_map(model, *, auto_dedent=False)` exists, is
  private, returns a `ruamel.yaml.comments.CommentedMap`, and that comment placement lives on that
  ruamel object's `.ca` — or, alternatively, that the ghagen `Commented` wrapper survives on the
  model's field as `field.value` / `field.eol_comment`.
- **TypeScript:** that a model stores mapped fields under `model.data[yamlKey]`, that `model.spec`
  is reference-equal to the module-level spec constant, and that `modelToYamlMap(model)` returns a
  `yaml` `YAMLMap` whose `.items` are `Pair`s with `.key.value`.

None of this is documented as supported. All of it is internal.

## Proposed interface

Add **one** supported public function per port: _emit any model to plain data_. It becomes THE test
surface for model behaviour — key names, values, ordering, aliasing, extras merge, dynamic keys, and
(optionally) comment placement — without exposing ruamel/`yaml` nodes, the `data` bag, or spec
identity.

### Python

```python
# ghagen.emitter (public; re-exported from ghagen.emitter.__init__)

@dataclass(frozen=True)
class CommentNode:
    """A value plus the comments the Emitter would attach to it.

    The public, backend-independent representation of a commented node — the
    observation-surface peer of the internal Commented wrapper and ruamel's
    CommentToken. Only produced when to_data(..., comments=True).
    """
    value: Any
    comment: str | None = None
    eol_comment: str | None = None


def to_data(
    model: GhagenModel,
    *,
    auto_dedent: bool = False,
    comments: bool = False,
) -> Any:
    """Emit any model to plain Python data — the supported observation surface.

    Returns a nested structure of plain ``dict`` / ``list`` / scalars in
    canonical emission order, with field names mapped to their YAML keys
    (from the model's ModelSpec), extras merged after ordered keys, and Raw
    escape-hatch values unwrapped to their inner value.

    - ``comments=False`` (default): Commented wrappers are unwrapped to their
      values. Use this for key/value/order/aliasing assertions.
    - ``comments=True``: a commented node is returned as a :class:`CommentNode`
      so comment placement is observable as data (no ruamel ``.ca`` reads).

    Unlike ``emit``, this does not run the ruamel-backend passes (block-scalar
    promotion, comment-column alignment) or the ``post_process`` hook, which
    operate on the backend node. Assert those via the emitted YAML string.
    """
```

Any model may be passed (Step, Job, On, …) — this is the Emitter observing a node, not file
serialization, so it is deliberately **not** gated on Document (that gate stays on
`emit`/`to_yaml`, per ADR-0001).

Assertions become:

```python
assert to_data(Step(name="Run tests", run="pytest")) == {"name": "Run tests", "run": "pytest"}
assert to_data(Step(if_="success()"))["if"] == "success()"        # aliasing, via the spec
assert list(to_data(step)) == ["id", "name", "if", "uses", ...]   # ordering
node = to_data(pinned_step, comments=True)["uses"]
assert node == CommentNode("actions/checkout@<sha>", eol_comment="v4")
```

### TypeScript

```ts
// packages/typescript/src/emitter/yaml-writer.ts (public; re-exported from index.ts)

export interface CommentNode {
  readonly value: unknown;
  readonly comment?: string;
  readonly eolComment?: string;
}

export interface ToDataOptions {
  autoDedent?: boolean; // default false
  comments?: boolean; // default false
}

/**
 * Emit any model to a plain POJO / array / scalar tree — the supported
 * observation surface. Keys are YAML keys in canonical order (from the spec),
 * extras merged after ordered keys, Raw unwrapped. With `comments: true`, a
 * commented node is returned as a {@link CommentNode}. Does not run the
 * `yaml`-backend passes or `postProcess`; assert those via the YAML string.
 */
export function toData(model: Model, options?: ToDataOptions): unknown;
```

```ts
expect(toData(step({ name: "Test", run: "pytest" }))).toEqual({ name: "Test", run: "pytest" });
expect((toData(step({ if_: "x" })) as Record<string, unknown>)["if"]).toBe("x");
const uses = (toData(pinnedStep, { comments: true }) as Record<string, unknown>)["uses"];
expect(uses).toEqual({ value: "actions/checkout@<sha>", eolComment: "v4" });
```

**Invariants / ordering / error modes (both ports):**

- Key order is exactly what `emit`/`toYaml` produce for that node — same `ModelSpec.order`
  consultation, same extras-after-ordered-keys rule. `to_data` and `emit` are two renderings of one
  walk (see _What sits behind the seam_), so they cannot disagree on structure.
- `comments=False` yields a value tree containing no framework wrapper types (`Commented`, `Raw`,
  `CommentNode`, `Model`, ruamel/`yaml` nodes) — pure data, safe for `==`/`toEqual`.
- Passing a non-model raises `TypeError` (Python) / is a compile error (`model: Model`, TS).

## What sits behind the seam

Recommended: introduce a **plain emission tree** as the Emitter's single internal representation and
make the ruamel/`yaml` backend a thin consumer of it.

- One recursion (Python `nodes.py`, TS `yaml-writer.ts`) walks a model → plain tree of
  `dict`/`list`/scalar, with commented nodes carried as `CommentNode`. This _is_ the "single internal
  node dispatcher" ADR-0001 called for; it just now produces a backend-neutral value instead of a
  ruamel node.
- `to_data` returns that tree (stripping `CommentNode`s to their `.value` when `comments=False`).
- `emit` converts the tree to ruamel/`yaml` nodes, attaches comments, runs the whole-tree passes
  (block-scalar promotion, comment-column alignment) and `post_process`, then dumps.

This deepens the Emitter: three small public functions (`emit`, `emit_file`, `to_data`) over one
shared walk and a swappable backend. It also removes the current mild duplication where
`_model_to_map` builds ruamel directly — the ruamel specifics (`CommentedMap`, `.ca`,
`LiteralScalarString`) collapse into the backend step.

A lighter alternative (a second dedicated model→dict walk beside the existing model→ruamel walk) is
possible but re-introduces exactly the kind of parallel recursion ADR-0001 fought to remove; prefer
the shared tree.

## Migration plan

Pre-1.0; replace, don't layer.

1. Implement the plain emission tree + `to_data` / `toData` + `CommentNode` in the Emitter; wire
   `emit`/`toYaml` onto the shared walk. Re-export `to_data`/`CommentNode` (Python
   `emitter/__init__.py`) and `toData`/`CommentNode`/`ToDataOptions` (TS `index.ts`).
2. Migrate model tests to the new surface (below). Delete the private imports.
3. **Un-export `modelToYamlMap`** (TS): make it module-private, matching Python's `_model_to_map`.
   Its two external readers (`image-snapshot.test.ts`, `yaml-writer.test.ts`) move to `toData`.
4. Delete tests that only exist to probe internals (below).
5. Full suite green; integration YAML snapshots byte-identical (untouched — they already assert on
   `emit`/`toYaml` output).

## Test impact

**Python — rewritten (private `_model_to_map` → public `to_data`):**

```python
# before — test_step.py:15-20
from ghagen.emitter.nodes import _model_to_map
def test_basic_uses_step():
    cm = _model_to_map(Step(uses="actions/checkout@v4"))
    assert cm["uses"] == "actions/checkout@v4"
    assert "name" not in cm

# after
from ghagen.emitter import to_data
def test_basic_uses_step():
    data = to_data(Step(uses="actions/checkout@v4"))
    assert data == {"uses": "actions/checkout@v4"}   # exhaustive: absence is asserted by ==
```

```python
# before — test_pin/test_transform.py:47-51 (reads the Commented wrapper on the model)
step = result.jobs["build"].steps[0]
assert is_commented(step.uses)
assert step.uses.value == f"actions/checkout@{SHA_CHECKOUT}"
assert step.uses.eol_comment == "v4"

# after (observe what the Emitter produces, not the wrapper internals)
step = result.jobs["build"].steps[0]
assert to_data(step, comments=True)["uses"] == CommentNode(
    f"actions/checkout@{SHA_CHECKOUT}", eol_comment="v4"
)
```

**Python — deleted:**

- `test_emitter/test_yaml_writer.py:201-206` `test_to_node_ghagen_model_matches_model_to_map` — a
  probe comparing two private functions; both disappear behind the seam.
- The `_model_to_map` import in `test_yaml_writer.py:19` (and the `_yaml_key` import at :26, already
  removed by [01](./01-modelspec-key-authority.md)).

**TypeScript — rewritten (`model.data` layout / spec identity → `toData`):**

```ts
// before — step.test.ts:19-23 (couples to the internal data bag)
const s = step({ uses: "actions/setup-node@v4", with_: { "node-version": "20" } });
expect(s.data["with"]).toEqual({ "node-version": "20" });
expect(s.data).not.toHaveProperty("with_");

// after (couples to emitted structure)
const data = toData(step({ uses: "actions/setup-node@v4", with_: { "node-version": "20" } }));
expect(data).toEqual({ uses: "actions/setup-node@v4", with: { "node-version": "20" } });
```

```ts
// before — image-snapshot.test.ts:49-56 (reaches the now-private modelToYamlMap)
const keys = modelToYamlMap(j).items.map((p) => (p.key as { value: string }).value);
expect(keys.indexOf("snapshot")).toBe(keys.indexOf("container") + 1);

// after
const keys = Object.keys(toData(j) as Record<string, unknown>);
expect(keys.indexOf("snapshot")).toBe(keys.indexOf("container") + 1);
```

**TypeScript — deleted / demoted:**

- `job.test.ts:141-145`, `action.test.ts`, `image-snapshot.test.ts:12` spec-identity assertions
  (`expect(j.spec).toBe(JOB_SPEC)`) — an internal-tagging detail. The behaviour that matters (kind,
  ordering) is covered by `toData` + `kind`. Delete the `=== SPEC` assertions; keep `expect(j.kind)
.toBe("job")`.
- `pin/sites.test.ts:149-172` brand-cast `data` reads — replaced by `toData` assertions or kept as
  UsesSite iterator tests where they belong (not emitter-shape tests).

**Is asserting on the YAML string sufficient instead?** For **structure** (key names, values,
ordering, presence/absence, aliasing, extras, dynamic keys) a structured surface is strictly better:
`==`/`toEqual` on a dict gives exhaustive, whitespace-insensitive, single-assertion coverage, where
string matching is brittle (indentation, quoting, flow vs block) and can't easily assert _absence_.
For **comment placement and block-scalar/column formatting**, the YAML string is the real contract
and `toData` deliberately does not model it — those tests stay on the string (Python
`test_emitter/test_comments.py`, TS `emitter/comments.test.ts`, and the integration snapshots).
`comments=True` exists only so tests that today read wrapper internals (pin) can assert _that a
comment is attached to a value_, as data, without a full-string match.

## Risks & alternatives

- **Does this contradict ADR-0001?** No. ADR-0001 (amended) puts all _recursion_ inside the Emitter
  behind a small public surface; it does not say the Emitter may expose only file serialization.
  `to_data` is the Emitter's **own** public surface — the recursion still lives entirely in the
  Emitter, models still carry only data + spec, and models still never call back into the Emitter.
  This _strengthens_ the ADR: with a supported observation surface, tests stop pinning the private
  recursion, so the recursion is finally free to change (the ADR's stated goal). File serialization
  stays gated on Document; `to_data` is node observation, not file emission.
- **Alternative: keep `_model_to_map` but make it public.** Rejected — it returns a ruamel
  `CommentedMap`, leaking the backend and forcing tests to read `.ca` for comments. `to_data`
  returns plain data with a backend-neutral `CommentNode`, so the ruamel→`yaml` port difference
  stops leaking into tests.
- **Risk: `to_data` and `emit` drift.** Mitigated by the shared-walk design (one recursion). If the
  cheaper two-walk alternative is taken instead, add a cross-check test that `to_data`'s key order
  equals the emitted YAML's key order for a representative Document.
- **Interaction with [01](./01-modelspec-key-authority.md):** both edit `test_yaml_writer.py`. Land
  01 first (removes `_yaml_key` + its tests), then 02 (removes `_model_to_map` + its probe test), so
  each deletion set is clean. `to_data`'s YAML keys come from `ModelSpec.yaml_keys`, which 01 makes
  the sole authority — so after both land, the observation surface and the key authority tell one
  story.
- **Interaction with [06](./06-close-modelspec-escape-hatches.md):** 06's declarative order/extras
  changes are observable through `toData` (e.g. asserting alphabetical `on:` order, or extras
  routed through the spec), giving 06 a clean test surface instead of `data`-bag probing.

## ADR / CONTEXT.md impact

- **Amend ADR-0001** with a short note: the Emitter's public surface is `emit` / `emit_file` /
  `to_data` (Python) and `toYaml` / `toYamlFile` / `toData` (TS). `to_data`/`toData` emit _any_
  model to plain data for observation and are not gated on Document; only file emission is.
- **CONTEXT.md (both), "Emitter" entry:** add that the Emitter exposes a plain-data observation
  surface (`to_data`/`toData`) as the supported way to inspect a model's emitted structure.
- **New glossary term (both CONTEXT.md):** **CommentNode** — the Emitter's public, backend-neutral
  representation of a value plus its attached block/EOL comment, produced by `to_data(...,
comments=True)`.
