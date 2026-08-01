"""Per-rule tests for ``collect_fields`` — the single home of emission membership.

``collect_fields`` is the shared collection half of the two Emitter passes (the
ruamel walk in :func:`ghagen.emitter.nodes._model_to_map` and the plain-data walk
in :func:`ghagen.emitter.data._model_to_data`), the peer of ``order_entries``.
These tests pin its five rules at rule level; the cross-pass *agreement*
invariant is not re-asserted here — it has a home already, and a better oracle,
in ``test_to_data.py::test_deep_structure_matches_emitted_yaml``.

The rules (``docs/specs/0001-python-single-pass-serialization.md`` §4, plus the
later Step-``run`` dedent rule):

1. meta fields are never collected;
2. ``exclude_unset``;
3. ``exclude_none``, checked on the *raw* wrapper;
4. the key is ``spec.yaml_keys[field]``, defaulting to the field name;
5. the Step ``run`` dedent, only when *auto_dedent*.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from ghagen import On, PushTrigger, Raw, Step, Workflow
from ghagen.emitter.nodes import collect_fields


def test_meta_fields_are_never_collected() -> None:
    # SCHEDULED CHANGE — proposal 10 (delete ModelSpec.order), migration step
    # 3(d): once collect_fields iterates ``spec.yaml_keys`` instead of
    # ``model_fields``, a meta field can no longer reach the loop at all and the
    # ``_META_FIELDS`` guard is deleted. This test then passes for a structural
    # reason rather than exercising the guard — i.e. it becomes unfalsifiable
    # and must be deleted or re-sited as an assertion about ``yaml_keys``.
    # A pass here after 10 lands is NOT evidence the guard still works.
    step = Step(
        name="Build",
        extras={"custom": "x"},
        comment="block",
        eol_comment="eol",
        post_process=lambda cm: None,
    )
    assert collect_fields(step, auto_dedent=False) == {"name": "Build"}


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


def test_field_absent_from_yaml_keys_lands_under_its_own_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # SCHEDULED CHANGE — proposal 10, migration step 3(d): this assertion
    # INVERTS. Once collect_fields iterates ``spec.yaml_keys``, a field absent
    # from that mapping is not reachable, so ``name`` is DROPPED rather than
    # emitted under its own name, and the ``.get(field_name, field_name)``
    # fallback this test exercises is deleted as unreachable. The post-10 form
    # of this test asserts ``"name" not in collected``. That inversion is the
    # intended semantic change 10 owns — not a regression.
    keys = {k: v for k, v in Step.SPEC.yaml_keys.items() if k != "name"}
    monkeypatch.setattr(Step, "SPEC", replace(Step.SPEC, yaml_keys=keys))

    collected = collect_fields(
        Step(name="Build", uses="actions/checkout@v4"), auto_dedent=False
    )
    assert collected == {"name": "Build", "uses": "actions/checkout@v4"}


def test_step_run_is_dedented_only_when_auto_dedent() -> None:
    step = Step(run="  echo one\n  echo two")
    assert collect_fields(step, auto_dedent=True)["run"] == "echo one\necho two"
    assert collect_fields(step, auto_dedent=False)["run"] == "  echo one\n  echo two"
