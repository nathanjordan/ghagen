# ghagen Dependency Update Action — Design Spec

## Context

ghagen users pin GitHub Action versions in two places: Python source files (`Step(uses="actions/checkout@v4")`) and a lockfile (`.github/ghagen.lock.toml`) that maps refs to commit SHAs. Currently there is no automated way to detect or apply updates to these dependencies.

Renovate and Dependabot don't support ghagen's Python-based format. Renovate's custom manager (regex/JSONata) approach lacks lockfile maintenance support and `postUpgradeTasks` requires self-hosted Renovate. A proper Renovate manager would require upstreaming to their monorepo.

This spec describes a self-contained solution: a new `ghagen deps upgrade` CLI command for detecting and applying updates, and a GitHub Action that automates creating PRs or issues for those updates.

## Architecture

Two components:

1. **`ghagen deps upgrade` CLI command** — core detection and update logic, usable standalone
2. **Composite GitHub Action** — thin orchestration layer that installs ghagen, runs `deps upgrade`, and creates PRs/issues

### Two Modes

| Mode | What it does | Typical schedule |
|------|-------------|-----------------|
| `lockfile-maintenance` | Runs `ghagen deps pin --update` — refreshes SHAs for existing refs without changing Python source | Daily |
| `version-bumps` | Detects newer tags for referenced actions, updates Python source + re-pins | Weekly |

Both modes default to creating PRs. Users can configure `output: issue` to file issues instead.

## `ghagen deps upgrade` CLI Command

### Interface

```
ghagen deps upgrade                       # Apply updates to Python source files (version bumps)
ghagen deps upgrade --check               # Human-readable update report (dry-run)
ghagen deps upgrade --check --json        # Machine-readable JSON output
ghagen deps upgrade --mode lockfile       # SHA refresh opportunities only
ghagen deps upgrade --mode versions       # Newer tag versions only
ghagen deps upgrade --mode all            # Both (default)
ghagen deps upgrade --token TOKEN         # GitHub token (defaults to $GITHUB_TOKEN, $GH_TOKEN)
ghagen deps upgrade --config PATH         # Path to ghagen config file
```

`ghagen deps upgrade` **applies updates** by default, writing to user source files (replacing `uses=` strings with newer versions). The `--check` flag switches to dry-run mode for detection and reporting only. Lockfile updates are always handled separately by `ghagen deps pin` / `ghagen deps pin --update` — `deps upgrade` never writes to the lockfile.

### Detection Flow

1. Load the ghagen `App` from the config file
2. Collect all `uses` refs via existing `collect_uses_refs()` from `src/ghagen/pin/collect.py`
3. Tag each ref with its **source origin** (user file vs ghagen helper — see Source Tracking below)
4. For each ref, query the GitHub Tags API to discover available versions
5. Compare current ref against available tags using semver ordering
6. Report updates grouped by severity (major/minor/patch) and origin

### Output Format (JSON)

```json
{
  "version_bumps": [
    {
      "uses": "actions/checkout@v4",
      "current": "v4",
      "latest": "v5",
      "severity": "major",
      "origin": "user",
      "source_file": ".github/ghagen_workflows.py",
      "release_url": "https://github.com/actions/checkout/releases/tag/v5"  // best-effort, null if no GitHub Release exists for the tag
    }
  ],
  "lockfile_stale": [
    {
      "uses": "actions/checkout@v4",
      "current_sha": "34e114876b0b11c390a56381ad16ebd13914f8d5",
      "latest_sha": "8f4b7f84864484a7bf31766abe9204da3cbe65b3",
      "origin": "user",
      "source_file": ".github/ghagen_workflows.py"
    }
  ],
  "helper_provided": [
    {
      "uses": "actions/setup-python@v5",
      "current": "v5",
      "latest": "v6",
      "severity": "major",
      "helper": "setup_python()"
    }
  ]
}
```

Helper-provided refs are reported separately — they cannot be auto-updated and require a ghagen version upgrade.

### Version Comparison

New module: `src/ghagen/pin/versions.py`

- Thin wrapper around `packaging.version.Version`
- Strips `v` prefix, pads single-segment tags (`v4` → `4.0.0`)
- Classifies updates as major/minor/patch
- Non-semver refs (`@main`, `@release/v1`) are skipped for version bumps, eligible for SHA refresh only
- Handles tag formats: `v1`, `v1.2`, `v1.2.3`, `prefix-v1.0.0`, `prefix/v1.0.0`

### Discovering Available Tags

New function in `src/ghagen/pin/resolve.py`:

```python
def list_tags(owner: str, repo: str, *, token: str | None = None) -> list[str]:
    """List all tags for a repository via the GitHub API."""
```

Uses `GET /repos/{owner}/{repo}/git/refs/tags` (paginated). Reuses existing `_api_get()` infrastructure.

### Source Tracking via `sys.modules` Diffing

New module: `src/ghagen/pin/sources.py`

Determines which Python files contain each `uses` ref:

1. Snapshot `sys.modules` keys before loading the app
2. Load the app (imports config file and all its transitive dependencies)
3. Diff `sys.modules` to find newly imported modules
4. Filter to **user files only**: exclude stdlib, `site-packages/`, and `ghagen` package files
5. Search those user files for each `uses` string literal
6. Tag each ref as `"user"` (found in user file) or `"helper"` (only in ghagen source)

This handles any import pattern (relative, absolute, dynamic) and naturally distinguishes user-controlled refs from helper-provided refs.

### Source Updating

New module: `src/ghagen/pin/update.py`

Given a mapping of `old_uses → new_uses` (e.g., `"actions/checkout@v4" → "actions/checkout@v5"`):

1. For each update, search only the identified user source files (from source tracking)
2. Replace the exact string literal (the full `uses` value including `@ref`)
3. Skip helper-provided refs entirely

Uses targeted string replacement scoped to known user files. AST-based replacement is not needed for v1 since `"actions/checkout@v4"` is a sufficiently unique string within the known file set.

## GitHub Action

### Location

`update-action/action.yml` — a second composite action in the ghagen repo, separate from the existing `ghagen check-synced` action at the repo root.

### Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `mode` | `all` | `lockfile`, `versions`, or `all` |
| `output` | `pr` | `pr` or `issue` |
| `config` | `.github/ghagen_workflows.py` | Path to ghagen config file |
| `python-version` | `3.13` | Python version to use |
| `ghagen-version` | `''` (latest) | Pin ghagen version |
| `token` | `${{ github.token }}` | GitHub token for API calls + PR/issue creation |
| `labels` | `''` | Comma-separated labels for PRs/issues |
| `branch-prefix` | `ghagen-update/` | Branch name prefix for PRs |
| `commit-message-prefix` | `''` | Optional prefix (e.g., `chore(deps):`) |
| `group` | `false` | Group all updates into a single PR/issue |

### Action Flow

1. **Setup**: Install Python, install ghagen (same pattern as existing `ghagen check-synced` action)
2. **Detect**: Run `ghagen deps upgrade --check --json --mode <mode>` to find available updates
3. **Exit early** if no updates found
4. **For `output=pr`**:
   - For each update (or grouped if `group=true`):
     - Create branch from default branch
     - Run `ghagen deps upgrade` (updates Python source for version bumps)
     - Run `ghagen deps pin` (refreshes lockfile)
     - Commit changes with descriptive message
     - Open PR with update details and release notes links
5. **For `output=issue`**:
   - Open issue listing all available updates with details
   - Include severity, current → latest version, release notes links
   - Include helper-provided refs as informational (upgrade ghagen to get these)

### PR Content Template

```markdown
## ghagen dependency update

Updates `actions/checkout` from `v4` to `v5`.

### Changes
- `.github/ghagen_workflows.py`: `actions/checkout@v4` → `actions/checkout@v5`
- `.github/ghagen.lock.toml`: SHA updated

### Release notes
- [actions/checkout v5](https://github.com/actions/checkout/releases/tag/v5)
```

### Example User Workflow

```yaml
name: Dependency Updates
on:
  schedule:
    - cron: '0 6 * * 1'  # Weekly Monday 6am
  workflow_dispatch:

jobs:
  update:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
      issues: write
    steps:
      - uses: actions/checkout@v4
      - uses: nathanjordan/ghagen/update-action@v1
        with:
          mode: all
          output: pr
          token: ${{ secrets.GITHUB_TOKEN }}
```

## Edge Cases

### Non-semver refs
Refs like `@main` or `@release/v1` are not semver-parseable. These are eligible for lockfile maintenance (SHA refresh) but skipped for version bumps. Matches Renovate's behavior.

### Docker-based actions
`docker://` refs are already skipped by `collect_uses_refs()` (`_is_pinnable()` returns false). No change needed.

### Local path actions
`./` refs are already skipped by `collect_uses_refs()`. No change needed.

### Already-pinned SHAs
Refs that are already 40-char SHAs are skipped by `collect_uses_refs()`. No change needed.

### Reusable workflows
`Job.uses` refs (e.g., `octo-org/repo/.github/workflows/ci.yml@v1`) are collected by `collect_uses_refs()` and follow the same update logic. The `parse_uses()` function already handles the `owner/repo/path@ref` format.

### Multiple versions of same action
A user might reference `actions/checkout@v3` in one place and `actions/checkout@v4` in another. Each is tracked independently as a separate `uses` string. Updates are proposed for each independently.

### Rate limiting
The GitHub Tags API is called once per unique `owner/repo`. With authentication, the limit is 5000 req/hr. For repos with many action dependencies, requests should be batched and cached per `owner/repo` (don't re-fetch tags for the same repo).

### Existing PRs/issues
Before creating a new PR or issue, the action should check if one already exists for the same update (by branch name or issue title) to avoid duplicates.

## Files to Create/Modify

### New files
- `src/ghagen/pin/versions.py` — semver comparison with `packaging.version` wrapper
- `src/ghagen/pin/sources.py` — `sys.modules` diffing for source file tracking
- `src/ghagen/pin/update.py` — source file string replacement
- `src/ghagen/cli/outdated.py` — `ghagen deps upgrade` command implementation (or added to `main.py`)
- `update-action/action.yml` — composite GitHub Action definition
- `tests/test_pin/test_versions.py` — version comparison tests
- `tests/test_pin/test_sources.py` — source tracking tests
- `tests/test_pin/test_update.py` — source update tests
- `tests/test_pin/test_outdated.py` — CLI command tests

### Modified files
- `src/ghagen/cli/main.py` — register `deps upgrade` subcommand
- `src/ghagen/pin/resolve.py` — add `list_tags()` function

### Existing code to reuse
- `src/ghagen/pin/collect.py` — `collect_uses_refs()` for gathering all action refs
- `src/ghagen/pin/resolve.py` — `parse_uses()`, `_api_get()`, `resolve_ref()` for GitHub API access
- `src/ghagen/pin/lockfile.py` — `read_lockfile()`, `write_lockfile()`, `Lockfile`, `PinEntry` models
- `src/ghagen/cli/main.py` — `_find_config()`, `_load_app()` for config loading, `pin()` command pattern

## Verification

1. **Unit tests**: Version comparison, source tracking, source updating all tested in isolation
2. **Integration test**: End-to-end `ghagen deps upgrade` on a fixture app with known available updates
3. **Action test**: Run the composite action in a test repo with a ghagen config, verify it creates a PR with correct changes
4. **Edge case tests**: Non-semver refs, helper-provided refs, multiple versions of same action, already-pinned SHAs
