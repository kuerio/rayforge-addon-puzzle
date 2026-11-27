"""Unit tests for the jigsaw geometry."""

from __future__ import annotations

import unittest

from puzzle_maker.core.geometry import Cubic, Line, Path
from puzzle_maker.core.jigsaw import (
    PuzzleParams,
    expected_draw_count,
    generate,
)
from puzzle_maker.core.rng import SeededRandom


def cubics(path) -> list[Cubic]:
    return [segment for segment in path.segments if isinstance(segment, Cubic)]


class TestPuzzleParams(unittest.TestCase):
    def test_cell_size_and_piece_count(self):
        params = PuzzleParams(width_mm=200, height_mm=150, columns=4, rows=3)
        self.assertAlmostEqual(params.cell_width_mm, 50.0)
        self.assertAlmostEqual(params.cell_height_mm, 50.0)
        self.assertEqual(params.piece_count, 12)

    def test_rejects_nonsense(self):
        for kwargs in (
            {"width_mm": 0},
            {"height_mm": -5},
            {"columns": 0},
            {"rows": 0},
            {"tab_size_percent": -1},
            {"tab_size_percent": 90},
            {"jitter_percent": 80},
            {"border_radius_mm": -1},
            {"width_mm": 100, "height_mm": 100, "border_radius_mm": 60},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    PuzzleParams(**kwargs)

    def test_describe_mentions_the_grid(self):
        text = PuzzleParams(columns=3, rows=2, seed=9).describe()
        self.assertIn("3x2", text)
        self.assertIn("6 pieces", text)
        self.assertIn("seed 9", text)


class TestPuzzleParamsSerialization(unittest.TestCase):
    """The dialog stores the last used values, so this must round-trip."""

    def test_round_trip(self):
        params = PuzzleParams(
            width_mm=222.5,
            height_mm=111.25,
            columns=7,
            rows=5,
            tab_size_percent=25.0,
            jitter_percent=6.0,
            seed=99,
            border_radius_mm=4.0,
        )
        self.assertEqual(PuzzleParams.from_dict(params.to_dict()), params)

    def test_dict_is_plain_data(self):
        data = PuzzleParams().to_dict()
        self.assertEqual(
            sorted(data),
            [
                "border_radius_mm",
                "columns",
                "height_mm",
                "jitter_percent",
                "rows",
                "seed",
                "tab_size_percent",
                "width_mm",
            ],
        )
        self.assertTrue(all(isinstance(v, (int, float)) for v in data.values()))

    def test_unknown_keys_are_ignored(self):
        data = {**PuzzleParams().to_dict(), "future_option": True}
        self.assertEqual(PuzzleParams.from_dict(data).columns, 6)

    def test_none_values_keep_the_default(self):
        params = PuzzleParams.from_dict({"columns": 3, "seed": None})
        self.assertEqual(params.columns, 3)
        self.assertEqual(params.seed, 1)

    def test_invalid_values_raise(self):
        with self.assertRaises(ValueError):
            PuzzleParams.from_dict({"columns": 0})
        with self.assertRaises(ValueError):
            PuzzleParams.from_dict({"width_mm": -1})

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            PuzzleParams.from_dict(["not", "a", "mapping"])

    def test_missing_keys_give_defaults(self):
        params = PuzzleParams.from_dict({})
        self.assertEqual(params, PuzzleParams())


class TestGenerate(unittest.TestCase):
    def test_line_count(self):
        puzzle = generate(PuzzleParams(columns=5, rows=4))
        self.assertEqual(len(puzzle.horizontal), 3)
        self.assertEqual(len(puzzle.vertical), 4)
        self.assertEqual(puzzle.cut_line_count, 7)

    def test_border_is_closed_and_exact(self):
        border = generate(PuzzleParams(width_mm=200, height_mm=150)).border
        self.assertTrue(border.is_closed)
        self.assertAlmostEqual(border.start[0], 0.0)
        self.assertAlmostEqual(border.start[1], 0.0)
        min_x, min_y, max_x, max_y = border.bounds()
        self.assertAlmostEqual(min_x, 0.0)
        self.assertAlmostEqual(min_y, 0.0)
        self.assertAlmostEqual(max_x, 200.0)
        self.assertAlmostEqual(max_y, 150.0)

    def test_interior_lines_are_open_and_touch_the_border(self):
        params = PuzzleParams(width_mm=200, height_mm=150, columns=4, rows=3)
        puzzle = generate(params)
        for line in puzzle.horizontal:
            self.assertFalse(line.closed)
            self.assertAlmostEqual(line.start[0], 0.0)
            self.assertAlmostEqual(line.end[0], params.width_mm)
        for line in puzzle.vertical:
            self.assertFalse(line.closed)
            self.assertAlmostEqual(line.start[1], 0.0)
            self.assertAlmostEqual(line.end[1], params.height_mm)

    def test_every_cell_edge_gets_three_cubics(self):
        params = PuzzleParams(columns=4, rows=3)
        puzzle = generate(params)
        for line in puzzle.horizontal:
            self.assertEqual(len(cubics(line)), 3 * params.columns)
            self.assertEqual(len(line.segments), 3 * params.columns)
        for line in puzzle.vertical:
            self.assertEqual(len(cubics(line)), 3 * params.rows)

    def test_same_seed_is_reproducible(self):
        params = PuzzleParams(seed=1234, columns=5, rows=4)
        first = [path.to_svg() for path in generate(params).all()]
        second = [path.to_svg() for path in generate(params).all()]
        self.assertEqual(first, second)

    def test_different_seed_changes_the_tabs(self):
        base = {"columns": 5, "rows": 4}
        first = [
            path.to_svg()
            for path in generate(PuzzleParams(seed=1, **base)).all()
        ]
        second = [
            path.to_svg()
            for path in generate(PuzzleParams(seed=2, **base)).all()
        ]
        self.assertNotEqual(first, second)

    def test_values_stay_within_the_puzzle(self):
        params = PuzzleParams(
            width_mm=120, height_mm=90, columns=3, rows=3, seed=5
        )
        for path in generate(params).all():
            min_x, min_y, max_x, max_y = path.bounds()
            self.assertGreaterEqual(min_x, -1e-6)
            self.assertGreaterEqual(min_y, -1e-6)
            self.assertLessEqual(max_x, params.width_mm + 1e-6)
            self.assertLessEqual(max_y, params.height_mm + 1e-6)

    def test_tab_profile_without_jitter(self):
        """A tab is a 3t bulge with a t neck on the other side."""
        params = PuzzleParams(
            width_mm=100,
            height_mm=100,
            columns=1,
            rows=2,
            jitter_percent=0.0,
            tab_size_percent=20.0,
            seed=3,
        )
        line = generate(params).horizontal[0]
        offsets = {round(abs(point[1] - 50.0), 6) for point in line.polyline_points()}
        # 3t = 0.3 * cell (15 mm) on one side, t = 0.1 * cell (5 mm) on the
        # other; the rest lies on the line itself.
        self.assertEqual(offsets, {0.0, 5.0, 15.0})

    def test_tab_size_scales_the_bulge(self):
        def depth(percent: float) -> float:
            params = PuzzleParams(
                width_mm=100,
                height_mm=100,
                columns=1,
                rows=2,
                jitter_percent=0.0,
                tab_size_percent=percent,
                seed=3,
            )
            line = generate(params).horizontal[0]
            return max(abs(point[1] - 50.0) for point in line.polyline_points())

        self.assertAlmostEqual(depth(10.0), 7.5, places=6)
        self.assertAlmostEqual(depth(20.0), 15.0, places=6)

    def test_rng_is_consumed_exactly_as_expected(self):
        """Pins the random stream to the reference implementation."""
        params = PuzzleParams(columns=4, rows=3, seed=99)
        rng = SeededRandom(99)
        generate(params, rng)
        self.assertEqual(rng.state, 99 + expected_draw_count(params))

    def test_next_from_a_shared_stream_matches_a_fresh_one(self):
        """Two puzzles may share one seed sequence."""
        params = PuzzleParams(columns=2, rows=2, seed=5)
        stream = SeededRandom(5)
        first = generate(params, stream).all()
        second = generate(params, stream).all()
        alone = generate(params).all()

        self.assertEqual(
            [path.to_svg() for path in first], [path.to_svg() for path in alone]
        )
        self.assertNotEqual(
            [path.to_svg() for path in first], [path.to_svg() for path in second]
        )

    def test_border_radius_rounds_the_corners(self):
        square = generate(PuzzleParams(columns=1, rows=1))
        rounded = generate(
            PuzzleParams(columns=1, rows=1, border_radius_mm=10.0)
        )
        # One line per side, closed by an explicit return to the start.
        self.assertEqual(len(square.border.segments), 4)
        self.assertTrue(
            all(isinstance(s, Line) for s in square.border.segments)
        )
        self.assertTrue(square.border.is_closed)
        # Four corners become cubics; five lines remain.
        self.assertEqual(len(cubics(rounded.border)), 4)
        self.assertEqual(len(rounded.border.segments), 9)
        self.assertTrue(rounded.border.is_closed)

    def test_closing_a_path_returns_to_the_start(self):
        path = Path((0.0, 0.0)).line_to(10.0, 0.0).line_to(10.0, 5.0)
        path.close()
        self.assertEqual(path.end, path.start)
        self.assertTrue(path.is_closed)
        # Closing twice must not add a zero-length segment.
        segments = len(path.segments)
        path.close()
        self.assertEqual(len(path.segments), segments)


if __name__ == "__main__":
    unittest.main()
