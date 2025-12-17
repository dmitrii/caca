# PURPOSE: Terminal output rendering with ASCII tables and histograms

from typing import TextIO


class TerminalRenderer:
    """Renders simulation results to terminal."""

    def __init__(self, width: int = 80):
        self.width = width

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
        members = ", ".join(f"{m['name']} ({m['profile']})" for m in household)
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
        bins: int = 20,
    ) -> None:
        """Render an ASCII histogram of costs."""
        if not costs:
            return

        min_cost = min(costs)
        max_cost = max(costs)

        if max_cost == min_cost:
            output.write(f"{plan_name}: all scenarios = {self.format_currency(min_cost)}\n")
            return

        output.write(f"{plan_name}\n")

        # Calculate histogram bins
        bin_width = (max_cost - min_cost) / bins
        bin_counts = [0] * bins

        for cost in costs:
            bin_idx = min(int((cost - min_cost) / bin_width), bins - 1)
            bin_counts[bin_idx] += 1

        max_count = max(bin_counts)
        bar_width = 40

        # Render range
        output.write(f"{self.format_currency(min_cost)} |")
        output.write("=" * bar_width)
        output.write(f"| {self.format_currency(max_cost)}\n")

        # Render distribution (simplified single-line)
        output.write(" " * (len(self.format_currency(min_cost)) + 2))
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

        # Sort by expected cost for consistent ordering
        ranked = sorted(summary.items(), key=lambda x: x[1]["expected_cost"])
        for name, _ in ranked:
            if name in plan_costs:
                self.render_histogram(output, name, plan_costs[name])
