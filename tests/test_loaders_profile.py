# PURPOSE: Tests for profile loader

import pytest
from io import StringIO
from caca.loaders.profile_loader import load_profile_yaml


class TestLoadProfileYaml:
    def test_loads_basic_profile(self):
        yaml_content = """
name: alice
primary_care_visit: 3
specialist_visit: 2
labs: 5
"""
        profile = load_profile_yaml(StringIO(yaml_content))

        assert profile["name"] == "alice"
        assert profile["usage"]["primary_care_visit"] == [
            {"count_min": 3, "count_max": 3, "probability": 1.0, "scheduled": False}
        ]

    def test_loads_range_counts(self):
        yaml_content = """
name: bob
primary_care_visit: 2-5
"""
        profile = load_profile_yaml(StringIO(yaml_content))

        assert profile["usage"]["primary_care_visit"] == [
            {"count_min": 2, "count_max": 5, "probability": 1.0, "scheduled": False}
        ]

    def test_loads_probability_events(self):
        yaml_content = """
name: carol
emergency_room:
  probability: 0.1
  count: 1
"""
        profile = load_profile_yaml(StringIO(yaml_content))

        assert profile["usage"]["emergency_room"][0]["probability"] == 0.1
        assert profile["usage"]["emergency_room"][0]["count_min"] == 1
