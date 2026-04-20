---
title: Linting
description: Rule-based checks for ghagen workflow definitions
---

`ghagen lint` runs rule-based checks against your workflow definitions
**at the TypeScript source level**. Violations point at the exact line in
your workflow config file that constructed the offending model -- not a
line number in a generated file -- so you can jump straight to the fix.

This is complementary to tools like
[actionlint](https://github.com/rhysd/actionlint), which lints the
generated `.yml` files. Use actionlint for YAML-level concerns (shell
syntax, action input types) and `ghagen lint` for ghagen-idiomatic
concerns.

## Running

```bash
# Lint using your .github/ghagen.workflows.ts
npx ghagen lint

# List all available rules and exit
npx ghagen lint --list-rules

# JSON output for scripts and CI
npx ghagen lint --format=json

# GitHub Actions annotations (for use inside CI)
npx ghagen lint --format=github

# Disable a rule from the command line
npx ghagen lint --disable missing-timeout
```

Exit codes:

| Code | Meaning                                                      |
| ---- | ------------------------------------------------------------ |
| `0`  | No error-severity violations (warnings may still be present) |
| `1`  | At least one error-severity violation found                  |
| `2`  | Configuration error (malformed TOML, unknown severity, etc.) |

## Built-in rules

### `missing-permissions` (warning)

Flags workflows with no top-level `permissions` set and no per-job
`permissions` either. GitHub's default `GITHUB_TOKEN` has broad write
access; setting an explicit `permissions` block is the OWASP-recommended
hardening.

```typescript
// Triggers the rule
workflow({
  name: "ci",
  on: { push: pushTrigger({ branches: ["main"] }) },
  jobs: {
    build: job({ runsOn: "ubuntu-latest", steps: [...] }),
  },
})

// Passes
workflow({
  name: "ci",
  on: { push: pushTrigger({ branches: ["main"] }) },
  permissions: { contents: "read" },
  jobs: {
    build: job({ runsOn: "ubuntu-latest", steps: [...] }),
  },
})
```

### `missing-timeout` (warning)

Flags jobs without `timeoutMinutes`. GitHub's default job timeout is 6
hours; setting an explicit shorter timeout bounds runaway builds. Jobs
that reference a reusable workflow via `uses` are skipped (their timeout
is owned by the reusable workflow).

```typescript
// Triggers the rule
job({ runsOn: "ubuntu-latest", steps: [...] })

// Passes
job({ runsOn: "ubuntu-latest", timeoutMinutes: 10, steps: [...] })
```

### `duplicate-step-ids` (error)

Flags two or more steps within a single job that share the same `id`.
GitHub Actions requires step ids to be unique within a job; duplicates
break `steps.<id>.outputs` references because the expression silently
resolves to just one of the matching steps. Step ids are scoped per-job,
so the same id in two different jobs is fine.

Severity is `error` (not warning) because this is a correctness bug, not
a hardening concern -- `ghagen lint` exits with code 1 when any
duplicates are found.

```typescript
// Triggers the rule
job({
  runsOn: "ubuntu-latest",
  steps: [
    step({ id: "build", run: "make" }),
    step({ id: "build", run: "make test" }),  // duplicate!
  ],
})

// Passes
job({
  runsOn: "ubuntu-latest",
  steps: [
    step({ id: "build", run: "make" }),
    step({ id: "test", run: "make test" }),
  ],
})
```

## Configuration

Lint behavior is configured via a TOML file or `package.json`. Two
locations are checked, in precedence order:

1. **`.github/ghagen.toml`** (preferred -- lives next to your workflow config)
2. **`package.json`** `"ghagen": { "lint": {...} }` section (fallback for Node.js projects)

If both exist, `.github/ghagen.toml` wins and a warning is printed to
stderr naming which file was used.

### Example `.github/ghagen.toml`

```toml
[lint]
# Disable specific rules by ID
disable = ["missing-timeout"]

[lint.severity]
# Override the default severity of a rule
missing-permissions = "error"
```

### Example `package.json` fallback

```json
{
  "ghagen": {
    "lint": {
      "disable": ["missing-timeout"],
      "severity": {
        "missing-permissions": "error"
      }
    }
  }
}
```

CLI flags layer on top of the config file:

```bash
# Union with any disables in the config file
npx ghagen lint --disable missing-permissions
```

## CI integration

Add `ghagen lint` to your pipeline with `--format=github` to get inline
PR annotations:

```typescript
import { job, step } from "@ghagen/ghagen";

job({
  name: "Lint",
  runsOn: "ubuntu-latest",
  timeoutMinutes: 10,
  steps: [
    step({ name: "Checkout", uses: "actions/checkout@v6" }),
    step({ name: "Set up Node", uses: "actions/setup-node@v4" }),
    step({ name: "Install", run: "npm ci" }),
    step({
      name: "ghagen lint",
      run: "npx ghagen lint --format=github",
    }),
  ],
})
```

## What's not covered

The following are intentionally out of scope for v1:

- **YAML-level linting** -- use `actionlint` for that.
- **User-defined rules** -- all rules are built-in. A public rule API may
  come later once the built-in rule shape is proven.
