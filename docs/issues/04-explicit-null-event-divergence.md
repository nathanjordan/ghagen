# Explicit-null trigger fields diverge across ports

**Status:** open — noted by proposal 06 implementation

`On(create=None)` (Python) is dropped by `exclude_none` → `on: {}`; TS `on({ create: null })`
keeps the key and a plain-null map value renders in the ugly `? create` explicit-key form. No
fixture exercises it. Decide one semantic (probably: drop in both), implement via spec rule.
