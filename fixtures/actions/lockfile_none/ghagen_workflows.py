"""CI fixture: a supported ``lockfile=None`` project with an outdated ref.

The H7 reproducer.  ``App(lockfile=None)`` is documented configuration
(``App.__init__``: "Set to ``None`` to disable lockfile auto-loading"), and
``actions/checkout@v1`` has had newer tags for as long as the repository has
existed, so a version bump is always found while the report's ``lockfile_stale``
is always empty.  That combination is exactly what made the shipped action's
refresh guard fire ``ghagen deps pin --update`` on a project where that command
exits 1.

Consumed by ``.github/workflows/check-deps-smoke.yml``, which runs it through
``uses: ./check-deps`` with ``dry-run: 'true'``.  Neither ruff nor pyright sees
this file -- both are scoped to ``packages/python/`` -- so a syntax error here
surfaces as a red scheduled job rather than a red lint.
"""

from ghagen import App, Job, On, PushTrigger, Step, Workflow

app = App(lockfile=None)

ci = Workflow(
    name="Lockfile None Fixture",
    on=On(push=PushTrigger(branches=["main"])),
    jobs={
        "build": Job(
            runs_on="ubuntu-latest",
            timeout_minutes=10,
            steps=[Step(uses="actions/checkout@v1")],
        ),
    },
)

app.add_workflow(ci, "ci.yml")
