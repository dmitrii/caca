# PURPOSE: Tests for simulation parameters loader

import pytest
from io import StringIO
from caca.loaders.params_loader import load_params_yaml


class TestLoadParamsYaml:
    def test_loads_basic_params(self):
        yaml_content = """
iterations: auto
convergence_threshold_dollars: 100
max_iterations: 100000
min_iterations: 1000
"""
        params = load_params_yaml(StringIO(yaml_content))

        assert params["iterations"] == "auto"
        assert params["convergence_threshold_dollars"] == 100
        assert params["max_iterations"] == 100000
        assert params["min_iterations"] == 1000

    def test_loads_numeric_iterations(self):
        yaml_content = """
iterations: 5000
convergence_threshold_dollars: 50
"""
        params = load_params_yaml(StringIO(yaml_content))

        assert params["iterations"] == 5000
