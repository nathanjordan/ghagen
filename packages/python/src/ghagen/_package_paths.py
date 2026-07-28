"""Classify filesystem paths as ghagen-internal vs. user-authored.

Shared by :mod:`ghagen.models._base` (stack-frame attribution for model
factories) and :mod:`ghagen.pin.sources` (deps-upgrade user-file tracking) so a
single ghagen-root computation and predicate serve both — the Python peer of
TypeScript's ``_package_paths.ts``.

The two callers ask the question with different remits, so this module exposes
*two* predicates over one shared root rather than forcing one algorithm on both:

* :func:`is_internal_frame` — stack attribution. A frame is internal when it is
  inside pydantic or the ghagen package; the first non-internal frame is the
  user's call site.
* :func:`is_user_file` — import tracking. A file is user-authored when it is
  neither under ``site-packages``, the ghagen package, nor the stdlib.
"""

from __future__ import annotations

import sysconfig
from pathlib import Path

#: Root of the installed ``ghagen`` package (…/ghagen). ``__file__`` is
#: ``…/ghagen/_package_paths.py``, so its parent is the package directory. Any
#: frame or file inside it is ghagen-internal, regardless of the submodule
#: (models/, emitter/, helpers/, pin/, …).
GHAGEN_ROOT = Path(__file__).resolve().parent


def is_internal_frame(filename: str) -> bool:
    """Return True if ``filename`` is inside pydantic or the ghagen package.

    Used by stack-frame attribution to skip framework frames when locating the
    user's model-construction call site.
    """
    if "pydantic" in Path(filename).parts:
        return True
    try:
        resolved = Path(filename).resolve()
    except (OSError, ValueError):  # pragma: no cover — defensive
        return False
    return resolved == GHAGEN_ROOT or GHAGEN_ROOT in resolved.parents


def is_user_file(path: Path) -> bool:
    """Return True if *path* is a user-authored file (not stdlib/site/ghagen).

    Used by deps-upgrade file tracking to keep the tracked set to files the
    user controls.
    """
    parts = path.parts

    # Exclude site-packages
    if "site-packages" in parts:
        return False

    # Exclude ghagen package files
    try:
        path.relative_to(GHAGEN_ROOT)
        return False
    except ValueError:
        pass

    # Exclude stdlib files
    stdlib_paths = sysconfig.get_paths()
    for key in ("stdlib", "platstdlib", "purelib", "platlib"):
        stdlib_dir = stdlib_paths.get(key)
        if stdlib_dir:
            try:
                path.relative_to(stdlib_dir)
                return False
            except ValueError:
                pass

    return True
