"""Error type for GitHub Action ref resolution.

The networked resolution logic lives in :mod:`ghagen.pin.github`
(:class:`~ghagen.pin.github.GitHubClient`).  ``ResolveError`` stays here as a
dependency-free leaf so both the client and its transports can import it
without a cycle.
"""

from __future__ import annotations


class ResolveError(Exception):
    """Raised when a ref cannot be resolved to a commit SHA."""
