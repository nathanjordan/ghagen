"""Resolve GitHub Action refs to commit SHAs via the GitHub REST API.

Uses ``urllib.request`` (stdlib) to avoid adding a third-party HTTP
dependency.  Supports both lightweight tags and annotated tags
(dereferences tag objects to their underlying commit).
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass


class ResolveError(Exception):
    """Raised when a ref cannot be resolved to a commit SHA."""


@dataclass(frozen=True)
class _ParsedUses:
    """Parsed components of an ``owner/repo[/path]@ref`` string."""

    owner: str
    repo: str
    path: str | None
    ref: str


def parse_uses(uses: str) -> _ParsedUses:
    """Parse an ``owner/repo[/path]@ref`` string into components.

    Raises:
        ValueError: If the string cannot be parsed.
    """
    if "@" not in uses:
        raise ValueError(f"No @ref in uses string: {uses!r}")

    action_part, ref = uses.rsplit("@", 1)
    parts = action_part.split("/", 2)
    if len(parts) < 2:
        raise ValueError(f"Cannot parse owner/repo from: {uses!r}")

    owner = parts[0]
    repo = parts[1]
    path = parts[2] if len(parts) > 2 else None
    return _ParsedUses(owner=owner, repo=repo, path=path, ref=ref)


def resolve_ref(
    owner: str,
    repo: str,
    ref: str,
    *,
    token: str | None = None,
) -> str:
    """Resolve a git ref to a commit SHA via the GitHub API.

    Tries ``tags/{ref}`` first, then ``heads/{ref}``.  For annotated
    tags the tag object is dereferenced to the underlying commit.

    Args:
        owner: Repository owner (e.g. ``"actions"``).
        repo: Repository name (e.g. ``"checkout"``).
        ref: Git ref (e.g. ``"v4"``, ``"main"``).
        token: Optional GitHub personal access token.

    Returns:
        A 40-character commit SHA.

    Raises:
        ResolveError: If the ref cannot be resolved.
    """
    for prefix in ("tags", "heads"):
        url = f"https://api.github.com/repos/{owner}/{repo}/git/ref/{prefix}/{ref}"
        try:
            data = _api_get(url, token=token)
        except _NotFoundError:
            continue

        obj = data["object"]
        sha = obj["sha"]

        # Annotated tags point to a "tag" object — dereference to commit.
        if obj["type"] == "tag":
            sha = _dereference_tag(owner, repo, sha, token=token)

        return sha

    raise ResolveError(
        f"Could not resolve ref '{ref}' for {owner}/{repo}. "
        "Tried tags/ and heads/ — neither exists."
    )


class _NotFoundError(Exception):
    pass


def _api_get(url: str, *, token: str | None = None) -> dict:
    """Make a GET request to the GitHub API and return parsed JSON."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "ghagen-pin",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, headers=headers)  # noqa: S310
    try:
        with urllib.request.urlopen(req) as resp:  # noqa: S310
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise _NotFoundError from exc
        if exc.code == 403:
            _warn_rate_limit(exc)
        raise ResolveError(
            f"GitHub API error {exc.code} for {url}: {exc.reason}"
        ) from exc
    except urllib.error.URLError as exc:
        raise ResolveError(f"Network error reaching GitHub API: {exc}") from exc


def _dereference_tag(
    owner: str, repo: str, tag_sha: str, *, token: str | None = None
) -> str:
    """Dereference an annotated tag object to its underlying commit SHA."""
    url = f"https://api.github.com/repos/{owner}/{repo}/git/tags/{tag_sha}"
    data = _api_get(url, token=token)
    obj = data.get("object", {})
    if obj.get("type") == "commit":
        return obj["sha"]
    raise ResolveError(
        f"Tag {tag_sha} in {owner}/{repo} does not point to a commit "
        f"(type={obj.get('type')!r})"
    )


def _warn_rate_limit(exc: urllib.error.HTTPError) -> None:
    """Print a warning about rate limiting."""
    remaining = exc.headers.get("X-RateLimit-Remaining", "?")
    print(
        f"warning: GitHub API rate limit hit (remaining={remaining}). "
        "Set $GITHUB_TOKEN or use --token for higher limits.",
        file=sys.stderr,
    )
