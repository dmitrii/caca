# PURPOSE: Tests for simulation runner

import pytest
from caca.simulation_runner import SimulationRunner
from caca.models import PlanRules, ServiceType, CostRange


def make_simple_plan(name: str, premium: float, deductible: float) -> PlanRules:
    return PlanRules(
        name=name,
        premium=premium,
        deductible_individual=deductible,
        deductible_family=deductible * 2,
        oop_max_individual=deductible * 2,
        oop_max_family=deductible * 4,
        service_costs={ServiceType.PRIMARY_CARE_VISIT: 1.0},
        service_costs_after_deductible={ServiceType.PRIMARY_CARE_VISIT: 0.2},
    )


class TestSimulationRunner:
    def test_run_fixed_iterations(self):
        plans = [
            make_simple_plan("cheap", 1000, 500),
            make_simple_plan("expensive", 2000, 100),
        ]
        profiles = {
            "test": {
                "primary_care_visit": [
                    {"count_min": 2, "count_max": 5, "probability": 1.0, "scheduled": False}
                ]
            }
        }
        household = [{"name": "alice", "profile": "test"}]
        default_costs = {"primary_care_visit": CostRange(100, 200)}

        runner = SimulationRunner(
            plans=plans,
            profiles=profiles,
            household=household,
            default_costs=default_costs,
            year=2025,
            seed=42,
        )

        results = runner.run(iterations=100)

        assert results.iterations == 100
        assert len(results.scenarios) == 100
        assert "cheap" in results.summary
        assert "expensive" in results.summary

    def test_convergence_tracking(self):
        plans = [make_simple_plan("test", 1000, 500)]
        profiles = {
            "test": {
                "primary_care_visit": [
                    {"count_min": 1, "count_max": 1, "probability": 1.0, "scheduled": False}
                ]
            }
        }
        household = [{"name": "alice", "profile": "test"}]
        default_costs = {"primary_care_visit": CostRange(100, 100)}  # Fixed cost

        runner = SimulationRunner(
            plans=plans,
            profiles=profiles,
            household=household,
            default_costs=default_costs,
            year=2025,
            seed=42,
        )

        results = runner.run(iterations=50)

        # With fixed cost, CI should be very tight
        summary = results.summary["test"]
        assert summary["ci_95_high"] - summary["ci_95_low"] < 100

    def test_auto_convergence(self):
        plans = [make_simple_plan("test", 1000, 500)]
        profiles = {
            "test": {
                "primary_care_visit": [
                    {"count_min": 1, "count_max": 3, "probability": 1.0, "scheduled": False}
                ]
            }
        }
        household = [{"name": "alice", "profile": "test"}]
        default_costs = {"primary_care_visit": CostRange(100, 200)}

        runner = SimulationRunner(
            plans=plans,
            profiles=profiles,
            household=household,
            default_costs=default_costs,
            year=2025,
            seed=42,
        )

        results = runner.run(
            iterations="auto",
            convergence_threshold_dollars=50,
            min_iterations=100,
            max_iterations=10000,
        )

        assert results.converged is True
        assert results.iterations >= 100
        assert results.iterations <= 10000

    def test_plan_ranking(self):
        plans = [
            make_simple_plan("expensive", 5000, 100),  # High premium, low deductible
            make_simple_plan("cheap", 1000, 500),      # Low premium, high deductible
        ]
        profiles = {
            "light_user": {
                "primary_care_visit": [
                    {"count_min": 1, "count_max": 2, "probability": 1.0, "scheduled": False}
                ]
            }
        }
        household = [{"name": "alice", "profile": "light_user"}]
        default_costs = {"primary_care_visit": CostRange(100, 150)}

        runner = SimulationRunner(
            plans=plans,
            profiles=profiles,
            household=household,
            default_costs=default_costs,
            year=2025,
            seed=42,
        )

        results = runner.run(iterations=500)

        # For light users, cheap plan should win
        ranked = results.get_ranked_plans()
        assert ranked[0][0] == "cheap"


def test_runner_gross_flag_controls_premium():
    from caca.models import PlanRules
    from caca.simulation_runner import SimulationRunner

    plan = PlanRules(
        name="Subsidized", premium=12000, deductible_individual=0, deductible_family=0,
        oop_max_individual=5000, oop_max_family=10000,
        service_costs={}, service_costs_after_deductible={}, subsidy=9000,
    )
    household = [{"name": "alice", "profile": "empty"}]

    net_runner = SimulationRunner(
        plans=[plan], profiles={"empty": {}}, household=household,
        default_costs={}, year=2025, seed=1,
    )
    net = net_runner.run(iterations=10, min_iterations=10)
    assert net.summary["Subsidized"]["expected_cost"] == 3000

    gross_runner = SimulationRunner(
        plans=[plan], profiles={"empty": {}}, household=household,
        default_costs={}, year=2025, seed=1, gross=True,
    )
    gross = gross_runner.run(iterations=10, min_iterations=10)
    assert gross.summary["Subsidized"]["expected_cost"] == 12000
