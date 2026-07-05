# PURPOSE: Tests for data models

import pytest
from datetime import date
from caca.models import (
    Event,
    ServiceType,
    Person,
    Household,
    SimulationConfig,
    PlanRules,
    ScenarioResult,
    PlanResult,
)


class TestEvent:
    def test_create_event(self):
        event = Event(
            service_type=ServiceType.SPECIALIST_VISIT,
            cost=300.0,
            date=date(2025, 3, 15),
            person="alice",
            description="pre-op consult",
        )
        assert event.service_type == ServiceType.SPECIALIST_VISIT
        assert event.cost == 300.0
        assert event.date == date(2025, 3, 15)
        assert event.person == "alice"
        assert event.description == "pre-op consult"

    def test_event_without_description(self):
        event = Event(
            service_type=ServiceType.PRIMARY_CARE_VISIT,
            cost=200.0,
            date=date(2025, 6, 1),
            person="bob",
        )
        assert event.description is None


class TestServiceType:
    def test_service_types_exist(self):
        assert ServiceType.PREVENTATIVE_VISIT
        assert ServiceType.PRIMARY_CARE_VISIT
        assert ServiceType.SPECIALIST_VISIT
        assert ServiceType.LABS
        assert ServiceType.IMAGING
        assert ServiceType.OUTPATIENT_SERVICES
        assert ServiceType.INPATIENT_SERVICES
        assert ServiceType.EMERGENCY_ROOM
        assert ServiceType.URGENT_CARE
        assert ServiceType.TIER_1_GENERIC_DRUGS
        assert ServiceType.TIER_2_PREFERRED_BRAND_DRUGS
        assert ServiceType.TIER_3_NON_PREFERRED_BRAND_DRUGS
        assert ServiceType.TIER_4_SPECIALTY_DRUGS
        assert ServiceType.UNCOVERED

    def test_is_drug(self):
        assert ServiceType.TIER_1_GENERIC_DRUGS.is_drug() is True
        assert ServiceType.TIER_4_SPECIALTY_DRUGS.is_drug() is True
        assert ServiceType.PRIMARY_CARE_VISIT.is_drug() is False


class TestPerson:
    def test_create_person(self):
        person = Person(name="alice", profile="healthy_adult")
        assert person.name == "alice"
        assert person.profile == "healthy_adult"


class TestHousehold:
    def test_create_household(self):
        household = Household(
            members=[
                Person(name="alice", profile="planned_surgery"),
                Person(name="bob", profile="healthy_adult"),
            ]
        )
        assert len(household.members) == 2
        assert household.members[0].name == "alice"


class TestPlanRules:
    def test_create_plan_rules(self):
        rules = PlanRules(
            name="Test Plan",
            premium=1000.0,
            deductible_individual=1500.0,
            deductible_family=3000.0,
            oop_max_individual=5000.0,
            oop_max_family=10000.0,
            service_costs={},
            service_costs_after_deductible={},
        )
        assert rules.name == "Test Plan"
        assert rules.premium == 1000.0
        assert rules.deductible_individual == 1500.0


def test_plan_rules_subsidy_defaults_to_zero():
    from caca.models import PlanRules
    plan = PlanRules(
        name="P", premium=12000, deductible_individual=0, deductible_family=0,
        oop_max_individual=5000, oop_max_family=10000,
        service_costs={}, service_costs_after_deductible={},
    )
    assert plan.subsidy == 0.0
    assert plan.effective_premium(gross=False) == 12000
    assert plan.effective_premium(gross=True) == 12000


def test_effective_premium_subtracts_subsidy_when_net():
    from caca.models import PlanRules
    plan = PlanRules(
        name="P", premium=12000, deductible_individual=0, deductible_family=0,
        oop_max_individual=5000, oop_max_family=10000,
        service_costs={}, service_costs_after_deductible={}, subsidy=9000,
    )
    assert plan.effective_premium(gross=False) == 3000
    assert plan.effective_premium(gross=True) == 12000


class TestScenarioResult:
    def test_create_scenario_result(self):
        result = ScenarioResult(
            scenario_id=1,
            events=[],
            plan_results={},
        )
        assert result.scenario_id == 1


class TestPlanResult:
    def test_create_plan_result(self):
        result = PlanResult(
            total_cost=5000.0,
            premium=3000.0,
            out_of_pocket=2000.0,
            deductible_hit_date=date(2025, 4, 15),
            oop_max_hit_date=None,
        )
        assert result.total_cost == 5000.0
        assert result.premium == 3000.0
        assert result.out_of_pocket == 2000.0
        assert result.deductible_hit_date == date(2025, 4, 15)
        assert result.oop_max_hit_date is None
