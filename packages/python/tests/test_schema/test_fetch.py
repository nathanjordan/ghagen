"""Tests for the schema fetcher."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ghagen.schema.fetch import SCHEMAS, fetch_schema, save_all_schemas, save_schema

SAMPLE_SCHEMA = {"type": "object", "properties": {"name": {"type": "string"}}}


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
        "ghagen.schema.fetch.httpx.get",
        lambda *a, **kw: _mock_response(SAMPLE_SCHEMA),
    )
    result = fetch_schema()
    assert result == SAMPLE_SCHEMA
    assert isinstance(result, dict)


def test_fetch_schema_raises_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "ghagen.schema.fetch.httpx.get",
        lambda *a, **kw: _mock_error_response(),
    )
    with pytest.raises(Exception, match="HTTP 500"):
        fetch_schema()


def test_save_schema_writes_valid_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "ghagen.schema.fetch.httpx.get",
        lambda *a, **kw: _mock_response(SAMPLE_SCHEMA),
    )
    dest = tmp_path / "schema.json"
    save_schema(dest)

    assert dest.exists()
    loaded = json.loads(dest.read_text())
    assert loaded == SAMPLE_SCHEMA


def test_save_schema_creates_parent_dirs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "ghagen.schema.fetch.httpx.get",
        lambda *a, **kw: _mock_response(SAMPLE_SCHEMA),
    )
    dest = tmp_path / "nested" / "dir" / "schema.json"
    save_schema(dest)

    assert dest.exists()


def test_save_schema_deterministic_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    schema = {"z_key": 1, "a_key": 2, "m_key": 3}
    monkeypatch.setattr(
        "ghagen.schema.fetch.httpx.get",
        lambda *a, **kw: _mock_response(schema),
    )

    dest1 = tmp_path / "s1.json"
    dest2 = tmp_path / "s2.json"
    save_schema(dest1)
    save_schema(dest2)

    assert dest1.read_text() == dest2.read_text()
    # Keys should be sorted
    text = dest1.read_text()
    assert text.index('"a_key"') < text.index('"m_key"') < text.index('"z_key"')


def test_save_schema_trailing_newline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "ghagen.schema.fetch.httpx.get",
        lambda *a, **kw: _mock_response(SAMPLE_SCHEMA),
    )
    dest = tmp_path / "schema.json"
    save_schema(dest)

    assert dest.read_text().endswith("\n")


def test_schemas_registry_has_workflow_and_action() -> None:
    """Both workflow and action schemas must be registered."""
    assert "workflow" in SCHEMAS
    assert "action" in SCHEMAS
    assert SCHEMAS["workflow"]["url"].endswith("github-workflow.json")
    assert SCHEMAS["action"]["url"].endswith("github-action.json")
    assert SCHEMAS["workflow"]["filename"] == "workflow_schema.json"
    assert SCHEMAS["action"]["filename"] == "action_schema.json"


def test_fetch_action_schema_uses_action_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``fetch_schema('action')`` hits the action URL, not the workflow one."""
    captured_urls: list[str] = []

    def capture(url: str, *args: object, **kwargs: object) -> MagicMock:
        captured_urls.append(url)
        return _mock_response(SAMPLE_SCHEMA)

    monkeypatch.setattr("ghagen.schema.fetch.httpx.get", capture)
    fetch_schema("action")
    assert len(captured_urls) == 1
    assert captured_urls[0] == SCHEMAS["action"]["url"]


def test_save_all_schemas_writes_both(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``save_all_schemas`` writes one file per registered schema."""
    monkeypatch.setattr(
        "ghagen.schema.fetch.httpx.get",
        lambda *a, **kw: _mock_response(SAMPLE_SCHEMA),
    )

    written = save_all_schemas(tmp_path)
    assert len(written) == len(SCHEMAS)
    assert (tmp_path / "workflow_schema.json").exists()
    assert (tmp_path / "action_schema.json").exists()
    for path in written:
        assert path.read_text().endswith("\n")
