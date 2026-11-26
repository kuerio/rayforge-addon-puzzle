"""Jigsaw cut-line generation.

The tab geometry is a faithful port of Draradech's ``jigsaw.html``
(CC0, the de-facto standard used by most online jigsaw generators): each
interior cell edge gets a three-cubic tab whose direction and jitter are
driven by a seeded random stream. Puzzles are therefore reproducible
from ``(seed, parameters)`` alone, and the output matches the reference
tool for the same input.

Coordinates are millimetres with the origin at the bottom left.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from .geometry import Path, Point, rounded_rect
from .rng import SeededRandom

__all__ = ["PuzzleParams", "PuzzlePaths", "generate", "iter_tab_centers"]

# Every tab is the chain of three cubics between ten points along the
# edge; ``_TabSequence`` provides those ten positions in cell fractions,
# in the order used by the reference implementation.


@dataclass(frozen=True)
class PuzzleParams:
    """Everything needed to reproduce a puzzle."""

    width_mm: float = 200.0
    height_mm: float = 150.0
    columns: int = 6
    rows: int = 4
    tab_size_percent: float = 20.0
    jitter_percent: float = 4.0
    seed: int = 1
    border_radius_mm: float = 0.0

    def __post_init__(self) -> None:
        if self.width_mm <= 0 or self.height_mm <= 0:
            raise ValueError("Puzzle width and height must be positive.")
        if self.columns < 1 or self.rows < 1:
            raise ValueError("A puzzle needs at least one column and row.")
        if not 0.0 <= self.tab_size_percent <= 60.0:
            raise ValueError("Tab size must be between 0 and 60 percent.")
        if not 0.0 <= self.jitter_percent <= 45.0:
            raise ValueError("Jitter must be between 0 and 45 percent.")
        if self.border_radius_mm < 0:
            raise ValueError("Border radius must not be negative.")
        if self.border_radius_mm > min(
            self.width_mm / 2.0, self.height_mm / 2.0
        ):
            raise ValueError("Border radius is larger than the puzzle.")

    @property
    def cell_width_mm(self) -> float:
        return self.width_mm / self.columns

    @property
    def cell_height_mm(self) -> float:
        return self.height_mm / self.rows

    @property
    def piece_count(self) -> int:
        return self.columns * self.rows

    def describe(self) -> str:
        """A one-line, human-readable summary."""
        return (
            f"{self.columns}x{self.rows} ({self.piece_count} pieces), "
            f"{self.width_mm:g}x{self.height_mm:g} mm, "
            f"tabs {self.tab_size_percent:g}%, jitter {self.jitter_percent:g}%, "
            f"seed {self.seed}"
        )


@dataclass
class PuzzlePaths:
    """The paths of one puzzle."""

    border: Path
    horizontal: list[Path]
    vertical: list[Path]

    def all(self) -> list[Path]:
        """Border first, then the interior grid lines."""
        return [self.border, *self.horizontal, *self.vertical]

    @property
    def cut_line_count(self) -> int:
        return len(self.horizontal) + len(self.vertical)


class _TabSequence:
    """The ``first()``/``next()`` tab parameter stream of the reference."""

    __slots__ = ("_rng", "_jitter", "_e", "flip", "a", "b", "c", "d", "e")

    def __init__(self, rng: SeededRandom, jitter: float) -> None:
        self._rng = rng
        self._jitter = jitter
        self._e = 0.0
        self.flip: bool | None = None
        self.a = self.b = self.c = self.d = self.e = 0.0

    def first(self) -> None:
        """Start a new line; draws one extra value for the first tab."""
        self._e = self._rng.uniform(-self._jitter, self._jitter)
        self.next()

    def next(self) -> None:
        """Advance to the parameters of the next tab."""
        previous = self.flip
        self.flip = self._rng.rbool()
        rng = self._rng
        self.a = -self._e if self.flip == previous else self._e
        self.b = rng.uniform(-self._jitter, self._jitter)
        self.c = rng.uniform(-self._jitter, self._jitter)
        self.d = rng.uniform(-self._jitter, self._jitter)
        self.e = rng.uniform(-self._jitter, self._jitter)
        self._e = self.e

    def length_values(self, tab: float) -> tuple[float, ...]:
        """The ten positions along the edge, in cell fractions."""
        b, d, t = self.b, self.d, tab
        return (
            0.0,
            0.2,
            0.5 + b + d,
            0.5 - t + b,
            0.5 - 2.0 * t + b - d,
            0.5 + 2.0 * t + b - d,
            0.5 + t + b,
            0.5 + b + d,
            0.8,
            1.0,
        )

    def width_values(self, tab: float) -> tuple[float, ...]:
        """The ten offsets across the edge, in cell fractions."""
        a, c, e, t = self.a, self.c, self.e, tab
        return (
            0.0,
            a,
            -t + c,
            t + c,
            3.0 * t + c,
            3.0 * t + c,
            t + c,
            -t + c,
            e,
            0.0,
        )


def _tab_path(
    origin: Point,
    along: float,
    across: float,
    tabs: _TabSequence,
    tab: float,
    swap: bool,
) -> Path:
    """One edge of ``along`` mm with a single tab.

    ``swap`` transposes the result, which is how the reference emits
    vertical lines: it always computes along/across and then swaps X/Y.
    """
    ox, oy = origin
    sign = -1.0 if tabs.flip else 1.0

    def point(length_value: float, width_value: float) -> Point:
        length = along * length_value
        width = across * width_value * sign
        if swap:
            return (ox + width, oy + length)
        return (ox + length, oy + width)

    lengths = tabs.length_values(tab)
    widths = tabs.width_values(tab)
    path = Path(point(lengths[0], widths[0]))
    for index in (1, 4, 7):
        path.curve_to(*point(lengths[index], widths[index]),
                      *point(lengths[index + 1], widths[index + 1]),
                      *point(lengths[index + 2], widths[index + 2]))
    return path


def expected_draw_count(params: PuzzleParams) -> int:
    """How many random values :func:`generate` consumes.

    Each line starts with ``first()`` (one extra uniform, then a full
    tuple, six draws in total) and every tab, including the last one,
    advances the stream by another five. The trailing advance mirrors
    the reference implementation, so a stream may be shared between
    puzzles and still match the online generators.
    """
    tabs = (params.rows - 1) * params.columns + (params.columns - 1) * params.rows
    lines = max(params.rows - 1, 0) + max(params.columns - 1, 0)
    return lines * 6 + tabs * 5


def generate(
    params: PuzzleParams, rng: SeededRandom | None = None
) -> PuzzlePaths:
    """Generate the cut lines of a puzzle.

    The border is a closed path; the interior lines are open paths that
    start and end exactly on the border, which is what a contour cut
    wants. The random stream is consumed in the same order as the
    reference implementation (all horizontal lines, then all vertical
    lines), so seeds are interchangeable with the online generators.

    Pass *rng* to continue an existing stream, e.g. to lay out several
    puzzles that share one seed sequence.
    """
    rng = rng if rng is not None else SeededRandom(params.seed)
    jitter = params.jitter_percent / 100.0
    tab = params.tab_size_percent / 200.0
    cell_w = params.cell_width_mm
    cell_h = params.cell_height_mm
    tabs = _TabSequence(rng, jitter)

    horizontal: list[Path] = []
    for row in range(1, params.rows):
        y = row * cell_h
        tabs.first()
        line = Path((0.0, y))
        for column in range(params.columns):
            edge = _tab_path(
                (column * cell_w, y), cell_w, cell_h, tabs, tab, swap=False
            )
            line.segments.extend(edge.segments)
            tabs.next()
        horizontal.append(line)

    vertical: list[Path] = []
    for column in range(1, params.columns):
        x = column * cell_w
        tabs.first()
        line = Path((x, 0.0))
        for row in range(params.rows):
            edge = _tab_path(
                (x, row * cell_h), cell_h, cell_w, tabs, tab, swap=True
            )
            line.segments.extend(edge.segments)
            tabs.next()
        vertical.append(line)

    border = rounded_rect(
        params.width_mm, params.height_mm, params.border_radius_mm
    )
    return PuzzlePaths(border=border, horizontal=horizontal, vertical=vertical)


def iter_tab_centers(params: PuzzleParams) -> Iterator[Point]:
    """The nominal centre of every tab, for tests and labels."""
    for row in range(1, params.rows):
        for column in range(params.columns):
            yield (
                (column + 0.5) * params.cell_width_mm,
                row * params.cell_height_mm,
            )
    for column in range(1, params.columns):
        for row in range(params.rows):
            yield (
                column * params.cell_width_mm,
                (row + 0.5) * params.cell_height_mm,
            )
