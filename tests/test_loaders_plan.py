# PURPOSE: Tests for YAML plan loader

import pytest
from io import StringIO
from caca.loaders.plan_loader import load_plan_yaml
from caca.models import ServiceType


class TestLoadPlanYaml:
    def test_loads_basic_plan(self):
        yaml_content = """
plan_name: Test Plan
premium: 500.00
deductible_individual: 1000
deductible_family: 2000
oop_max_individual: 5000
oop_max_family: 10000
primary_care_visit: 30
primary_care_visit_after_deductible: 30
"""
        plan = load_plan_yaml(StringIO(yaml_content))

        assert plan.name == "Test Plan"
        assert plan.premium == 6000.0  # monthly * 12
        assert plan.deductible_individual == 1000
        assert plan.deductible_family == 2000
        assert plan.oop_max_individual == 5000
        assert plan.oop_max_family == 10000
        assert plan.service_costs[ServiceType.PRIMARY_CARE_VISIT] == 30

    def test_handles_coinsurance(self):
        yaml_content = """
plan_name: Coinsurance Plan
premium: 400
deductible_individual: 2000
deductible_family: 4000
oop_max_individual: 8000
oop_max_family: 16000
outpatient_services: 0.3
outpatient_services_after_deductible: 0.3
"""
        plan = load_plan_yaml(StringIO(yaml_content))

        assert plan.service_costs[ServiceType.OUTPATIENT_SERVICES] == 0.3

    def test_handles_percentage_format(self):
        yaml_content = """
plan_name: Percent Plan
premium: 400
deductible_individual: 2000
deductible_family: 4000
oop_max_individual: 8000
oop_max_family: 16000
outpatient_services: 30%
outpatient_services_after_deductible: 30%
"""
        plan = load_plan_yaml(StringIO(yaml_content))

        assert plan.service_costs[ServiceType.OUTPATIENT_SERVICES] == 0.3

    def test_preserves_comments_in_source(self):
        # Comments should be ignored during parsing (YAML handles this)
        yaml_content = """
# This is a comment
plan_name: Commented Plan
premium: 400  # monthly premium
deductible_individual: 2000
deductible_family: 4000
oop_max_individual: 8000
oop_max_family: 16000
"""
        plan = load_plan_yaml(StringIO(yaml_content))

        assert plan.name == "Commented Plan"
