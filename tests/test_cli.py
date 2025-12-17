# PURPOSE: Tests for CLI entry point

import pytest
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch
from caca.cli import main, parse_args


class TestParseArgs:
    def test_minimal_args(self):
        args = parse_args(["config.yaml"])
        assert args.config == "config.yaml"
        assert args.plans == "plans.csv"
        assert args.json is None
        assert args.quiet is False

    def test_all_args(self):
        args = parse_args([
            "my_config.yaml",
            "--plans", "my_plans.csv",
            "--json", "output.json",
            "--quiet",
        ])
        assert args.config == "my_config.yaml"
        assert args.plans == "my_plans.csv"
        assert args.json == "output.json"
        assert args.quiet is True


class TestCLI:
    def test_missing_config_file(self, tmp_path):
        with pytest.raises(SystemExit):
            with patch.object(sys, "argv", ["caca", "nonexistent.yaml"]):
                main()

    def test_run_simulation(self, tmp_path):
        # Create minimal config
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
simulation:
  iterations: 10

defaults:
  costs:
    primary_care_visit: 200

profiles:
  test:
    primary_care_visit: 1

household:
  - name: alice
    profile: test
""")

        # Create minimal plans CSV
        plans_file = tmp_path / "plans.csv"
        plans_file.write_text("""plan_name,test_plan
premium,1000
deductible_individual,500
deductible_family,1000
oop_max_individual,2000
oop_max_family,4000
primary_care_visit,50
primary_care_visit_after_deductible,20
""")

        output = StringIO()
        with patch.object(sys, "stdout", output):
            with patch.object(sys, "argv", [
                "caca",
                str(config_file),
                "--plans", str(plans_file),
            ]):
                main()

        result = output.getvalue()
        assert "Care Casino" in result
        assert "test_plan" in result
