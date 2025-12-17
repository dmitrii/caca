# PURPOSE: Load simulation configuration from YAML

import yaml
from typing import TextIO, Any
from caca.models import CostRange


def parse_cost_range(value: str | int | float) -> CostRange:
    """Parse a cost value or range into a CostRange."""
    if isinstance(value, (int, float)):
        return CostRange(float(value), float(value))

    value = str(value).strip()
    # Remove dollar signs
    value = value.replace("$", "")

    if "-" in value:
        parts = value.split("-")
        return CostRange(float(parts[0]), float(parts[1]))

    return CostRange(float(value), float(value))


def parse_count_range(value: str | int) -> tuple[int, int]:
    """Parse a count value or range into (min, max)."""
    if isinstance(value, int):
        return (value, value)

    value = str(value).strip()
    if "-" in value:
        parts = value.split("-")
        return (int(parts[0]), int(parts[1]))

    count = int(value)
    return (count, count)


def parse_usage_entry(entry: Any) -> dict:
    """Parse a profile usage entry into a normalized dict."""
    # Simple string/int format: "2-5" or 3
    if isinstance(entry, (str, int)):
        count_min, count_max = parse_count_range(entry)
        return {
            "count_min": count_min,
            "count_max": count_max,
            "probability": 1.0,
            "scheduled": False,
        }

    # Dict format
    if isinstance(entry, dict):
        result: dict[str, Any] = {"scheduled": False}

        # Check if this is a scheduled event (has date or explicit cost)
        if "date" in entry:
            result["scheduled"] = True
            result["date"] = entry["date"]
            result["cost"] = float(entry.get("cost", 0))
            result["description"] = entry.get("description")
            result["count_min"] = 1
            result["count_max"] = 1
            return result

        # Has cost but no date - scheduled with random date
        if "cost" in entry and "count" in entry:
            count_min, count_max = parse_count_range(entry["count"])
            result["cost"] = float(entry["cost"])
            result["count_min"] = count_min
            result["count_max"] = count_max
            result["probability"] = entry.get("probability", 1.0)
            result["description"] = entry.get("description")
            return result

        # Probability format
        if "probability" in entry:
            result["probability"] = entry["probability"]
            if "count" in entry:
                count_min, count_max = parse_count_range(entry["count"])
            else:
                count_min, count_max = 1, 1
            result["count_min"] = count_min
            result["count_max"] = count_max
            return result

        # Just count
        if "count" in entry:
            count_min, count_max = parse_count_range(entry["count"])
            result["count_min"] = count_min
            result["count_max"] = count_max
            result["probability"] = entry.get("probability", 1.0)
            result["description"] = entry.get("description")
            result["cost"] = entry.get("cost")
            return result

    raise ValueError(f"Cannot parse usage entry: {entry}")


def process_profile(profile: dict) -> dict:
    """Process a profile's usage entries."""
    processed = {}
    for service_name, entry in profile.items():
        if isinstance(entry, list):
            # List of entries (mix of scheduled and random)
            processed[service_name] = [parse_usage_entry(e) for e in entry]
        else:
            processed[service_name] = [parse_usage_entry(entry)]
    return processed


def load_config(file: TextIO) -> dict:
    """Load configuration from a YAML file."""
    raw = yaml.safe_load(file)

    config = {
        "simulation": raw.get("simulation", {}),
        "defaults": {
            "costs": {},
            "highlight_thresholds": {
                "high_copay": 50,
                "high_deductible": 2000,
            },
        },
        "profiles": {},
        "household": raw.get("household", []),
    }

    # Process defaults section
    if "defaults" in raw:
        # Costs
        if "costs" in raw["defaults"]:
            for service, cost in raw["defaults"]["costs"].items():
                config["defaults"]["costs"][service] = parse_cost_range(cost)

        # Highlight thresholds
        if "highlight_thresholds" in raw["defaults"]:
            for key, value in raw["defaults"]["highlight_thresholds"].items():
                config["defaults"]["highlight_thresholds"][key] = value

    # Process profiles
    if "profiles" in raw:
        for profile_name, profile in raw["profiles"].items():
            if profile:
                config["profiles"][profile_name] = process_profile(profile)

    return config
