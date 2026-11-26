"""Command line interface for the puzzle generator.

Useful on its own (no Rayforge, no GTK)::

    python3 -m puzzle_maker.cli --columns 6 --rows 4 --seed 7 -o puzzle.svg
    python3 -m puzzle_maker.cli --width 300 --height 200 --pieces 24 -o big.svg

It is also the quickest way to check a puzzle before importing it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core.jigsaw import PuzzleParams
from .core.svg import write_puzzle_svg

__all__ = ["build_parser", "main"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="puzzle_maker",
        description=(
            "Generate a jigsaw puzzle as an SVG of laser-ready cut lines."
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("puzzle.svg"),
        help="where to write the SVG (default: %(default)s)",
    )
    parser.add_argument(
        "--width",
        type=float,
        default=200.0,
        help="puzzle width in mm (default: %(default)s)",
    )
    parser.add_argument(
        "--height",
        type=float,
        default=150.0,
        help="puzzle height in mm (default: %(default)s)",
    )
    size = parser.add_mutually_exclusive_group()
    size.add_argument(
        "--columns",
        type=int,
        default=6,
        help="number of columns (default: %(default)s)",
    )
    size.add_argument(
        "--pieces",
        type=int,
        help="aim for about this many pieces, keeping the aspect ratio",
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=4,
        help="number of rows (default: %(default)s)",
    )
    parser.add_argument(
        "--tab-size",
        type=float,
        default=20.0,
        help="tab size in percent of a cell edge (default: %(default)s)",
    )
    parser.add_argument(
        "--jitter",
        type=float,
        default=4.0,
        help="tab jitter in percent (default: %(default)s)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=1,
        help="random seed; same seed, same puzzle (default: %(default)s)",
    )
    parser.add_argument(
        "--radius",
        type=float,
        default=0.0,
        help="border corner radius in mm (default: %(default)s)",
    )
    parser.add_argument(
        "--stroke",
        type=float,
        default=0.1,
        help="stroke width in mm (default: %(default)s)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="do not print a summary",
    )
    return parser


def _resolve_grid(args: argparse.Namespace) -> tuple[int, int]:
    """Work out columns and rows from either --columns or --pieces."""
    if args.pieces is None:
        return args.columns, args.rows

    # Keep the target cell square-ish: columns / rows ~ width / height.
    columns = max(1, round((args.pieces * args.width / args.height) ** 0.5))
    rows = max(1, round(args.pieces / columns))
    return columns, rows


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    columns, rows = _resolve_grid(args)
    try:
        params = PuzzleParams(
            width_mm=args.width,
            height_mm=args.height,
            columns=columns,
            rows=rows,
            tab_size_percent=args.tab_size,
            jitter_percent=args.jitter,
            seed=args.seed,
            border_radius_mm=args.radius,
        )
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    target = write_puzzle_svg(args.output, params, stroke_mm=args.stroke)
    if not args.quiet:
        print(f"{params.describe()}")
        print(f"wrote {target}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
