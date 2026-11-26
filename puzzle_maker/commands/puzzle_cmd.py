"""
Adds a generated jigsaw to the document.

Mirrors how the bundled calibration tests build their items: the puzzle
is rendered to an SVG, imported through the SVG importer (the only
supported route from geometry to a workpiece with a source asset), and
placed on a new layer in a single undoable transaction. A Contour step
is added as well, so the puzzle is directly cuttable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from gettext import gettext as _
from typing import TYPE_CHECKING, Any

from rayforge.context import get_context
from rayforge.core.color import pick_unused_color
from rayforge.core.layer import Layer
from rayforge.core.source_asset import SourceAsset
from rayforge.core.step import Step
from rayforge.core.step_registry import step_registry
from rayforge.core.undo import ListItemCommand
from rayforge.core.vectorization_spec import PassthroughSpec
from rayforge.core.workpiece import WorkPiece
from rayforge.doceditor.layer_cmd import AddLayerAndSetActiveCommand
from rayforge.image.svg.importer import SvgImporter

from ..core.jigsaw import PuzzleParams
from ..core.svg import puzzle_to_svg

if TYPE_CHECKING:
    from rayforge.doceditor.editor import DocEditor

logger = logging.getLogger(__name__)

#: Where the puzzle is placed when the machine has no work area set.
DEFAULT_MARGIN_MM = 5.0


@dataclass
class BuiltPuzzle:
    """The items one puzzle adds to the document."""

    source: SourceAsset
    workpiece: WorkPiece
    step: Step | None = None


class PuzzleCmd:
    """Creates puzzles in the document."""

    def __init__(self, editor: "DocEditor") -> None:
        self._editor = editor

    @property
    def _doc(self):
        return self._editor.doc

    # -- public API ---------------------------------------------------
    def add_puzzle(
        self,
        params: PuzzleParams,
        *,
        with_contour: bool = True,
    ) -> BuiltPuzzle:
        """Add *params* as a new layer with a Contour step.

        Raises ``ValueError`` when the puzzle cannot be built.
        """
        built = self.build(params, with_contour=with_contour)
        layer = self._new_layer(params)
        layer.add_child(built.workpiece)
        if built.step is not None and layer.workflow is not None:
            layer.workflow.set_steps([built.step])

        label = _("Add puzzle")
        with self._editor.history_manager.transaction(label) as transaction:
            transaction.execute(
                ListItemCommand(
                    self._doc, built.source, "remove_asset", "add_asset"
                )
            )
            transaction.execute(
                AddLayerAndSetActiveCommand(self._editor, layer, label)
            )
        logger.info("Added %s", params.describe())
        return built

    def build(
        self, params: PuzzleParams, *, with_contour: bool = True
    ) -> BuiltPuzzle:
        """Generate the geometry and turn it into document items."""
        name = self._name_for(params)
        data = puzzle_to_svg(params).encode("utf-8")
        source, workpiece = self._import_svg(name, data)
        workpiece.name = name
        self._place(workpiece, params)
        step = self._contour_step(workpiece) if with_contour else None
        return BuiltPuzzle(source=source, workpiece=workpiece, step=step)

    # -- helpers ------------------------------------------------------
    @staticmethod
    def _name_for(params: PuzzleParams) -> str:
        return _("Puzzle {cols}x{rows} seed {seed}").format(
            cols=params.columns, rows=params.rows, seed=params.seed
        )

    def _new_layer(self, params: PuzzleParams) -> Layer:
        """A new layer named after the puzzle, with an unused color."""
        existing = {layer.name for layer in self._doc.layers}
        name = self._name_for(params)
        number = 2
        while name in existing:
            name = f"{self._name_for(params)} ({number})"
            number += 1

        layer = Layer(name)
        try:
            material = get_context().material_mgr.get_default_material()
            layer.set_stock_material_uid(material.uid)
        except Exception:  # pragma: no cover - depends on user setup
            logger.debug("No default material available", exc_info=True)
        layer.set_color(
            pick_unused_color({layer.color for layer in self._doc.layers})
        )
        return layer

    def _contour_step(self, workpiece: WorkPiece) -> Step | None:
        """A Contour step for the puzzle, or None when unavailable."""
        step_class: Any = step_registry.get("ContourStep")
        if step_class is None:
            logger.warning("No Contour step available; add one by hand.")
            return None
        try:
            step = step_class.create(self._editor.context, name=_("Cut"))
        except Exception:  # pragma: no cover - depends on addon set
            logger.warning("Could not create a Contour step", exc_info=True)
            return None
        step.workpiece_uids = [workpiece.uid]
        return step

    @staticmethod
    def _import_svg(
        name: str, data: bytes
    ) -> tuple[SourceAsset, WorkPiece]:
        """Import SVG *data* as a hidden source asset plus workpiece.

        One path element becomes one workpiece; the puzzle is generated
        as a single element, so this is the whole puzzle.
        """
        result = SvgImporter(data).get_doc_items(PassthroughSpec())
        if not result or not result.payload or not result.payload.items:
            raise ValueError(_("The puzzle could not be imported."))
        workpiece = result.payload.items[0]
        if not isinstance(workpiece, WorkPiece):
            raise ValueError(_("The puzzle produced an unexpected item."))
        source = result.payload.source
        source.name = name
        source.hidden = True
        return source, workpiece

    def _place(self, workpiece: WorkPiece, params: PuzzleParams) -> None:
        """Center the puzzle on the work area, without overflowing it."""
        dimensions = self._editor.machine_dimensions
        if dimensions:
            area_w, area_h = dimensions
            target_x = max(0.0, (area_w - params.width_mm) / 2.0)
            target_y = max(0.0, (area_h - params.height_mm) / 2.0)
        else:
            target_x = target_y = DEFAULT_MARGIN_MM

        bbox = workpiece.bbox
        offset_x, offset_y = bbox[0], bbox[1]
        workpiece.pos = (
            workpiece.pos[0] + target_x - offset_x,
            workpiece.pos[1] + target_y - offset_y,
        )
