"""Puzzle Maker: jigsaw cut lines for laser cutters.

The ``core`` package is dependency-free and usable on its own::

    from puzzle_maker.core import PuzzleParams, puzzle_to_svg

    svg = puzzle_to_svg(PuzzleParams(columns=6, rows=4, seed=7))

Everything Rayforge-specific lives one level up (:mod:`puzzle_maker.backend`,
:mod:`puzzle_maker.frontend`), so the geometry can be tested and reused
without GTK or Rayforge installed.
"""

from __future__ import annotations

__all__ = ["__version__", "addon_name"]

#: Version of this addon (keep in sync with the git tag).
__version__ = "0.2.0"

#: Must match the directory name and the ``name`` key in
#: ``rayforge-addon.yaml``.
addon_name = "puzzle_maker"
