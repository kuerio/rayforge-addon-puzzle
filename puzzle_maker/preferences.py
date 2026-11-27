"""Remembering the last used puzzle parameters.

Ergonomics: the dialog should open with the values of the previous puzzle
instead of the built-in defaults, including the seed.

Storage: Rayforge gives every addon a private data directory inside its
config directory, so the values travel with the rest of the configuration
(also when the config is shared between machines). Writes go through
Rayforge's atomic YAML helpers, which keep a ``.bak`` sidecar, so a
half-written file cannot happen.

Robustness: importing Rayforge's helpers and locating the directory are
both optional. If either fails, the dialog still works — it just stops
remembering. Nothing in here raises to the caller.
"""

from __future__ import annotations

import logging
from pathlib import Path

from .core.jigsaw import PuzzleParams

logger = logging.getLogger(__name__)

ADDON_NAME = "puzzle_maker"
FILENAME = "last_puzzle.yaml"


# -- Rayforge helpers, with a stdlib fallback -------------------------
try:  # pragma: no cover - exercised inside Rayforge
    from rayforge.shared.util.atomic import (
        atomic_write_yaml,
        load_yaml_with_backup,
    )
except Exception:  # pragma: no cover - defensive
    logger.warning("Rayforge's atomic helpers are unavailable", exc_info=True)
    import os

    import yaml

    def atomic_write_yaml(path: Path, data, keep_backup: bool = True) -> None:
        content = yaml.safe_dump(data, sort_keys=False)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(content, encoding="utf-8")
        os.replace(tmp, path)

    def load_yaml_with_backup(path: Path):
        return yaml.safe_load(path.read_text(encoding="utf-8")), False


def preferences_file() -> Path | None:
    """Where the last used parameters are stored, or None if unknown."""
    try:
        from rayforge import config as rayforge_config

        getter = getattr(rayforge_config, "get_addon_data_dir", None)
        if callable(getter):
            directory = Path(getter(ADDON_NAME))
        else:
            directory = Path(rayforge_config.CONFIG_DIR) / "addon_data" / ADDON_NAME
        directory.mkdir(parents=True, exist_ok=True)
        return directory / FILENAME
    except Exception:  # pragma: no cover - defensive
        logger.warning(
            "Cannot locate the puzzle settings directory", exc_info=True
        )
        return None


def load() -> PuzzleParams:
    """The last used parameters, or the built-in defaults."""
    path = preferences_file()
    if path is None:
        return PuzzleParams()
    try:
        data, recovered = load_yaml_with_backup(path)
    except FileNotFoundError:
        return PuzzleParams()
    except Exception:
        logger.warning("Could not read %s; using defaults", path, exc_info=True)
        return PuzzleParams()
    if recovered:
        logger.info("Recovered puzzle settings from %s.bak", path)
    try:
        return PuzzleParams.from_dict(data)
    except ValueError:
        logger.warning("Invalid puzzle settings in %s; using defaults", path)
        return PuzzleParams()


def save(params: PuzzleParams) -> None:
    """Store *params* for the next time the dialog opens."""
    path = preferences_file()
    if path is None:
        return
    try:
        atomic_write_yaml(path, params.to_dict())
    except Exception:
        logger.warning("Could not save %s", path, exc_info=True)


def clear() -> None:
    """Forget the stored parameters, so the defaults apply again."""
    path = preferences_file()
    if path is None:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.warning("Could not remove %s", path, exc_info=True)
