"""Dev-only schema pipeline orchestrator for ghagen (see ADR-0003).

This is **maintainer tooling**, not a shipped runtime feature. It is the single
home for the three-verb schema pipeline that keeps the canonical JSON Schema
Snapshot (``schema/*.json``) and the generated TypeScript reference types
(``packages/typescript/src/schema/*.generated.ts``) coherent:

``sync``
    Network. Fetch the upstream schemas from SchemaStore and overwrite the
    committed Snapshot. The only verb that touches the network; run weekly by
    the drift job or by a maintainer refreshing the Snapshot.
``generate``
    Offline. Regenerate the TypeScript reference types from the committed
    Snapshot by shelling the TS codegen. A pure function of the Snapshot.
``check``
    Offline, CI-safe. ``generate`` then assert ``git`` is clean for the
    generated types -- the staleness guard that repairs ADR-0003's
    author-conformance guarantee. Never fetches, so it is deterministic and
    runs on every PR.

The single canonical Snapshot stays at the repo-root ``schema/`` directory; only
the tooling lives here, not the data. No Python models are generated -- the
hand-written Pydantic models are the public API and the schema is a conformance
target (see ADR-0003).
"""

from __future__ import annotations
