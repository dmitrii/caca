# PURPOSE: Tests for event distribution strategies

import pytest
from datetime import date
import numpy as np
from caca.distribution import DistributionStrategy, UniformDistribution


class TestUniformDistribution:
    def test_generates_dates_in_year(self):
        dist = UniformDistribution(seed=42)
        year = 2025
        dates = dist.generate_dates(year, count=100)

        assert len(dates) == 100
        for d in dates:
            assert d.year == year
            assert date(year, 1, 1) <= d <= date(year, 12, 31)

    def test_deterministic_with_seed(self):
        dist1 = UniformDistribution(seed=42)
        dist2 = UniformDistribution(seed=42)

        dates1 = dist1.generate_dates(2025, count=10)
        dates2 = dist2.generate_dates(2025, count=10)

        assert dates1 == dates2

    def test_different_with_different_seed(self):
        dist1 = UniformDistribution(seed=42)
        dist2 = UniformDistribution(seed=123)

        dates1 = dist1.generate_dates(2025, count=10)
        dates2 = dist2.generate_dates(2025, count=10)

        assert dates1 != dates2

    def test_generates_sorted_dates(self):
        dist = UniformDistribution(seed=42)
        dates = dist.generate_dates(2025, count=50)

        assert dates == sorted(dates)

    def test_zero_count(self):
        dist = UniformDistribution(seed=42)
        dates = dist.generate_dates(2025, count=0)

        assert dates == []


class TestDistributionStrategyInterface:
    def test_is_abstract(self):
        # DistributionStrategy should not be instantiable directly
        with pytest.raises(TypeError):
            DistributionStrategy()
