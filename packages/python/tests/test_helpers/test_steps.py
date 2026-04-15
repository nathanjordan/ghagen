"""Tests for step factory functions."""

from __future__ import annotations

from ghagen.helpers.steps import (
    cache,
    checkout,
    download_artifact,
    setup_node,
    setup_python,
    setup_uv,
    upload_artifact,
)
from ghagen.models.step import Step

# --- checkout ---


def test_checkout_defaults():
    step = checkout()
    assert isinstance(step, Step)
    assert step.uses == "actions/checkout@v6"
    assert step.name == "Checkout"
    cm = step.to_commented_map()
    assert cm["with"]["fetch-depth"] == 1


def test_checkout_with_ref():
    step = checkout(ref="main")
    cm = step.to_commented_map()
    assert cm["with"]["ref"] == "main"
    assert cm["with"]["fetch-depth"] == 1


def test_checkout_no_fetch_depth():
    step = checkout(fetch_depth=None)
    cm = step.to_commented_map()
    # with_ should be None (empty after filtering) so 'with' key absent
    assert "with" not in cm


def test_checkout_override_name():
    step = checkout(name="Custom checkout")
    assert step.name == "Custom checkout"


def test_checkout_kwarg_if():
    step = checkout(if_="github.event_name == 'push'")
    cm = step.to_commented_map()
    assert cm["if"] == "github.event_name == 'push'"


def test_checkout_kwarg_env():
    step = checkout(env={"TOKEN": "abc"})
    cm = step.to_commented_map()
    assert cm["env"]["TOKEN"] == "abc"


def test_checkout_extra_with():
    step = checkout(with_={"submodules": "true"})
    cm = step.to_commented_map()
    assert cm["with"]["submodules"] == "true"
    assert cm["with"]["fetch-depth"] == 1


# --- setup_python ---


def test_setup_python_basic():
    step = setup_python("3.12")
    assert isinstance(step, Step)
    assert step.uses == "actions/setup-python@v6"
    assert step.name == "Set up Python"
    cm = step.to_commented_map()
    assert cm["with"]["python-version"] == "3.12"


def test_setup_python_with_cache():
    step = setup_python("3.12", cache="pip")
    cm = step.to_commented_map()
    assert cm["with"]["cache"] == "pip"


def test_setup_python_no_cache():
    step = setup_python("3.12")
    cm = step.to_commented_map()
    assert "cache" not in cm["with"]


# --- setup_node ---


def test_setup_node_basic():
    step = setup_node("20")
    assert isinstance(step, Step)
    assert step.uses == "actions/setup-node@v6"
    assert step.name == "Set up Node.js"
    cm = step.to_commented_map()
    assert cm["with"]["node-version"] == "20"


def test_setup_node_with_cache():
    step = setup_node("20", cache="npm")
    cm = step.to_commented_map()
    assert cm["with"]["cache"] == "npm"


# --- setup_uv ---


def test_setup_uv_defaults():
    step = setup_uv()
    assert isinstance(step, Step)
    assert step.uses == "astral-sh/setup-uv@v7"
    assert step.name == "Set up uv"
    # No version means with_ is None
    assert step.with_ is None


def test_setup_uv_with_version():
    step = setup_uv(version="0.4.0")
    cm = step.to_commented_map()
    assert cm["with"]["version"] == "0.4.0"


# --- cache ---


def test_cache_basic():
    step = cache("pip-key", "~/.cache/pip")
    assert isinstance(step, Step)
    assert step.uses == "actions/cache@v4"
    assert step.name == "Cache"
    cm = step.to_commented_map()
    assert cm["with"]["key"] == "pip-key"
    assert cm["with"]["path"] == "~/.cache/pip"


def test_cache_with_restore_keys_string():
    step = cache("pip-key", "~/.cache/pip", restore_keys="pip-")
    cm = step.to_commented_map()
    assert cm["with"]["restore-keys"] == "pip-"


def test_cache_with_restore_keys_list():
    step = cache("pip-key", "~/.cache/pip", restore_keys=["pip-linux-", "pip-"])
    cm = step.to_commented_map()
    assert cm["with"]["restore-keys"] == "pip-linux-\npip-"


def test_cache_no_restore_keys():
    step = cache("pip-key", "~/.cache/pip")
    cm = step.to_commented_map()
    assert "restore-keys" not in cm["with"]


# --- upload_artifact ---


def test_upload_artifact_basic():
    step = upload_artifact("dist", "dist/")
    assert isinstance(step, Step)
    assert step.uses == "actions/upload-artifact@v4"
    assert step.name == "Upload artifact"
    cm = step.to_commented_map()
    assert cm["with"]["name"] == "dist"
    assert cm["with"]["path"] == "dist/"


# --- download_artifact ---


def test_download_artifact_basic():
    step = download_artifact("dist")
    assert isinstance(step, Step)
    assert step.uses == "actions/download-artifact@v4"
    assert step.name == "Download artifact"
    cm = step.to_commented_map()
    assert cm["with"]["name"] == "dist"


def test_download_artifact_with_path():
    step = download_artifact("dist", path="./artifacts")
    cm = step.to_commented_map()
    assert cm["with"]["path"] == "./artifacts"


def test_download_artifact_no_path():
    step = download_artifact("dist")
    cm = step.to_commented_map()
    assert "path" not in cm["with"]


# --- cross-cutting ---


def test_all_factories_return_step():
    factories = [
        checkout(),
        setup_python("3.12"),
        setup_node("20"),
        setup_uv(),
        cache("key", "path"),
        upload_artifact("name", "path"),
        download_artifact("name"),
    ]
    for step in factories:
        assert isinstance(step, Step)


def test_comment_kwarg():
    step = checkout(comment="Check out the code")
    assert step.comment == "Check out the code"


def test_id_kwarg():
    step = checkout(id="checkout-step")
    assert step.id == "checkout-step"
