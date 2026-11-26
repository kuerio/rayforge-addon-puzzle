"""
Backend entry point for the Puzzle Maker addon.

Loaded in both the worker and the main process, so this module must not
import GTK. It registers the editor command that turns puzzle parameters
into a document item.
"""

from __future__ import annotations

import gettext
import logging
from pathlib import Path

from rayforge.core.hooks import hookimpl

# Must match the directory name for proper cleanup on unload.
ADDON_NAME = "puzzle_maker"

_localedir = Path(__file__).parent.parent / "locales"
_t = gettext.translation("puzzle_maker", localedir=_localedir, fallback=True)
_ = _t.gettext

logger = logging.getLogger(__name__)


@hookimpl
def rayforge_init(context):
    """Called when the application context is fully initialized."""
    logger.info("Puzzle Maker loaded (command: %s)", ADDON_NAME)


@hookimpl
def on_unload():
    """Called when the addon is being disabled or unloaded."""
    logger.info("Puzzle Maker unloaded")


@hookimpl
def register_commands(command_registry):
    """Register the editor command that adds a puzzle to the document."""
    from .commands.puzzle_cmd import PuzzleCmd

    command_registry.register(ADDON_NAME, PuzzleCmd, ADDON_NAME)
