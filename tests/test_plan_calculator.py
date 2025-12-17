# PURPOSE: Tests for plan cost calculation

import pytest
from datetime import date
from caca.plan_calculator import PlanCalculator
from caca.models import Event, ServiceType, PlanRules, PlanResult


def make_plan(
    name="Test Plan",
    premium=12000,
    deductible_individual=2000,
    deductible_family=4000,
    oop_max_individual=5000,
    oop_max_family=10000,
    **kwargs,
) -> PlanRules:
    """Helper to create a plan with defaults."""
    return PlanRules(
        name=name,
        premium=premium,
        deductible_individual=deductible_individual,
        deductible_family=deductible_family,
        oop_max_individual=oop_max_individual,
        oop_max_family=oop_max_family,
        service_costs=kwargs.get("service_costs", {}),
        service_costs_after_deductible=kwargs.get("service_costs_after_deductible", {}),
        deductible_rx_individual=kwargs.get("deductible_rx_individual"),
        deductible_rx_family=kwargs.get("deductible_rx_family"),
        oop_max_rx_individual=kwargs.get("oop_max_rx_individual"),
        oop_max_rx_family=kwargs.get("oop_max_rx_family"),
        oop_max_per_rx=kwargs.get("oop_max_per_rx"),
        deductible_model=kwargs.get("deductible_model", "individual_first"),
    )


def make_event(
    service_type=ServiceType.PRIMARY_CARE_VISIT,
    cost=200,
    day=15,
    month=1,
    person="alice",
) -> Event:
    """Helper to create an event."""
    return Event(
        service_type=service_type,
        cost=cost,
        date=date(2025, month, day),
        person=person,
    )


class TestPlanCalculatorBasics:
    def test_premium_only_no_events(self):
        plan = make_plan(premium=12000)
        calc = PlanCalculator(plan, ["alice"])

        result = calc.calculate([])

        assert result.premium == 12000
        assert result.out_of_pocket == 0
        assert result.total_cost == 12000

    def test_preventative_visit_free(self):
        plan = make_plan(
            service_costs={ServiceType.PREVENTATIVE_VISIT: 0},
            service_costs_after_deductible={ServiceType.PREVENTATIVE_VISIT: 0},
        )
        calc = PlanCalculator(plan, ["alice"])

        events = [make_event(service_type=ServiceType.PREVENTATIVE_VISIT, cost=500)]
        result = calc.calculate(events)

        assert result.out_of_pocket == 0

    def test_copay_before_deductible(self):
        plan = make_plan(
            service_costs={ServiceType.PRIMARY_CARE_VISIT: 50},  # $50 copay
            service_costs_after_deductible={ServiceType.PRIMARY_CARE_VISIT: 50},
        )
        calc = PlanCalculator(plan, ["alice"])

        events = [make_event(cost=200)]
        result = calc.calculate(events)

        # Should pay $50 copay regardless of deductible
        assert result.out_of_pocket == 50

    def test_full_cost_before_deductible(self):
        plan = make_plan(
            deductible_individual=2000,
            service_costs={ServiceType.PRIMARY_CARE_VISIT: 1.0},  # 100% before deductible
            service_costs_after_deductible={ServiceType.PRIMARY_CARE_VISIT: 0.2},
        )
        calc = PlanCalculator(plan, ["alice"])

        events = [make_event(cost=500)]
        result = calc.calculate(events)

        # Should pay full $500, haven't hit deductible
        assert result.out_of_pocket == 500

    def test_coinsurance_after_deductible(self):
        plan = make_plan(
            deductible_individual=500,
            service_costs={ServiceType.PRIMARY_CARE_VISIT: 1.0},
            service_costs_after_deductible={ServiceType.PRIMARY_CARE_VISIT: 0.2},
        )
        calc = PlanCalculator(plan, ["alice"])

        events = [
            make_event(cost=500, day=1),   # Hits deductible exactly
            make_event(cost=1000, day=2),  # 20% coinsurance = $200
        ]
        result = calc.calculate(events)

        assert result.out_of_pocket == 500 + 200
        assert result.deductible_hit_date == date(2025, 1, 1)

    def test_oop_max_caps_costs(self):
        plan = make_plan(
            deductible_individual=1000,
            oop_max_individual=2000,
            service_costs={ServiceType.INPATIENT_SERVICES: 1.0},
            service_costs_after_deductible={ServiceType.INPATIENT_SERVICES: 0.2},
        )
        calc = PlanCalculator(plan, ["alice"])

        # $1000 to deductible, then 20% of $50000 = $10000, but capped at OOP max
        events = [make_event(service_type=ServiceType.INPATIENT_SERVICES, cost=51000)]
        result = calc.calculate(events)

        assert result.out_of_pocket == 2000
        assert result.oop_max_hit_date == date(2025, 1, 15)


class TestFamilyDeductibles:
    def test_individual_deductible_tracked_separately(self):
        plan = make_plan(
            deductible_individual=1000,
            deductible_family=2000,
            service_costs={ServiceType.PRIMARY_CARE_VISIT: 1.0},
            service_costs_after_deductible={ServiceType.PRIMARY_CARE_VISIT: 0.2},
        )
        calc = PlanCalculator(plan, ["alice", "bob"])

        events = [
            make_event(cost=1000, person="alice", day=1),  # Alice hits individual deductible
            make_event(cost=500, person="alice", day=2),   # Alice pays 20% = $100
            make_event(cost=500, person="bob", day=3),     # Bob hasn't hit deductible, pays full
        ]
        result = calc.calculate(events)

        # Alice: $1000 + $100 = $1100
        # Bob: $500
        assert result.out_of_pocket == 1600

    def test_family_deductible_individual_first_model(self):
        plan = make_plan(
            deductible_individual=1000,
            deductible_family=1500,
            service_costs={ServiceType.INPATIENT_SERVICES: 1.0},
            service_costs_after_deductible={ServiceType.INPATIENT_SERVICES: 0.2},
            deductible_model="individual_first",
        )
        calc = PlanCalculator(plan, ["alice", "bob"])

        # Alice has catastrophic event, exceeds family deductible alone
        events = [
            make_event(service_type=ServiceType.INPATIENT_SERVICES, cost=5000, person="alice", day=1),
            make_event(cost=500, person="bob", day=2),  # Bob should pay 20% since family deductible met
        ]
        result = calc.calculate(events)

        # Alice: $1500 (family deductible) + 20% of $3500 = $1500 + $700 = $2200
        # Bob: 20% of $500 = $100 (family deductible already met)
        assert result.out_of_pocket == 2300


class TestUncoveredServices:
    def test_uncovered_bypasses_plan(self):
        plan = make_plan()
        calc = PlanCalculator(plan, ["alice"])

        events = [
            make_event(service_type=ServiceType.UNCOVERED, cost=1000),
        ]
        result = calc.calculate(events)

        # Uncovered goes straight to OOP, doesn't count toward deductible
        assert result.out_of_pocket == 1000


class TestRxDeductibles:
    def test_separate_rx_deductible(self):
        plan = make_plan(
            deductible_individual=2000,
            deductible_rx_individual=500,
            service_costs={
                ServiceType.PRIMARY_CARE_VISIT: 1.0,
                ServiceType.TIER_1_GENERIC_DRUGS: 1.0,
            },
            service_costs_after_deductible={
                ServiceType.PRIMARY_CARE_VISIT: 0.2,
                ServiceType.TIER_1_GENERIC_DRUGS: 20,  # $20 copay after Rx deductible
            },
        )
        calc = PlanCalculator(plan, ["alice"])

        events = [
            make_event(service_type=ServiceType.TIER_1_GENERIC_DRUGS, cost=100, day=1),
            make_event(service_type=ServiceType.TIER_1_GENERIC_DRUGS, cost=100, day=2),
            make_event(service_type=ServiceType.TIER_1_GENERIC_DRUGS, cost=100, day=3),
            make_event(service_type=ServiceType.TIER_1_GENERIC_DRUGS, cost=100, day=4),
            make_event(service_type=ServiceType.TIER_1_GENERIC_DRUGS, cost=100, day=5),  # Hits $500 Rx deductible
            make_event(service_type=ServiceType.TIER_1_GENERIC_DRUGS, cost=100, day=6),  # After Rx deductible, $20 copay
        ]
        result = calc.calculate(events)

        # First 5 drugs: $500 (Rx deductible)
        # 6th drug: $20 copay
        assert result.out_of_pocket == 520
