# PURPOSE: Integration tests using real plans.csv and config

import pytest
from pathlib import Path
from io import StringIO
from caca.cli import main
from unittest.mock import patch
import sys


@pytest.fixture
def project_root():
    """Get project root directory."""
    return Path(__file__).parent.parent


class TestIntegration:
    def test_full_simulation_with_template(self, project_root, tmp_path, monkeypatch):
        """Test running simulation with template config."""
        # Change to tmp_path since new config uses cwd-relative paths
        monkeypatch.chdir(tmp_path)

        # Create simulation params file
        params_file = tmp_path / "params.yaml"
        params_file.write_text("""
iterations: 100
convergence_threshold_dollars: 50
max_iterations: 200
min_iterations: 50
""")

        # Create costs file
        costs_file = tmp_path / "costs.yaml"
        costs_file.write_text("""
preventative_visit_before_deductible: 0
preventative_visit_after_deductible: 0
primary_care_visit_before_deductible: 150-300
primary_care_visit_after_deductible: 150-300
specialist_visit_before_deductible: 200-500
specialist_visit_after_deductible: 200-500
labs_before_deductible: 100-500
labs_after_deductible: 100-500
imaging_before_deductible: 500-2500
imaging_after_deductible: 500-2500
emergency_room_before_deductible: 1500-5000
emergency_room_after_deductible: 1500-5000
urgent_care_before_deductible: 150-400
urgent_care_after_deductible: 150-400
inpatient_services_before_deductible: 15000-75000
inpatient_services_after_deductible: 15000-75000
outpatient_services_before_deductible: 2000-15000
outpatient_services_after_deductible: 2000-15000
outpatient_rehabilitation_services_before_deductible: 100-500
outpatient_rehabilitation_services_after_deductible: 100-500
tier_1_generic_drugs_before_deductible: 10-50
tier_1_generic_drugs_after_deductible: 10-50
tier_2_preferred_brand_drugs_before_deductible: 50-200
tier_2_preferred_brand_drugs_after_deductible: 50-200
tier_3_non_preferred_brand_drugs_before_deductible: 150-500
tier_3_non_preferred_brand_drugs_after_deductible: 150-500
tier_4_specialty_drugs_before_deductible: 500-2000
tier_4_specialty_drugs_after_deductible: 500-2000
""")

        # Create plan file
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        plan_file = plans_dir / "test-plan.yaml"
        plan_file.write_text("""
plan_name: Test Bronze PPO
premium: 200
deductible_individual: 5000
deductible_family: 10000
oop_max_individual: 8000
oop_max_family: 16000
""")

        # Create profile files
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()

        alice_profile = profiles_dir / "alice.yaml"
        alice_profile.write_text("""
name: alice
preventative_visit: 1
primary_care_visit: 2-4
specialist_visit: 0-2
labs: 1-3
emergency_room: { probability: 0.05 }
tier_1_generic_drugs: 0-6
""")

        bob_profile = profiles_dir / "bob.yaml"
        bob_profile.write_text("""
name: bob
preventative_visit: 1
primary_care_visit: 2-4
specialist_visit: 0-2
labs: 1-3
emergency_room: { probability: 0.05 }
tier_1_generic_drugs: 0-6
""")

        charlie_profile = profiles_dir / "charlie.yaml"
        charlie_profile.write_text("""
name: charlie
preventative_visit: 2
primary_care_visit: 4-6
specialist_visit: 1-2
urgent_care: { probability: 0.3, count: 1-2 }
""")

        # Create run config
        run_config = tmp_path / "run.yaml"
        run_config.write_text("""
simulation: params.yaml
costs: costs.yaml

plans:
  - plans/test-plan.yaml

people:
  - profiles/alice.yaml
  - profiles/bob.yaml
  - profiles/charlie.yaml
""")

        json_output = tmp_path / "results.json"

        output = StringIO()
        with patch.object(sys, "stdout", output):
            with patch.object(sys, "argv", [
                "caca",
                "generate",
                str(run_config),
                "--json", str(json_output),
            ]):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0

        result = output.getvalue()

        # Verify terminal output
        assert "Care Casino" in result
        assert "alice" in result
        assert "100" in result  # iterations

        # Verify JSON was created
        assert json_output.exists()

    def test_planned_surgery_scenario(self, project_root, tmp_path, monkeypatch):
        """Test with planned surgery for one family member."""
        monkeypatch.chdir(tmp_path)

        # Create simulation params file
        params_file = tmp_path / "params.yaml"
        params_file.write_text("""
iterations: 100
convergence_threshold_dollars: 50
max_iterations: 200
min_iterations: 50
""")

        # Create costs file
        costs_file = tmp_path / "costs.yaml"
        costs_file.write_text("""
preventative_visit_before_deductible: 0
preventative_visit_after_deductible: 0
primary_care_visit_before_deductible: 200
primary_care_visit_after_deductible: 200
specialist_visit_before_deductible: 350
specialist_visit_after_deductible: 350
labs_before_deductible: 250
labs_after_deductible: 250
imaging_before_deductible: 1500
imaging_after_deductible: 1500
emergency_room_before_deductible: 2000
emergency_room_after_deductible: 2000
urgent_care_before_deductible: 200
urgent_care_after_deductible: 200
inpatient_services_before_deductible: 50000
inpatient_services_after_deductible: 50000
outpatient_services_before_deductible: 5000
outpatient_services_after_deductible: 5000
outpatient_rehabilitation_services_before_deductible: 200
outpatient_rehabilitation_services_after_deductible: 200
tier_1_generic_drugs_before_deductible: 20
tier_1_generic_drugs_after_deductible: 20
tier_2_preferred_brand_drugs_before_deductible: 100
tier_2_preferred_brand_drugs_after_deductible: 100
tier_3_non_preferred_brand_drugs_before_deductible: 300
tier_3_non_preferred_brand_drugs_after_deductible: 300
tier_4_specialty_drugs_before_deductible: 1000
tier_4_specialty_drugs_after_deductible: 1000
""")

        # Create plan file
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        plan_file = plans_dir / "test-plan.yaml"
        plan_file.write_text("""
plan_name: Test Gold HMO
premium: 400
deductible_individual: 1000
deductible_family: 2000
oop_max_individual: 5000
oop_max_family: 10000
""")

        # Create profile files
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()

        spouse_profile = profiles_dir / "spouse.yaml"
        spouse_profile.write_text("""
name: spouse
primary_care_visit: 2
preventative_visit: 1
""")

        patient_profile = profiles_dir / "patient.yaml"
        patient_profile.write_text("""
name: patient
primary_care_visit: 4
specialist_visit:
  - { cost: 350, date: "2025-03-01", description: "pre-op consult" }
  - { cost: 350, date: "2025-05-01", description: "post-op follow-up" }
labs:
  - { cost: 250, date: "2025-03-01", description: "pre-op bloodwork" }
imaging:
  - { cost: 1500, date: "2025-03-01", description: "MRI" }
inpatient_services:
  - { cost: 50000, date: "2025-04-01", description: "knee replacement" }
""")

        # Create run config
        run_config = tmp_path / "run.yaml"
        run_config.write_text("""
simulation: params.yaml
costs: costs.yaml

plans:
  - plans/test-plan.yaml

people:
  - profiles/patient.yaml
  - profiles/spouse.yaml
""")

        output = StringIO()
        with patch.object(sys, "stdout", output):
            with patch.object(sys, "argv", [
                "caca",
                "generate",
                str(run_config),
            ]):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0

        result = output.getvalue()

        # With a $50k surgery, costs should be substantial
        assert "Care Casino" in result
        # Should see plan rankings
        assert "Rank" in result
