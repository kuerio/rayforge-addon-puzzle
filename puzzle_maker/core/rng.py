"""Deterministic pseudo-random numbers, compatible with the reference
jigsaw generators (Draradech's ``jigsaw.html``, CC0).

The exact sequence matters: it makes puzzles reproducible from a seed and
lets us compare output against the reference implementation.
"""

from __future__ import annotations

import math

__all__ = ["SeededRandom"]


class SeededRandom:
    """The ``sin(seed)``-fract generator used by the reference tools.

    Note that ``seed`` is advanced by one for every draw, so the stream
    is fully determined by the initial seed.
    """

    __slots__ = ("_seed",)

    def __init__(self, seed: int | float = 1) -> None:
        self._seed = float(seed)

    @property
    def state(self) -> float:
        """The next value that will be fed into the generator."""
        return self._seed

    def random(self) -> float:
        """A float in ``[0, 1)``, advancing the stream."""
        x = math.sin(self._seed) * 10000.0
        self._seed += 1.0
        return x - math.floor(x)

    def uniform(self, low: float, high: float) -> float:
        """A float in ``[low, high)``."""
        return low + self.random() * (high - low)

    def rbool(self) -> bool:
        """A random boolean."""
        return self.random() > 0.5
