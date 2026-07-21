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
                    Step(name="Install docs deps", run="npm ci", working_directory="docs"),
                    Step(name="Lint", run="scripts/lint.sh ts"),
                    Step(name="Format check", run="scripts/fmt.sh ts"),
                ],
            ),
            # actionlint and `ghagen deps check-synced` are language-neutral, so
            # scripts/lint.sh only runs them under its default `all` scope (see the
            # script). The per-language jobs above call it scoped to `py`/`ts` and
            # never trigger them, so this job runs them directly instead.
            "lint-meta": Job(
                name="Lint (meta)",
                runs_on="ubuntu-latest",
                timeout_minutes=10,
                steps=[
                    Step(name="Checkout", uses="actions/checkout@v6"),
                    Step(name="Set up uv", uses="astral-sh/setup-uv@v7"),
                    Step(name="Sync", run="uv sync"),
                    Step(
                        name="actionlint",
                        uses="rhysd/actionlint@v1.7.12",
                    ),
                    Step(
                        name="ghagen deps check-synced",
                        run="uv run ghagen deps check-synced",
                        env={"GITHUB_TOKEN": str(expr.secrets["GITHUB_TOKEN"])},
                    ),
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
                    Step(name="Checkout", uses="actions/checkout@v6"),
                    Step(name="Set up uv", uses="astral-sh/setup-uv@v7"),
                    Step(name="Sync", run="uv sync"),
                    Step(
                        name="Fetch upstream schema into the canonical snapshot",
                        run="uv run python packages/python/scripts/schema_sync.py sync",
                    ),
                    Step(
                        name="Check for drift",
                        run="""
                            if ! git diff --exit-code schema/; then
                              echo "::warning::Schema drift detected"
                              gh issue create \\
                                --title "GitHub Actions schema drift detected" \\
                                --body "$(git diff schema/)" \\
                                --label schema-drift
                            fi
                        """,
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
    """ghagen's own composite action wrapping ``ghagen deps upgrade``.

    Dogfooding: replaces the hand-written ``check-deps/action.yml`` so it is
    generated, pinned, and drift-checked exactly like ``check-synth``. The
    PR/issue-body builders use ``python3 - <<'PY'`` heredocs (same mechanism as
    ``_release_workflow``'s homebrew-bump step), which ``auto_dedent`` and the
    ``<<'PY'`` sentinel keep intact.
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
            "group": ActionInput(
                description="Group all updates into a single PR/issue",
                required=False,
                default="false",
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
                        if [ -n "${{ inputs.ghagen-version }}" ]; then
                          pip install "ghagen==${{ inputs.ghagen-version }}"
                        else
                          pip install ghagen
                        fi
                    """,
                    shell="bash",
                ),
                Step(
                    name="Detect outdated dependencies",
                    id="detect",
                    env={"GITHUB_TOKEN": "${{ inputs.token }}"},
                    run="""
                        set -euo pipefail

                        JSON_FILE=$(mktemp)
                        ghagen deps upgrade --check --json --mode "${{ inputs.mode }}" --config "${{ inputs.config }}" > "$JSON_FILE" || true

                        VERSION_BUMPS=$(python3 -c "import json; d=json.load(open('$JSON_FILE')); print(len(d.get('version_bumps',[])))")
                        LOCKFILE_STALE=$(python3 -c "import json; d=json.load(open('$JSON_FILE')); print(len(d.get('lockfile_stale',[])))")

                        echo "json_file=$JSON_FILE" >> "$GITHUB_OUTPUT"
                        echo "version_bumps=$VERSION_BUMPS" >> "$GITHUB_OUTPUT"
                        echo "lockfile_stale=$LOCKFILE_STALE" >> "$GITHUB_OUTPUT"

                        TOTAL=$((VERSION_BUMPS + LOCKFILE_STALE))
                        echo "total_updates=$TOTAL" >> "$GITHUB_OUTPUT"

                        if [ "$TOTAL" -eq 0 ]; then
                          echo "No dependency updates found."
                        else
                          echo "Found $VERSION_BUMPS version bump(s) and $LOCKFILE_STALE stale lockfile entry/entries."
                        fi
                    """,
                    shell="bash",
                ),
                Step(
                    name="Exit early if no updates",
                    if_="steps.detect.outputs.total_updates == '0'",
                    run='echo "Everything is up to date."',
                    shell="bash",
                ),
                Step(
                    name="Create PR",
                    if_="steps.detect.outputs.total_updates != '0' && inputs.output == 'pr'",
                    env={
                        "GITHUB_TOKEN": "${{ inputs.token }}",
                        "GH_TOKEN": "${{ inputs.token }}",
                    },
                    run=r"""
                        set -euo pipefail

                        BRANCH="${{ inputs.branch-prefix }}$(date +%Y%m%d)"
                        PREFIX="${{ inputs.commit-message-prefix }}"

                        # Build label args as an array to avoid eval
                        LABEL_ARGS=()
                        if [ -n "${{ inputs.labels }}" ]; then
                          IFS=',' read -ra LABELS <<< "${{ inputs.labels }}"
                          for label in "${LABELS[@]}"; do
                            trimmed=$(echo "$label" | xargs)
                            LABEL_ARGS+=(--label "$trimmed")
                          done
                        fi

                        # Check if branch/PR already exists
                        EXISTING_PR=$(gh pr list --head "$BRANCH" --json number --jq '.[0].number' 2>/dev/null || echo "")
                        if [ -n "$EXISTING_PR" ]; then
                          echo "PR #$EXISTING_PR already exists for branch $BRANCH. Skipping."
                          exit 0
                        fi

                        git config user.name "github-actions[bot]"
                        git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
                        git checkout -b "$BRANCH"

                        # Apply version bumps if any
                        if [ "${{ steps.detect.outputs.version_bumps }}" != "0" ]; then
                          ghagen deps upgrade --mode versions --config "${{ inputs.config }}"
                        fi

                        # Refresh lockfile
                        if [ "${{ steps.detect.outputs.lockfile_stale }}" != "0" ] || [ "${{ steps.detect.outputs.version_bumps }}" != "0" ]; then
                          ghagen deps pin --config "${{ inputs.config }}" --update
                        fi

                        # Check if there are actual changes
                        if git diff --quiet && git diff --cached --quiet; then
                          echo "No file changes after applying updates."
                          exit 0
                        fi

                        # Build commit message
                        COMMIT_MSG="update ghagen action dependencies"
                        if [ -n "$PREFIX" ]; then
                          COMMIT_MSG="${PREFIX} ${COMMIT_MSG}"
                        fi

                        git add -A
                        git commit -m "$COMMIT_MSG"
                        git push -u origin "$BRANCH"

                        # Build PR body via Python to a temp file (avoids shell quoting issues)
                        BODY_FILE=$(mktemp)
                        export BODY_FILE
                        export JSON_FILE="${{ steps.detect.outputs.json_file }}"
                        python3 - <<'PY'
                        import json, os
                        d = json.load(open(os.environ['JSON_FILE']))
                        lines = ['## ghagen dependency update', '']

                        bumps = d.get('version_bumps', [])
                        if bumps:
                            lines.append('### Version bumps')
                            lines.append('')
                            for b in bumps:
                                lines.append(f'- `{b["uses"]}` -> `{b["latest"]}` [{b["severity"]}]')
                            lines.append('')

                        stale = d.get('lockfile_stale', [])
                        if stale:
                            lines.append('### Lockfile maintenance')
                            lines.append('')
                            for s in stale:
                                lines.append(f'- `{s["uses"]}` SHA refreshed')
                            lines.append('')

                        with open(os.environ['BODY_FILE'], 'w') as f:
                            f.write('\n'.join(lines))
                        PY

                        gh pr create --title "$COMMIT_MSG" --body-file "$BODY_FILE" "${LABEL_ARGS[@]}"
                        rm -f "$BODY_FILE"
                    """,
                    shell="bash",
                ),
                Step(
                    name="Create issue",
                    if_="steps.detect.outputs.total_updates != '0' && inputs.output == 'issue'",
                    env={"GH_TOKEN": "${{ inputs.token }}"},
                    run=r"""
                        set -euo pipefail

                        TITLE="ghagen dependency updates available ($(date +%Y-%m-%d))"

                        # Build label args as an array
                        LABEL_ARGS=()
                        if [ -n "${{ inputs.labels }}" ]; then
                          IFS=',' read -ra LABELS <<< "${{ inputs.labels }}"
                          for label in "${LABELS[@]}"; do
                            trimmed=$(echo "$label" | xargs)
                            LABEL_ARGS+=(--label "$trimmed")
                          done
                        fi

                        # Check if issue already exists
                        EXISTING=$(gh issue list --search "$TITLE in:title" --state open --json number --jq '.[0].number' 2>/dev/null || echo "")
                        if [ -n "$EXISTING" ]; then
                          echo "Issue #$EXISTING already exists. Skipping."
                          exit 0
                        fi

                        # Build issue body via Python to a temp file
                        BODY_FILE=$(mktemp)
                        export BODY_FILE
                        export JSON_FILE="${{ steps.detect.outputs.json_file }}"
                        python3 - <<'PY'
                        import json, os
                        d = json.load(open(os.environ['JSON_FILE']))
                        lines = []

                        bumps = d.get('version_bumps', [])
                        if bumps:
                            lines.append('## Version updates available')
                            lines.append('')
                            for b in bumps:
                                files = ', '.join(f'`{f}`' for f in b.get('source_files', []))
                                line = f'- [ ] `{b["uses"]}` -> `{b["latest"]}` [{b["severity"]}]'
                                if files:
                                    line += f'  in {files}'
                                lines.append(line)
                            lines.append('')

                        stale = d.get('lockfile_stale', [])
                        if stale:
                            lines.append('## Stale lockfile entries')
                            lines.append('')
                            lines.append('Run `ghagen deps pin --update` to refresh.')
                            lines.append('')
                            for s in stale:
                                lines.append(f'- [ ] `{s["uses"]}` — SHA changed')
                            lines.append('')

                        with open(os.environ['BODY_FILE'], 'w') as f:
                            f.write('\n'.join(lines))
                        PY

                        gh issue create --title "$TITLE" --body-file "$BODY_FILE" "${LABEL_ARGS[@]}"
                        rm -f "$BODY_FILE"
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
    app.add_workflow(_release_workflow(), "release.yml")
    app.add_workflow(_docs_workflow(), "docs.yml")
    app.add_action(_ghagen_check_action(), dir="check-synth")
    app.add_action(_ghagen_update_action(), dir="check-deps")
    return app
