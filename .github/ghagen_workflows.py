"""ghagen's own CI/CD workflows, defined with ghagen (dogfooding)."""

from __future__ import annotations

from ghagen import (
    Action,
    ActionInput,
    ActionOutput,
    App,
    Branding,
    CompositeRuns,
    Job,
    Matrix,
    On,
    Permissions,
    PRTrigger,
    PushTrigger,
    ScheduleTrigger,
    Step,
    Strategy,
    Workflow,
    WorkflowDispatchTrigger,
    expr,
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
            "lint-py": Job(
                name="Lint (Python)",
                runs_on="ubuntu-latest",
                timeout_minutes=10,
                steps=[
                    Step(name="Checkout", uses="actions/checkout@v6"),
                    Step(name="Set up uv", uses="astral-sh/setup-uv@v7"),
                    Step(name="Sync", run="uv sync"),
                    Step(name="Lint", run="scripts/lint.sh py"),
                    Step(name="Format check", run="scripts/fmt.sh py"),
                ],
            ),
            "lint-ts": Job(
                name="Lint (TypeScript)",
                runs_on="ubuntu-latest",
                timeout_minutes=10,
                steps=[
                    Step(name="Checkout", uses="actions/checkout@v6"),
                    Step(name="Setup Node.js", uses="actions/setup-node@v6", with_={"node-version": "24"}),
                    Step(name="Install TS deps", run="npm ci", working_directory="packages/typescript"),
                    Step(name="Lint", run="scripts/lint.sh ts"),
                    Step(name="Format check", run="scripts/fmt.sh ts"),
                ],
            ),
            # `docs/` is a separate npm root from `packages/typescript/`, so it is a
            # separate scope and a separate job: lint-ts no longer installs an Astro
            # site to run oxlint, and docs linting runs in parallel instead of
            # serially inside it.
            "lint-docs": Job(
                name="Lint (docs)",
                runs_on="ubuntu-latest",
                timeout_minutes=10,
                steps=[
                    Step(name="Checkout", uses="actions/checkout@v6"),
                    Step(name="Setup Node.js", uses="actions/setup-node@v6", with_={"node-version": "24"}),
                    Step(name="Install docs deps", run="npm ci", working_directory="docs"),
                    Step(name="Lint", run="scripts/lint.sh docs"),
                    Step(name="Format check", run="scripts/fmt.sh docs"),
                ],
            ),
            "lint-meta": Job(
                name="Lint (meta)",
                runs_on="ubuntu-latest",
                timeout_minutes=10,
                steps=[
                    Step(name="Checkout", uses="actions/checkout@v6"),
                    Step(name="Set up uv", uses="astral-sh/setup-uv@v7"),
                    Step(name="Setup Node.js", uses="actions/setup-node@v6", with_={"node-version": "24"}),
                    Step(name="Sync", run="uv sync"),
                    Step(name="Install TS deps", run="npm ci", working_directory="packages/typescript"),
                    Step(
                        name="actionlint",
                        uses="rhysd/actionlint@v1.7.12",
                    ),
                    # `meta` is a declared scope of scripts/lint.sh, so its contents
                    # live in the script rather than being re-listed here: the
                    # lockfile sync check, plus the staleness guard that regenerates
                    # the TS reference types from the committed Snapshot and fails if
                    # they differ from what is committed. Both are offline and
                    # deterministic (no token, no network), so they are safe on every
                    # PR. The staleness guard is the single line that actively
                    # enforces ADR-0003's author-conformance guarantee.
                    Step(name="Meta lint", run="scripts/lint.sh meta"),
                ],
            ),
            "typecheck-py": Job(
                name="Type check (Python)",
                runs_on="ubuntu-latest",
                timeout_minutes=10,
                steps=[
                    Step(name="Checkout", uses="actions/checkout@v6"),
                    Step(name="Set up uv", uses="astral-sh/setup-uv@v7"),
                    Step(name="Sync", run="uv sync"),
                    Step(name="Pyright", run="scripts/typecheck.sh py"),
                ],
            ),
            "typecheck-ts": Job(
                name="Type check (TypeScript)",
                runs_on="ubuntu-latest",
                timeout_minutes=10,
                steps=[
                    Step(name="Checkout", uses="actions/checkout@v6"),
                    Step(name="Setup Node.js", uses="actions/setup-node@v6", with_={"node-version": "24"}),
                    Step(name="Install TS deps", run="npm ci", working_directory="packages/typescript"),
                    Step(name="tsc", run="scripts/typecheck.sh ts"),
                ],
            ),
            "test-py": Job(
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
                    Step(name="Checkout", uses="actions/checkout@v6"),
                    Step(name="Set up uv", uses="astral-sh/setup-uv@v7"),
                    Step(name="Set up Python", uses="actions/setup-python@v6", with_={"python-version": "${{ matrix.python-version }}"}),
                    Step(name="Sync", run="uv sync"),
                    Step(name="Test", run="scripts/test.sh py"),
                ],
            ),
            "test-ts": Job(
                name="Test (TypeScript)",
                runs_on="ubuntu-latest",
                timeout_minutes=15,
                steps=[
                    Step(name="Checkout", uses="actions/checkout@v6"),
                    Step(name="Setup Node.js", uses="actions/setup-node@v6", with_={"node-version": "24"}),
                    Step(name="Install TS deps", run="npm ci", working_directory="packages/typescript"),
                    Step(name="Test", run="scripts/test.sh ts"),
                ],
            ),
            "check-sync": Job(
                name="Check workflow sync",
                runs_on="ubuntu-latest",
                timeout_minutes=10,
                steps=[
                    Step(name="Checkout", uses="actions/checkout@v6"),
                    Step(name="Set up uv", uses="astral-sh/setup-uv@v7"),
                    Step(name="Sync", run="uv sync"),
                    Step(name="Verify workflows", run="uv run ghagen check-synced"),
                ],
            ),
            "test-action": Job(
                name="Test action",
                runs_on="ubuntu-latest",
                timeout_minutes=10,
                steps=[
                    Step(name="Checkout", uses="actions/checkout@v6"),
                    Step(
                        name="Test composite action",
                        uses="./check-synth",
                        with_={"source": "."},
                    ),
                    # The hermetic half of the check-deps exercise
                    # docs/issues/05 asks for. It lives in this job rather than
                    # a new one because every per-PR job in this repository is
                    # tokenless, and this one is too: the fixture's refs are all
                    # SHAs, so `collect_uses_refs` returns nothing and
                    # `upgrade()` returns before either detection stage -- zero
                    # HTTP requests, structurally. `source: .` is what makes it
                    # exercise this commit rather than the last PyPI release.
                    Step(
                        name="Test check-deps action (offline)",
                        id="check-deps",
                        uses="./check-deps",
                        with_={
                            "source": ".",
                            "dry-run": "true",
                            "config": "fixtures/actions/all_pinned/ghagen_workflows.py",
                        },
                    ),
                    Step(
                        name="Assert plan",
                        run="""
                            set -euo pipefail
                            [ "${{ steps.check-deps.outputs.action }}" = "none" ]
                            [ "${{ steps.check-deps.outputs.total_updates }}" = "0" ]
                            [ "${{ steps.check-deps.outputs.changed }}" = "false" ]
                        """,
                    ),
                ],
            ),
        },
    )


def _schema_drift_workflow() -> Workflow:
    """Weekly schema drift detection: refresh the Snapshot + regenerate types,
    then open a PR carrying the complete fix (issue fallback if PR fails)."""
    return Workflow(
        name="Schema Drift Check",
        on=On(
            schedule=[ScheduleTrigger(cron="0 9 * * 1")],
            workflow_dispatch=WorkflowDispatchTrigger(),
        ),
        permissions=Permissions(
            contents=PermissionLevel.WRITE,  # was READ: the PR branch is pushed
            pull_requests=PermissionLevel.WRITE,  # new: open the drift PR
            issues=PermissionLevel.WRITE,  # kept for the issue fallback
        ),
        jobs={
            "check-drift": Job(
                runs_on="ubuntu-latest",
                timeout_minutes=10,
                steps=[
                    Step(name="Checkout", uses="actions/checkout@v6"),
                    Step(name="Set up uv", uses="astral-sh/setup-uv@v7"),
                    Step(name="Setup Node.js", uses="actions/setup-node@v6", with_={"node-version": "24"}),
                    Step(name="Sync", run="uv sync"),
                    Step(name="Install TS deps", run="npm ci", working_directory="packages/typescript"),
                    # Refresh the Snapshot AND regenerate the types from it, so the
                    # PR is a complete, mergeable fix rather than a diff to reproduce.
                    Step(
                        name="Refresh Snapshot",
                        run="uv run python -m ghagen_schema sync",
                        env={"PYTHONPATH": "scripts"},
                    ),
                    Step(
                        name="Regenerate types",
                        run="uv run python -m ghagen_schema generate",
                        env={"PYTHONPATH": "scripts"},
                    ),
                    # NOTE: no `ghagen_schema check` step here. `check` diffs the
                    # regenerated types against HEAD, so on real drift (the case
                    # this job exists to handle) it exits 1, turns the job red, and
                    # the un-`if:`'d PR/issue step below never runs -- the exact
                    # failure this job must recover from. The offline staleness
                    # guard runs authoritatively in the CI `lint-meta` job on the
                    # resulting PR/commit; duplicating it here can only break the
                    # recovery path.
                    Step(
                        name="Open PR on drift (else issue fallback)",
                        run="""
                            set -euo pipefail
                            if git diff --quiet; then
                              echo "No schema drift."
                              exit 0
                            fi
                            BRANCH="schema-drift/$(date +%Y%m%d)"
                            if gh pr list --head "$BRANCH" --json number \\
                                 --jq '.[0].number' | grep -q .; then
                              echo "Drift PR already open for $BRANCH."
                              exit 0
                            fi
                            git config user.name  "github-actions[bot]"
                            git config user.email \\
                              "41898282+github-actions[bot]@users.noreply.github.com"
                            git checkout -b "$BRANCH"
                            git add schema/ packages/typescript/src/schema/
                            git commit -m "chore(schema): sync upstream drift + regenerate types"
                            if ! git push --force-with-lease -u origin "$BRANCH" || ! gh pr create \\
                                 --title "Schema drift: refreshed Snapshot + types" \\
                                 --body "Automated upstream schema refresh (Snapshot + regenerated types). CI's offline staleness guard (lint-meta) runs on this PR; review the Snapshot diff and regenerated types before merging." \\
                                 --label schema-drift; then
                              echo "::warning::PR creation failed; opening a fallback issue."
                              gh issue create \\
                                --title "GitHub Actions schema drift detected" \\
                                --body "Automated schema refresh could not open a PR. Reproduce locally with \\`uv run python -m ghagen_schema sync && uv run python -m ghagen_schema generate\\`." \\
                                --label schema-drift
                            fi
                        """,
                        env={"GH_TOKEN": str(expr.secrets["GITHUB_TOKEN"])},
                    ),
                ],
            ),
        },
    )


def _check_deps_smoke_workflow() -> Workflow:
    """Weekly networked smoke of the shipped ``check-deps`` action.

    The half of the ``docs/issues/05`` exercise that has to talk to GitHub, kept
    off pull requests on purpose. Every per-PR job in this repository is
    hermetic and tokenless; the only workflows here allowed to call GitHub with
    a token are ``schedule``/``workflow_dispatch`` ones, and this is modelled on
    ``_schema_drift_workflow`` for exactly that reason. The offline half runs on
    every PR inside CI's ``test-action`` job.

    Both cases run with ``dry-run: 'true'``, so ``git push`` and ``gh pr create``
    stay unexercised -- after this rewrite they are about fifteen lines of pure
    I/O rather than a hundred and twelve lines of I/O and decisions.

    The fixture pins ``actions/checkout@v1``, so a newer tag exists for as long
    as that repository does and case 1's ``create-pr`` assertion is not
    time-dependent. Residual upstream dependency, stated rather than hidden: if
    ``actions/checkout`` were deleted or its tags rewritten this job goes red --
    on a schedule, not on anyone's pull request, which is the right blast radius
    for an assertion about someone else's repository.
    """
    return Workflow(
        name="check-deps Smoke",
        on=On(
            schedule=[ScheduleTrigger(cron="0 10 * * 1")],
            workflow_dispatch=WorkflowDispatchTrigger(),
        ),
        # Read-only: dry-run raises nothing, so nothing here needs write.
        permissions=Permissions(contents=PermissionLevel.READ),
        jobs={
            "smoke": Job(
                name="Smoke check-deps against a lockfile-less fixture",
                runs_on="ubuntu-latest",
                timeout_minutes=10,
                steps=[
                    Step(name="Checkout", uses="actions/checkout@v6"),
                    # H7 and H7b, observed on the real shipped artifact. The
                    # fixture is `App(lockfile=None)` with an outdated ref, so
                    # `lockfile_stale` is necessarily empty while a bump is
                    # real -- the exact combination under which the old shell
                    # guard fired `ghagen deps pin --update` on a project where
                    # that command exits 1.
                    Step(
                        name="Versions mode on a lockfile-less project",
                        id="versions",
                        uses="./check-deps",
                        with_={
                            "source": ".",
                            "dry-run": "true",
                            "mode": "versions",
                            "config": (
                                "fixtures/actions/lockfile_none/ghagen_workflows.py"
                            ),
                        },
                    ),
                    Step(
                        name="Assert no lockfile cascade",
                        run="""
                            set -euo pipefail
                            [ "${{ steps.versions.outputs.refresh_lockfile }}" = "false" ]
                            [ "${{ steps.versions.outputs.action }}" = "create-pr" ]
                        """,
                    ),
                    Step(
                        name="Issue output on the same fixture",
                        id="issue",
                        uses="./check-deps",
                        with_={
                            "source": ".",
                            "dry-run": "true",
                            "output": "issue",
                            "config": (
                                "fixtures/actions/lockfile_none/ghagen_workflows.py"
                            ),
                        },
                    ),
                    Step(
                        name="Assert issue plan",
                        run="""
                            set -euo pipefail
                            [ "${{ steps.issue.outputs.action }}" = "create-issue" ]
                            [ -z "${{ steps.issue.outputs.branch }}" ]
                        """,
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
            "ts_release_created": "${{ steps.release.outputs['packages/typescript--release_created'] }}",
            "ts_tag_name": "${{ steps.release.outputs['packages/typescript--tag_name'] }}",
        },
        steps=[
            Step(
                name="Release Please",
                id="release",
                uses="googleapis/release-please-action@v4",
            ),
            Step(
                name="Checkout",
                if_="steps.release.outputs.release_created == 'true'",
                uses="actions/checkout@v6",
            ),
            Step(
                name="Update major version tag",
                if_="steps.release.outputs.release_created == 'true'",
                run="""
                    TAG="${{ steps.release.outputs.tag_name }}"
                    MAJOR="${TAG%%.*}"
                    git config user.name "github-actions[bot]"
                    git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
                    git tag -fa "$MAJOR" -m "Update $MAJOR tag to $TAG"
                    git push origin "$MAJOR" --force
                """,
            ),
        ],
    )

    approve_release_job = Job(
        name="Approve Release",
        runs_on="ubuntu-latest",
        timeout_minutes=5,
        needs="release-please",
        if_=(
            "needs.release-please.outputs.release_created == 'true'"
            " || needs.release-please.outputs.ts_release_created == 'true'"
        ),
        environment=Environment(name="release-gate"),
        steps=[
            Step(
                name="Approve",
                run='echo "Release approved"',
            ),
        ],
    )

    publish_job = Job(
        name="Publish to PyPI",
        runs_on="ubuntu-latest",
        timeout_minutes=10,
        needs=["release-please", "approve-release"],
        if_="needs.release-please.outputs.release_created == 'true'",
        environment=Environment(name="release"),
        permissions=Permissions(
            contents=PermissionLevel.READ,
            id_token=PermissionLevel.WRITE,
        ),
        steps=[
            Step(name="Checkout", uses="actions/checkout@v6"),
            Step(name="Set up uv", uses="astral-sh/setup-uv@v7"),
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
    # Pulls the sdist URL+sha256 from PyPI, regex-rewrites Formula/ghagen.rb,
    # and pushes directly to main. Transitive `resource` stanzas are refreshed
    # manually via `brew update-python-resources` when runtime deps change.
    homebrew_bump_job = Job(
        name="Bump Homebrew tap",
        runs_on="ubuntu-latest",
        timeout_minutes=10,
        needs=["release-please", "approve-release", "publish"],
        if_="needs.release-please.outputs.release_created == 'true'",
        environment=Environment(name="release-homebrew"),
        permissions=Permissions(contents=PermissionLevel.READ),
        steps=[
            Step(
                name="Check out nathanjordan/homebrew-tap",
                uses="actions/checkout@v6",
                with_={
                    "repository": "nathanjordan/homebrew-tap",
                    "token": "${{ secrets.HOMEBREW_TAP_TOKEN }}",
                    "path": "homebrew-tap",
                },
            ),
            Step(
                name="Bump ghagen formula",
                working_directory="homebrew-tap",
                env={
                    "TAG": "${{ needs.release-please.outputs.tag_name }}",
                },
                run="""
                    # Strip tag prefix: v0.2.1 -> 0.2.1
                    VERSION="${TAG#v}"
                    export VERSION

                    # Fetch sdist URL + sha256 from PyPI and rewrite Formula/ghagen.rb.
                    # re.M + `^  ` (2-space indent) targets top-level url/sha256 only,
                    # never the 4-space-indented fields inside `resource` blocks.
                    python3 - <<'PY'
                    import json, os, pathlib, re, urllib.request
                    version = os.environ["VERSION"]
                    meta = json.loads(
                        urllib.request.urlopen(
                            f"https://pypi.org/pypi/ghagen/{version}/json"
                        ).read()
                    )
                    sdist = next(f for f in meta["urls"] if f["packagetype"] == "sdist")
                    formula = pathlib.Path("Formula/ghagen.rb")
                    text = formula.read_text()
                    text = re.sub(
                        r'^  url "[^"]*"',
                        f'  url "{sdist["url"]}"',
                        text,
                        count=1,
                        flags=re.M,
                    )
                    text = re.sub(
                        r'^  sha256 "[^"]*"',
                        f'  sha256 "{sdist["digests"]["sha256"]}"',
                        text,
                        count=1,
                        flags=re.M,
                    )
                    formula.write_text(text)
                    PY

                    # Stop if the formula didn't actually change (e.g. re-run of same release).
                    if git diff --quiet Formula/ghagen.rb; then
                      echo "Formula/ghagen.rb already matches ${VERSION}, nothing to do."
                      exit 0
                    fi

                    # Commit and push directly to main.
                    git config user.name "github-actions[bot]"
                    git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
                    git add Formula/ghagen.rb
                    git commit -m "ghagen ${VERSION}"
                    git push origin main
                """,
            ),
        ],
    )

    npm_publish_job = Job(
        name="Publish to npm",
        runs_on="ubuntu-latest",
        timeout_minutes=10,
        needs=["release-please", "approve-release"],
        if_="needs.release-please.outputs.ts_release_created == 'true'",
        environment=Environment(name="release-npm"),
        permissions=Permissions(
            contents=PermissionLevel.READ,
            id_token=PermissionLevel.WRITE,
        ),
        steps=[
            Step(name="Checkout", uses="actions/checkout@v6"),
            Step(
                name="Setup Node.js",
                uses="actions/setup-node@v6",
                with_={
                    "node-version": "24",
                    "registry-url": "https://registry.npmjs.org",
                },
            ),
            Step(
                name="Install dependencies",
                run="npm install",
                working_directory="packages/typescript",
            ),
            Step(
                name="Build",
                run="npm run build",
                working_directory="packages/typescript",
            ),
            Step(
                name="Publish to npm",
                run="npm publish --provenance",
                working_directory="packages/typescript",
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
            "approve-release": approve_release_job,
            "publish": publish_job,
            "npm-publish": npm_publish_job,
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
            contents=PermissionLevel.READ,
            pages=PermissionLevel.WRITE,
            id_token=PermissionLevel.WRITE,
        ),
        jobs={
            "build": Job(
                name="Build docs",
                runs_on="ubuntu-latest",
                timeout_minutes=15,
                steps=[
                    Step(name="Checkout", uses="actions/checkout@v6"),
                    Step(
                        name="Setup Node.js",
                        uses="actions/setup-node@v6",
                        with_={"node-version": "24"},
                    ),
                    Step(
                        name="Install TypeScript package dependencies",
                        run="npm ci",
                        working_directory="packages/typescript",
                    ),
                    Step(
                        name="Install dependencies",
                        run="npm ci",
                        working_directory="docs",
                    ),
                    Step(
                        name="Build docs",
                        run="npm run build",
                        working_directory="docs",
                    ),
                    Step(
                        name="Upload Pages artifact",
                        uses="actions/upload-pages-artifact@v5",
                        with_={"path": "docs/dist"},
                    ),
                ],
            ),
            "deploy": Job(
                name="Deploy docs",
                runs_on="ubuntu-latest",
                needs="build",
                timeout_minutes=5,
                environment=Environment(name="github-pages"),
                steps=[
                    Step(
                        name="Deploy to GitHub Pages",
                        uses="actions/deploy-pages@v5",
                    ),
                ],
            ),
        },
    )


def _ghagen_check_action() -> Action:
    """ghagen's own composite action wrapping ``ghagen check-synced``.

    Dogfooding: this is what currently lives at ``check-synth/action.yml`` and is
    consumed by the ``test-action`` job in CI via ``uses: ./check-synth``.
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
                    uses="actions/setup-python@v6",
                    with_={"python-version": "${{ inputs.python-version }}"},
                ),
                Step(
                    name="Install ghagen",
                    run="""
                        if [ -n "${{ inputs.source }}" ]; then
                          pip install "${{ inputs.source }}"
                        else
                          pip install ghagen${{ inputs.ghagen-version != '' && format('=={0}', inputs.ghagen-version) || '' }}
                        fi
                    """,
                    shell="bash",
                ),
                Step(
                    name="Check workflows",
                    run='ghagen check-synced --config "${{ inputs.config }}"',
                    shell="bash",
                ),
            ],
        ),
    )


def _ghagen_update_action() -> Action:
    """ghagen's own composite action wrapping ``ghagen deps update``.

    Dogfooding: replaces the hand-written ``check-deps/action.yml`` so it is
    generated, pinned, and drift-checked exactly like ``check-synth``.

    Two run blocks, zero decisions. The first runs ``ghagen deps update``,
    which sweeps once, does every write the update needs, and appends its plan
    to ``$GITHUB_OUTPUT``. The second does git and ``gh`` and nothing else.

    What used to be here -- a ``python3 -c`` reader for ghagen's own JSON, a
    reconstruction of the lockfile-refresh rule from that JSON, a label-parsing
    loop written twice -- is gone. The lockfile rule in particular could never
    be right here: the payload deliberately does not carry ``app.lockfile_path``,
    so the guard fired ``ghagen deps pin --update`` on ``lockfile=None``
    projects, where that command exits 1. ``pin/plan`` holds the ``App`` and
    answers it once.
    """
    return Action(
        name="ghagen Update",
        description=(
            "Detect and apply dependency updates for "
            "ghagen-managed GitHub Actions workflows"
        ),
        branding=Branding(icon="refresh-cw", color="blue"),
        inputs={
            "mode": ActionInput(
                description="Detection mode: 'versions', 'lockfile', or 'all'",
                required=False,
                default="all",
            ),
            "output": ActionInput(
                description="Output type: 'pr' or 'issue'",
                required=False,
                default="pr",
            ),
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
            "token": ActionInput(
                description="GitHub token for API calls and PR/issue creation",
                required=False,
                default="${{ github.token }}",
            ),
            "labels": ActionInput(
                description="Comma-separated labels to apply to PRs/issues",
                required=False,
                default="",
            ),
            "branch-prefix": ActionInput(
                description="Branch name prefix for PRs",
                required=False,
                default="ghagen-update/",
            ),
            "commit-message-prefix": ActionInput(
                description='Optional prefix for commit messages (e.g. "chore(deps):")',
                required=False,
                default="",
            ),
            # Exact mirror of check-synth's `source` (:576-583 above). Without
            # it a CI job writing `uses: ./check-deps` gets the action
            # definition from the working tree but `pip install ghagen` from
            # PyPI -- so it exercises the last published release and a
            # regression introduced in the same PR passes. That is what kept
            # docs/issues/05 unactionable rather than merely unaddressed.
            "source": ActionInput(
                description=(
                    "Local source path to install from (for testing). "
                    "Leave empty to install from PyPI."
                ),
                required=False,
                default="",
            ),
            "dry-run": ActionInput(
                description=(
                    "Plan only: no source edits, no lockfile write, "
                    "no git, no gh"
                ),
                required=False,
                default="false",
            ),
        },
        # Per-step `steps.<id>.outputs.*` are invisible outside a composite
        # action, so without this block no caller -- including a CI job -- can
        # assert anything about what the action decided. Named exhaustively:
        # this is the surface a tag-pinned consumer reads.
        outputs={
            "action": ActionOutput(
                description="none | create-pr | create-issue",
                value="${{ steps.plan.outputs.action }}",
            ),
            "total_updates": ActionOutput(
                description="Version bumps plus stale lockfile entries",
                value="${{ steps.plan.outputs.total_updates }}",
            ),
            "refresh_lockfile": ActionOutput(
                # A decision, not an outcome: `pin/plan` documents every
                # `UpdatePlan` field as what to do, and this one reads `true`
                # under `--dry-run` with nothing re-resolved.
                description=(
                    "Whether the lockfile is to be re-resolved "
                    "(always false when lockfile=None)"
                ),
                value="${{ steps.plan.outputs.refresh_lockfile }}",
            ),
            "branch": ActionOutput(
                description="The dated branch, or empty unless action is create-pr",
                value="${{ steps.plan.outputs.branch }}",
            ),
            "title": ActionOutput(
                description="The PR or issue title",
                value="${{ steps.plan.outputs.title }}",
            ),
            "changed": ActionOutput(
                description=(
                    "Whether anything was written (always false under dry-run)"
                ),
                value="${{ steps.plan.outputs.changed }}",
            ),
        },
        runs=CompositeRuns(
            steps=[
                Step(
                    uses="actions/setup-python@v6",
                    with_={"python-version": "${{ inputs.python-version }}"},
                ),
                Step(
                    name="Install ghagen",
                    run="""
                        if [ -n "${{ inputs.source }}" ]; then
                          pip install "${{ inputs.source }}"
                        elif [ -n "${{ inputs.ghagen-version }}" ]; then
                          pip install "ghagen==${{ inputs.ghagen-version }}"
                        else
                          pip install ghagen
                        fi
                    """,
                    shell="bash",
                ),
                # One sweep, one plan, one append. No `|| true`: the CLI's exit
                # code is the step's, and its one-line diagnostic is the log.
                # The previous shape ended the detect command in `|| true` and
                # then parsed the file it was supposed to have written, so any
                # CLI failure surfaced as exit 1 plus a JSONDecodeError
                # traceback from the reader instead.
                Step(
                    name="Plan dependency updates",
                    id="plan",
                    env={"GITHUB_TOKEN": "${{ inputs.token }}"},
                    run="""
                        set -euo pipefail

                        ghagen deps update \\
                          --config "${{ inputs.config }}" \\
                          --mode "${{ inputs.mode }}" \\
                          --output "${{ inputs.output }}" \\
                          --labels "${{ inputs.labels }}" \\
                          --branch-prefix "${{ inputs.branch-prefix }}" \\
                          --commit-message-prefix "${{ inputs.commit-message-prefix }}" \\
                          --body-file "$RUNNER_TEMP/ghagen-body.md" \\
                          ${{ inputs.dry-run == 'true' && '--dry-run' || '' }} \\
                          --format github >> "$GITHUB_OUTPUT"
                    """,
                    shell="bash",
                ),
                # git and `gh`, and nothing else. Every value it uses was
                # decided by `pin/plan` and handed over as a step output.
                Step(
                    name="Raise PR or issue",
                    if_=(
                        "steps.plan.outputs.action != 'none' "
                        "&& inputs.dry-run != 'true'"
                    ),
                    env={
                        "GITHUB_TOKEN": "${{ inputs.token }}",
                        "GH_TOKEN": "${{ inputs.token }}",
                    },
                    run=r"""
                        set -euo pipefail

                        BODY_FILE="$RUNNER_TEMP/ghagen-body.md"

                        # Already split and trimmed by the CLI; this only turns
                        # a comma-separated string into argv without eval.
                        #
                        # Every expansion below is `${LABEL_ARGS[@]+...}`, not a
                        # bare `"${LABEL_ARGS[@]}"`: under `set -u` an empty
                        # array is an unbound variable on bash 3.2, and the
                        # action's own default is `labels: ''`, so the default
                        # configuration is the one that trips it. Modern bash
                        # (4.4+, which the ubuntu runners have) tolerates the
                        # bare form, so this is correct-anyway hardening rather
                        # than a fix for the hosted runners.
                        LABEL_ARGS=()
                        if [ -n "${{ steps.plan.outputs.labels }}" ]; then
                          IFS=',' read -ra LABELS <<< "${{ steps.plan.outputs.labels }}"
                          for label in "${LABELS[@]}"; do
                            LABEL_ARGS+=(--label "$label")
                          done
                        fi

                        case "${{ steps.plan.outputs.action }}" in
                          create-pr)
                            BRANCH="${{ steps.plan.outputs.branch }}"

                            # Dedupe on the thing `git push` will actually
                            # collide with -- the branch -- not on open PRs,
                            # which misses a same-day branch whose PR was
                            # closed. Distinguishes absent (2) from failed
                            # (anything else) rather than swallowing both;
                            # `--force-with-lease` is deliberately not used,
                            # since actions/checkout fetches a single ref so
                            # there is no remote-tracking ref to lease against.
                            set +e
                            git ls-remote --exit-code --heads origin "$BRANCH" >/dev/null
                            LS=$?
                            set -e
                            BRANCH_EXISTS=0
                            case "$LS" in
                              0) BRANCH_EXISTS=1 ;;
                              2) : ;;
                              *) echo "::error::git ls-remote failed ($LS)"; exit "$LS" ;;
                            esac

                            if [ "$BRANCH_EXISTS" = 1 ]; then
                              # A branch on the remote is not evidence the work
                              # landed. A run that pushed and then failed to open
                              # the PR -- `gh pr create` denied by the org's
                              # "Allow GitHub Actions to create and approve pull
                              # requests" setting, or by a missing
                              # `pull-requests: write` -- leaves exactly this
                              # state. Skipping on the branch alone then reports
                              # success on every retry until the dated name rolls
                              # over at midnight UTC, which is a regression from
                              # the PR-based dedupe this replaced. Dedupe on the
                              # branch for the push, but on the PR for the skip:
                              # the PR is the thing the caller wants to exist.
                              EXISTING_PR=$(gh pr list --head "$BRANCH" \
                                --state all --json number --jq '.[0].number // empty')
                              if [ -n "$EXISTING_PR" ]; then
                                echo "PR #$EXISTING_PR already exists for $BRANCH; skipping."
                                exit 0
                              fi
                              echo "Branch $BRANCH exists with no PR; opening one against it."
                            else
                              if [ "${{ steps.plan.outputs.changed }}" != "true" ]; then
                                echo "No file changes after applying updates."
                                exit 0
                              fi

                              git config user.name "github-actions[bot]"
                              git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
                              git checkout -b "$BRANCH"
                              # Not a bare `git add -A`: loading the config module
                              # writes `__pycache__` beside it, and the tree
                              # `ghagen init` scaffolds ships no `.gitignore`, so
                              # a consumer repo without one gets a committed
                              # `.pyc` in its dependency-update PR. A pathspec
                              # exclusion rather than adding only the CLI's
                              # reported paths: those are printed on the plan
                              # step's stderr, which no later step can address,
                              # and the plan's outputs carry `changed` as a bool
                              # and no file list.
                              git add -A -- ':!**/__pycache__'
                              git commit -m "${{ steps.plan.outputs.commit_message }}"
                              git push -u origin "$BRANCH"
                            fi

                            # `--head` is required on the recovery path, where
                            # the branch was pushed by an earlier run and this
                            # checkout is not on it.
                            gh pr create \
                              --title "${{ steps.plan.outputs.title }}" \
                              --head "$BRANCH" \
                              --body-file "$BODY_FILE" ${LABEL_ARGS[@]+"${LABEL_ARGS[@]}"}
                            ;;
                          create-issue)
                            # No `|| echo ""`: an API failure here used to read
                            # as "no existing issue" and open a duplicate.
                            # `// empty` because `.[0].number` on an empty list
                            # prints the string "null", which is not empty and
                            # would skip forever.
                            EXISTING=$(gh issue list \
                              --search "${{ steps.plan.outputs.title }} in:title" \
                              --state open --json number --jq '.[0].number // empty')
                            if [ -n "$EXISTING" ]; then
                              echo "Issue #$EXISTING already exists. Skipping."
                              exit 0
                            fi

                            gh issue create \
                              --title "${{ steps.plan.outputs.title }}" \
                              --body-file "$BODY_FILE" ${LABEL_ARGS[@]+"${LABEL_ARGS[@]}"}
                            ;;
                        esac
                    """,
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
    app.add_workflow(_check_deps_smoke_workflow(), "check-deps-smoke.yml")
    app.add_workflow(_release_workflow(), "release.yml")
    app.add_workflow(_docs_workflow(), "docs.yml")
    app.add_action(_ghagen_check_action(), dir="check-synth")
    app.add_action(_ghagen_update_action(), dir="check-deps")
    return app
