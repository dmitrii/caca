# PURPOSE: Terminal output rendering with ASCII tables and histograms

from typing import TextIO
from caca.models import ServiceType


class TerminalRenderer:
    """Renders simulation results to terminal."""

    def __init__(self, width: int = 80, histogram_width: int = 79):
        self.width = width
        self.histogram_width = histogram_width

    def format_currency(self, amount: float) -> str:
        """Format a number as currency."""
        return f"${amount:,.0f}"

    def render_header(
        self,
        output: TextIO,
        household: list[dict],
        iterations: int,
        converged: bool,
        convergence_threshold: float,
    ) -> None:
        """Render the report header."""
        output.write("\n")
        output.write("Care Casino - Healthcare Plan Simulator\n")
        output.write("=" * 40 + "\n\n")

        # Household
        def format_member(m):
            if m['name'] == m['profile']:
                return m['name']
            return f"{m['name']} ({m['profile']})"
        members = ", ".join(format_member(m) for m in household)
        output.write(f"Household: {members}\n")

        # Iterations
        if converged:
            output.write(f"Scenarios simulated: {iterations:,} (converged at +/-${convergence_threshold:.0f})\n")
        else:
            output.write(f"Scenarios simulated: {iterations:,}\n")

        output.write("\n")

    def render_rankings(self, output: TextIO, summary: dict[str, dict]) -> None:
        """Render the plan rankings table."""
        output.write("Plan Rankings (by expected annual cost)\n")
        output.write("=" * 40 + "\n")

        # Sort by expected cost
        ranked = sorted(summary.items(), key=lambda x: x[1]["expected_cost"])

        # Header
        output.write(f"{'Rank':<5} {'Plan':<30} {'Expected':<12} {'95% CI':<20} {'Best':<10} {'Worst':<10}\n")
        output.write("-" * 97 + "\n")

        for rank, (name, stats) in enumerate(ranked, 1):
            expected = self.format_currency(stats["expected_cost"])
            ci = f"{self.format_currency(stats['ci_95_low'])}-{self.format_currency(stats['ci_95_high'])}"
            best = self.format_currency(stats["min"])
            worst = self.format_currency(stats["max"])

            output.write(f"{rank:<5} {name:<30} {expected:<12} {ci:<20} {best:<10} {worst:<10}\n")

        output.write("\n")

    def render_histogram(
        self,
        output: TextIO,
        plan_name: str,
        costs: list[float],
        global_min: float | None = None,
        global_max: float | None = None,
    ) -> None:
        """Render an ASCII histogram of costs with consistent axis."""
        if not costs:
            return

        local_min = min(costs)
        local_max = max(costs)

        # Use global range if provided, otherwise use local
        axis_min = global_min if global_min is not None else local_min
        axis_max = global_max if global_max is not None else local_max

        if local_max == local_min:
            output.write(f"{plan_name}: all scenarios = {self.format_currency(local_min)}\n")
            return

        output.write(f"{plan_name}\n")

        # Calculate where this plan's data falls on the global axis
        bar_width = self.histogram_width
        bins = bar_width

        # Calculate histogram bins across the global range
        bin_width = (axis_max - axis_min) / bins
        bin_counts = [0] * bins

        for cost in costs:
            bin_idx = min(int((cost - axis_min) / bin_width), bins - 1)
            bin_counts[bin_idx] += 1

        max_count = max(bin_counts) if bin_counts else 1

        # Render range line
        output.write(f"{self.format_currency(axis_min)} |")
        output.write("=" * bar_width)
        output.write(f"| {self.format_currency(axis_max)}\n")

        # Render distribution
        output.write(" " * (len(self.format_currency(axis_min)) + 2))
        for count in bin_counts:
            if max_count > 0:
                height = count / max_count
                if height > 0.75:
                    output.write("#")
                elif height > 0.5:
                    output.write("*")
                elif height > 0.25:
                    output.write("+")
                elif height > 0:
                    output.write(".")
                else:
                    output.write(" ")
        output.write("\n\n")

    def render_full_report(
        self,
        output: TextIO,
        household: list[dict],
        iterations: int,
        converged: bool,
        convergence_threshold: float,
        summary: dict[str, dict],
        plan_costs: dict[str, list[float]],
    ) -> None:
        """Render the complete report."""
        self.render_header(output, household, iterations, converged, convergence_threshold)
        self.render_rankings(output, summary)

        output.write("Cost Distribution\n")
        output.write("=" * 40 + "\n")

        # Calculate global min/max across all plans for consistent axis
        all_costs = [cost for costs in plan_costs.values() for cost in costs]
        global_min = min(all_costs) if all_costs else 0
        global_max = max(all_costs) if all_costs else 0

        # Sort by expected cost for consistent ordering
        ranked = sorted(summary.items(), key=lambda x: x[1]["expected_cost"])
        for name, _ in ranked:
            if name in plan_costs:
                self.render_histogram(output, name, plan_costs[name], global_min, global_max)

    def render_breakdown(
        self,
        output: TextIO,
        plan_name: str,
        scenarios: list,
        plan_premium: float,
        plan_rules: "PlanRules | None" = None,
        highlight_thresholds: dict | None = None,
    ) -> None:
        """Render cost breakdown by service type for a specific plan."""
        from caca.models import PlanRules

        output.write(f"\nCost Breakdown for {plan_name}\n")
        output.write("=" * 95 + "\n")

        # Find scenarios with min and max OOP for this plan
        min_oop_scenario = None
        max_oop_scenario = None
        min_oop = float('inf')
        max_oop = float('-inf')

        for scenario in scenarios:
            plan_result = scenario.plan_results.get(plan_name)
            if not plan_result:
                continue
            if plan_result.out_of_pocket < min_oop:
                min_oop = plan_result.out_of_pocket
                min_oop_scenario = scenario
            if plan_result.out_of_pocket > max_oop:
                max_oop = plan_result.out_of_pocket
                max_oop_scenario = scenario

        if min_oop_scenario is None:
            output.write("No scenarios found for this plan.\n")
            return

        # Render both scenarios side by side
        self._render_scenario_comparison(
            output, plan_name, min_oop_scenario, max_oop_scenario, plan_premium
        )

        # Render plan highlights if plan_rules provided
        if plan_rules:
            self._render_plan_highlights(output, plan_rules, highlight_thresholds or {})

    def _render_scenario_comparison(
        self,
        output: TextIO,
        plan_name: str,
        min_scenario,
        max_scenario,
        plan_premium: float,
    ) -> None:
        """Render side-by-side comparison of min and max OOP scenarios."""
        min_result = min_scenario.plan_results[plan_name]
        max_result = max_scenario.plan_results[plan_name]

        # Build breakdown for each scenario
        def build_breakdown(plan_result):
            by_type: dict[ServiceType, dict] = {}
            for ec in plan_result.event_costs:
                stype = ec.event.service_type
                if stype not in by_type:
                    by_type[stype] = {"provider": 0.0, "patient": 0.0, "plan": 0.0}
                by_type[stype]["provider"] += ec.provider_cost
                by_type[stype]["patient"] += ec.patient_cost
                by_type[stype]["plan"] += ec.plan_cost
            return by_type

        min_breakdown = build_breakdown(min_result)
        max_breakdown = build_breakdown(max_result)

        # Get all service types from both scenarios
        all_types = set(min_breakdown.keys()) | set(max_breakdown.keys())
        sorted_types = sorted(all_types, key=lambda x: x.value)

        # Check if min and max are the same
        same_scenario = min_result.out_of_pocket == max_result.out_of_pocket

        if same_scenario:
            # Single scenario display
            output.write(f"All scenarios have the same OOP: {self.format_currency(min_result.out_of_pocket)}\n\n")
            output.write(f"{'Service Type':<35} {'Provider':>12} {'Patient OOP':>12} {'Plan Paid':>12}\n")
            output.write("-" * 71 + "\n")

            total_provider = 0.0
            total_patient = 0.0
            total_plan = 0.0

            for stype in sorted_types:
                costs = min_breakdown.get(stype, {"provider": 0, "patient": 0, "plan": 0})
                name = stype.value.replace("_", " ").title()
                output.write(
                    f"{name:<35} "
                    f"{self.format_currency(costs['provider']):>12} "
                    f"{self.format_currency(costs['patient']):>12} "
                    f"{self.format_currency(costs['plan']):>12}\n"
                )
                total_provider += costs["provider"]
                total_patient += costs["patient"]
                total_plan += costs["plan"]

            output.write("-" * 71 + "\n")
            output.write(
                f"{'Total':<35} "
                f"{self.format_currency(total_provider):>12} "
                f"{self.format_currency(total_patient):>12} "
                f"{self.format_currency(total_plan):>12}\n"
            )
            output.write(
                f"{'Annual Premium':<35} {'':>12} "
                f"{self.format_currency(plan_premium):>12}\n"
            )
            output.write(
                f"{'Total Annual Cost':<35} {'':>12} "
                f"{self.format_currency(total_patient + plan_premium):>12}\n"
            )
        else:
            # Two scenario comparison
            output.write(f"{'':35} {'--- Best Case ---':^26} {'--- Worst Case ---':^26}\n")
            output.write(f"{'Service Type':<35} {'Provider':>12} {'OOP':>12} {'Provider':>12} {'OOP':>12}\n")
            output.write("-" * 95 + "\n")

            min_total_provider = 0.0
            min_total_patient = 0.0
            max_total_provider = 0.0
            max_total_patient = 0.0

            for stype in sorted_types:
                min_costs = min_breakdown.get(stype, {"provider": 0, "patient": 0, "plan": 0})
                max_costs = max_breakdown.get(stype, {"provider": 0, "patient": 0, "plan": 0})
                name = stype.value.replace("_", " ").title()
                output.write(
                    f"{name:<35} "
                    f"{self.format_currency(min_costs['provider']):>12} "
                    f"{self.format_currency(min_costs['patient']):>12} "
                    f"{self.format_currency(max_costs['provider']):>12} "
                    f"{self.format_currency(max_costs['patient']):>12}\n"
                )
                min_total_provider += min_costs["provider"]
                min_total_patient += min_costs["patient"]
                max_total_provider += max_costs["provider"]
                max_total_patient += max_costs["patient"]

            output.write("-" * 95 + "\n")
            output.write(
                f"{'Total':<35} "
                f"{self.format_currency(min_total_provider):>12} "
                f"{self.format_currency(min_total_patient):>12} "
                f"{self.format_currency(max_total_provider):>12} "
                f"{self.format_currency(max_total_patient):>12}\n"
            )
            output.write(
                f"{'Annual Premium':<35} {'':>12} "
                f"{self.format_currency(plan_premium):>12} "
                f"{'':>12} "
                f"{self.format_currency(plan_premium):>12}\n"
            )
            output.write(
                f"{'Total Annual Cost':<35} {'':>12} "
                f"{self.format_currency(min_total_patient + plan_premium):>12} "
                f"{'':>12} "
                f"{self.format_currency(max_total_patient + plan_premium):>12}\n"
            )

    def _render_plan_highlights(
        self,
        output: TextIO,
        plan_rules: "PlanRules",
        thresholds: dict,
    ) -> None:
        """Render plan positives and negatives."""
        high_copay = thresholds.get("high_copay", 50)
        high_deductible = thresholds.get("high_deductible", 2000)

        positives = []
        negatives = []

        # Check deductible
        if plan_rules.deductible_individual == 0:
            positives.append("$0 deductible")
        elif plan_rules.deductible_individual >= high_deductible:
            negatives.append(f"High deductible: {self.format_currency(plan_rules.deductible_individual)}")

        # Check service costs after deductible
        for stype, cost in plan_rules.service_costs_after_deductible.items():
            name = stype.value.replace("_", " ").title()
            if stype.value == "preventative_visit":
                continue  # Skip preventative, always free

            if cost > 0 and cost < 1:
                # Coinsurance
                negatives.append(f"{name}: {cost:.0%} coinsurance after deductible")
            elif cost >= high_copay:
                # High copay
                negatives.append(f"{name}: {self.format_currency(cost)} copay after deductible")

        # Check for $0 cost services (beyond preventative)
        for stype, cost in plan_rules.service_costs_after_deductible.items():
            name = stype.value.replace("_", " ").title()
            if stype.value == "preventative_visit":
                continue
            if cost == 0:
                # Also check before-deductible cost
                before_cost = plan_rules.service_costs.get(stype, 0)
                if before_cost == 0:
                    positives.append(f"{name}: $0")

        output.write("\n")
        output.write("Plan Highlights\n")
        output.write("-" * 40 + "\n")

        if positives:
            output.write("Positives:\n")
            for p in positives[:5]:  # Limit to 5
                output.write(f"  + {p}\n")

        if negatives:
            output.write("Negatives:\n")
            for n in negatives[:5]:  # Limit to 5
                output.write(f"  - {n}\n")

        if not positives and not negatives:
            output.write("  No notable highlights.\n")
