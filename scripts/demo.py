#!/usr/bin/env python3
"""Write a few sample puzzles to ``out/`` for eyeballing.

Run from the repository root::

    python3 scripts/demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from puzzle_maker.core.jigsaw import PuzzleParams  # noqa: E402
from puzzle_maker.core.svg import write_puzzle_svg  # noqa: E402

SAMPLES: tuple[tuple[str, PuzzleParams], ...] = (
    (
        "classic-6x4",
        PuzzleParams(
            width_mm=200,
            height_mm=150,
            columns=6,
            rows=4,
            tab_size_percent=20,
            jitter_percent=4,
            seed=1,
        ),
    ),
    (
        "rounded-10x8",
        PuzzleParams(
            width_mm=300,
            height_mm=220,
            columns=10,
            rows=8,
            tab_size_percent=18,
            jitter_percent=3,
            seed=42,
            border_radius_mm=8,
        ),
    ),
    (
        "chunky-tabs-3x2",
        PuzzleParams(
            width_mm=150,
            height_mm=100,
            columns=3,
            rows=2,
            tab_size_percent=30,
            jitter_percent=12,
            seed=7,
        ),
    ),
    (
        "kids-4x3-rounded",
        PuzzleParams(
            width_mm=120,
            height_mm=90,
            columns=4,
            rows=3,
            tab_size_percent=25,
            jitter_percent=6,
            seed=2026,
            border_radius_mm=6,
        ),
    ),
)


def main() -> int:
    folder = ROOT / "out"
    folder.mkdir(exist_ok=True)
    for name, params in SAMPLES:
        target = write_puzzle_svg(folder / f"{name}.svg", params)
        size_kb = target.stat().st_size / 1024.0
        print(f"{target.relative_to(ROOT)}\t{params.describe()}\t{size_kb:.1f} kB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
