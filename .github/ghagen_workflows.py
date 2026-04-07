"""ghagen's own CI/CD workflows, defined with ghagen (dogfooding)."""

from __future__ import annotations

from ghagen import (
    App,
    Job,
    Matrix,
    On,
    Permissions,
    PRTrigger,
    PushTrigger,
    Raw,
    ScheduleTrigger,
    Step,
    Strategy,
    Workflow,
    WorkflowDispatchTrigger,
    checkout,
    expr,
    setup_python,
    setup_uv,
)
from ghagen.models.common import PermissionLevel
from ghagen.models.job import Environment


def _ci_workflow() -> Workflow:
    """CI: lint, type-check, test across Python versions, verify sync."""
    return Workflow(
        name="CI",
        on=On(
            push=PushTrigger(branches=["main"]),
            pull_request=PRTrigger(branches=["main"]),
        ),
        jobs={
            "lint": Job(
                name="Lint",
                runs_on="ubuntu-latest",
                steps=[
                    checkout(),
                    setup_uv(),
                    Step(name="Sync", run="uv sync"),
                    Step(name="Ruff check", run="uv run ruff check src/ tests/"),
                    Step(
                        name="actionlint",
                        uses="rhysd/actionlint@v1.7.11",
                    ),
                ],
            ),
            "typecheck": Job(
                name="Type check",
                runs_on="ubuntu-latest",
                steps=[
                    checkout(),
                    setup_uv(),
                    Step(name="Sync", run="uv sync"),
                    Step(name="Pyright", run="uv run pyright src/"),
                ],
            ),
            "test": Job(
                name="Test (Python ${{ matrix.python-version }})",
                runs_on="ubuntu-latest",
                strategy=Strategy(
                    matrix=Matrix(
                        extras={
                            "python-version": ["3.11", "3.12", "3.13"],
                        },
                    ),
                ),
                steps=[
                    checkout(),
                    setup_uv(),
                    setup_python(version="${{ matrix.python-version }}"),
                    Step(name="Sync", run="uv sync"),
                    Step(name="Test", run="uv run pytest"),
                ],
            ),
            "check-sync": Job(
                name="Check workflow sync",
                runs_on="ubuntu-latest",
                steps=[
                    checkout(),
                    setup_uv(),
                    Step(name="Sync", run="uv sync"),
                    Step(name="Verify workflows", run="uv run ghagen check"),
                ],
            ),
        },
    )


def _schema_drift_workflow() -> Workflow:
    """Weekly schema drift detection."""
    return Workflow(
        name="Schema Drift Check",
        on=On(
            schedule=[ScheduleTrigger(cron="0 9 * * 1")],
            workflow_dispatch=WorkflowDispatchTrigger(),
        ),
        permissions=Permissions(
            contents=PermissionLevel.READ,
            issues=PermissionLevel.WRITE,
        ),
        jobs={
            "check-drift": Job(
                runs_on="ubuntu-latest",
                steps=[
                    checkout(),
                    setup_uv(),
                    Step(name="Sync", run="uv sync"),
                    Step(
                        name="Fetch schema and regenerate",
                        run=(
                            "uv run python -m ghagen.schema.fetch\n"
                            "uv run python -m ghagen.schema.codegen"
                        ),
                    ),
                    Step(
                        name="Check for drift",
                        run=(
                            'if ! git diff --exit-code src/ghagen/schema/snapshot/; then\n'
                            '  echo "::warning::Schema drift detected"\n'
                            '  gh issue create \\\n'
                            '    --title "GitHub Actions schema drift detected" \\\n'
                            '    --body "$(git diff src/ghagen/schema/snapshot/)" \\\n'
                            '    --label schema-drift\n'
                            'fi'
                        ),
                        env={"GH_TOKEN": str(expr.secrets["GITHUB_TOKEN"])},
                    ),
                ],
            ),
        },
    )


def _release_workflow() -> Workflow:
    """Release Please + PyPI publish on push to main."""
    release_please_job = Job(
        name="Release Please",
        runs_on="ubuntu-latest",
        permissions=Permissions(
            contents=PermissionLevel.WRITE,
            pull_requests=PermissionLevel.WRITE,
        ),
        outputs={
            "release_created": "${{ steps.release.outputs.release_created }}",
            "tag_name": "${{ steps.release.outputs.tag_name }}",
        },
        steps=[
            Step(
                name="Release Please",
                id="release",
                uses="googleapis/release-please-action@v4",
            ),
        ],
    )

    publish_job = Job(
        name="Publish to PyPI",
        runs_on="ubuntu-latest",
        needs="release-please",
        if_="needs.release-please.outputs.release_created == 'true'",
        environment=Environment(name="release"),
        permissions=Permissions(
            id_token=PermissionLevel.WRITE,
        ),
        steps=[
            checkout(),
            setup_uv(),
            Step(name="Build", run="uv build"),
            Step(
                name="Publish to PyPI",
                uses="pypa/gh-action-pypi-publish@release/v1",
            ),
        ],
    )

    return Workflow(
        name="Release",
        on=On(
            push=PushTrigger(branches=["main"]),
        ),
        jobs={
            "release-please": release_please_job,
            "publish": publish_job,
        },
    )


def _docs_workflow() -> Workflow:
    """Build and deploy documentation to GitHub Pages."""
    return Workflow(
        name="Docs",
        on=On(
            push=PushTrigger(branches=["main"]),
            workflow_dispatch=WorkflowDispatchTrigger(),
        ),
        permissions=Permissions(
            contents=PermissionLevel.WRITE,
        ),
        jobs={
            "deploy": Job(
                name="Deploy docs",
                runs_on="ubuntu-latest",
                steps=[
                    checkout(),
                    setup_uv(),
                    setup_python(version="3.13"),
                    Step(
                        name="Install dependencies",
                        run="uv sync",
                    ),
                    Step(
                        name="Configure Git",
                        run=(
                            "git config user.name github-actions[bot]\n"
                            "git config user.email "
                            "41898282+github-actions[bot]"
                            "@users.noreply.github.com"
                        ),
                    ),
                    Step(
                        name="Deploy docs",
                        run="uv run mkdocs gh-deploy --force",
                    ),
                ],
            ),
        },
    )


def create_app() -> App:
    """Create the ghagen App with all workflows."""
    app = App(outdir=".github/workflows")
    app.add(_ci_workflow(), "ci.yml")
    app.add(_schema_drift_workflow(), "schema-drift.yml")
    app.add(_release_workflow(), "release.yml")
    app.add(_docs_workflow(), "docs.yml")
    return app
