"""Collect all pinnable ``uses:`` references from an App."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ghagen.pin.sites import iter_uses_sites

if TYPE_CHECKING:
    from ghagen.app import App


def collect_uses_refs(app: App) -> set[str]:
    """Walk every registered Document in *app* and return pinnable ``uses:`` strings.

    Iterates the :class:`~ghagen.pin.sites.UsesSite` of every Document (the
    single traversal policy — see :func:`~ghagen.pin.sites.iter_uses_sites`)
    and keeps the refs that are **Pinnable**.

    Skips local path refs (``./…``), docker image refs (``docker://…``), and
    refs already pinned to a 40-char SHA — see :meth:`UsesRef.is_pinnable`.
    """
    refs: set[str] = set()

    for document in app.documents():
        for site in iter_uses_sites(document):
            if site.ref.is_pinnable:
                refs.add(site.uses)

    return refs
