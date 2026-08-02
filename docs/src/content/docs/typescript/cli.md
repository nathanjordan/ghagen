---
title: CLI Reference
description: ghagen CLI command documentation for TypeScript
---

ghagen provides commands organized into top-level commands (`synth`, `check-synced`, `init`) and a `deps` subgroup (`deps pin`, `deps check-synced`, `deps upgrade`, `deps update`).

## Installation

```bash
npm install --save-dev @ghagen/ghagen
```

## ghagen synth

Generate YAML workflow files from your TypeScript/JavaScript definitions.

```bash
npx ghagen synth
```

### Options

| Option          | Description                                                 |
| --------------- | ----------------------------------------------------------- |
| `--config PATH` | Path to the configuration file. Defaults to auto-detection. |

### Config file resolution

If `--config` is not specified, ghagen locates the workflow file in this order:

1. The top-level `entrypoint` key in `.ghagen.yml`, if present
2. `.github/ghagen.workflows.ts`
3. `.github/ghagen.workflows.js`
4. `.github/ghagen.workflows.mjs`
5. `ghagen.workflows.ts`
6. `ghagen.workflows.js`
7. `ghagen.workflows.mjs`
8. `ghagen.config.ts`
9. `ghagen.config.js`
10. `ghagen.config.mjs`

The `entrypoint` value is a path (relative paths resolve against the
`.ghagen.yml` parent directory, i.e. the repo root, not the current working
directory). Use this when your workflow file lives outside the default
locations:

```yaml
# .ghagen.yml
entrypoint: scripts/workflows.ts
```

Within the workflow file, ghagen looks for:

1. A `createApp()` function that returns an `App` instance
2. An `app` variable that is an `App` instance

### Example

```bash
# Use default config detection
npx ghagen synth

# Specify a config file
npx ghagen synth --config workflows/generate.ts
```

## ghagen check-synced

Verify that generated YAML files match the current TypeScript/JavaScript definitions. Fails if any file is stale (see [Exit codes](#exit-codes)).

```bash
npx ghagen check-synced
```

### Options

| Option          | Description                                                 |
| --------------- | ----------------------------------------------------------- |
| `--config PATH` | Path to the configuration file. Defaults to auto-detection. |

This command follows the same config file resolution as `synth`.

### Example

```bash
# Run in CI to catch stale workflows
npx ghagen check-synced

# Check with explicit config
npx ghagen check-synced --config .github/ghagen.workflows.ts
```

### CI usage

Add `ghagen check-synced` to your CI pipeline to ensure that generated YAML files are never out of sync with their TypeScript definitions:

```yaml
- name: Check workflow freshness
  run: npx ghagen check-synced
```

If someone edits a generated YAML file directly instead of updating the TypeScript source, `ghagen check-synced` will fail and the CI run will report the mismatch.

## ghagen deps pin

Pin every `uses:` reference in your workflows to an exact commit SHA, recorded
in `.ghagen.lock.yml`. When a lockfile is present, `ghagen synth`
automatically rewrites `uses:` entries to the pinned SHA on emission, so your
generated YAML is reproducible without hand-editing.

```bash
npx ghagen deps pin           # Resolve any refs missing from the lockfile
npx ghagen deps pin --update  # Re-resolve every entry to the latest SHA
npx ghagen deps pin --prune   # Drop lockfile entries no longer referenced
```

### Options

| Option                | Description                                                                                                                        |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `--config PATH`, `-c` | Path to the configuration file. Defaults to auto-detection.                                                                        |
| `--update`            | Re-resolve every entry to its current SHA, not just the missing ones.                                                              |
| `--prune`             | Remove lockfile entries that are no longer referenced by any workflow.                                                             |
| `--token TOKEN`       | GitHub token used to resolve refs. Defaults to `$GITHUB_TOKEN`, then `$GH_TOKEN`. Unauthenticated requests are limited to 60/hour. |

## ghagen deps check-synced

Verify the lockfile is in sync with the current code. Fails if the lockfile is stale (see [Exit codes](#exit-codes)). Does not make network calls.

```bash
npx ghagen deps check-synced
```

### Options

| Option                | Description                                                                    |
| --------------------- | ------------------------------------------------------------------------------ |
| `--config PATH`, `-c` | Path to the configuration file. Defaults to auto-detection.                    |
| `--prune`             | Also check for lockfile entries that are no longer referenced by any workflow. |

### CI usage

Run `ghagen deps check-synced --prune` in CI to catch PRs that introduce a new
`uses:` without updating the lockfile:

```typescript
step({
  name: "Check lockfile sync",
  run: "npx ghagen deps check-synced --prune",
});
```

`ghagen deps check-synced` does not make network calls, so it doesn't need a GitHub token.

## ghagen deps upgrade

Detect and apply updates to action dependencies in your workflows. By default,
applies updates to source files (version bumps). Use `--check` for a
dry-run report without modifying files.

```bash
npx ghagen deps upgrade                     # Apply available updates to source files
npx ghagen deps upgrade --check             # Report available updates without applying
npx ghagen deps upgrade --check --format json  # Machine-readable JSON report
```

### Options

| Option                | Description                                                                      |
| --------------------- | -------------------------------------------------------------------------------- |
| `--config PATH`, `-c` | Path to the configuration file. Defaults to auto-detection.                      |
| `--check`             | Report available updates without applying changes (dry-run mode).                |
| `--format FORMAT`     | Output format: `json`, `pr-body`, or `issue-body`. Omit for human-readable text. |
| `--mode MODE`         | Detection mode: `versions`, `lockfile`, or `all` (default).                      |
| `--token TOKEN`       | GitHub token used to query tags. Defaults to `$GITHUB_TOKEN`, then `$GH_TOKEN`.  |

### Which keys `--format json` emits

The JSON payload's top-level keys are decided by `--mode` alone, never by what
the run happened to find. A key is present exactly when its stage was asked
for, and its value is `[]` when that stage found nothing.

| `--mode`            | Keys emitted                      |
| ------------------- | --------------------------------- |
| `versions`          | `version_bumps`                   |
| `lockfile`          | `lockfile_stale`                  |
| `all` (the default) | `version_bumps`, `lockfile_stale` |

So `--mode versions --format json` always emits exactly `version_bumps`, and a
consumer can index it unconditionally. Both keys appear together only under
`--mode all`.

`--mode lockfile` reports what it was _asked_ to check, not what it ran: with
`lockfile: null` on the `App` the lockfile stage is skipped entirely, and the
payload is still `{"lockfile_stale": []}`.

The same rule is applied by `renderUpgradeReport`, which this command calls —
the payload is identical whether you go through the CLI or render a report
yourself. The key set is identical in the Python port.

### Which refs count as version tags

Only refs that match ghagen's version-tag grammar are upgrade candidates. A ref
is a version tag when it is an optional prefix (`prefix-` or `prefix/`), an
optional `v`, and dot-separated integers — and every segment's value is at most
`999999999999999`. When a prefix is present the numeric part needs at least two
segments, so `release/v1` stays a branch ref.

| Ref              | Version tag? | Why                                         |
| ---------------- | ------------ | ------------------------------------------- |
| `v4`             | yes          | release `4.0.0` — short forms are padded    |
| `v4.1`           | yes          | release `4.1.0`                             |
| `v1.2.3.4`       | yes          | more than three segments is allowed         |
| `v2.04`          | yes          | release `2.4.0` — leading zeros are numeric |
| `prefix/v1.0.0`  | yes          | prefixed, two or more segments              |
| `release/v1`     | no           | prefixed with one segment — a branch ref    |
| `main`, `latest` | no           | not numeric                                 |
| `v1.2.3-rc1`     | no           | prereleases and build metadata are not tags |

The **canonical release** of a tag is its segments as integers, padded to three
and stripped of trailing zeros beyond the third — so `v1.2.3.0` and `v1.2.3` are
the same version. Two tags are compared by that release, element-wise and then
by length, and only tags sharing the current ref's prefix are considered. The
severity reported for a bump is `major` when the first element changes, `minor`
when the second does, and `patch` otherwise.

The grammar is identical in the Python port — it is the shared contract in
`schema/tag-grammar.yml`, which both ports' suites are driven against.

## ghagen deps update

Do one whole automation run: sweep for updates, perform every write the update
needs, and print what the caller should raise. This is the command the shipped
`check-deps` action runs.

```bash
npx ghagen deps update                          # Apply updates, print a $GITHUB_OUTPUT plan
npx ghagen deps update --dry-run --format json  # Decide everything, write nothing
npx ghagen deps update --output issue           # Raise an issue rather than a PR
```

`deps update` differs from `deps upgrade` in what it returns. `upgrade` reports
what it _found_; `update` reports what to _do_ about it, which is a different
question with a different input: the decision needs the `App`, not just the
report. Callers must read the plan rather than reconstruct it from
`deps upgrade --format json`, because that payload cannot carry
`app.lockfilePath` and so cannot answer the lockfile question.

### Options

| Option                        | Description                                                                         |
| ----------------------------- | ----------------------------------------------------------------------------------- |
| `--config PATH`, `-c`         | Path to the configuration file. Defaults to auto-detection.                         |
| `--mode MODE`                 | Detection mode: `versions`, `lockfile`, or `all` (default).                         |
| `--output OUTPUT`             | What to raise when there is something: `pr` (default) or `issue`.                   |
| `--format FORMAT`             | Plan format: `github` (default, `key=value` lines) or `json`.                       |
| `--branch-prefix PREFIX`      | Prefix for the dated PR branch. Default `ghagen-update/`.                           |
| `--commit-message-prefix STR` | Prefix for the commit subject, e.g. `chore(deps):`. Default empty.                  |
| `--labels LABELS`             | Comma-separated labels for the PR or issue. Split and trimmed for you.              |
| `--body-file PATH`            | Write the PR or issue body to this path. Nothing is written when there is no body.  |
| `--dry-run`                   | Decide everything, write nothing: no source edits, no lockfile write, no body file. |
| `--token TOKEN`               | GitHub token used to query tags. Defaults to `$GITHUB_TOKEN`, then `$GH_TOKEN`.     |

An unknown `--mode`, `--output`, or `--format` value exits `2`, as does a
newline in `--branch-prefix`, `--commit-message-prefix`, or `--labels` — under
`--format github` a newline in a value would forge extra `$GITHUB_OUTPUT` keys.

### The plan

Stdout carries the plan and nothing else, so `--format github` can be a bare
`>> "$GITHUB_OUTPUT"` redirect. Warnings and progress go to stderr. Both
formats carry the same ten fields, in the same order, under the same
snake_case names — snake_case rather than the camelCase of the `UpdatePlan`
interface, because the field names are a cross-port wire contract shared byte
for byte with the Python port.

| Field                 | Meaning                                                                     |
| --------------------- | --------------------------------------------------------------------------- |
| `action`              | `none`, `create-pr`, or `create-issue`.                                     |
| `total_updates`       | Version bumps plus stale lockfile entries.                                  |
| `apply_version_bumps` | Whether newer tags are to be written back into user source.                 |
| `refresh_lockfile`    | Whether the lockfile is to be re-resolved. Always `false` with `lockfile: null`. |
| `branch`              | The dated branch, or empty unless `action` is `create-pr`.                  |
| `title`               | The PR or issue title.                                                      |
| `commit_message`      | The commit subject, prefix already applied.                                 |
| `labels`              | Comma-separated under `github`, an array under `json`.                      |
| `body_format`         | Which `pin/render` format the body is in; empty when there is no body.      |
| `changed`             | Whether anything was written. Always `false` under `--dry-run`.             |

Every field except `changed` is a **decision, not an outcome** — what the run
determined should happen, which under `--dry-run` is exactly what did not. Only
`changed` reports what was actually written, which is why it is the one field
the plan itself does not carry.

`refreshLockfile` is not `lockfileStale.length > 0`. It is `false` whenever the
`App` has no lockfile — `ghagen deps pin` exits `1` on such a project, so a
cascade into it is not harmless extra work — and it is `true` when version
bumps were applied even if no entry was stale, because a bumped ref makes the
lockfile stale by definition.

### Writes

Without `--dry-run` this command modifies the working tree. Version bumps are
written into your source files, and the lockfile is re-resolved when
`refresh_lockfile` is true. That holds for `--output issue` too: the issue
describes updates that have _already_ been applied locally. Use `--dry-run`
when you want the decision without the writes.

## ghagen init

Scaffold a starter configuration file with a minimal CI workflow.

```bash
npx ghagen init
```

### Options

| Option          | Description                                                    |
| --------------- | -------------------------------------------------------------- |
| `--outdir PATH` | Directory to create the config file in. Defaults to `.github`. |

### Example

```bash
# Create .github/ghagen.workflows.ts
npx ghagen init

# Create in a custom directory
npx ghagen init --outdir workflows
```

The generated file contains an `App` instance with a single CI workflow that checks out code and runs a placeholder test command.

## Exit codes

Every command exits with one of three codes. The table is identical in the
Python port — it is the shared contract in `fixtures/cli-exit-codes.yml`,
which both ports' `main()` is tested against.

| Code | Meaning                                                                                                                                                                                                    |
| ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `0`  | The command did what it was asked. Includes both "no updates available" and "updates available" under `deps upgrade --check` and `deps update` — a report is not a failure.                                |
| `1`  | Expected failure: generated files are stale, the lockfile is stale, refs failed to resolve, no config file was found, or the config module raised.                                                         |
| `2`  | Usage error: unknown command, unknown option, missing option argument, invalid option value, or no arguments at all. Framework-detected and hand-validated usage errors are indistinguishable to a caller. |
