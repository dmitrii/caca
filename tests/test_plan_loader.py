# PURPOSE: Tests for CSV plan loading

import pytest
from io import StringIO
from caca.plan_loader import load_plans, parse_value
from caca.models import ServiceType


class TestParseValue:
    def test_parse_integer(self):
        assert parse_value("100") == 100.0

    def test_parse_float(self):
        assert parse_value("0.4") == 0.4

    def test_parse_with_dollar_sign(self):
        assert parse_value("$100") == 100.0

    def test_parse_with_percent(self):
        assert parse_value("40%") == 0.4

    def test_parse_with_comma(self):
        assert parse_value("8,650") == 8650.0

    def test_parse_empty(self):
        assert parse_value("") is None

    def test_parse_whitespace(self):
        assert parse_value("  ") is None


class TestLoadPlans:
    def test_load_single_plan(self):
        csv_content = """plan_name,test_plan
premium,1000
deductible_individual,2000
deductible_family,4000
oop_max_individual,5000
oop_max_family,10000
primary_care_visit,50
primary_care_visit_after_deductible,20
"""
        plans = load_plans(StringIO(csv_content))
        assert len(plans) == 1
        plan = plans[0]
        assert plan.name == "test_plan"
        assert plan.premium == 12000.0  # monthly premium * 12
        assert plan.deductible_individual == 2000.0
        assert plan.deductible_family == 4000.0
        assert plan.oop_max_individual == 5000.0
        assert plan.oop_max_family == 10000.0
        assert plan.service_costs[ServiceType.PRIMARY_CARE_VISIT] == 50.0
        assert plan.service_costs_after_deductible[ServiceType.PRIMARY_CARE_VISIT] == 20.0

    def test_load_multiple_plans(self):
        csv_content = """plan_name,plan_a,plan_b
premium,1000,2000
deductible_individual,2000,1000
deductible_family,4000,2000
oop_max_individual,5000,3000
oop_max_family,10000,6000
"""
        plans = load_plans(StringIO(csv_content))
        assert len(plans) == 2
        assert plans[0].name == "plan_a"
        assert plans[1].name == "plan_b"
        assert plans[0].premium == 12000.0  # monthly premium * 12
        assert plans[1].premium == 24000.0  # monthly premium * 12

    def test_coinsurance_value(self):
        csv_content = """plan_name,test_plan
premium,1000
deductible_individual,2000
deductible_family,4000
oop_max_individual,5000
oop_max_family,10000
imaging,1
imaging_after_deductible,0.4
"""
        plans = load_plans(StringIO(csv_content))
        plan = plans[0]
        # 1 means 100% patient responsibility
        assert plan.service_costs[ServiceType.IMAGING] == 1.0
        # 0.4 means 40% coinsurance
        assert plan.service_costs_after_deductible[ServiceType.IMAGING] == 0.4

    def test_rx_deductible(self):
        csv_content = """plan_name,test_plan
premium,1000
deductible_individual,2000
deductible_family,4000
deductible_rx_individual,500
deductible_rx_family,1000
oop_max_individual,5000
oop_max_family,10000
"""
        plans = load_plans(StringIO(csv_content))
        plan = plans[0]
        assert plan.deductible_rx_individual == 500.0
        assert plan.deductible_rx_family == 1000.0

    def test_empty_rx_deductible(self):
        csv_content = """plan_name,test_plan
premium,1000
deductible_individual,2000
deductible_family,4000
deductible_rx_individual,
deductible_rx_family,
oop_max_individual,5000
oop_max_family,10000
"""
        plans = load_plans(StringIO(csv_content))
        plan = plans[0]
        assert plan.deductible_rx_individual is None
        assert plan.deductible_rx_family is None
