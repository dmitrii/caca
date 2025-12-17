# PURPOSE: Tests for validation module

import pytest
import tempfile
from pathlib import Path
from caca.validation import (
    validate_plan,
    validate_profile,
    validate_costs,
    validate_run_config,
    ValidationError,
)


class TestValidatePlan:
    def test_valid_plan_passes(self):
        plan_data = {
            "plan_name": "Test Plan",
            "premium": 500,
            "deductible_individual": 1000,
            "deductible_family": 2000,
            "oop_max_individual": 5000,
            "oop_max_family": 10000,
        }
        errors = validate_plan(plan_data, "test.yaml")
        assert errors == []

    def test_missing_required_field(self):
        plan_data = {
            "plan_name": "Test Plan",
            "premium": 500,
            # missing deductible_individual
            "deductible_family": 2000,
            "oop_max_individual": 5000,
            "oop_max_family": 10000,
        }
        errors = validate_plan(plan_data, "test.yaml")
        assert len(errors) == 1
        assert "deductible_individual" in errors[0].message

    def test_deductible_exceeds_oop_max(self):
        plan_data = {
            "plan_name": "Test Plan",
            "premium": 500,
            "deductible_individual": 10000,  # exceeds oop_max
            "deductible_family": 2000,
            "oop_max_individual": 5000,
            "oop_max_family": 10000,
        }
        errors = validate_plan(plan_data, "test.yaml")
        assert len(errors) == 1
        assert "exceeds" in errors[0].message.lower()

    def test_invalid_coinsurance(self):
        plan_data = {
            "plan_name": "Test Plan",
            "premium": 500,
            "deductible_individual": 1000,
            "deductible_family": 2000,
            "oop_max_individual": 5000,
            "oop_max_family": 10000,
            "outpatient_services": 1.5,  # invalid: > 1
        }
        errors = validate_plan(plan_data, "test.yaml")
        assert len(errors) == 1
        assert "coinsurance" in errors[0].message.lower()


class TestValidateProfile:
    def test_valid_profile_passes(self):
        profile_data = {"name": "alice", "primary_care_visit": 3}
        errors = validate_profile(profile_data, "alice.yaml")
        assert errors == []

    def test_missing_name(self):
        profile_data = {"primary_care_visit": 3}
        errors = validate_profile(profile_data, "alice.yaml")
        assert len(errors) == 1
        assert "name" in errors[0].message.lower()


class TestValidateDuplicates:
    def test_duplicate_plan_names(self, tmp_path):
        # Create two plans with same name
        plan1 = tmp_path / "plan1.yaml"
        plan1.write_text("""
plan_name: Duplicate Name
premium: 500
deductible_individual: 1000
deductible_family: 2000
oop_max_individual: 5000
oop_max_family: 10000
""")
        plan2 = tmp_path / "plan2.yaml"
        plan2.write_text("""
plan_name: Duplicate Name
premium: 600
deductible_individual: 1000
deductible_family: 2000
oop_max_individual: 5000
oop_max_family: 10000
""")

        run_config = {
            "plans": [plan1, plan2],
            "people": [],
        }
        errors = validate_run_config(run_config, tmp_path / "run.yaml")
        assert any("duplicate" in e.message.lower() for e in errors)
