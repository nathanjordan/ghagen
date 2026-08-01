"""CI fixture: a project whose every ref is already a SHA.

The hermetic half of the ``check-deps`` exercise.  **Zero HTTP requests here is
structural, not observed.**  ``collect_uses_refs`` keeps only pinnable refs
(``pin/collect.py``: ``if site.ref.is_pinnable``), and ``is_pinnable`` is
``not ref_is_sha`` against a 40-character pattern, so an all-SHA config yields
``refs == []`` and ``upgrade()`` returns before either detection stage runs --
before any ``list_tags`` or ``resolve_ref``.  Constructing the ``GitHubClient``
performs no I/O either, so the only observable effect of running tokenless is
the one-line no-token warning on stderr.

That is what lets the exercise live in the existing ``test-action`` job, which
declares no ``permissions:`` and passes no token, instead of becoming this
repository's first networked per-PR job.

``lockfile=None`` so the fixture needs no ``.ghagen.lock.yml`` beside it: with
no pinnable refs there is nothing for a lockfile to hold.

Consumed by ``.github/workflows/ci.yml`` via ``uses: ./check-deps`` with
``dry-run: 'true'``.  Neither ruff nor pyright sees this file -- both are scoped
to ``packages/python/`` -- so a syntax error here surfaces as a red CI job
rather than a red lint.
"""

from ghagen import App, Job, On, PushTrigger, Step, Workflow

app = App(lockfile=None)

ci = Workflow(
    name="All Pinned Fixture",
    on=On(push=PushTrigger(branches=["main"])),
    jobs={
        "build": Job(
            runs_on="ubuntu-latest",
            timeout_minutes=10,
            steps=[
                # actions/checkout v4.2.2 and actions/setup-python v5.3.0.
                # Never resolved at runtime: a 40-character ref is not
                # pinnable, so neither is ever looked up.
                Step(uses="actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683"),
                Step(
                    uses="actions/setup-python@0b93645e9fea7318ecaed2b359559ac225c90a2b"
                ),
            ],
        ),
    },
)

app.add_workflow(ci, "ci.yml")
