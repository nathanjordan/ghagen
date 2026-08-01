"""``ghagen init`` scaffolds the workflow both ports agree on.

The two templates are hand-written source strings that nothing compared, and
they drifted: the TypeScript one set ``timeoutMinutes: 10`` and the Python one
set no timeout at all. This drives the real scaffold through ``main()``, loads
the file it wrote, and compares its emission byte-for-byte against the shared
oracle in ``fixtures/expected/`` -- the same oracle, and the same
``header=None`` shape, that the snapshot suites use. The TypeScript mirror is
``packages/typescript/src/cli/init-scaffold.test.ts``, which asserts against
the *same* fixture file; that is what makes this a parity test rather than two
independent goldens.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from ghagen_schema.paths import FIXTURES_DIR

from ghagen.app import App
from ghagen.cli.main import main

_FIXTURE = FIXTURES_DIR / "expected" / "init_scaffold.yml"


def _load_app(config_path: Path) -> App:
    """Import the scaffolded module and return its ``app``."""
    spec = importlib.util.spec_from_file_location("scaffolded_workflows", config_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    app = getattr(module, "app", None)
    assert isinstance(app, App)
    return app


def test_init_scaffold_matches_fixture(tmp_path: Path, monkeypatch: Any):
    """The scaffolded config emits exactly ``fixtures/expected/init_scaffold.yml``."""
    monkeypatch.chdir(tmp_path)

    assert main(["init", "--outdir", str(tmp_path)]) == 0

    config_path = tmp_path / "ghagen_workflows.py"
    assert config_path.exists()

    app = _load_app(config_path)
    documents = app.documents()
    assert len(documents) == 1

    assert documents[0].to_yaml(header=None) == _FIXTURE.read_text()
