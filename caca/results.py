# PURPOSE: Results storage and serialization

from dataclasses import dataclass, field
from datetime import datetime
from caca.models import ScenarioResult, Event


@dataclass
class ResultsStore:
    """Stores simulation results with serialization support."""

    iterations: int
    converged: bool
    convergence_threshold_dollars: float
    household: list[dict]
    plan_names: list[str]
    scenarios: list[ScenarioResult] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def add_scenario(self, scenario: ScenarioResult) -> None:
        """Add a scenario result."""
        self.scenarios.append(scenario)

    def get_plan_costs(self, plan_name: str) -> list[float]:
        """Get all costs for a specific plan."""
        return [
            s.plan_results[plan_name].total_cost
            for s in self.scenarios
            if plan_name in s.plan_results
        ]

    def to_json(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "metadata": {
                "iterations": self.iterations,
                "converged": self.converged,
                "convergence_threshold_dollars": self.convergence_threshold_dollars,
                "timestamp": self.timestamp.isoformat(),
            },
            "household": self.household,
            "plans": self.plan_names,
            "scenarios": [
                self._scenario_to_json(s) for s in self.scenarios
            ],
        }

    def _scenario_to_json(self, scenario: ScenarioResult) -> dict:
        """Convert a scenario to JSON."""
        return {
            "id": scenario.scenario_id,
            "events": [self._event_to_json(e) for e in scenario.events],
            "results_by_plan": {
                name: {
                    "total_cost": result.total_cost,
                    "premium": result.premium,
                    "out_of_pocket": result.out_of_pocket,
                    "deductible_hit_date": (
                        result.deductible_hit_date.isoformat()
                        if result.deductible_hit_date else None
                    ),
                    "oop_max_hit_date": (
                        result.oop_max_hit_date.isoformat()
                        if result.oop_max_hit_date else None
                    ),
                }
                for name, result in scenario.plan_results.items()
            },
        }

    def _event_to_json(self, event: Event) -> dict:
        """Convert an event to JSON."""
        return {
            "service_type": event.service_type.value,
            "cost": event.cost,
            "date": event.date.isoformat(),
            "person": event.person,
            "description": event.description,
        }
