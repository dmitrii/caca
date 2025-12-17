# PURPOSE: Load run configuration that references other files

import yaml
from pathlib import Path
from caca.loaders.plan_loader import load_plan_yaml
from caca.loaders.profile_loader import load_profile_yaml
from caca.loaders.costs_loader import load_costs_yaml
from caca.loaders.params_loader import load_params_yaml


def load_run_config(config_path: Path) -> dict:
    """Load a run configuration and all referenced files.

    Paths in the config file are resolved relative to the current working
    directory, not the config file location.

    Args:
        config_path: Path to the run config YAML file

    Returns:
        Dict with 'simulation', 'costs', 'plans', and 'people' keys
    """
    with open(config_path) as f:
        raw = yaml.safe_load(f)

    # Load simulation parameters
    simulation_path = Path(raw["simulation"])
    with open(simulation_path) as f:
        simulation = load_params_yaml(f)

    # Load costs
    costs_path = Path(raw["costs"])
    with open(costs_path) as f:
        costs = load_costs_yaml(f)

    # Load plans
    plans = []
    for plan_ref in raw.get("plans", []):
        plan_path = Path(plan_ref)
        with open(plan_path) as f:
            plans.append(load_plan_yaml(f))

    # Load people (profiles)
    people = []
    for person_ref in raw.get("people", []):
        person_path = Path(person_ref)
        with open(person_path) as f:
            people.append(load_profile_yaml(f))

    return {
        "simulation": simulation,
        "costs": costs,
        "plans": plans,
        "people": people,
    }
