"""Unit tests for the SVG writer."""

from __future__ import annotations

import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from puzzle_maker.core.jigsaw import PuzzleParams, generate
from puzzle_maker.core.svg import (
    paths_to_svg,
    puzzle_to_svg,
    write_puzzle_svg,
)

SVG_NS = "{http://www.w3.org/2000/svg}"
NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


class TestPuzzleToSvg(unittest.TestCase):
    def setUp(self):
        self.params = PuzzleParams(
            width_mm=200.0, height_mm=150.0, columns=4, rows=3, seed=11
        )
        self.svg = puzzle_to_svg(self.params)

    def test_is_well_formed_xml(self):
        root = ET.fromstring(self.svg)
        self.assertEqual(root.tag, f"{SVG_NS}svg")

    def test_physical_size_and_viewbox(self):
        root = ET.fromstring(self.svg)
        self.assertEqual(root.get("width"), "200.000mm")
        self.assertEqual(root.get("height"), "150.000mm")
        self.assertEqual(root.get("viewBox"), "0 0 200.000 150.000")

    def test_single_path_element_with_one_subpath_per_line(self):
        """One path element, so Rayforge imports one workpiece."""
        root = ET.fromstring(self.svg)
        paths = root.findall(f"{SVG_NS}path")
        self.assertEqual(len(paths), 1)
        puzzle = generate(self.params)
        self.assertEqual(
            paths[0].get("d").count("M "), len(puzzle.all())
        )

    def test_cubic_count_matches_the_grid(self):
        root = ET.fromstring(self.svg)
        data = root.find(f"{SVG_NS}path").get("d")
        params = self.params
        expected = 3 * (params.rows - 1) * params.columns + 3 * (
            params.columns - 1
        ) * params.rows
        self.assertEqual(data.count("C "), expected)

    def test_no_transforms_or_hidden_attributes(self):
        """Rayforge resolves units itself; keep the document plain."""
        self.assertNotIn("transform", self.svg)
        self.assertNotIn("<g", self.svg)

    def test_hairline_stroke_and_no_fill(self):
        self.assertIn('stroke-width="0.1"', self.svg)
        self.assertIn('fill="none"', self.svg)

    def test_coordinates_are_inside_the_document(self):
        root = ET.fromstring(self.svg)
        data = root.find(f"{SVG_NS}path").get("d")
        numbers = [float(value) for value in NUMBER.findall(data)]
        xs = numbers[0::2]
        ys = numbers[1::2]
        self.assertGreaterEqual(min(xs), -1e-6)
        self.assertLessEqual(max(xs), self.params.width_mm + 1e-6)
        self.assertGreaterEqual(min(ys), -1e-6)
        self.assertLessEqual(max(ys), self.params.height_mm + 1e-6)

    def test_y_axis_is_flipped(self):
        height = self.params.height_mm
        puzzle = generate(self.params)
        for path in puzzle.all():
            min_x, min_y, max_x, max_y = path.bounds()
            f_min_x, f_min_y, f_max_x, f_max_y = path.flipped_y(height).bounds()
            self.assertAlmostEqual(f_min_x, min_x)
            self.assertAlmostEqual(f_max_x, max_x)
            self.assertAlmostEqual(f_min_y, height - max_y)
            self.assertAlmostEqual(f_max_y, height - min_y)

    def test_same_params_give_identical_bytes(self):
        self.assertEqual(self.svg, puzzle_to_svg(self.params))

    def test_other_seed_gives_other_document(self):
        other = puzzle_to_svg(
            PuzzleParams(
                width_mm=200.0, height_mm=150.0, columns=4, rows=3, seed=12
            )
        )
        self.assertNotEqual(self.svg, other)


class TestPathsToSvg(unittest.TestCase):
    def test_rejects_empty_input(self):
        with self.assertRaises(ValueError):
            paths_to_svg([], 100.0, 100.0)

    def test_rejects_nonsense_size(self):
        with self.assertRaises(ValueError):
            paths_to_svg(generate(PuzzleParams()).all(), 0.0, 100.0)


class TestWritePuzzleSvg(unittest.TestCase):
    def test_writes_the_same_content_as_the_string_api(self):
        params = PuzzleParams(columns=2, rows=2, seed=3)
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "puzzle.svg"
            returned = write_puzzle_svg(target, params)
            self.assertEqual(returned, target)
            self.assertEqual(
                target.read_text(encoding="utf-8"),
                puzzle_to_svg(params),
            )


if __name__ == "__main__":
    unittest.main()
