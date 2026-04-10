"""ghagen's own CI/CD workflows, defined with ghagen (dogfooding)."""

from __future__ import annotations

from ghagen import (
    Action,
    ActionInput,
    App,
    Branding,
    CompositeRuns,
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
        permissions=Permissions(contents=PermissionLevel.READ),
        jobs={
            "lint": Job(
                name="Lint",
                runs_on="ubuntu-latest",
                timeout_minutes=10,
                steps=[
                    checkout(),
                    setup_uv(),
                    Step(name="Sync", run="uv sync"),
                    Step(name="Ruff check", run="uv run ruff check src/ tests/"),
                    Step(
                        name="actionlint",
                        uses="rhysd/actionlint@v1.7.11",
                    ),
                    Step(
                        name="ghagen lint",
                        run="uv run ghagen lint --format=github",
                    ),
                    Step(
                        name="ghagen pin --check",
                        run="uv run ghagen pin --check --prune",
                        env={"GITHUB_TOKEN": str(expr.secrets["GITHUB_TOKEN"])},
                    ),
                ],
            ),
            "typecheck": Job(
                name="Type check",
                runs_on="ubuntu-latest",
                timeout_minutes=10,
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
                timeout_minutes=15,
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
                timeout_minutes=10,
                steps=[
                    checkout(),
                    setup_uv(),
                    Step(name="Sync", run="uv sync"),
                    Step(name="Verify workflows", run="uv run ghagen check"),
                ],
            ),
            "test-action": Job(
                name="Test action",
                runs_on="ubuntu-latest",
                timeout_minutes=10,
                steps=[
                    checkout(),
                    Step(
                        name="Test composite action",
                        uses="./",
                        with_={"source": "."},
                    ),
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
                timeout_minutes=10,
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
        timeout_minutes=10,
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
        timeout_minutes=10,
        needs="release-please",
        if_="needs.release-please.outputs.release_created == 'true'",
        environment=Environment(name="release"),
        permissions=Permissions(
            contents=PermissionLevel.READ,
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

    # Bump the ghagen formula in nathanjordan/homebrew-tap after PyPI publish.
    #
    # Runs inside the Release workflow (not on release:published) because
    # release-please creates releases via the default GITHUB_TOKEN, and
    # GITHUB_TOKEN-originated events don't trigger new workflow runs.
    #
    # Uses the PinViz approach (nordstad/PinViz/blob/main/.github/workflows/
    # brew-publish.yml): pull the sdist URL+sha256 from PyPI, regex-rewrite
    # Formula/ghagen.rb, git push to a branch, open a PR via `gh`. We
    # deliberately do *not* use `brew bump-formula-pr` or
    # `dawidd6/action-homebrew-bump-formula` — the former has no working
    # CI precedent and the latter is documented-broken for virtualenv
    # formulae. Transitive `resource` stanzas are refreshed manually via
    # `brew update-python-resources` when runtime deps actually change.
    homebrew_bump_job = Job(
        name="Bump Homebrew tap",
        runs_on="ubuntu-latest",
        timeout_minutes=10,
        needs=["release-please", "publish"],
        if_="needs.release-please.outputs.release_created == 'true'",
        environment=Environment(name="release"),
        permissions=Permissions(contents=PermissionLevel.READ),
        steps=[
            Step(
                name="Check out nathanjordan/homebrew-tap",
                uses="actions/checkout@v4",
                with_={
                    "repository": "nathanjordan/homebrew-tap",
                    "token": "${{ secrets.HOMEBREW_TAP_TOKEN }}",
                    "path": "homebrew-tap",
                },
            ),
            Step(
                name="Bump ghagen formula and open PR",
                working_directory="homebrew-tap",
                env={
                    "GH_TOKEN": "${{ secrets.HOMEBREW_TAP_TOKEN }}",
                    "TAG": "${{ needs.release-please.outputs.tag_name }}",
                },
                run=(
                    "# Strip release-please tag prefix: ghagen-v0.2.1 -> 0.2.1\n"
                    'VERSION="${TAG#ghagen-v}"\n'
                    'VERSION="${VERSION#v}"\n'
                    "export VERSION\n"
                    "\n"
                    "# Fetch sdist URL + sha256 from PyPI and rewrite Formula/ghagen.rb.\n"
                    "# re.M + `^  ` (2-space indent) targets top-level url/sha256 only,\n"
                    "# never the 4-space-indented fields inside `resource` blocks.\n"
                    "python3 - <<'PY'\n"
                    "import json, os, pathlib, re, urllib.request\n"
                    'version = os.environ["VERSION"]\n'
                    'meta = json.loads(\n'
                    '    urllib.request.urlopen(\n'
                    '        f"https://pypi.org/pypi/ghagen/{version}/json"\n'
                    "    ).read()\n"
                    ")\n"
                    'sdist = next(f for f in meta["urls"] if f["packagetype"] == "sdist")\n'
                    'formula = pathlib.Path("Formula/ghagen.rb")\n'
                    "text = formula.read_text()\n"
                    "text = re.sub(\n"
                    '    r\'^  url "[^"]*"\',\n'
                    "    f'  url \"{sdist[\"url\"]}\"',\n"
                    "    text,\n"
                    "    count=1,\n"
                    "    flags=re.M,\n"
                    ")\n"
                    "text = re.sub(\n"
                    '    r\'^  sha256 "[^"]*"\',\n'
                    "    f'  sha256 \"{sdist[\"digests\"][\"sha256\"]}\"',\n"
                    "    text,\n"
                    "    count=1,\n"
                    "    flags=re.M,\n"
                    ")\n"
                    "formula.write_text(text)\n"
                    "PY\n"
                    "\n"
                    "# Stop if the formula didn't actually change (e.g. re-run of same release).\n"
                    "if git diff --quiet Formula/ghagen.rb; then\n"
                    '  echo "Formula/ghagen.rb already matches ${VERSION}, nothing to do."\n'
                    "  exit 0\n"
                    "fi\n"
                    "\n"
                    '# Commit, push to a branch, open PR via gh.\n'
                    'git config user.name "github-actions[bot]"\n'
                    "git config user.email "
                    '"41898282+github-actions[bot]@users.noreply.github.com"\n'
                    'BRANCH="bump-ghagen-${VERSION}"\n'
                    'git checkout -b "$BRANCH"\n'
                    "git add Formula/ghagen.rb\n"
                    'git commit -m "ghagen ${VERSION}"\n'
                    'git push origin "$BRANCH"\n'
                    "gh pr create \\\n"
                    "  --repo nathanjordan/homebrew-tap \\\n"
                    '  --title "ghagen ${VERSION}" \\\n'
                    '  --body "Automated bump by the ghagen release workflow." \\\n'
                    '  --head "$BRANCH" \\\n'
                    "  --base main"
                ),
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
            "homebrew-bump": homebrew_bump_job,
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
                timeout_minutes=15,
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


def _ghagen_check_action() -> Action:
    """ghagen's own composite action wrapping ``ghagen check``.

    Dogfooding: this is what currently lives at ``action.yml`` and is
    consumed by the ``test-action`` job in CI via ``uses: ./``.
    """
    return Action(
        name="ghagen Check",
        description=(
            "Verify GitHub Actions workflows are in sync "
            "with Python definitions"
        ),
        branding=Branding(icon="check-circle", color="green"),
        inputs={
            "config": ActionInput(
                description="Path to ghagen config file",
                required=False,
                default=".github/ghagen_workflows.py",
            ),
            "python-version": ActionInput(
                description="Python version to use",
                required=False,
                default="3.13",
            ),
            "ghagen-version": ActionInput(
                description="ghagen version to install (empty for latest)",
                required=False,
                default="",
            ),
            "source": ActionInput(
                description=(
                    "Local source path to install from (for testing). "
                    "Leave empty to install from PyPI."
                ),
                required=False,
                default="",
            ),
        },
        runs=CompositeRuns(
            steps=[
                Step(
                    uses="actions/setup-python@v5",
                    with_={"python-version": "${{ inputs.python-version }}"},
                ),
                Step(
                    name="Install ghagen",
                    run=(
                        'if [ -n "${{ inputs.source }}" ]; then\n'
                        '  pip install "${{ inputs.source }}"\n'
                        "else\n"
                        "  pip install ghagen${{ inputs.ghagen-version != ''"
                        " && format('=={0}', inputs.ghagen-version) || '' }}\n"
                        "fi"
                    ),
                    shell="bash",
                ),
                Step(
                    name="Check workflows",
                    run='ghagen check --config "${{ inputs.config }}"',
                    shell="bash",
                ),
            ],
        ),
    )


def create_app() -> App:
    """Create the ghagen App with all workflows and the composite action."""
    app = App()
    app.add_workflow(_ci_workflow(), "ci.yml")
    app.add_workflow(_schema_drift_workflow(), "schema-drift.yml")
    app.add_workflow(_release_workflow(), "release.yml")
    app.add_workflow(_docs_workflow(), "docs.yml")
    app.add_action(_ghagen_check_action())
    return app
