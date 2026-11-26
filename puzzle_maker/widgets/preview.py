"""A live preview of the puzzle, drawn with cairo.

Only depends on GTK and the dependency-free core, so it renders exactly
what the SVG export will contain.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gi.repository import Gtk

from ..core.geometry import Cubic, Path
from ..core.jigsaw import PuzzleParams, generate

if TYPE_CHECKING:  # pragma: no cover
    import cairo

__all__ = ["PuzzlePreview"]

#: Padding around the drawing, in device pixels.
PADDING = 10


class PuzzlePreview(Gtk.DrawingArea):
    """Shows the current puzzle, scaled to fit the widget."""

    def __init__(self, params: PuzzleParams | None = None) -> None:
        super().__init__()
        self._params = params or PuzzleParams()
        self.set_content_height(260)
        self.set_hexpand(True)
        self.set_draw_func(self._draw)

    def set_params(self, params: PuzzleParams) -> None:
        """Show *params*, redrawing the widget."""
        self._params = params
        self.queue_draw()

    # -- drawing ------------------------------------------------------
    def _draw(
        self,
        _area: Gtk.DrawingArea,
        cr: "cairo.Context",
        width: int,
        height: int,
    ) -> None:
        params = self._params
        available_w = max(width - 2 * PADDING, 1)
        available_h = max(height - 2 * PADDING, 1)
        scale = min(
            available_w / params.width_mm, available_h / params.height_mm
        )
        offset_x = (width - params.width_mm * scale) / 2.0
        offset_y = (height - params.height_mm * scale) / 2.0

        cr.save()
        cr.set_line_join(1)  # cairo.LINE_JOIN_ROUND
        cr.set_line_cap(1)  # cairo.LINE_CAP_ROUND

        # Flip Y: the generator works in maths orientation, cairo does not.
        cr.translate(offset_x, offset_y + params.height_mm * scale)
        cr.scale(scale, -scale)
        hairline = 1.0 / scale

        puzzle = generate(params)
        cr.set_line_width(hairline * 1.6)
        cr.set_source_rgb(0.20, 0.20, 0.22)
        _stroke_path(cr, puzzle.border)
        cr.stroke()

        cr.set_line_width(hairline)
        cr.set_source_rgb(0.45, 0.45, 0.50)
        for path in (*puzzle.horizontal, *puzzle.vertical):
            _stroke_path(cr, path)
            cr.stroke()

        cr.restore()


def _stroke_path(cr: "cairo.Context", path: Path) -> None:
    cr.move_to(*path.start)
    for segment in path.segments:
        if isinstance(segment, Cubic):
            cr.curve_to(
                segment.x1,
                segment.y1,
                segment.x2,
                segment.y2,
                segment.x,
                segment.y,
            )
        else:
            cr.line_to(segment.x, segment.y)
    if path.closed:
        cr.close_path()
