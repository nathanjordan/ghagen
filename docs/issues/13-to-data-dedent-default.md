# `to_data` and `to_yaml` disagree about `auto_dedent` by default — in both ports

**Status:** closed — defaults converged

A `to_data` / `to_yaml` pair called with no options disagrees about the content of a Step's `run`:

| Port       | `to_yaml` default                                | `to_data` default                 |
| ---------- | ------------------------------------------------ | --------------------------------- |
| TypeScript | `?? true` (`yaml-writer.ts:425`)                 | `?? false` (`yaml-writer.ts:302`) |
| Python     | `= True` (`models/_base.py`, `Document.to_yaml`) | `= False` (`emitter/data.py:52`)  |

This was originally logged as a TypeScript-only asymmetry. It is not — **the two ports agree with
each other exactly**, so it is not a parity divergence and no byte oracle will ever catch it.

What is left is a genuine interface question: `to_data` is documented as the observation surface for
what `to_yaml` will emit, and by default it observes something `to_yaml` does not emit. Either the
defaults converge, or the docstrings state the asymmetry and say why. No proposal in round 2 owned
it.

## Resolution

Converged: `to_data` / `toData`'s `auto_dedent` / `autoDedent` default is now `true` in both ports,
matching `to_yaml` / `toYaml`. A `to_data` / `to_yaml` pair called with no options can no longer
disagree about a Step's `run`.

- **Python:** `packages/python/src/ghagen/emitter/data.py` — `to_data(..., auto_dedent: bool = True, ...)`.
- **TypeScript:** `packages/typescript/src/emitter/yaml-writer.ts` — `toData(model, options?.autoDedent ?? true)`.

The parameter is kept: a caller that genuinely wants the authored (undedented) string passes
`auto_dedent=False` / `autoDedent: false` explicitly.

Dedent was never a backend pass to begin with, which is why this was safe to converge without
touching the "`to_data` does not run the ruamel/`yaml`-backend passes" carve-out. In Python,
`nodes.py:127` applies the Step `run` dedent inside `collect_fields`, the shared pre-backend
collection stage that both `to_data` and `emit` walk (`nodes.py:108-110` calls that "the sole home
of the dedent-at-emit rule"); in TypeScript it is applied identically in the `modelToData`
recursion, matching `dedentSteps`. Both docstrings now say so explicitly, and the backend-pass
carve-out itself is unchanged — it still applies only to block-scalar promotion, comment-column
alignment, and `post_process`/`postProcess`.

### Fallout

Both ports' emitter and `models/_base.py` call sites were audited (`to_data`/`toData` has ~82 Python
and ~107 TypeScript call sites total, only ~6 of which passed the flag explicitly, and most of the
rest use single-line `run` values where dedent is a no-op). Only two tests asserted the _old_
`to_data` default with an indented multi-line `run` and needed a real change — both were rewritten
to assert the new default, with a sibling test added that passes `auto_dedent=False` /
`autoDedent: false` explicitly to keep the "authored string" behavior covered:

- `packages/python/tests/test_models/test_step.py` — `test_to_data_without_dedent_keeps_raw_run`
  renamed/rewritten to `test_to_data_defaults_dedent_dedents_run` (asserts the new default), plus a
  new `test_to_data_auto_dedent_false_keeps_raw_run` (explicit opt-out).
- `packages/typescript/src/emitter/to-data.test.ts` — the equivalent "dedents a bare Step's run"
  case now asserts the no-options default; the deep-structure cross-check test dropped its
  now-redundant explicit `autoDedent: true`.

A handful of other tests that already passed `auto_dedent=True` / `autoDedent: true` explicitly
(now redundant) were left passing it, or had the now-unneeded flag dropped where it read cleaner
without it (e.g. `test_bare_step_run_dedented_by_default` in both ports).

### The deliverable: the invariant test

Both ports gained a test that binds the fix directly, so a regression here is caught immediately
rather than by accident:

- Python: `test_to_data_and_to_yaml_agree_on_run_with_no_options` in
  `packages/python/tests/test_emitter/test_to_data.py`.
- TypeScript: `"agrees with toYaml on a Step's run with no options"` in
  `packages/typescript/src/emitter/to-data.test.ts`.

Each builds a `Workflow` with one `Step` whose `run` carries leading indentation, calls both
`to_yaml`/`toYaml` and `to_data`/`toData` with no options, and asserts the parsed YAML's `run` and
the observed data's `run` are identical (and dedented).

### Also closes the docs half of issue 26

`docs/src/content/docs/guides/cookbook.mdx:708-710` (pre-edit line numbers) claimed "Auto-dedent is
enabled by default in Python... This option is Python-only; TypeScript does not perform
auto-dedent." Both halves were already false before this change — TypeScript's `toYaml` has
defaulted `autoDedent` to `true` since before this issue, and `packages/typescript/src/config.ts`
already supports the same `.ghagen.yml` `options.auto_dedent` key as
`packages/python/src/ghagen/config.py`. That paragraph, the "no dedent needed" framing at
`cookbook.mdx:568-570`, the `dedent` helper aside at `cookbook.mdx:665-667`, and
`docs/src/content/docs/python/api/step.md:39`'s `run` parameter description were all corrected to
state that auto-dedent is an emit-time default in both ports, not a Python-only construction-time
behavior.
