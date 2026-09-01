---
title: Permissions
description: Model for configuring GITHUB_TOKEN permission scopes at workflow or job level.
---

The `Permissions` class controls the access levels for each `GITHUB_TOKEN` scope. It can be used at the workflow level or on individual jobs.

## Permissions

Each scope can be set to `"read"`, `"write"`, or `"none"` using the `PermissionLevel` enum. Only set the scopes you need; unset scopes are omitted from the output.

```python
from ghagen.models.permissions import Permissions
from ghagen.models.common import PermissionLevel

permissions = Permissions(
    contents=PermissionLevel.READ,
    pull_requests=PermissionLevel.WRITE,
    id_token=PermissionLevel.WRITE,
)
```

### Parameters

| Parameter             | Type                                  | Default | Description                                                                          |
| --------------------- | ------------------------------------- | ------- | ------------------------------------------------------------------------------------ |
| `actions`             | `PermissionLevel \| Raw[str] \| None` | `None`  | Permission for the `actions` scope.                                                  |
| `artifact_metadata`   | `PermissionLevel \| Raw[str] \| None` | `None`  | Permission for the `artifact-metadata` scope. Serialized as `artifact-metadata`.     |
| `attestations`        | `PermissionLevel \| Raw[str] \| None` | `None`  | Permission for the `attestations` scope.                                             |
| `checks`              | `PermissionLevel \| Raw[str] \| None` | `None`  | Permission for the `checks` scope.                                                   |
| `contents`            | `PermissionLevel \| Raw[str] \| None` | `None`  | Permission for the `contents` scope.                                                 |
| `deployments`         | `PermissionLevel \| Raw[str] \| None` | `None`  | Permission for the `deployments` scope.                                              |
| `discussions`         | `PermissionLevel \| Raw[str] \| None` | `None`  | Permission for the `discussions` scope.                                              |
| `id_token`            | `PermissionLevel \| Raw[str] \| None` | `None`  | Permission for the `id-token` scope. Serialized as `id-token`.                       |
| `issues`              | `PermissionLevel \| Raw[str] \| None` | `None`  | Permission for the `issues` scope.                                                   |
| `models`              | `PermissionLevel \| Raw[str] \| None` | `None`  | Permission for the `models` scope. GitHub accepts only `read` or `none` here.        |
| `packages`            | `PermissionLevel \| Raw[str] \| None` | `None`  | Permission for the `packages` scope.                                                 |
| `pages`               | `PermissionLevel \| Raw[str] \| None` | `None`  | Permission for the `pages` scope.                                                    |
| `pull_requests`       | `PermissionLevel \| Raw[str] \| None` | `None`  | Permission for the `pull-requests` scope. Serialized as `pull-requests`.             |
| `repository_projects` | `PermissionLevel \| Raw[str] \| None` | `None`  | Permission for the `repository-projects` scope. Serialized as `repository-projects`. |
| `security_events`     | `PermissionLevel \| Raw[str] \| None` | `None`  | Permission for the `security-events` scope. Serialized as `security-events`.         |
| `statuses`            | `PermissionLevel \| Raw[str] \| None` | `None`  | Permission for the `statuses` scope.                                                 |

## PermissionLevel

An enum of valid permission access levels.

```python
from ghagen.models.common import PermissionLevel
```

| Value                   | String    |
| ----------------------- | --------- |
| `PermissionLevel.READ`  | `"read"`  |
| `PermissionLevel.WRITE` | `"write"` |
| `PermissionLevel.NONE`  | `"none"`  |

## PermissionsValue

The type of **both** `Workflow.permissions` and `Job.permissions`. The canonical
schema gives the two fields one `$ref` to the same node, so ghagen gives them one
alias:

```python
from ghagen import PermissionsValue

PermissionsValue = OrRaw[Permissions | Literal["read-all", "write-all"] | Raw[str]]
```

That admits:

- a `Permissions` object, for fine-grained control;
- `"read-all"` or `"write-all"` — the blanket shorthand, a closed two-member set;
- a `Raw[str]` to emit a string the closed set does not contain;
- a `CommentedMap` (the `OrRaw` arm), the standard escape hatch for a
  hand-assembled mapping with comments attached.

A plain `dict[str, str]` is **not** accepted; build a `Permissions`, or reach for
`raw()` / a `CommentedMap` if you need something the model cannot express. The
accepted and rejected values are pinned for both ports by the `job.permissions` and
`workflow.permissions` rows of `schema/conformance-inputs.yml`.

The TypeScript peer is `PermissionsValue` in `models/permissions.ts`, exported from
the package root.

## String shorthand

Anywhere `permissions` is accepted — on the workflow and on a job alike — you can pass the
string shorthand instead of a full `Permissions` object. It emits as a bare scalar
(`permissions: read-all`), never as a mapping:

```python
from ghagen import Workflow

# Blanket read-only
workflow = Workflow(
    name="CI",
    permissions="read-all",
    # ...
)

# Fine-grained
workflow = Workflow(
    name="CI",
    permissions=Permissions(contents=PermissionLevel.READ),
    # ...
)

# Same union on a job
job = Job(runs_on="ubuntu-latest", permissions="write-all", steps=[...])
```
