"""Collect all pinnable ``uses:`` references from an App."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ghagen.pin.sites import iter_uses_sites

if TYPE_CHECKING:
    from ghagen.app import App
    from ghagen.pin.uses import UsesRef


def collect_uses_refs(app: App) -> list[UsesRef]:
    """Return every pinnable ``uses:`` ref across the app, parsed and deduped.

    Iterates the :class:`~ghagen.pin.sites.UsesSite` of every Document (the
    single traversal policy — see :func:`~ghagen.pin.sites.iter_uses_sites`)
    and keeps the refs that are **Pinnable**.

    Dedup is by full ref string (:attr:`~ghagen.pin.uses.UsesRef.uses`) — the
    same key the lockfile uses, so a collected ref lines up with its lockfile
    entry by construction. The result is a ``list`` sorted by ``uses``, so
    engine consumers get deterministic iteration without re-sorting.

    Parse failure and the pinnable filter live in
    :func:`~ghagen.pin.sites.iter_uses_sites` / :class:`~ghagen.pin.uses.UsesRef`;
    a ref that reaches this list is guaranteed parseable and Pinnable. Local
    path refs (``./…``), docker image refs (``docker://…``), and refs already
    pinned to a 40-char SHA are skipped.
    """
    by_key: dict[str, UsesRef] = {}

    for document in app.documents():
        for site in iter_uses_sites(document):
            if site.ref.is_pinnable:
                by_key[site.uses] = site.ref

    return [by_key[k] for k in sorted(by_key)]
