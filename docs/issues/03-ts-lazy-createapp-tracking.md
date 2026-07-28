# TS: modules imported lazily inside createApp() are not tracked

**Status:** open — pre-existing, surfaced in round 1 review

TS resolves the App after the jiti cache-diff window, so a helper dynamically imported inside
`createApp()` never enters the tracked file set and its `uses:` refs are silently not rewritten by
`deps upgrade` (ADR-0004's defended failure mode). Python includes App resolution in its snapshot
window and tracks these. Options: move TS resolution inside the diff window, or document the
limitation. Parity gap either way.
