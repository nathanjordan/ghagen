"""Exit-code fixture: a config module that raises at import time.

Discovered by the Python port via ``CONFIG_SEARCH_PATHS``
(``.github/ghagen_workflows.py``). The TypeScript port never sees this file --
its own search paths are disjoint -- so the sibling ``ghagen.workflows.ts``
is the TypeScript half of the same fixture.

Deliberately raises a plain ``RuntimeError``: the contract row this backs
(``config-module-raises``) is about an *arbitrary* exception escaping a
command, not about any error type the CLI knows.
"""

raise RuntimeError("ghagen exit-code fixture: the config module raised")
