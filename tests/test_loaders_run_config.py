# PURPOSE: Tests for run config loader

import pytest
import tempfile
import os
from pathlib import Path
from caca.loaders.run_config_loader import load_run_config


class TestLoadRunConfig:
    def test_loads_complete_config(self, tmp_path, monkeypatch):
        # Change to tmp_path since paths are resolved relative to cwd
        monkeypatch.chdir(tmp_path)

        # Create simulation params file
        params_file = tmp_path / "params.yaml"
        params_file.write_text("""
iterations: 5000
convergence_threshold_dollars: 50
max_iterations: 10000
min_iterations: 500
""")

        # Create costs file
        costs_file = tmp_path / "costs.yaml"
        costs_file.write_text("""
primary_care_visit: 150-300
specialist_visit: 200-500
""")

        # Create plan file
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        plan_file = plans_dir / "test-plan.yaml"
        plan_file.write_text("""
plan_name: Test Plan
premium: 500
deductible_individual: 1000
deductible_family: 2000
oop_max_individual: 5000
oop_max_family: 10000
""")

        # Create profile file
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        profile_file = profiles_dir / "alice.yaml"
        profile_file.write_text("""
name: alice
primary_care_visit: 3
""")

        # Create run config with cwd-relative paths
        run_config = tmp_path / "run.yaml"
        run_config.write_text("""
simulation: params.yaml
costs: costs.yaml

plans:
  - plans/test-plan.yaml

people:
  - profiles/alice.yaml
""")

        config = load_run_config(run_config)

        assert config["simulation"]["iterations"] == 5000
        assert "primary_care_visit" in config["costs"]
        assert len(config["plans"]) == 1
        assert config["plans"][0].name == "Test Plan"
        assert len(config["people"]) == 1
        assert config["people"][0]["name"] == "alice"
