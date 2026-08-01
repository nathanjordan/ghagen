"""Per-rule tests for ``collect_fields`` — the single home of emission membership.

``collect_fields`` is the shared collection half of the two Emitter passes (the
ruamel walk in :func:`ghagen.emitter.nodes._model_to_map` and the plain-data walk
in :func:`ghagen.emitter.data._model_to_data`), the peer of ``order_entries``.
These tests pin its rules at rule level; the cross-pass *agreement* invariant is
not re-asserted here — it has a home already, and a better oracle, in
``test_to_data.py::test_deep_structure_matches_emitted_yaml``.

The rules (``docs/specs/0001-python-single-pass-serialization.md`` §4, plus the
later Step-``run`` dedent rule):

1. the field is named in ``spec.yaml_keys``, and is collected in that mapping's
   declaration order;
2. ``exclude_unset``;
3. ``exclude_none``, checked on the *raw* wrapper;
4. the key is ``spec.yaml_keys[field]``;
5. the Step ``run`` dedent, only when *auto_dedent*.

Rule 1 used to read "meta fields are never collected", enforced by a
``_META_FIELDS`` skip over a ``model_fields`` loop, and rule 4 used to carry a
"defaulting to the field name" fallback. Iterating ``spec.yaml_keys`` made both
unreachable — ``test_spec.py::test_spec_covers_exactly_the_content_fields``
asserts ``set(SPEC.yaml_keys) == set(model_fields) - _META_FIELDS`` for every
model — so both were deleted rather than left as guards that cannot fire. The
meta-field test went with the skip: it would have kept passing for a structural
reason, and the structure it depends on is asserted, more strongly, in
``test_spec.py``.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from ghagen import On, PushTrigger, Raw, Step, Workflow
from ghagen.emitter.nodes import collect_fields


def test_unset_field_with_a_non_none_default_is_not_collected() -> None:
    # ``jobs`` defaults to ``{}`` (not None), so only exclude_unset can drop it.
    wf = Workflow(name="CI", on=On(push=PushTrigger(branches=["main"])))
    assert "jobs" not in collect_fields(wf, auto_dedent=False)


def test_set_field_holding_the_same_default_value_is_collected() -> None:
    wf = Workflow(name="CI", jobs={})
    assert collect_fields(wf, auto_dedent=False)["jobs"] == {}


def test_none_valued_field_is_not_collected() -> None:
    step = Step(name="Build", shell=None)
    assert collect_fields(step, auto_dedent=False) == {"name": "Build"}


def test_raw_none_is_collected_because_none_is_checked_on_the_wrapper() -> None:
    # Rule 3's subtlety: exclude_none looks at the raw attribute, before any
    # Raw see-through, so Raw(None) survives to become a present-null key.
    collected = collect_fields(Step(shell=Raw(None)), auto_dedent=False)
    assert list(collected) == ["shell"]
    assert isinstance(collected["shell"], Raw)
    assert collected["shell"].value is None


def test_aliased_field_lands_under_its_yaml_key() -> None:
    collected = collect_fields(Step(if_="success()"), auto_dedent=False)
    assert collected == {"if": "success()"}


def test_field_absent_from_yaml_keys_is_not_collected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The inversion of the pre-proposal-10 rule 4. The loop iterates
    # ``spec.yaml_keys``, so a field the spec does not name is not reachable:
    # it is DROPPED, not emitted under its own name. Unreachable in production —
    # ``test_spec.py::test_spec_covers_exactly_the_content_fields`` makes every
    # content field named — which is why the old ``.get(field, field)`` fallback
    # was deleted rather than kept; this pins what the deletion decided.
    keys = {k: v for k, v in Step.SPEC.yaml_keys.items() if k != "name"}
    monkeypatch.setattr(Step, "SPEC", replace(Step.SPEC, yaml_keys=keys))

    collected = collect_fields(
        Step(name="Build", uses="actions/checkout@v4"), auto_dedent=False
    )
    assert collected == {"uses": "actions/checkout@v4"}


def test_step_run_is_dedented_only_when_auto_dedent() -> None:
    step = Step(run="  echo one\n  echo two")
    assert collect_fields(step, auto_dedent=True)["run"] == "echo one\necho two"
    assert collect_fields(step, auto_dedent=False)["run"] == "  echo one\n  echo two"
