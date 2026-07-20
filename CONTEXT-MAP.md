# Context Map

ghagen generates GitHub Actions YAML from a real programming language. It ships two
implementations that model **one shared domain** — they are language *ports*, not distinct
subdomains — so their glossaries are intentionally mirrored. Each package's `CONTEXT.md` carries
the same domain vocabulary plus a short "surface notes" section for language-idiom differences.

## Contexts

- [Python](./packages/python/CONTEXT.md) — the `ghagen` Python package (Pydantic models, method-based API)
- [TypeScript](./packages/typescript/CONTEXT.md) — the TypeScript/JavaScript package (factory functions, free-function serializers)

## Relationships

- **Python ↔ TypeScript**: feature parity is a project mandate. The *invariants* stay in lockstep
  even where the *surface* differs by language idiom (Python methods vs TypeScript free functions).
- **Shared on-disk formats**: both emit the same YAML and read/write the same `.ghagen.lock.yml`
  lockfile (snake_case keys for cross-language interop) and the same canonical schema snapshot.

## Architectural decisions

System-wide decisions live in [`docs/adr/`](./docs/adr/). Start with:

- ADR-0001 — Document serialization seam
- ADR-0002 — No construction-time config globals
- ADR-0003 — Schema sync is dev-only; Python conformance is test-based
