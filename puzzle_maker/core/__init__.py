"""Dependency-free puzzle geometry.

Nothing in here imports Rayforge, GTK or third-party packages, so it can
be unit tested and scripted anywhere::

    python3 -m puzzle_maker.cli --columns 6 --rows 4 --seed 7 -o puzzle.svg
"""

from __future__ import annotations

from .geometry import Cubic, Line, Path, format_number, rounded_rect
from .jigsaw import (
    PuzzleParams,
    PuzzlePaths,
    expected_draw_count,
    generate,
    iter_tab_centers,
)
from .rng import SeededRandom
from .svg import (
    DEFAULT_STROKE_MM,
    paths_to_svg,
    puzzle_to_svg,
    write_puzzle_svg,
)

__all__ = [
    "Cubic",
    "DEFAULT_STROKE_MM",
    "Line",
    "Path",
    "PuzzleParams",
    "PuzzlePaths",
    "SeededRandom",
    "expected_draw_count",
    "format_number",
    "generate",
    "iter_tab_centers",
    "paths_to_svg",
    "puzzle_to_svg",
    "rounded_rect",
    "write_puzzle_svg",
]
