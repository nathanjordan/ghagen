# No construction-time config globals

**Status:** accepted

Project options that affect YAML output (notably `auto_dedent`) are applied at **serialization
time** and threaded explicitly — as an `auto_dedent`/`autoDedent` keyword argument read from
`self._auto_dedent`/`this.autoDedent` on the `App.synth` path, and through a
`to_yaml(auto_dedent=...)` parameter on the standalone path. Model-specific output quirks (e.g. the
`On` trigger's `schedule` reshape and empty `workflow_dispatch` → null) are normalized at
**construction time** via validators/factories. No module-level mutable global carries configuration.

## Why

`auto_dedent` was a module-level global set by `App.__init__` and read by the `Step` validator at
construction time, so a `Step` built before its `App` dedented differently than one built after —
action-at-a-distance with a thread-safety hazard. `auto_dedent` only affects YAML *output*, so
applying it at output time removes the temporal coupling and makes the behavior testable by
parameter instead of by mutating and restoring a global.

## Consequences

`step.run` (and the TypeScript step's `run` data) now holds the **raw** string until emission
rather than being dedented at construction. Code that inspects `run` before synthesis sees the
undedented value. The public `setAutoDedent` / `getAutoDedent` exports (TypeScript) are removed.
