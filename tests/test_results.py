# PURPOSE: Tests for results data structure

import pytest
from datetime import date
from caca.results import ResultsStore
from caca.models import ScenarioResult, PlanResult, Event, ServiceType


class TestResultsStore:
    def test_create_store(self):
        store = ResultsStore(
            iterations=100,
            converged=True,
            convergence_threshold_dollars=100,
            household=[{"name": "alice", "profile": "test"}],
            plan_names=["plan_a", "plan_b"],
        )
        assert store.iterations == 100
        assert store.converged is True

    def test_add_scenario(self):
        store = ResultsStore(
            iterations=0,
            converged=False,
            convergence_threshold_dollars=100,
            household=[],
            plan_names=["test"],
        )

        scenario = ScenarioResult(
            scenario_id=0,
            events=[],
            plan_results={"test": PlanResult(
                total_cost=1000,
                premium=800,
                out_of_pocket=200,
                deductible_hit_date=None,
                oop_max_hit_date=None,
            )},
        )

        store.add_scenario(scenario)

        assert len(store.scenarios) == 1
        assert store.get_plan_costs("test") == [1000]

    def test_to_json(self):
        store = ResultsStore(
            iterations=1,
            converged=True,
            convergence_threshold_dollars=100,
            household=[{"name": "alice", "profile": "test"}],
            plan_names=["test_plan"],
        )

        store.add_scenario(ScenarioResult(
            scenario_id=0,
            events=[Event(
                service_type=ServiceType.PRIMARY_CARE_VISIT,
                cost=200,
                date=date(2025, 3, 15),
                person="alice",
                description="checkup",
            )],
            plan_results={"test_plan": PlanResult(
                total_cost=1200,
                premium=1000,
                out_of_pocket=200,
                deductible_hit_date=None,
                oop_max_hit_date=None,
            )},
        ))

        json_data = store.to_json()

        assert json_data["metadata"]["iterations"] == 1
        assert json_data["metadata"]["converged"] is True
        assert len(json_data["scenarios"]) == 1
        assert json_data["scenarios"][0]["events"][0]["service_type"] == "primary_care_visit"
