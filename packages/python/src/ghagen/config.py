"""Project configuration: the single owner of ``.ghagen.yml``.

This module discovers the project root, parses ``.ghagen.yml`` **once**, and
returns a typed :class:`ProjectConfig` whose error modes are *values*
(:class:`ConfigError`), never thrown framework exceptions — no ``typer`` import
lives here. Callers pick which errors bind: the CLI renders every error and
exits; the header's ``{source_file}`` path (:func:`load_options`) keeps only
option errors so a malformed ``entrypoint:`` cannot break it.

What lives behind this seam:

* **Root discovery** — :func:`find_app_root` walks upward for the
  ``.ghagen.yml`` marker. The *single* root locator, used here and by the
  header's ``{source_file}`` resolution.
* **Single parse + validation** — :func:`load_project_config` reads the file
  once and derives both options and the workflow entrypoint from it.
* **Entrypoint resolution** — the ``entrypoint:`` key, falling back to
  :data:`CONFIG_SEARCH_PATHS` against a single anchor.
* **Module -> App resolution** — :func:`resolve_app`, the policy shared by the
  CLI's app loading and pin's ``track_user_files``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ruamel.yaml import YAML, YAMLError

if TYPE_CHECKING:
    from ghagen.app import App

#: Canonical marker file: its presence identifies the ghagen project root.
GHAGEN_YML_MARKER = Path(".ghagen.yml")

#: Default pin-lockfile path, relative to ``App.root``. Single home for the literal.
DEFAULT_LOCKFILE_PATH = Path(".ghagen.lock.yml")

#: Conventional workflow-config filenames, probed (in order) against the project
#: root — or the cwd when no ``.ghagen.yml`` marker exists.
CONFIG_SEARCH_PATHS = [
    ".github/ghagen_workflows.py",
    "ghagen_config.py",
]


def find_app_root(start: Path | None = None) -> Path | None:
    """Walk upward from *start* looking for ``.ghagen.yml``.

    Returns the directory containing ``.ghagen.yml`` if found,
    else ``None``. When *start* is ``None``, walks from ``Path.cwd()``.
    When *start* refers to a file, the search begins at the file's
    parent directory.

    Args:
        start: The path to begin searching from. May be a directory or
            a file. Defaults to the current working directory.

    Returns:
        The absolute directory containing ``.ghagen.yml``, or ``None`` if no
        ancestor contains the marker. Lexical only -- ``.`` and ``..`` are
        collapsed and the result is joined against the cwd, but a symlink
        anywhere in *start* is never followed. That matches the TypeScript
        peer's ``findAppRoot``, which uses ``resolve()`` from ``node:path``
        (string manipulation only, no filesystem access) and has no
        equivalent of ``Path.resolve()``'s realpath behaviour to opt out of.
    """
    base = Path(os.path.abspath(start or Path.cwd()))
    if base.is_file():
        base = base.parent

    for parent in [base, *base.parents]:
        if (parent / GHAGEN_YML_MARKER).is_file():
            return parent
    return None


@dataclass(frozen=True)
class GhagenOptions:
    """Options controlling ghagen behaviour.

    Loaded from the ``options:`` section in ``.ghagen.yml``.
    """

    #: Dedent each Step's ``run`` script at emit time. The single default lives here.
    auto_dedent: bool = True


@dataclass(frozen=True)
class ConfigError:
    """A ``.ghagen.yml`` (or entrypoint-module) problem, surfaced as a value.

    ``kind`` is one of ``"parse"``, ``"not-a-mapping"``,
    ``"bad-entrypoint-type"``, ``"entrypoint-missing"``, ``"bad-option-type"``,
    or ``"app-resolution"``. ``message`` is human-readable text; renderers
    prepend ``Error: ``.
    """

    kind: str
    path: Path
    message: str


@dataclass(frozen=True)
class ProjectConfig:
    """The result of a single ``.ghagen.yml`` discovery + parse + validation."""

    #: Directory containing ``.ghagen.yml``, or ``None`` when no marker was found.
    root: Path | None
    #: Resolved workflow entrypoint, or ``None`` when none could be resolved.
    config_path: Path | None
    #: Always fully populated (defaults applied).
    options: GhagenOptions
    #: The raw ``entrypoint`` string from the file, or ``None``.
    entrypoint: str | None
    #: Empty on success.
    errors: tuple[ConfigError, ...] = field(default_factory=tuple)


def _read_ghagen_yml(path: Path) -> tuple[dict[str, Any] | None, ConfigError | None]:
    """Parse ``.ghagen.yml`` once, classifying user-input failures as values.

    OS-level I/O faults (an unreadable file the OS refuses) still raise — those
    are not config errors.
    """
    yaml = YAML()
    try:
        with path.open() as f:
            raw = yaml.load(f)
    except YAMLError as exc:
        return None, ConfigError("parse", path, f"{path}: failed to parse YAML: {exc}")
    if raw is None:
        return {}, None
    if not isinstance(raw, dict):
        return None, ConfigError(
            "not-a-mapping", path, f"{path}: expected a YAML mapping at top level"
        )
    return dict(raw), None


def _read_options(
    data: dict[str, Any], path: Path
) -> tuple[GhagenOptions, ConfigError | None]:
    """Validate the ``options:`` section into a fully-populated GhagenOptions."""
    raw = data.get("options")
    if raw is None:
        return GhagenOptions(), None
    if not isinstance(raw, dict):
        return GhagenOptions(), ConfigError(
            "bad-option-type", path, f"{path}: [options] must be a table"
        )
    auto_dedent = raw.get("auto_dedent", True)
    if not isinstance(auto_dedent, bool):
        return GhagenOptions(), ConfigError(
            "bad-option-type",
            path,
            f"{path}: [options].auto_dedent must be a boolean, "
            f"got {type(auto_dedent).__name__}",
        )
    return GhagenOptions(auto_dedent=auto_dedent), None


def load_project_config(
    start: Path | None = None,
    cli_config_flag: str | None = None,
) -> ProjectConfig:
    """Discover the root, parse ``.ghagen.yml`` **once**, and resolve the entrypoint.

    Resolves the workflow entrypoint (the ``entrypoint`` key, else
    :data:`CONFIG_SEARCH_PATHS`) and reads options. Never raises for user-input
    problems: they are returned in ``errors``. *cli_config_flag* short-circuits
    discovery when the user passed ``--config``.
    """
    cwd = start or Path.cwd()
    root = find_app_root(cwd)

    # ``--config`` short-circuits the search entirely, BEFORE any ``.ghagen.yml``
    # read. The explicit flag is the user's override, so a malformed marker file
    # (bad ``entrypoint:``, unparseable YAML) must never block it — parsing it
    # here and returning its errors would make ``_find_config`` exit 1 on the
    # very config the user just overrode (regression vs. main, which
    # short-circuited before any read). Options load best-effort elsewhere via
    # ``load_options``, which already tolerates a bad ``entrypoint:``/YAML.
    if cli_config_flag:
        flag_path = Path(cli_config_flag)
        if not flag_path.is_file():
            return ProjectConfig(
                root,
                None,
                GhagenOptions(),
                None,
                (
                    ConfigError(
                        "entrypoint-missing",
                        flag_path,
                        f"config file not found: {flag_path}",
                    ),
                ),
            )
        return ProjectConfig(root, flag_path, GhagenOptions(), None, ())

    errors: list[ConfigError] = []
    options = GhagenOptions()
    entrypoint: str | None = None
    entrypoint_valid = False

    # Single read of the marker file: both options and the entrypoint key come
    # from this one parse.
    if root is not None:
        ghagen_yml = root / GHAGEN_YML_MARKER
        data, read_err = _read_ghagen_yml(ghagen_yml)
        if read_err is not None:
            errors.append(read_err)
        if data is not None:
            options, opt_err = _read_options(data, ghagen_yml)
            if opt_err is not None:
                errors.append(opt_err)
            raw_entry = data.get("entrypoint")
            if raw_entry is not None:
                if not isinstance(raw_entry, str):
                    errors.append(
                        ConfigError(
                            "bad-entrypoint-type",
                            ghagen_yml,
                            f"{ghagen_yml}: 'entrypoint' must be a string, "
                            f"got {type(raw_entry).__name__}",
                        )
                    )
                else:
                    entrypoint = raw_entry
                    entrypoint_valid = True

    # Resolve the entrypoint key when present and valid.
    if root is not None and entrypoint_valid and entrypoint is not None:
        ghagen_yml = root / GHAGEN_YML_MARKER
        resolved = (root / entrypoint).resolve()
        if not resolved.is_file():
            errors.append(
                ConfigError(
                    "entrypoint-missing",
                    ghagen_yml,
                    f"{ghagen_yml}: entrypoint '{entrypoint}' does not exist "
                    f"(resolved to {resolved})",
                )
            )
            return ProjectConfig(root, None, options, entrypoint, tuple(errors))
        return ProjectConfig(root, resolved, options, entrypoint, tuple(errors))

    # A bad entrypoint type is fatal to config resolution — do not fall through
    # to the search paths (the caller renders ``errors``).
    if any(e.kind == "bad-entrypoint-type" for e in errors):
        return ProjectConfig(root, None, options, entrypoint, tuple(errors))

    # The two former search loops collapse into one anchored probe: the only
    # thing that differed between them was the anchor.
    anchor = root if root is not None else cwd
    for candidate in CONFIG_SEARCH_PATHS:
        path = anchor / candidate
        if path.is_file():
            return ProjectConfig(root, path, options, entrypoint, tuple(errors))

    return ProjectConfig(root, None, options, entrypoint, tuple(errors))


def load_options(start: Path | None = None) -> GhagenOptions:
    """Load project options from ``.ghagen.yml`` at the repository root.

    The header's ``{source_file}`` path, which must never fail on a bad
    ``entrypoint:``. Keeps only ``bad-option-type`` errors (re-raised as
    ``ValueError`` so a malformed ``options:`` is not silently ignored) and
    swallows every other kind. Falls back to defaults when no config file is
    found or when the file has no ``options:`` section.

    Args:
        start: Directory (or file) to begin the ancestor walk from.
            Defaults to the current working directory.
    """
    config = load_project_config(start)
    for err in config.errors:
        if err.kind == "bad-option-type":
            raise ValueError(err.message)
    return config.options


def resolve_app(
    module: Any, config_path: Path
) -> tuple[App | None, ConfigError | None]:
    """Extract an :class:`~ghagen.app.App` from a config module, as a value.

    Looks for ``create_app()`` first, then ``app``. Returns
    ``(app, None)`` on success or ``(None, ConfigError)`` when the module does
    not expose a usable ``App``. The single module -> App policy shared by the
    CLI's app loading and pin's ``track_user_files``.
    """
    from ghagen.app import App

    if hasattr(module, "create_app"):
        result = module.create_app()
        if not isinstance(result, App):
            return None, ConfigError(
                "app-resolution",
                config_path,
                f"create_app() in {config_path} must return an App instance",
            )
        return result, None

    if hasattr(module, "app"):
        result = module.app
        if not isinstance(result, App):
            return None, ConfigError(
                "app-resolution",
                config_path,
                f"'app' in {config_path} must be an App instance",
            )
        return result, None

    return None, ConfigError(
        "app-resolution",
        config_path,
        f"{config_path} must define 'app = App(...)' or 'def create_app() -> App'",
    )
