# PURPOSE: Monte Carlo simulation runner with adaptive convergence

from dataclasses import dataclass, field
import numpy as np
from caca.models import PlanRules, CostRange, ScenarioResult, PlanResult, Event
from caca.distribution import UniformDistribution
from caca.event_generator import EventGenerator
from caca.plan_calculator import PlanCalculator


@dataclass
class SimulationResults:
    """Results from a simulation run."""

    iterations: int
    converged: bool
    scenarios: list[ScenarioResult]
    summary: dict[str, dict]  # plan_name -> stats

    def get_ranked_plans(self) -> list[tuple[str, float]]:
        """Return plans ranked by expected cost (lowest first)."""
        ranked = [
            (name, stats["expected_cost"])
            for name, stats in self.summary.items()
        ]
        ranked.sort(key=lambda x: x[1])
        return ranked


class SimulationRunner:
    """Runs Monte Carlo simulations across multiple plans."""

    def __init__(
        self,
        plans: list[PlanRules],
        profiles: dict,
        household: list[dict],
        default_costs: dict[str, CostRange],
        year: int,
        seed: int | None = None,
        gross: bool = False,
    ):
        self.plans = plans
        self.profiles = profiles
        self.household = household
        self.default_costs = default_costs
        self.year = year
        self.seed = seed
        self.gross = gross
        self.rng = np.random.default_rng(seed)

    def run(
        self,
        iterations: int | str = 1000,
        convergence_threshold_dollars: float = 100,
        min_iterations: int = 1000,
        max_iterations: int = 100000,
    ) -> SimulationResults:
        """Run the simulation."""
        auto_converge = iterations == "auto"
        target_iterations = max_iterations if auto_converge else iterations

        scenarios: list[ScenarioResult] = []
        plan_costs: dict[str, list[float]] = {p.name: [] for p in self.plans}

        converged = False
        batch_size = 100

        household_members = [m["name"] for m in self.household]

        i = 0
        while i < target_iterations:
            # Run a batch
            batch_end = min(i + batch_size, target_iterations)
            for scenario_id in range(i, batch_end):
                # Generate events for this scenario
                scenario_seed = self.rng.integers(0, 2**31)
                events = self._generate_scenario_events(scenario_seed)

                # Calculate costs for each plan
                plan_results: dict[str, PlanResult] = {}
                for plan in self.plans:
                    calc = PlanCalculator(plan, household_members, gross=self.gross)
                    result = calc.calculate(events)
                    plan_results[plan.name] = result
                    plan_costs[plan.name].append(result.total_cost)

                scenarios.append(ScenarioResult(
                    scenario_id=scenario_id,
                    events=events,
                    plan_results=plan_results,
                ))

            i = batch_end

            # Check convergence if auto mode and past minimum
            if auto_converge and i >= min_iterations:
                if self._check_convergence(plan_costs, convergence_threshold_dollars):
                    converged = True
                    break

        # Build summary statistics
        summary = self._build_summary(plan_costs)

        return SimulationResults(
            iterations=len(scenarios),
            converged=converged or not auto_converge,
            scenarios=scenarios,
            summary=summary,
        )

    def _generate_scenario_events(self, seed: int) -> list[Event]:
        """Generate all events for one scenario."""
        all_events: list[Event] = []

        distribution = UniformDistribution(seed=seed)
        generator = EventGenerator(
            distribution=distribution,
            default_costs=self.default_costs,
            year=self.year,
            seed=seed,
        )

        for member in self.household:
            profile_name = member["profile"]
            profile = self.profiles.get(profile_name, {})
            events = generator.generate_events(member["name"], profile)
            all_events.extend(events)

        # Sort all events by date
        all_events.sort(key=lambda e: e.date)
        return all_events

    def _check_convergence(
        self,
        plan_costs: dict[str, list[float]],
        threshold: float,
    ) -> bool:
        """Check if all plans have converged."""
        for costs in plan_costs.values():
            if len(costs) < 100:
                return False

            arr = np.array(costs)
            sem = np.std(arr, ddof=1) / np.sqrt(len(arr))
            ci_width = 2 * 1.96 * sem  # 95% CI width

            if ci_width > threshold:
                return False

        return True

    def _build_summary(self, plan_costs: dict[str, list[float]]) -> dict[str, dict]:
        """Build summary statistics for each plan."""
        summary = {}

        for plan_name, costs in plan_costs.items():
            arr = np.array(costs)
            mean = float(np.mean(arr))
            std = float(np.std(arr, ddof=1))
            sem = std / np.sqrt(len(arr))

            summary[plan_name] = {
                "expected_cost": mean,
                "std_dev": std,
                "ci_95_low": mean - 1.96 * sem,
                "ci_95_high": mean + 1.96 * sem,
                "min": float(np.min(arr)),
                "max": float(np.max(arr)),
                "percentiles": {
                    "10": float(np.percentile(arr, 10)),
                    "25": float(np.percentile(arr, 25)),
                    "50": float(np.percentile(arr, 50)),
                    "75": float(np.percentile(arr, 75)),
                    "90": float(np.percentile(arr, 90)),
                },
            }

        return summary
