# PURPOSE: Load simulation parameters from YAML files

import yaml
from typing import TextIO


def load_params_yaml(file: TextIO) -> dict:
    """Load simulation parameters from a YAML file."""
    data = yaml.safe_load(file)

    return {
        "iterations": data.get("iterations", 1000),
        "convergence_threshold_dollars": data.get("convergence_threshold_dollars", 100),
        "max_iterations": data.get("max_iterations", 100000),
        "min_iterations": data.get("min_iterations", 1000),
    }
