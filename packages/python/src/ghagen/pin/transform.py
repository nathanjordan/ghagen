"""PinTransform — model-level transform that applies lockfile SHAs.

Replaces ``Step.uses`` and ``Job.uses`` values with their pinned SHAs from
the lockfile, attaching the original ref as a YAML end-of-line comment. The
"which models carry ``uses``, and how to reach it through a Commented wrapper"
policy lives in :mod:`ghagen.pin.sites`; this module only decides *what* SHA
to write.
"""

from __future__ import annotations

from ghagen.models.action import Action
from ghagen.models.workflow import Workflow
from ghagen.pin.lockfile import Lockfile
from ghagen.pin.sites import iter_uses_sites


class PinError(Exception):
    """Raised when a ``uses:`` ref has no lockfile entry during synthesis."""


class PinTransform:
    """Apply lockfile SHA pins to ``uses:`` references in models.

    This transform is automatically registered by :class:`~ghagen.App`
    when a lockfile is present.
    """

    def __init__(self, lockfile: Lockfile) -> None:
        self._lockfile = lockfile

    def __call__(self, item: Workflow | Action) -> Workflow | Action:
        """Pin every pinnable ``uses:`` site in *item* to its lockfile SHA.

        Refs that are not pinnable — local paths, docker images, malformed
        refs, or refs already written as a SHA — are skipped and never consult
        the lockfile. Only a pinnable ref missing from the lockfile raises
        :class:`PinError`.
        """
        for site in iter_uses_sites(item):
            if not site.ref.is_pinnable:
                continue
            entry = self._lockfile.get(site.uses)
            if entry is None:
                raise PinError(
                    f"No lockfile entry for '{site.uses}'. "
                    "Run `ghagen pin` to resolve it."
                )
            site.replace(site.ref.with_sha(entry.sha))
        return item
