"""Canonical parsed ``uses:`` action reference.

One type replaces the scattered ``@``-splits and the divergent pinnability
predicate that used to live in :mod:`ghagen.pin.collect`,
:mod:`ghagen.pin.transform`, :mod:`ghagen.pin.resolve`, and the deps CLI.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# 40-character lowercase hex — already a commit SHA.
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class UsesRef:
    """A parsed ``owner/repo[/path]@ref`` action reference.

    Knows whether it is **Pinnable** — remote (not ``./`` or ``docker://``)
    and not already written as a commit SHA.
    """

    owner: str
    repo: str
    path: str | None
    ref: str

    @classmethod
    def parse(cls, uses: str) -> UsesRef | None:
        """Parse an ``owner/repo[/path]@ref`` string, or return ``None``.

        Returns ``None`` for references that are unpinnable by *shape*:
        local paths (``./…``), docker images (``docker://…``), or strings
        with no ``@ref`` component. Otherwise splits into
        ``owner/repo[/path]@ref`` where *path* is everything between the
        repo and the ``@`` (and may itself contain ``/``).
        """
        if uses.startswith("./") or uses.startswith("docker://"):
            return None
        if "@" not in uses:
            return None

        action_part, ref = uses.rsplit("@", 1)
        parts = action_part.split("/", 2)
        if len(parts) < 2:
            return None

        owner = parts[0]
        repo = parts[1]
        path = parts[2] if len(parts) > 2 else None
        return cls(owner=owner, repo=repo, path=path, ref=ref)

    @property
    def ref_is_sha(self) -> bool:
        """Return ``True`` if ``ref`` is a 40-character lowercase hex SHA."""
        return _SHA_RE.match(self.ref) is not None

    @property
    def is_pinnable(self) -> bool:
        """Return ``True`` if this ref can be pinned (not already a SHA)."""
        return not self.ref_is_sha

    @property
    def action_part(self) -> str:
        """Return the ``owner/repo[/path]`` portion (without ``@ref``)."""
        if self.path is not None:
            return f"{self.owner}/{self.repo}/{self.path}"
        return f"{self.owner}/{self.repo}"

    def with_sha(self, sha: str) -> str:
        """Rebuild the reference as ``owner/repo[/path]@sha``."""
        return f"{self.action_part}@{sha}"
