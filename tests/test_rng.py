"""Unit tests for the seeded random generator."""

from __future__ import annotations

import math
import unittest

from puzzle_maker.core.rng import SeededRandom


class TestSeededRandom(unittest.TestCase):
    def test_first_value_matches_reference_formula(self):
        rng = SeededRandom(1)
        expected = math.sin(1.0) * 10000.0
        expected -= math.floor(expected)
        self.assertAlmostEqual(rng.random(), expected, places=12)

    def test_values_are_in_unit_interval(self):
        rng = SeededRandom(42)
        for _ in range(500):
            value = rng.random()
            self.assertGreaterEqual(value, 0.0)
            self.assertLess(value, 1.0)

    def test_same_seed_gives_same_stream(self):
        left = SeededRandom(7)
        right = SeededRandom(7)
        self.assertEqual(
            [left.random() for _ in range(50)],
            [right.random() for _ in range(50)],
        )

    def test_different_seed_gives_different_stream(self):
        left = SeededRandom(1)
        right = SeededRandom(2)
        self.assertNotEqual(
            [left.random() for _ in range(10)],
            [right.random() for _ in range(10)],
        )

    def test_state_advances_by_one(self):
        rng = SeededRandom(3)
        self.assertEqual(rng.state, 3.0)
        rng.random()
        self.assertEqual(rng.state, 4.0)

    def test_uniform_respects_bounds(self):
        rng = SeededRandom(11)
        values = [rng.uniform(-0.25, 0.25) for _ in range(200)]
        self.assertTrue(all(-0.25 <= value < 0.25 for value in values))
        # Jitter must not be biased to one side.
        self.assertTrue(any(value < 0 for value in values))
        self.assertTrue(any(value > 0 for value in values))

    def test_rbool_is_boolean_and_not_constant(self):
        rng = SeededRandom(5)
        results = [rng.rbool() for _ in range(200)]
        self.assertTrue(all(isinstance(value, bool) for value in results))
        self.assertTrue(any(results))
        self.assertFalse(all(results))


if __name__ == "__main__":
    unittest.main()
