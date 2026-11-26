"""
Frontend entry point for the Puzzle Maker addon.

Loaded only in the main process. Adds a "Create Puzzle…" action to the
Tools menu, which opens the parameter dialog and adds the result to the
document through the backend command.
"""

from __future__ import annotations

import gettext
import logging
from pathlib import Path

from gi.repository import Gio

from rayforge.core.hooks import hookimpl
from rayforge.ui_gtk.action_registry import MenuPlacement

from .core.jigsaw import PuzzleParams
from .widgets import PuzzleDialog

ADDON_NAME = "puzzle_maker"

_localedir = Path(__file__).parent.parent / "locales"
_t = gettext.translation("puzzle_maker", localedir=_localedir, fallback=True)
_ = _t.gettext

logger = logging.getLogger(__name__)

ACTION_NAME = "puzzle_maker_create_puzzle"


def _notify(editor, message: str) -> None:
    editor.notification_requested.send(editor, message=message)


def _accept(
    dialog: PuzzleDialog,
    command,
    editor,
    params: PuzzleParams,
    with_contour: bool,
) -> None:
    """Add the puzzle to the document, then close the dialog."""
    try:
        command.add_puzzle(params, with_contour=with_contour)
    except ValueError as error:
        _notify(editor, str(error))
        return
    except Exception as error:  # pragma: no cover - surfaced to the user
        logger.exception("Could not add the puzzle")
        _notify(editor, _("Could not add the puzzle: {error}").format(error=error))
        return
    dialog.close()


def _open_dialog(action_registry) -> None:
    window = action_registry.window
    editor = window.doc_editor
    command = getattr(editor, ADDON_NAME, None)
    if command is None:
        _notify(editor, _("The Puzzle Maker command is not available."))
        return

    dialog: PuzzleDialog

    def on_accept(params: PuzzleParams, with_contour: bool) -> None:
        _accept(dialog, command, editor, params, with_contour)

    dialog = PuzzleDialog(window, on_accept)
    dialog.present()


@hookimpl
def register_actions(action_registry):
    """Register the Tools menu entry."""
    action = Gio.SimpleAction.new(ACTION_NAME, None)
    action.connect("activate", lambda *_args: _open_dialog(action_registry))
    action_registry.register(
        action_name=ACTION_NAME,
        action=action,
        addon_name=ADDON_NAME,
        label=_("Create Puzzle…"),
        menu=MenuPlacement(menu_id="tools", priority=110),
    )
