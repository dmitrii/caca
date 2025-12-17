# PURPOSE: Tests for YAML config loading

import pytest
from io import StringIO
from caca.config_loader import load_config, parse_cost_range, parse_usage_entry
from caca.models import CostRange


class TestParseCostRange:
    def test_parse_single_value(self):
        result = parse_cost_range("500")
        assert result == CostRange(500.0, 500.0)

    def test_parse_range(self):
        result = parse_cost_range("100-500")
        assert result == CostRange(100.0, 500.0)

    def test_parse_with_dollar_signs(self):
        result = parse_cost_range("$100-$500")
        assert result == CostRange(100.0, 500.0)

    def test_parse_integer(self):
        result = parse_cost_range(500)
        assert result == CostRange(500.0, 500.0)


class TestParseUsageEntry:
    def test_simple_count(self):
        result = parse_usage_entry("2-5")
        assert result["count_min"] == 2
        assert result["count_max"] == 5
        assert result["probability"] == 1.0

    def test_single_count(self):
        result = parse_usage_entry("3")
        assert result["count_min"] == 3
        assert result["count_max"] == 3

    def test_integer_count(self):
        result = parse_usage_entry(3)
        assert result["count_min"] == 3
        assert result["count_max"] == 3

    def test_probability_only(self):
        result = parse_usage_entry({"probability": 0.05})
        assert result["probability"] == 0.05
        assert result["count_min"] == 1
        assert result["count_max"] == 1

    def test_probability_with_count(self):
        result = parse_usage_entry({"probability": 0.3, "count": "1-2"})
        assert result["probability"] == 0.3
        assert result["count_min"] == 1
        assert result["count_max"] == 2

    def test_scheduled_event(self):
        result = parse_usage_entry({"cost": 300, "date": "2025-03-15", "description": "pre-op"})
        assert result["cost"] == 300.0
        assert result["date"] == "2025-03-15"
        assert result["description"] == "pre-op"
        assert result["scheduled"] is True

    def test_scheduled_with_count(self):
        result = parse_usage_entry({"count": 12, "cost": 800})
        assert result["count_min"] == 12
        assert result["count_max"] == 12
        assert result["cost"] == 800.0


class TestLoadConfig:
    def test_load_minimal_config(self):
        yaml_content = """
simulation:
  iterations: 1000

defaults:
  costs:
    primary_care_visit: 200

profiles:
  test_profile:
    primary_care_visit: 2-3

household:
  - name: alice
    profile: test_profile
"""
        config = load_config(StringIO(yaml_content))
        assert config["simulation"]["iterations"] == 1000
        assert config["defaults"]["costs"]["primary_care_visit"] == CostRange(200.0, 200.0)
        assert config["household"][0]["name"] == "alice"

    def test_load_auto_iterations(self):
        yaml_content = """
simulation:
  iterations: auto
  convergence_threshold_dollars: 100
  max_iterations: 50000
  min_iterations: 500

defaults:
  costs: {}

profiles: {}

household: []
"""
        config = load_config(StringIO(yaml_content))
        assert config["simulation"]["iterations"] == "auto"
        assert config["simulation"]["convergence_threshold_dollars"] == 100
        assert config["simulation"]["max_iterations"] == 50000
        assert config["simulation"]["min_iterations"] == 500

    def test_profile_with_list_entries(self):
        yaml_content = """
simulation:
  iterations: 1000

defaults:
  costs: {}

profiles:
  surgery_person:
    specialist_visit:
      - { cost: 300, date: "2025-03-15" }
      - { count: 2-4 }

household: []
"""
        config = load_config(StringIO(yaml_content))
        profile = config["profiles"]["surgery_person"]
        assert len(profile["specialist_visit"]) == 2
