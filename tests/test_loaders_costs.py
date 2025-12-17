# PURPOSE: Tests for costs loader

import pytest
from io import StringIO
from caca.loaders.costs_loader import load_costs_yaml
from caca.models import CostRange


class TestLoadCostsYaml:
    def test_loads_cost_ranges(self):
        yaml_content = """
primary_care_visit: 150-300
specialist_visit: 200-500
labs: 100-500
"""
        costs = load_costs_yaml(StringIO(yaml_content))

        assert costs["primary_care_visit"] == CostRange(150, 300)
        assert costs["specialist_visit"] == CostRange(200, 500)

    def test_loads_fixed_costs(self):
        yaml_content = """
primary_care_visit: 200
"""
        costs = load_costs_yaml(StringIO(yaml_content))

        assert costs["primary_care_visit"] == CostRange(200, 200)
