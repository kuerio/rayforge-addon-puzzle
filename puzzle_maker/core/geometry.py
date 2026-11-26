"""A tiny, dependency-free path model.

Deliberately minimal: the puzzle generator only needs straight lines and
cubic Béziers, and both the SVG writer and the GTK preview have to walk
the same geometry. Arcs are approximated with cubic Béziers so that no
consumer needs arc support.

Coordinates are always in millimetres, with the origin at the bottom
left of the puzzle (the SVG writer flips Y, see :mod:`puzzle_maker.core.svg`).
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = [
    "KAPPA",
    "Cubic",
    "Line",
    "Path",
    "rounded_rect",
    "format_number",
]

#: Circle-to-cubic magic number. A quarter circle of radius r is
#: approximated by a cubic with control points offset by r * KAPPA.
KAPPA = 0.5522847498307936

Point = tuple[float, float]


def format_number(value: float, precision: int = 3) -> str:
    """Format *value* compactly and without a negative zero."""
    text = f"{value:.{precision}f}"
    text = text.rstrip("0").rstrip(".") if "." in text else text
    return "0" if text in ("-0", "") else text


class Segment:
    """Base class for path segments."""

    __slots__ = ()

    def end(self) -> Point:  # pragma: no cover - overridden
        raise NotImplementedError

    def to_svg(self, precision: int = 3) -> str:  # pragma: no cover
        raise NotImplementedError

    def cubic_segments(self) -> tuple[tuple[float, ...], ...]:
        """Return the segment as one or more ``(x1, y1, x2, y2, x, y)``.

        Used by the preview, which only understands cubics and lines.
        """
        raise NotImplementedError

    def points(self) -> tuple[Point, ...]:
        """Return the points the segment passes through (incl. controls)."""
        raise NotImplementedError


@dataclass(frozen=True)
class Line(Segment):
    """A straight line to ``(x, y)``."""

    x: float
    y: float

    def end(self) -> Point:
        return (self.x, self.y)

    def to_svg(self, precision: int = 3) -> str:
        n = format_number
        return (
            f"L {n(self.x, precision)} {n(self.y, precision)}"
        )

    def cubic_segments(self) -> tuple[tuple[float, ...], ...]:
        return ()

    def points(self) -> tuple[Point, ...]:
        return ((self.x, self.y),)


@dataclass(frozen=True)
class Cubic(Segment):
    """A cubic Bézier to ``(x, y)`` with two control points."""

    x1: float
    y1: float
    x2: float
    y2: float
    x: float
    y: float

    def end(self) -> Point:
        return (self.x, self.y)

    def to_svg(self, precision: int = 3) -> str:
        n = format_number
        return (
            f"C {n(self.x1, precision)} {n(self.y1, precision)} "
            f"{n(self.x2, precision)} {n(self.y2, precision)} "
            f"{n(self.x, precision)} {n(self.y, precision)}"
        )

    def cubic_segments(self) -> tuple[tuple[float, ...], ...]:
        return ((self.x1, self.y1, self.x2, self.y2, self.x, self.y),)

    def points(self) -> tuple[Point, ...]:
        return ((self.x1, self.y1), (self.x2, self.y2), (self.x, self.y))


@dataclass
class Path:
    """An open or closed sequence of :class:`Segment` objects."""

    start: Point
    segments: list[Segment] = field(default_factory=list)
    closed: bool = False

    # -- building -----------------------------------------------------
    def line_to(self, x: float, y: float) -> "Path":
        self.segments.append(Line(x, y))
        return self

    def curve_to(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        x: float,
        y: float,
    ) -> "Path":
        self.segments.append(Cubic(x1, y1, x2, y2, x, y))
        return self

    def close(self) -> "Path":
        """Close the path, adding the closing line when it is missing.

        The last point is made to coincide with the start so the path is
        a real closed loop even for consumers that ignore SVG's ``Z``,
        and so :attr:`is_closed` can be trusted.
        """
        if self.segments:
            tail = self.end
            head = self.start
            if abs(tail[0] - head[0]) > 1e-9 or abs(tail[1] - head[1]) > 1e-9:
                self.segments.append(Line(head[0], head[1]))
        self.closed = True
        return self

    # -- queries ------------------------------------------------------
    @property
    def end(self) -> Point:
        return self.segments[-1].end() if self.segments else self.start

    @property
    def is_closed(self) -> bool:
        """Whether the path returns to its start point."""
        return self.closed

    def polyline_points(self) -> list[Point]:
        """All points, for bounding boxes and previews."""
        points = [self.start]
        for segment in self.segments:
            points.extend(segment.points())
        return points

    def bounds(self) -> tuple[float, float, float, float]:
        """Conservative bounding box ``(min_x, min_y, max_x, max_y)``."""
        points = self.polyline_points()
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return (min(xs), min(ys), max(xs), max(ys))

    # -- output -------------------------------------------------------
    def to_svg(self, precision: int = 3) -> str:
        n = format_number
        parts = [f"M {n(self.start[0], precision)} {n(self.start[1], precision)}"]
        parts.extend(seg.to_svg(precision) for seg in self.segments)
        if self.closed:
            parts.append("Z")
        return " ".join(parts)

    def flipped_y(self, height: float) -> "Path":
        """A copy mirrored about the X axis (SVG has Y pointing down)."""
        new = Path((self.start[0], height - self.start[1]), closed=self.closed)
        for segment in self.segments:
            end = segment.end()
            if isinstance(segment, Cubic):
                new.curve_to(
                    segment.x1,
                    height - segment.y1,
                    segment.x2,
                    height - segment.y2,
                    end[0],
                    height - end[1],
                )
            else:
                new.line_to(end[0], height - end[1])
        return new


def rounded_rect(
    width: float, height: float, radius: float = 0.0
) -> Path:
    """A rectangle ``width`` × ``height`` with optional rounded corners."""
    radius = max(0.0, min(radius, width / 2.0, height / 2.0))
    path = Path((0.0, 0.0))
    if radius <= 0.0:
        path.line_to(width, 0.0).line_to(width, height).line_to(0.0, height)
        return path.close()

    k = radius * KAPPA
    path.line_to(width - radius, 0.0)
    path.curve_to(width - radius + k, 0.0, width, radius - k, width, radius)
    path.line_to(width, height - radius)
    path.curve_to(
        width, height - radius + k, width - radius + k, height, width - radius, height
    )
    path.line_to(radius, height)
    path.curve_to(radius - k, height, 0.0, height - radius + k, 0.0, height - radius)
    path.line_to(0.0, radius)
    path.curve_to(0.0, radius - k, radius - k, 0.0, radius, 0.0)
    return path.close()
