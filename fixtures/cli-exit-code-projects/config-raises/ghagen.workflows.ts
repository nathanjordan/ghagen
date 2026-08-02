/**
 * Exit-code fixture: a config module that throws at import time.
 *
 * Discovered by the TypeScript port via `CONFIG_SEARCH_PATHS`
 * (`ghagen.workflows.ts`). The Python port never sees this file -- its own
 * search paths are disjoint -- so the sibling `.github/ghagen_workflows.py`
 * is the Python half of the same fixture.
 *
 * Imports nothing on purpose: the fixture is copied into a temp directory
 * where `@ghagen/ghagen` would not resolve, and throwing before any import
 * keeps the row independent of module resolution.
 */

throw new Error("ghagen exit-code fixture: the config module raised");
