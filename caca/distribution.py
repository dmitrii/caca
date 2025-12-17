# PURPOSE: Distribution strategies for random event date generation

from abc import ABC, abstractmethod
from datetime import date, timedelta
import numpy as np


class DistributionStrategy(ABC):
    """Abstract base class for event date distribution strategies."""

    @abstractmethod
    def generate_dates(self, year: int, count: int) -> list[date]:
        """Generate a sorted list of dates within the given year."""
        pass


class UniformDistribution(DistributionStrategy):
    """Uniform random distribution of events across the year."""

    def __init__(self, seed: int | None = None):
        self.rng = np.random.default_rng(seed)

    def generate_dates(self, year: int, count: int) -> list[date]:
        """Generate uniformly distributed dates within the year."""
        if count == 0:
            return []

        start = date(year, 1, 1)
        end = date(year, 12, 31)
        days_in_year = (end - start).days + 1

        # Generate random day offsets
        day_offsets = self.rng.integers(0, days_in_year, size=count)

        # Convert to dates and sort
        dates = [start + timedelta(days=int(offset)) for offset in day_offsets]
        dates.sort()

        return dates
