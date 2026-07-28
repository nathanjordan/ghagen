"""Tests for the dev-only schema fetcher (``ghagen_schema.sync``)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from ghagen_schema import sync
from ghagen_schema.manifest import ManifestEntry, load_manifest
from ghagen_schema.sync import fetch_schema, save_all_schemas, save_schema

SAMPLE_SCHEMA = {"type": "object", "properties": {"name": {"type": "string"}}}

_WORKFLOW = ManifestEntry(
    name="workflow",
    url="https://json.schemastore.org/github-workflow.json",
    filename="workflow_schema.json",
)
_ACTION = ManifestEntry(
    name="action",
    url="https://json.schemastore.org/github-action.json",
    filename="action_schema.json",
)


def _mock_response(data: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = data
    resp.raise_for_status.return_value = None
    return resp


def _mock_error_response() -> MagicMock:
    resp = MagicMock()
    resp.status_code = 500
    resp.raise_for_status.side_effect = Exception("HTTP 500")
    return resp


def test_fetch_schema_returns_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sync.httpx,
        "get",
        lambda *a, **kw: _mock_response(SAMPLE_SCHEMA),
    )
    result = fetch_schema(_WORKFLOW)
    assert result == SAMPLE_SCHEMA
    assert isinstance(result, dict)


def test_fetch_schema_raises_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sync.httpx,
        "get",
        lambda *a, **kw: _mock_error_response(),
    )
    with pytest.raises(Exception, match="HTTP 500"):
        fetch_schema(_WORKFLOW)


def test_save_schema_writes_valid_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        sync.httpx,
        "get",
        lambda *a, **kw: _mock_response(SAMPLE_SCHEMA),
    )
    dest = save_schema(_WORKFLOW, tmp_path)

    assert dest == tmp_path / "workflow_schema.json"
    assert dest.exists()
    loaded = json.loads(dest.read_text())
    assert loaded == SAMPLE_SCHEMA


def test_save_schema_creates_parent_dirs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        sync.httpx,
        "get",
        lambda *a, **kw: _mock_response(SAMPLE_SCHEMA),
    )
    nested = tmp_path / "nested" / "dir"
    dest = save_schema(_WORKFLOW, nested)

    assert dest.exists()


def test_save_schema_deterministic_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    schema = {"z_key": 1, "a_key": 2, "m_key": 3}
    monkeypatch.setattr(
        sync.httpx,
        "get",
        lambda *a, **kw: _mock_response(schema),
    )

    dest1 = save_schema(_WORKFLOW, tmp_path / "one")
    dest2 = save_schema(_WORKFLOW, tmp_path / "two")

    assert dest1.read_text() == dest2.read_text()
    # Keys should be sorted
    text = dest1.read_text()
    assert text.index('"a_key"') < text.index('"m_key"') < text.index('"z_key"')


def test_save_schema_trailing_newline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        sync.httpx,
        "get",
        lambda *a, **kw: _mock_response(SAMPLE_SCHEMA),
    )
    dest = save_schema(_WORKFLOW, tmp_path)

    assert dest.read_text().endswith("\n")


def test_manifest_has_workflow_and_action() -> None:
    """Both workflow and action schemas must be registered."""
    entries = {e.name: e for e in load_manifest()}
    assert "workflow" in entries
    assert "action" in entries
    assert entries["workflow"].url.endswith("github-workflow.json")
    assert entries["action"].url.endswith("github-action.json")
    assert entries["workflow"].filename == "workflow_schema.json"
    assert entries["action"].filename == "action_schema.json"


def test_fetch_action_schema_uses_action_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``fetch_schema`` hits the entry's URL, not any other."""
    captured_urls: list[str] = []

    def capture(url: str, *args: object, **kwargs: object) -> MagicMock:
        captured_urls.append(url)
        return _mock_response(SAMPLE_SCHEMA)

    monkeypatch.setattr(sync.httpx, "get", capture)
    fetch_schema(_ACTION)
    assert len(captured_urls) == 1
    assert captured_urls[0] == _ACTION.url


def test_save_all_schemas_writes_both(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``save_all_schemas`` writes one file per registered schema."""
    monkeypatch.setattr(
        sync.httpx,
        "get",
        lambda *a, **kw: _mock_response(SAMPLE_SCHEMA),
    )

    written = save_all_schemas(tmp_path)
    assert len(written) == len(load_manifest())
    assert (tmp_path / "workflow_schema.json").exists()
    assert (tmp_path / "action_schema.json").exists()
    for path in written:
        assert path.read_text().endswith("\n")
