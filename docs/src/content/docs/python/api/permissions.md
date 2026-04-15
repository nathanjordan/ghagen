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
| `checks`              | `PermissionLevel \| Raw[str] \| None` | `None`  | Permission for the `checks` scope.                                                   |
| `contents`            | `PermissionLevel \| Raw[str] \| None` | `None`  | Permission for the `contents` scope.                                                 |
| `deployments`         | `PermissionLevel \| Raw[str] \| None` | `None`  | Permission for the `deployments` scope.                                              |
| `discussions`         | `PermissionLevel \| Raw[str] \| None` | `None`  | Permission for the `discussions` scope.                                              |
| `id_token`            | `PermissionLevel \| Raw[str] \| None` | `None`  | Permission for the `id-token` scope. Serialized as `id-token`.                       |
| `issues`              | `PermissionLevel \| Raw[str] \| None` | `None`  | Permission for the `issues` scope.                                                   |
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

A type alias used for the `Workflow.permissions` field, which accepts multiple forms:

```python
PermissionsValue = Permissions | Literal["read-all", "write-all"] | Raw[str] | dict[str, str]
```

This allows setting permissions as:

- A `Permissions` object for fine-grained control
- `"read-all"` or `"write-all"` for blanket permissions
- A `Raw[str]` for arbitrary string values
- A plain `dict[str, str]` for quick inline definitions

## Workflow-level shorthand

At the workflow level, you can pass a string shorthand instead of a full `Permissions` object:

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
```
