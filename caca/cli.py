# PURPOSE: Command-line interface for Care Casino

import argparse
import sys
from pathlib import Path
from caca.loaders.run_config_loader import load_run_config
from caca.simulation_runner import SimulationRunner
from caca.results import ResultsStore
from caca.output.terminal import TerminalRenderer
from caca.output.json_export import JsonExporter
from caca.validation import validate_directory, validate_run_config_file, ValidationError


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="caca",
        description="Care Casino - Monte Carlo healthcare cost simulator",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Generate subcommand
    gen_parser = subparsers.add_parser(
        "generate",
        aliases=["gen"],
        help="Run simulation and generate estimates",
    )
    gen_parser.add_argument(
        "config",
        help="Path to run configuration file",
    )
    gen_parser.add_argument(
        "--json",
        help="Path to write JSON results",
    )
    gen_parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress terminal output",
    )
    gen_parser.add_argument(
        "--gross",
        action="store_true",
        help="Price plans at full premium, ignoring subsidies",
    )
    gen_parser.add_argument(
        "--breakdown",
        help="Write detailed breakdown to file",
    )
    gen_parser.add_argument(
        "--histogram-width",
        type=int,
        default=79,
        help="Width of histogram in characters (default: 79)",
    )
    gen_parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Skip cache lookup, force fresh simulation",
    )
    gen_parser.add_argument(
        "--cache-dir",
        default=".caca-cache",
        help="Cache directory (default: .caca-cache)",
    )

    # Validate subcommand
    val_parser = subparsers.add_parser(
        "validate",
        aliases=["val"],
        help="Validate data files",
    )
    val_parser.add_argument(
        "paths",
        nargs="+",
        help="Directories to validate",
    )

    parsed = parser.parse_args(args)

    # Normalize aliases
    if parsed.command == "gen":
        parsed.command = "generate"
    elif parsed.command == "val":
        parsed.command = "validate"

    return parsed


def cmd_generate(args: argparse.Namespace) -> int:
    """Run the generate command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file not found: {args.config}", file=sys.stderr)
        return 1

    # Load configuration
    config = load_run_config(config_path)

    # Extract simulation parameters
    sim_params = config["simulation"]

    # Build profiles dict for simulation runner
    profiles = {}
    household = []
    for person in config["people"]:
        name = person["name"]
        profiles[name] = person["usage"]
        household.append({"name": name, "profile": name})

    # Run simulation
    runner = SimulationRunner(
        plans=config["plans"],
        profiles=profiles,
        household=household,
        default_costs=config["costs"],
        year=2025,
        gross=args.gross,
    )

    results = runner.run(
        iterations=sim_params["iterations"],
        convergence_threshold_dollars=sim_params["convergence_threshold_dollars"],
        min_iterations=sim_params["min_iterations"],
        max_iterations=sim_params["max_iterations"],
    )

    # Collect plan costs for histograms
    plan_costs = {
        plan.name: [
            s.plan_results[plan.name].total_cost
            for s in results.scenarios
        ]
        for plan in config["plans"]
    }

    # Terminal output
    if not args.quiet:
        renderer = TerminalRenderer(histogram_width=args.histogram_width)
        renderer.render_full_report(
            sys.stdout,
            household,
            results.iterations,
            results.converged,
            sim_params["convergence_threshold_dollars"],
            results.summary,
            plan_costs,
            gross=args.gross,
        )

    # Breakdown output
    if args.breakdown:
        with open(args.breakdown, "w") as f:
            renderer = TerminalRenderer(histogram_width=args.histogram_width)
            for plan in config["plans"]:
                renderer.render_breakdown(
                    f,
                    plan.name,
                    results.scenarios,
                    plan.effective_premium(args.gross),
                    plan_rules=plan,
                    gross=args.gross,
                )
        if not args.quiet:
            print(f"\nBreakdown written to {args.breakdown}")

    # JSON output
    if args.json:
        store = ResultsStore(
            iterations=results.iterations,
            converged=results.converged,
            convergence_threshold_dollars=sim_params["convergence_threshold_dollars"],
            household=household,
            plan_names=[p.name for p in config["plans"]],
            scenarios=results.scenarios,
        )
        exporter = JsonExporter()
        with open(args.json, "w") as f:
            exporter.export(f, store, results.summary)
        if not args.quiet:
            print(f"\nResults written to {args.json}")

    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Run the validate command."""
    all_errors: list[ValidationError] = []

    for path_str in args.paths:
        path = Path(path_str)
        if not path.exists():
            print(f"Error: Path not found: {path_str}", file=sys.stderr)
            return 1
        if path.is_dir():
            all_errors.extend(validate_directory(path))
        elif path.suffix in (".yaml", ".yml"):
            all_errors.extend(validate_run_config_file(path))
        else:
            print(f"Warning: Skipping non-YAML file: {path_str}", file=sys.stderr)

    if all_errors:
        print(f"Found {len(all_errors)} validation error(s):\n", file=sys.stderr)
        for error in all_errors:
            print(f"Error: {error.message}", file=sys.stderr)
            print(f"  In: {error.file_path}", file=sys.stderr)
            if error.line:
                print(f"  Line: {error.line}", file=sys.stderr)
            print(file=sys.stderr)
        return 1

    print(f"✓ All files valid")
    return 0


def main() -> None:
    """Main entry point."""
    args = parse_args()

    if args.command == "generate":
        sys.exit(cmd_generate(args))
    elif args.command == "validate":
        sys.exit(cmd_validate(args))


if __name__ == "__main__":
    main()
