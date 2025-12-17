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


def complete_plan_data(**overrides):
    """Return a complete valid plan data dict, with optional overrides."""
    data = {
        "plan_name": "Test Plan",
        "premium": 500,
        "deductible_individual": 1000,
        "deductible_family": 2000,
        "oop_max_individual": 5000,
        "oop_max_family": 10000,
        # All required service fields (before deductible)
        "preventative_visit": 0,
        "primary_care_visit": 50,
        "specialist_visit": 100,
        "labs": 50,
        "imaging": 200,
        "outpatient_services": 0.3,
        "outpatient_rehabilitation_services": 50,
        "inpatient_services": 0.3,
        "emergency_room": 300,
        "urgent_care": 50,
        "tier_1_generic_drugs": 15,
        "tier_2_preferred_brand_drugs": 50,
        "tier_3_non_preferred_brand_drugs": 100,
        "tier_4_specialty_drugs": 0.2,
        # All required service fields (after deductible)
        "preventative_visit_after_deductible": 0,
        "primary_care_visit_after_deductible": 50,
        "specialist_visit_after_deductible": 100,
        "labs_after_deductible": 50,
        "imaging_after_deductible": 200,
        "outpatient_services_after_deductible": 0.3,
        "outpatient_rehabilitation_services_after_deductible": 50,
        "inpatient_services_after_deductible": 0.3,
        "emergency_room_after_deductible": 300,
        "urgent_care_after_deductible": 50,
        "tier_1_generic_drugs_after_deductible": 15,
        "tier_2_preferred_brand_drugs_after_deductible": 50,
        "tier_3_non_preferred_brand_drugs_after_deductible": 100,
        "tier_4_specialty_drugs_after_deductible": 0.2,
    }
    data.update(overrides)
    return data


class TestValidatePlan:
    def test_valid_plan_passes(self):
        plan_data = complete_plan_data()
        errors = validate_plan(plan_data, "test.yaml")
        assert errors == []

    def test_missing_required_field(self):
        plan_data = complete_plan_data()
        del plan_data["deductible_individual"]
        errors = validate_plan(plan_data, "test.yaml")
        assert len(errors) == 1
        assert "deductible_individual" in errors[0].message

    def test_missing_service_field(self):
        plan_data = complete_plan_data()
        del plan_data["primary_care_visit"]
        errors = validate_plan(plan_data, "test.yaml")
        assert len(errors) == 1
        assert "primary_care_visit" in errors[0].message

    def test_missing_after_deductible_field(self):
        plan_data = complete_plan_data()
        del plan_data["specialist_visit_after_deductible"]
        errors = validate_plan(plan_data, "test.yaml")
        assert len(errors) == 1
        assert "specialist_visit_after_deductible" in errors[0].message

    def test_deductible_exceeds_oop_max(self):
        plan_data = complete_plan_data(
            deductible_individual=10000,  # exceeds oop_max
            oop_max_individual=5000,
        )
        errors = validate_plan(plan_data, "test.yaml")
        assert len(errors) == 1
        assert "exceeds" in errors[0].message.lower()

    def test_invalid_coinsurance(self):
        plan_data = complete_plan_data(
            outpatient_services=1.5,  # invalid: > 1 but < 2
        )
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


class TestValidateRunConfigFile:
    def test_valid_run_config(self, tmp_path, monkeypatch):
        """Valid run config with all files present passes validation."""
        monkeypatch.chdir(tmp_path)

        # Create all referenced files
        params = tmp_path / "params.yaml"
        params.write_text("iterations: 1000\nconvergence_threshold_dollars: 50\nmax_iterations: 5000\nmin_iterations: 100\n")

        costs = tmp_path / "costs.yaml"
        costs.write_text("primary_care_visit_before_deductible: 100-200\nprimary_care_visit_after_deductible: 100-200\n")

        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        plan = plans_dir / "test.yaml"
        # Write a complete valid plan using the same fields as complete_plan_data()
        plan.write_text("""
plan_name: Test
premium: 500
deductible_individual: 1000
deductible_family: 2000
oop_max_individual: 5000
oop_max_family: 10000
preventative_visit: 0
primary_care_visit: 50
specialist_visit: 100
labs: 50
imaging: 200
outpatient_services: 0.3
outpatient_rehabilitation_services: 50
inpatient_services: 0.3
emergency_room: 300
urgent_care: 50
tier_1_generic_drugs: 15
tier_2_preferred_brand_drugs: 50
tier_3_non_preferred_brand_drugs: 100
tier_4_specialty_drugs: 0.2
preventative_visit_after_deductible: 0
primary_care_visit_after_deductible: 50
specialist_visit_after_deductible: 100
labs_after_deductible: 50
imaging_after_deductible: 200
outpatient_services_after_deductible: 0.3
outpatient_rehabilitation_services_after_deductible: 50
inpatient_services_after_deductible: 0.3
emergency_room_after_deductible: 300
urgent_care_after_deductible: 50
tier_1_generic_drugs_after_deductible: 15
tier_2_preferred_brand_drugs_after_deductible: 50
tier_3_non_preferred_brand_drugs_after_deductible: 100
tier_4_specialty_drugs_after_deductible: 0.2
""")

        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        profile = profiles_dir / "alice.yaml"
        profile.write_text("name: alice\nprimary_care_visit: 3\n")

        run_config = tmp_path / "run.yaml"
        run_config.write_text("""
simulation: params.yaml
costs: costs.yaml
plans:
  - plans/test.yaml
people:
  - profiles/alice.yaml
""")

        from caca.validation import validate_run_config_file
        errors = validate_run_config_file(run_config)
        assert errors == []

    def test_missing_simulation_file(self, tmp_path, monkeypatch):
        """Run config with missing simulation file reports error."""
        monkeypatch.chdir(tmp_path)

        run_config = tmp_path / "run.yaml"
        run_config.write_text("""
simulation: nonexistent.yaml
costs: costs.yaml
plans: []
people: []
""")

        from caca.validation import validate_run_config_file
        errors = validate_run_config_file(run_config)
        assert len(errors) >= 1
        assert any("nonexistent.yaml" in e.message for e in errors)

    def test_missing_plan_file(self, tmp_path, monkeypatch):
        """Run config with missing plan file reports error."""
        monkeypatch.chdir(tmp_path)

        params = tmp_path / "params.yaml"
        params.write_text("iterations: 1000\nconvergence_threshold_dollars: 50\nmax_iterations: 5000\nmin_iterations: 100\n")

        costs = tmp_path / "costs.yaml"
        costs.write_text("primary_care_visit_before_deductible: 100\nprimary_care_visit_after_deductible: 100\n")

        run_config = tmp_path / "run.yaml"
        run_config.write_text("""
simulation: params.yaml
costs: costs.yaml
plans:
  - plans/missing.yaml
people: []
""")

        from caca.validation import validate_run_config_file
        errors = validate_run_config_file(run_config)
        assert len(errors) >= 1
        assert any("missing.yaml" in e.message for e in errors)

    def test_missing_profile_file(self, tmp_path, monkeypatch):
        """Run config with missing profile file reports error."""
        monkeypatch.chdir(tmp_path)

        params = tmp_path / "params.yaml"
        params.write_text("iterations: 1000\nconvergence_threshold_dollars: 50\nmax_iterations: 5000\nmin_iterations: 100\n")

        costs = tmp_path / "costs.yaml"
        costs.write_text("primary_care_visit_before_deductible: 100\nprimary_care_visit_after_deductible: 100\n")

        run_config = tmp_path / "run.yaml"
        run_config.write_text("""
simulation: params.yaml
costs: costs.yaml
plans: []
people:
  - profiles/missing.yaml
""")

        from caca.validation import validate_run_config_file
        errors = validate_run_config_file(run_config)
        assert len(errors) >= 1
        assert any("missing.yaml" in e.message for e in errors)
