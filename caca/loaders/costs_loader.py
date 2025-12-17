# PURPOSE: Load cost assumptions from YAML files

import yaml
from typing import TextIO
from caca.models import CostRange


def parse_cost_range(value: str | int | float) -> CostRange:
    """Parse a cost value or range into a CostRange."""
    if isinstance(value, (int, float)):
        return CostRange(float(value), float(value))

    value = str(value).strip().replace("$", "")

    if "-" in value:
        parts = value.split("-")
        return CostRange(float(parts[0]), float(parts[1]))

    return CostRange(float(value), float(value))


def load_costs_yaml(file: TextIO) -> dict[str, CostRange]:
    """Load costs from a YAML file."""
    data = yaml.safe_load(file)

    costs = {}
    for service_name, value in data.items():
        costs[service_name] = parse_cost_range(value)

    return costs
