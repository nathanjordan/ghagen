# Synthesis pipeline and transform ordering

**Status:** accepted (2026-07-28)

`synth.render(items, transforms, *, header, auto_dedent)` (Python) / `render(items, transforms,
options)` (TypeScript) is the single Document→text synthesis pipeline: deep-copy each Document,
fold the Transforms over the copy in list order, emit to YAML text. `App.synth` and `App.check`
are thin consumers that differ only in write-vs-diff; the pipeline itself never touches the
filesystem. The TypeScript path is fully synchronous.

**Transforms apply in list order, and the pin Transform runs last** — after user Transforms. User
Transforms therefore see authored refs (never SHAs), and a `uses:` ref a user Transform injects or
rewrites gets pinned like any authored ref.

## Why

`synth` and `check` previously duplicated the build-transforms → clone → fold → emit prefix with
two independently assembled emit-option objects, and the pin-first ordering was implicit and
untested. Pin-first also meant user Transforms observed pinned SHAs — surprising, and it silently
exempted user-injected refs from pinning.

## Consequences

- A user Transform that injects a remote, Pinnable ref whose entry is missing from the Lockfile
  makes synthesis fail with the pin transform's missing-entry error (previously the ref passed
  through unpinned). Run `ghagen deps pin` to add the entry.
- The ordering contract is part of the pipeline interface and is tested at the render seam in both
  ports.
