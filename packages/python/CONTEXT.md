# ghagen (Python)

The Python implementation of ghagen: Pydantic models describing GitHub Actions, serialized to YAML.
Shares its domain vocabulary with the [TypeScript](../typescript/CONTEXT.md) port — see
[`CONTEXT-MAP.md`](../../CONTEXT-MAP.md).

## Language

### Models

**App**:
The user's whole generation surface — every **Document** to be generated, the output directory, and
the optional lockfile path. Built by the user's config module and returned to the CLI by the config
loader; `synth()` is the one call that turns an App into files on disk. The App, not the Document, is
what the pin subsystem and the `deps` family operate over, and `app.lockfile_path is None` is a
supported configuration that several decisions turn on (see **UpdatePlan**).
_Avoid_: project, workspace, root config.

**Document**:
A Workflow or Action — the unit that maps 1:1 to a generated YAML file, and the only thing that may
be serialized to a file.
_Avoid_: manifest, item, artifact.

**Workflow**:
A GitHub Actions workflow definition, generated to `.github/workflows/*.yml`.

**Action**:
A composite / docker / node action definition, generated to `action.yml`.

**Step**, **Job**:
The nested units inside a Workflow (a Job contains Steps).

**ImageSnapshot**:
A custom runner-image generation request on a Job (`jobs.<id>.snapshot`) — image name plus optional
version.
_Avoid_: snapshot (reserved for the schema **Snapshot**).

**Transform**:
A synthesis-time mutation applied to a deep copy of a Document before emission (e.g. the pin transform).
_Avoid_: plugin, hook, middleware.

**Emitter**:
The module that serializes a model tree to YAML — key ordering, comments, block scalars. Owns all
serialization recursion (see ADR-0001, amended); models never serialize themselves. Also exposes
the plain-data observation surface `to_data()` — the supported way to inspect a model's emitted
structure (see **CommentNode**).
Comment _geometry_ — the end-of-line gutter (`EOL_GUTTER`, 2 columns) and the block-comment
column — is a named module, `emitter/comment_geometry.py`, applied as a node pass before the dump.
No Emitter pass rewrites emitted text. The Emitter also owns the emitted **Header** bytes end to
end — the backend never sees them.

**ModelSpec**:
The per-model serialization spec — YAML key names (field → emitted key), an **OrderMode**, and
per-field emission rules (present-null-when-empty) — declared next to the model, consumed by the
Emitter. The single home for the emitted-key fact: models carry no `serialization_alias`. Its
`yaml_keys` **declaration order is the emission order** — there is no second list beside it. Its
`patterns` map binds a *value grammar* to a field, checked at construction on the unwrapped value so
that `Raw(...)` stays the deliberate escape hatch and `with_comment(...)` is not one.
_Avoid_: field map, key-order table.

**OrderMode**:
A ModelSpec's emission-order rule. Two cases, no third and no placement modifier (ADR-0011):
`explicit` (the default — emit in `yaml_keys` declaration order, then extras) or `alphabetical`
(sort every key, extras interleaved). Carries no payload: `explicit` used to name the key sequence
a second time, restating `tuple(yaml_keys.values())` in every spec.

**CommentNode**:
The Emitter's public, backend-neutral representation of a value plus its attached block/EOL
comment, produced by `to_data(..., comments=True)`.

**Header**:
The auto-generated comment block at the top of every emitted file. `format_header` /
`formatHeader` resolves the four input shapes (default, `None`/`null`, string, closure) to the
exact bytes that precede the YAML body — `#`-prefixed, one trailing newline, blank lines as a
bare `#`, one trailing line break in the input dropped — or to `None`/`null` for "no header".
The writer concatenates; it never re-wraps, pads, or re-indents. Byte parity is asserted by
`fixtures/expected/header_*.yml`.
_Avoid_: banner, preamble, file comment.

### Pinning

**UsesRef**:
A parsed `owner/repo[/path]@ref` action reference; knows whether it is **Pinnable**. Carries its
authored `uses` string (the **Lockfile** key) via the `uses` accessor.

**UsesSite**:
One `uses:` occurrence inside a Document — a parsed **UsesRef** plus the ability to replace the
ref in place. Pin's collect and transform both iterate UsesSites; the "which models carry `uses`"
policy — and parse failure — live only in the UsesSite iterator. Collect returns parsed,
deduplicated UsesRefs, never strings (ADR-0006).

**Pinnable**:
A UsesRef that is remote and not already a commit SHA, so it can be pinned. A ref already written as
a SHA is left untouched (never re-pinned, never an error).

**Pin** (verb):
Replace a `uses:` ref with its locked commit SHA at synthesis time.

**Lockfile**:
Maps `uses:` strings to resolved commit SHAs (`.ghagen.lock.yml`); always holds valid entries.

**PinEntry**:
One resolved pin — a commit SHA plus a resolved-at timestamp.

**Transport**:
The injected HTTP adapter behind `HttpClient`. Returns a response for any status it obtains,
raises `TransportError` for every failure to obtain one, and honours the module deadline —
including reading the body. Every adapter, real or canned, passes the transport conformance table.

**Version tag**:
A `uses:` ref that matches ghagen's declared tag grammar (optional `prefix-`/`prefix/`, optional
`v`, dot-separated integers, each ≤ 10^15 − 1); its **canonical release** is the integer tuple
padded to three and stripped of trailing zeros beyond the third. Refs that are not version tags
(`main`, `release/v1`) are never upgrade candidates. The grammar is declared once, in
`schema/tag-grammar.yml`, and pinned by both suites.

**Bump**:
A version tag strictly newer than the current one, with the same prefix, plus its severity
(major/minor/patch). `pin/versions` is the sole authority on both; the engine consumes Bumps and
never compares versions itself. Equal versions produce no Bump.

**Upgrade report**:
What one `upgrade` run was **asked to check** and what it found — the **Bumps**, the stale lockfile
entries, and a flag per stage recording what the run's mode asked for. The flags are set before the
engine's no-refs early return, so every run carries them, and the rendered output's shape follows
them rather than following what the run happened to find. "Asked for" is not "ran": the lockfile
flag stays true when no lockfile is configured and the stage is skipped.

**UpdatePlan**:
What a caller should **do** about an **Upgrade report** — whether to apply bumps, whether to
refresh the lockfile, what to raise, and under what branch, title, and labels. Every field is a
decision, never data, and a caller never re-derives one from another. Deciding needs the **App**
as well as the report, because one rule turns on `app.lockfile_path`, a fact the serialized report
deliberately does not carry. Its ten-field wire shape (both `--format json` and `--format github`)
is declared once, in `schema/update-plan-fields.yml`, and pinned by both suites.

### Schema

**Snapshot**:
The committed canonical copy of an upstream JSON schema from SchemaStore.

**Drift**:
Divergence between the committed schema Snapshot and the current upstream schema.

**Scope**:
A named node in a Snapshot (`schema/conformance-scopes.yml`) that both ports must bind to a
covering model, and whose declared property set that model must emit in full. A path segment may
be an integer, indexing a `oneOf` alternative. A scope one port cannot bind is a parity failure.

**Gap**:
A limit both ports intentionally do not close, recorded in `schema/conformance-gaps.yml`. Two
kinds, proved differently. A **property gap** is a scope property neither port models,
allow-listed by name; both sweeps hold every such row to three claims, not just "listed": the name
must still exist upstream (else stale), must still be uncovered by the model (else the gap has been
closed and the row must go), and the file's own snapshot/scope keys must equal the sweep's exactly.
A **constraint gap**, under the reserved top-level `constraints` key, records a cross-field rule
neither port enforces — today only `workflowDispatchInput.default`'s dependence on the sibling
`type`. It has no absent property to point at, so its three claims differ: the upstream paths it
names must still hold the values it names, its `counterexample` must still *construct* in both
ports (the day either enforces the rule, the row fails and must go), and the same key-set parity.
Either way a gap row is a live regression guard, not a comment that happens to be YAML.

**Input type**:
The accepted type union of a model field, bound to the Snapshot by `schema/conformance-inputs.yml`
— the third shared table, alongside scopes (property sets) and values (grammars). A row names the
`yaml_key` the field emits, the Snapshot `type_paths` whose union the declared type must equal, and
accept/reject vectors both ports execute. `yaml_key` is what lets one row cover a field the two
ports name differently. The reject direction is asymmetric by construction: Python runs it under
`pytest.raises`, TypeScript compiles it under `@ts-expect-error`.

### CLI

**Exit code**:
One of three numbers `main()` returns — `0` success, `1` expected failure, `2` usage error. The
contract is `fixtures/cli-exit-codes.yml`, which both ports drive through their `main()`; the CLI
framework renders the text, `main()` decides the number.

## Relationships

- A **Document** is a **Workflow** or an **Action**.
- A **Workflow** contains **Jobs**, each containing **Steps**.
- The **Emitter** serializes any model to a node; only a **Document** can be emitted to a file.
- Every model declares a **ModelSpec**; the **Emitter** reads it for key names and ordering.
- **Pin** iterates **UsesSites** over each **Document**; only **Pinnable** refs are pinned.
- `upgrade` compares only **version tags** with the same prefix; the comparison lives in
  `pin/versions`, never in a third-party library.
- An **UpdatePlan** is derived from an **Upgrade report** *and* an **App**; the report alone is not
  enough, and no consumer may reconstruct a plan from `deps upgrade --format json`.

## Surface notes (Python)

- Models are Pydantic classes. **Document** is a base class; **Workflow** and **Action** extend it.
- `GhagenModel.walk()` / `.children()` are the traversal primitive, and both yield **bare models** —
  no key path: `walk()` is every model in this document, root first, depth-first; within a model,
  its schema fields in declaration order, then its `extras`. That is *traversal* order, not emission
  order (emission order is the spec's, via `order_entries`), and it is the same sequence
  TypeScript's `walk()` produces. `extras` is declared on the base class, so `children()` skips it
  in the `model_fields` loop and rescans it last — that is what keeps the two ports agreeing on
  visit order as well as visit set.
- `to_yaml()` / `to_yaml_file()` are **methods** on Document that delegate to the Emitter's
  `emit()` / `emit_file()`. Models do not serialize themselves — the Emitter owns all recursion
  (ADR-0001, amended).
- User input is validated at construction (Pydantic). Schema faithfulness is checked by integration
  tests, not by generated types (see ADR-0003). The TypeScript port enforces the same
  construction-time input contract; declared value grammars live in each port's `ModelSpec` and the
  two are bound to the Snapshot by `schema/conformance-values.yml`; the accepted *type union* of a
  field is bound by its peer `schema/conformance-inputs.yml`, whose reject vectors Python executes
  at runtime and TypeScript executes at compile time. Every field carrying a `patterns`
  entry must admit `Raw[str]` in its annotation, so the grammar-violation message's "wrap the value in
  `Raw(...)`" advice is true wherever it can fire (issue 22) — `conformance-values.yml`'s raw-hatch
  check asserts this in both ports.
- The config module (`config.py`) solely owns `.ghagen.yml` — discovery, single parse, validation,
  App resolution — returning typed results with errors as values (ADR-0007); `cli/_common.py`
  renders a `ConfigError` to `typer.Exit`, which is CLI-local (the TypeScript peer's equivalent is
  `CliError`, in `cli/_errors.ts` — Python has no such class). The CLI entry point is
  `main(argv) -> int`, not the Typer app: click runs in
  `standalone_mode=False`, so the exit code is ghagen's decision rather than the framework's, and
  Typer's error rendering is reproduced explicitly. The synthesis pipeline is `synth.render()`; pin
  runs last (ADR-0005).
- The upgrade path is three layers with one direction of dependency: `pin/engine` produces an
  **Upgrade report** and never formats; `pin/render` turns that report into a string and never
  writes, exits, or touches the network (`render_upgrade_report(report, output_format=...)` — one
  function over all four formats, `text` the default); `cli/deps` owns stream selection and exit
  codes only, and writes the returned string verbatim. The report's `checked_versions` /
  `checked_lockfile` flags exist so the renderer never has to re-derive `--mode`, which is what
  makes the `--format json` key set identical for empty and non-empty runs (ADR-0007;
  `docs/specs/0005-typed-engine-report-seam.md` §2.2). All four formats are byte-compared against
  shared goldens in `fixtures/expected/` by both ports.
- `pin/plan` is the sibling of `pin/render` at the same layer: `render` answers "what bytes do I
  write?", `plan` answers "what do I do next?". Both are pure — no network, no filesystem, no
  console, and no clock either: `plan_update` takes `today` as an argument, the same reasoning
  ADR-0002 applies to construction-time config globals. `plan_update(app, report, ...)` takes the
  **App** for exactly one fact, `app.lockfile_path`, which is why `refresh_lockfile` is not
  `bool(report.lockfile_stale)`. `render_update_plan(plan, changed=..., output_format=...)` is
  `pin/plan`'s renderer for the resulting **UpdatePlan** — the `plan` peer of `pin/render`'s
  `render_upgrade_report`, same two-format (`json`/`github`) shape. `ghagen deps update` is the one
  command that runs a whole automation pass — sweep, `pin/update`'s `apply_updates` writes the
  version bumps back into user source, `plan_update` decides the rest — and prints the rendered
  plan and nothing else on stdout, so `--format github` can be a bare `>> "$GITHUB_OUTPUT"`
  redirect. `check-deps/action.yml` is its only in-repo consumer; the shell there branches on the
  plan and computes nothing.
- `_package_paths.py` is the shared "is this file ghagen-internal / a user file" predicate (peer of
  the TS `_package_paths.ts`). Tests resolve repo paths via `ghagen_schema.paths`, never via
  hand-rolled `parents[N]`.
- The pin transport seam is `HttpClient`, and its contract — the deadline, the totality of
  `TransportError`, and the transport reading the body — lives in its docstring and is executed by
  the conformance table (`tests/test_pin/transport_contract.py`) that every adapter runs. The one
  intentional asymmetry with TypeScript is the response type: `Response` here, `HttpResponse` there
  (the name `Response` is taken by the platform global), carrying `bytes` here and `str` there,
  matching each stdlib. `TransportError` and `ResolveError` are the only two error types crossing
  the pin/network boundary, and the engine's per-ref recovery depends on that totality.
- The model registry is `GhagenModel.__subclasses__()` reflection, which only sees modules that have
  been imported. `tests/test_models/test_spec.py` walks `ghagen.models` with `pkgutil` and imports
  every module before reflecting, so a new model module is covered on creation rather than on the
  day someone remembers to add an import.

## Example dialogue

> **Dev:** "Can I call `to_yaml()` on a **Step**?"
> **Maintainer:** "No — only a **Document** (a **Workflow** or **Action**) serializes to a file. A
> **Step** doesn't serialize itself at all; the **Emitter** recurses into it while emitting the
> Document that contains it."

> **Dev:** "My lockfile diff shows nine changed lines and I only added one action."
> **Maintainer:** "Both ports write one canonical encoding — every value double-quoted,
> `resolved_at` UTC at whole seconds — and a reader raises `LockfileError` rather than degrading to
> an empty **Lockfile**. `fixtures/expected/lockfile_golden.yml` is the byte oracle both suites
> assert against. Python adds one guard the TypeScript port doesn't need: a naive `datetime` in a
> **PinEntry** is rejected at write time, because `Date` makes that mistake unrepresentable."
