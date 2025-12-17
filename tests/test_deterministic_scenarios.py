# PURPOSE: Tests with deterministic inputs to verify correct cost calculations

import pytest
from datetime import date
from caca.models import Event, ServiceType, PlanRules, CostRange
from caca.plan_calculator import PlanCalculator
from caca.simulation_runner import SimulationRunner


class TestDeterministicCostCalculations:
    """Tests with known inputs and expected outputs."""

    def test_single_copay_visit(self):
        """One primary care visit with $50 copay should cost exactly $50 OOP."""
        plan = PlanRules(
            name="Copay Plan",
            premium=12000,  # $1000/month
            deductible_individual=1000,
            deductible_family=2000,
            oop_max_individual=5000,
            oop_max_family=10000,
            service_costs={ServiceType.PRIMARY_CARE_VISIT: 50},  # $50 copay
            service_costs_after_deductible={ServiceType.PRIMARY_CARE_VISIT: 50},
        )
        calc = PlanCalculator(plan, ["alice"])

        events = [Event(
            service_type=ServiceType.PRIMARY_CARE_VISIT,
            cost=200,  # Actual cost doesn't matter for copay
            date=date(2025, 3, 15),
            person="alice",
        )]

        result = calc.calculate(events)

        assert result.premium == 12000
        assert result.out_of_pocket == 50
        assert result.total_cost == 12050

    def test_multiple_copay_visits(self):
        """Five visits at $50 copay each = $250 OOP."""
        plan = PlanRules(
            name="Copay Plan",
            premium=12000,
            deductible_individual=1000,
            deductible_family=2000,
            oop_max_individual=5000,
            oop_max_family=10000,
            service_costs={ServiceType.PRIMARY_CARE_VISIT: 50},
            service_costs_after_deductible={ServiceType.PRIMARY_CARE_VISIT: 50},
        )
        calc = PlanCalculator(plan, ["alice"])

        events = [
            Event(ServiceType.PRIMARY_CARE_VISIT, 200, date(2025, i, 15), "alice")
            for i in range(1, 6)  # 5 visits
        ]

        result = calc.calculate(events)

        assert result.out_of_pocket == 250  # 5 * $50
        assert result.total_cost == 12250

    def test_hdhp_under_deductible(self):
        """HDHP: $500 service when deductible is $1000 = pay full $500."""
        plan = PlanRules(
            name="HDHP",
            premium=6000,
            deductible_individual=1000,
            deductible_family=2000,
            oop_max_individual=3000,
            oop_max_family=6000,
            service_costs={ServiceType.SPECIALIST_VISIT: 1.0},  # 100% before deductible
            service_costs_after_deductible={ServiceType.SPECIALIST_VISIT: 0.2},  # 20% after
        )
        calc = PlanCalculator(plan, ["alice"])

        events = [Event(
            service_type=ServiceType.SPECIALIST_VISIT,
            cost=500,
            date=date(2025, 3, 15),
            person="alice",
        )]

        result = calc.calculate(events)

        assert result.out_of_pocket == 500
        assert result.total_cost == 6500
        assert result.deductible_hit_date is None  # Didn't hit deductible

    def test_hdhp_hits_deductible_exactly(self):
        """HDHP: $1000 service when deductible is $1000 = pay $1000, hit deductible."""
        plan = PlanRules(
            name="HDHP",
            premium=6000,
            deductible_individual=1000,
            deductible_family=2000,
            oop_max_individual=3000,
            oop_max_family=6000,
            service_costs={ServiceType.SPECIALIST_VISIT: 1.0},
            service_costs_after_deductible={ServiceType.SPECIALIST_VISIT: 0.2},
        )
        calc = PlanCalculator(plan, ["alice"])

        events = [Event(
            service_type=ServiceType.SPECIALIST_VISIT,
            cost=1000,
            date=date(2025, 3, 15),
            person="alice",
        )]

        result = calc.calculate(events)

        assert result.out_of_pocket == 1000
        assert result.total_cost == 7000
        assert result.deductible_hit_date == date(2025, 3, 15)

    def test_hdhp_exceeds_deductible(self):
        """HDHP: $2000 service when deductible is $1000.

        First $1000 goes to deductible (100%), remaining $1000 at 20% = $200.
        Total OOP = $1200.
        """
        plan = PlanRules(
            name="HDHP",
            premium=6000,
            deductible_individual=1000,
            deductible_family=2000,
            oop_max_individual=3000,
            oop_max_family=6000,
            service_costs={ServiceType.INPATIENT_SERVICES: 1.0},
            service_costs_after_deductible={ServiceType.INPATIENT_SERVICES: 0.2},
        )
        calc = PlanCalculator(plan, ["alice"])

        events = [Event(
            service_type=ServiceType.INPATIENT_SERVICES,
            cost=2000,
            date=date(2025, 4, 1),
            person="alice",
        )]

        result = calc.calculate(events)

        # $1000 to deductible + 20% of remaining $1000 = $1000 + $200 = $1200
        assert result.out_of_pocket == 1200
        assert result.total_cost == 7200
        assert result.deductible_hit_date == date(2025, 4, 1)

    def test_hdhp_hits_oop_max(self):
        """HDHP: Large surgery should hit OOP max.

        $50,000 surgery with $1000 deductible and $3000 OOP max:
        - First $1000 to deductible
        - Remaining $49,000 at 20% = $9,800, but capped at OOP max
        - Total OOP = $3000 (the OOP max)
        """
        plan = PlanRules(
            name="HDHP",
            premium=6000,
            deductible_individual=1000,
            deductible_family=2000,
            oop_max_individual=3000,
            oop_max_family=6000,
            service_costs={ServiceType.INPATIENT_SERVICES: 1.0},
            service_costs_after_deductible={ServiceType.INPATIENT_SERVICES: 0.2},
        )
        calc = PlanCalculator(plan, ["alice"])

        events = [Event(
            service_type=ServiceType.INPATIENT_SERVICES,
            cost=50000,
            date=date(2025, 4, 1),
            person="alice",
        )]

        result = calc.calculate(events)

        assert result.out_of_pocket == 3000  # OOP max
        assert result.total_cost == 9000  # $6000 premium + $3000 OOP max
        assert result.oop_max_hit_date == date(2025, 4, 1)

    def test_zero_deductible_hmo(self):
        """HMO with $0 deductible: copays apply immediately.

        $30 specialist copay, 5 visits = $150 OOP.
        """
        plan = PlanRules(
            name="HMO",
            premium=18000,
            deductible_individual=0,
            deductible_family=0,
            oop_max_individual=1500,
            oop_max_family=3000,
            service_costs={ServiceType.SPECIALIST_VISIT: 30},  # $30 copay
            service_costs_after_deductible={ServiceType.SPECIALIST_VISIT: 30},
        )
        calc = PlanCalculator(plan, ["alice"])

        events = [
            Event(ServiceType.SPECIALIST_VISIT, 500, date(2025, i, 15), "alice")
            for i in range(1, 6)
        ]

        result = calc.calculate(events)

        assert result.out_of_pocket == 150  # 5 * $30
        assert result.total_cost == 18150

    def test_preventative_always_free(self):
        """Preventative visits should cost $0 regardless of deductible status."""
        plan = PlanRules(
            name="Any Plan",
            premium=12000,
            deductible_individual=5000,  # High deductible
            deductible_family=10000,
            oop_max_individual=7000,
            oop_max_family=14000,
            service_costs={ServiceType.PREVENTATIVE_VISIT: 0},
            service_costs_after_deductible={ServiceType.PREVENTATIVE_VISIT: 0},
        )
        calc = PlanCalculator(plan, ["alice"])

        events = [
            Event(ServiceType.PREVENTATIVE_VISIT, 500, date(2025, 3, 15), "alice"),
            Event(ServiceType.PREVENTATIVE_VISIT, 300, date(2025, 9, 15), "alice"),
        ]

        result = calc.calculate(events)

        assert result.out_of_pocket == 0
        assert result.total_cost == 12000  # Premium only

    def test_family_individual_deductibles(self):
        """Two people, each has own deductible tracking.

        Plan: $1000 individual deductible, $2000 family deductible
        Alice: $800 in services (under her individual deductible)
        Bob: $800 in services (under his individual deductible)

        Neither hits individual deductible, family total is $1600 (under $2000).
        Both pay full cost = $1600 total OOP.
        """
        plan = PlanRules(
            name="Family Plan",
            premium=24000,
            deductible_individual=1000,
            deductible_family=2000,
            oop_max_individual=5000,
            oop_max_family=10000,
            service_costs={ServiceType.PRIMARY_CARE_VISIT: 1.0},
            service_costs_after_deductible={ServiceType.PRIMARY_CARE_VISIT: 0.2},
        )
        calc = PlanCalculator(plan, ["alice", "bob"])

        events = [
            Event(ServiceType.PRIMARY_CARE_VISIT, 400, date(2025, 2, 1), "alice"),
            Event(ServiceType.PRIMARY_CARE_VISIT, 400, date(2025, 3, 1), "alice"),
            Event(ServiceType.PRIMARY_CARE_VISIT, 400, date(2025, 4, 1), "bob"),
            Event(ServiceType.PRIMARY_CARE_VISIT, 400, date(2025, 5, 1), "bob"),
        ]

        result = calc.calculate(events)

        assert result.out_of_pocket == 1600
        assert result.deductible_hit_date is None  # Neither hit deductible

    def test_family_one_person_hits_individual_deductible(self):
        """Alice hits her $1000 individual deductible, Bob doesn't.

        Alice: $1500 in services
          - First $1000 at 100% (deductible)
          - Remaining $500 at 20% = $100
          - Alice OOP = $1100

        Bob: $500 in services at 100% (hasn't hit his deductible)
          - Bob OOP = $500

        Total OOP = $1600
        """
        plan = PlanRules(
            name="Family Plan",
            premium=24000,
            deductible_individual=1000,
            deductible_family=3000,  # High family deductible
            oop_max_individual=5000,
            oop_max_family=10000,
            service_costs={ServiceType.SPECIALIST_VISIT: 1.0},
            service_costs_after_deductible={ServiceType.SPECIALIST_VISIT: 0.2},
        )
        calc = PlanCalculator(plan, ["alice", "bob"])

        events = [
            Event(ServiceType.SPECIALIST_VISIT, 1500, date(2025, 3, 1), "alice"),
            Event(ServiceType.SPECIALIST_VISIT, 500, date(2025, 4, 1), "bob"),
        ]

        result = calc.calculate(events)

        # Alice: $1000 + 20% of $500 = $1100
        # Bob: $500 (full cost, hasn't hit deductible)
        assert result.out_of_pocket == 1600
        assert result.deductible_hit_date == date(2025, 3, 1)  # Alice hit hers


class TestDeterministicSimulation:
    """End-to-end tests with deterministic profiles."""

    def test_single_fixed_event_simulation(self):
        """Simulation with one scheduled event should give consistent results."""
        plan = PlanRules(
            name="Test Plan",
            premium=12000,
            deductible_individual=1000,
            deductible_family=2000,
            oop_max_individual=5000,
            oop_max_family=10000,
            service_costs={ServiceType.INPATIENT_SERVICES: 1.0},
            service_costs_after_deductible={ServiceType.INPATIENT_SERVICES: 0.2},
        )

        # Profile with one scheduled event at known cost
        profiles = {
            "surgery": {
                "inpatient_services": [
                    {
                        "scheduled": True,
                        "date": "2025-04-01",
                        "cost": 50000,
                        "count_min": 1,
                        "count_max": 1,
                    }
                ]
            }
        }

        runner = SimulationRunner(
            plans=[plan],
            profiles=profiles,
            household=[{"name": "alice", "profile": "surgery"}],
            default_costs={},
            year=2025,
            seed=42,
        )

        results = runner.run(iterations=100)

        # With a fixed $50k surgery:
        # $1000 deductible + 20% of $49000 = $1000 + $9800 = $10800
        # But OOP max is $5000, so OOP = $5000
        # Total = $12000 premium + $5000 OOP = $17000
        #
        # All scenarios should be identical
        summary = results.summary["Test Plan"]
        assert summary["expected_cost"] == 17000
        assert summary["min"] == 17000
        assert summary["max"] == 17000
        assert summary["ci_95_low"] == summary["ci_95_high"] == 17000

    def test_comparing_plans_deterministic(self):
        """Compare plans with deterministic input to verify ranking."""
        # High premium, low OOP plan
        hmo = PlanRules(
            name="HMO",
            premium=18000,
            deductible_individual=0,
            deductible_family=0,
            oop_max_individual=1500,
            oop_max_family=3000,
            service_costs={ServiceType.INPATIENT_SERVICES: 0},  # $0 for surgery
            service_costs_after_deductible={ServiceType.INPATIENT_SERVICES: 0},
        )

        # Low premium, high OOP plan
        hdhp = PlanRules(
            name="HDHP",
            premium=6000,
            deductible_individual=3000,
            deductible_family=6000,
            oop_max_individual=6000,
            oop_max_family=12000,
            service_costs={ServiceType.INPATIENT_SERVICES: 1.0},
            service_costs_after_deductible={ServiceType.INPATIENT_SERVICES: 0.2},
        )

        # Expensive surgery scenario
        profiles = {
            "surgery": {
                "inpatient_services": [
                    {
                        "scheduled": True,
                        "date": "2025-04-01",
                        "cost": 100000,
                        "count_min": 1,
                        "count_max": 1,
                    }
                ]
            }
        }

        runner = SimulationRunner(
            plans=[hmo, hdhp],
            profiles=profiles,
            household=[{"name": "alice", "profile": "surgery"}],
            default_costs={},
            year=2025,
            seed=42,
        )

        results = runner.run(iterations=50)

        # HMO: $18000 premium + $0 OOP = $18000
        # HDHP: $6000 premium + $6000 OOP max = $12000
        #
        # For expensive surgery, HDHP wins!
        ranked = results.get_ranked_plans()
        assert ranked[0][0] == "HDHP"
        assert ranked[0][1] == 12000
        assert ranked[1][0] == "HMO"
        assert ranked[1][1] == 18000

    def test_light_usage_favors_low_premium(self):
        """With minimal usage, low premium plan should win."""
        hmo = PlanRules(
            name="HMO",
            premium=18000,
            deductible_individual=0,
            deductible_family=0,
            oop_max_individual=1500,
            oop_max_family=3000,
            service_costs={ServiceType.PRIMARY_CARE_VISIT: 15},
            service_costs_after_deductible={ServiceType.PRIMARY_CARE_VISIT: 15},
        )

        hdhp = PlanRules(
            name="HDHP",
            premium=6000,
            deductible_individual=3000,
            deductible_family=6000,
            oop_max_individual=6000,
            oop_max_family=12000,
            service_costs={ServiceType.PRIMARY_CARE_VISIT: 1.0},
            service_costs_after_deductible={ServiceType.PRIMARY_CARE_VISIT: 0.2},
        )

        # Minimal usage: 2 PCP visits at fixed cost
        profiles = {
            "healthy": {
                "primary_care_visit": [
                    {
                        "scheduled": True,
                        "date": "2025-03-01",
                        "cost": 200,
                        "count_min": 1,
                        "count_max": 1,
                    },
                    {
                        "scheduled": True,
                        "date": "2025-09-01",
                        "cost": 200,
                        "count_min": 1,
                        "count_max": 1,
                    },
                ]
            }
        }

        runner = SimulationRunner(
            plans=[hmo, hdhp],
            profiles=profiles,
            household=[{"name": "alice", "profile": "healthy"}],
            default_costs={},
            year=2025,
            seed=42,
        )

        results = runner.run(iterations=50)

        # HMO: $18000 premium + 2 * $15 copay = $18030
        # HDHP: $6000 premium + 2 * $200 (full cost under deductible) = $6400
        ranked = results.get_ranked_plans()
        assert ranked[0][0] == "HDHP"
        assert ranked[0][1] == 6400
        assert ranked[1][0] == "HMO"
        assert ranked[1][1] == 18030
