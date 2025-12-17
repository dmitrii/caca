# PURPOSE: Load usage profiles from YAML files

import yaml
from typing import TextIO, Any


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
    if isinstance(entry, (str, int)):
        count_min, count_max = parse_count_range(entry)
        return {
            "count_min": count_min,
            "count_max": count_max,
            "probability": 1.0,
            "scheduled": False,
        }

    if isinstance(entry, dict):
        result: dict[str, Any] = {"scheduled": False}

        if "date" in entry:
            result["scheduled"] = True
            result["date"] = entry["date"]
            result["cost"] = float(entry.get("cost", 0))
            result["description"] = entry.get("description")
            result["count_min"] = 1
            result["count_max"] = 1
            return result

        if "count" in entry:
            count_min, count_max = parse_count_range(entry["count"])
        else:
            count_min, count_max = 1, 1

        result["count_min"] = count_min
        result["count_max"] = count_max
        result["probability"] = entry.get("probability", 1.0)
        result["description"] = entry.get("description")
        if "cost" in entry:
            result["cost"] = float(entry["cost"])
        return result

    raise ValueError(f"Cannot parse usage entry: {entry}")


def load_profile_yaml(file: TextIO) -> dict:
    """Load a profile from a YAML file.

    Returns a dict with 'name' and 'usage' keys.
    """
    data = yaml.safe_load(file)

    name = data.pop("name", "unknown")

    usage = {}
    for service_name, entry in data.items():
        if isinstance(entry, list):
            usage[service_name] = [parse_usage_entry(e) for e in entry]
        else:
            usage[service_name] = [parse_usage_entry(entry)]

    return {"name": name, "usage": usage}
