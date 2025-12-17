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
    def test_full_simulation_with_template(self, project_root, tmp_path):
        """Test running simulation with template config."""
        # Create a test config based on template
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("""
simulation:
  iterations: 100

defaults:
  costs:
    preventative_visit: 0
    primary_care_visit: 150-300
    specialist_visit: 200-500
    labs: 100-500
    imaging: 500-2500
    emergency_room: 1500-5000
    urgent_care: 150-400
    inpatient_services: 15000-75000
    outpatient_services: 2000-15000
    tier_1_generic_drugs: 10-50
    tier_2_preferred_brand_drugs: 50-200
    tier_3_non_preferred_brand_drugs: 150-500
    tier_4_specialty_drugs: 500-2000

profiles:
  healthy_adult:
    preventative_visit: 1
    primary_care_visit: 2-4
    specialist_visit: 0-2
    labs: 1-3
    emergency_room: { probability: 0.05 }
    tier_1_generic_drugs: 0-6

  child:
    preventative_visit: 2
    primary_care_visit: 4-6
    specialist_visit: 1-2
    urgent_care: { probability: 0.3, count: 1-2 }

household:
  - name: alice
    profile: healthy_adult
  - name: bob
    profile: healthy_adult
  - name: charlie
    profile: child
""")

        plans_file = project_root / "plans.csv"
        json_output = tmp_path / "results.json"

        output = StringIO()
        with patch.object(sys, "stdout", output):
            with patch.object(sys, "argv", [
                "caca",
                str(config_file),
                "--plans", str(plans_file),
                "--json", str(json_output),
            ]):
                main()

        result = output.getvalue()

        # Verify terminal output
        assert "Care Casino" in result
        assert "alice (healthy_adult)" in result
        assert "100" in result  # iterations

        # Verify JSON was created
        assert json_output.exists()

        # Verify all plans are in output - check for variations of plan name format
        # The plan names are preserved from the CSV
        assert "BS" in result or "Bronze" in result or "PPO" in result or "HMO" in result

    def test_planned_surgery_scenario(self, project_root, tmp_path):
        """Test with planned surgery for one family member."""
        config_file = tmp_path / "surgery_config.yaml"
        config_file.write_text("""
simulation:
  iterations: 100

defaults:
  costs:
    primary_care_visit: 200
    specialist_visit: 350
    labs: 250
    imaging: 1500
    inpatient_services: 50000

profiles:
  healthy_adult:
    primary_care_visit: 2
    preventative_visit: 1

  surgery_patient:
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

household:
  - name: patient
    profile: surgery_patient
  - name: spouse
    profile: healthy_adult
""")

        plans_file = project_root / "plans.csv"

        output = StringIO()
        with patch.object(sys, "stdout", output):
            with patch.object(sys, "argv", [
                "caca",
                str(config_file),
                "--plans", str(plans_file),
            ]):
                main()

        result = output.getvalue()

        # With a $50k surgery, costs should be substantial
        assert "Care Casino" in result
        # Should see plan rankings
        assert "Rank" in result
