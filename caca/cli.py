# PURPOSE: Command-line interface for Care Casino

import argparse
import sys
from pathlib import Path
from caca.config_loader import load_config
from caca.plan_loader import load_plans
from caca.simulation_runner import SimulationRunner
from caca.results import ResultsStore
from caca.output.terminal import TerminalRenderer
from caca.output.json_export import JsonExporter


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="caca",
        description="Care Casino - Monte Carlo healthcare cost simulator",
    )

    parser.add_argument(
        "config",
        help="Path to YAML configuration file",
    )
    parser.add_argument(
        "--plans",
        default="plans.csv",
        help="Path to plans CSV file (default: plans.csv)",
    )
    parser.add_argument(
        "--json",
        help="Path to write JSON results",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress terminal output (use with --json)",
    )
    parser.add_argument(
        "--breakdown",
        help="Show cost breakdown by service type for a specific plan",
    )
    parser.add_argument(
        "--histogram-width",
        type=int,
        default=79,
        help="Width of histogram in characters (default: 79)",
    )

    return parser.parse_args(args)


def main() -> None:
    """Main entry point."""
    args = parse_args()

    # Validate files exist
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file not found: {args.config}", file=sys.stderr)
        sys.exit(1)

    plans_path = Path(args.plans)
    if not plans_path.exists():
        print(f"Error: Plans file not found: {args.plans}", file=sys.stderr)
        sys.exit(1)

    # Load configuration
    with open(config_path) as f:
        config = load_config(f)

    # Load plans
    with open(plans_path) as f:
        plans = load_plans(f)

    # Extract simulation parameters
    sim_config = config["simulation"]
    iterations = sim_config.get("iterations", 1000)
    convergence_threshold = sim_config.get("convergence_threshold_dollars", 100)
    min_iterations = sim_config.get("min_iterations", 1000)
    max_iterations = sim_config.get("max_iterations", 100000)

    # Run simulation
    runner = SimulationRunner(
        plans=plans,
        profiles=config["profiles"],
        household=config["household"],
        default_costs=config["defaults"]["costs"],
        year=2025,
    )

    results = runner.run(
        iterations=iterations,
        convergence_threshold_dollars=convergence_threshold,
        min_iterations=min_iterations,
        max_iterations=max_iterations,
    )

    # Build results store
    store = ResultsStore(
        iterations=results.iterations,
        converged=results.converged,
        convergence_threshold_dollars=convergence_threshold,
        household=config["household"],
        plan_names=[p.name for p in plans],
        scenarios=results.scenarios,
    )

    # Collect plan costs for histograms
    plan_costs = {
        plan.name: [
            s.plan_results[plan.name].total_cost
            for s in results.scenarios
        ]
        for plan in plans
    }

    # Terminal output
    if not args.quiet:
        renderer = TerminalRenderer(histogram_width=args.histogram_width)
        renderer.render_full_report(
            sys.stdout,
            config["household"],
            results.iterations,
            results.converged,
            convergence_threshold,
            results.summary,
            plan_costs,
        )

        # Breakdown for specific plan
        if args.breakdown:
            # Find matching plan (case-insensitive partial match)
            matching_plan = None
            for plan in plans:
                if args.breakdown.lower() in plan.name.lower():
                    matching_plan = plan
                    break

            if matching_plan:
                renderer.render_breakdown(
                    sys.stdout,
                    matching_plan.name,
                    results.scenarios,
                    matching_plan.premium,
                    plan_rules=matching_plan,
                    highlight_thresholds=config["defaults"]["highlight_thresholds"],
                )
            else:
                print(f"\nWarning: No plan found matching '{args.breakdown}'", file=sys.stderr)
                print(f"Available plans: {', '.join(p.name for p in plans)}", file=sys.stderr)

    # JSON output
    if args.json:
        exporter = JsonExporter()
        with open(args.json, "w") as f:
            exporter.export(f, store, results.summary)
        if not args.quiet:
            print(f"\nResults written to {args.json}")


if __name__ == "__main__":
    main()
