# PURPOSE: Tests for JSON export

import pytest
import json
from io import StringIO
from caca.output.json_export import JsonExporter
from caca.results import ResultsStore
from caca.models import ScenarioResult, PlanResult


class TestJsonExporter:
    def test_export_to_file(self):
        store = ResultsStore(
            iterations=10,
            converged=True,
            convergence_threshold_dollars=100,
            household=[{"name": "alice", "profile": "test"}],
            plan_names=["test_plan"],
        )

        for i in range(10):
            store.add_scenario(ScenarioResult(
                scenario_id=i,
                events=[],
                plan_results={"test_plan": PlanResult(
                    total_cost=1000 + i * 10,
                    premium=800,
                    out_of_pocket=200 + i * 10,
                    deductible_hit_date=None,
                    oop_max_hit_date=None,
                )},
            ))

        summary = {
            "test_plan": {
                "expected_cost": 1045,
                "ci_95_low": 1000,
                "ci_95_high": 1090,
                "min": 1000,
                "max": 1090,
                "percentiles": {"50": 1045},
            }
        }

        exporter = JsonExporter()
        output = StringIO()

        exporter.export(output, store, summary)

        result = json.loads(output.getvalue())
        assert result["metadata"]["iterations"] == 10
        assert result["summary"]["test_plan"]["expected_cost"] == 1045
        assert len(result["scenarios"]) == 10

    def test_export_minimal(self):
        store = ResultsStore(
            iterations=1,
            converged=False,
            convergence_threshold_dollars=100,
            household=[],
            plan_names=["a"],
        )

        exporter = JsonExporter()
        output = StringIO()

        exporter.export(output, store, {"a": {"expected_cost": 100}})

        result = json.loads(output.getvalue())
        assert "metadata" in result
        assert "summary" in result
