# PURPOSE: Validate configuration files and report errors

import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ValidationError:
    """A validation error with context."""
    message: str
    file_path: str
    line: int | None = None


REQUIRED_PLAN_FIELDS = [
    "plan_name",
    "premium",
    "deductible_individual",
    "deductible_family",
    "oop_max_individual",
    "oop_max_family",
]

# All service types that must have cost-sharing rules defined
REQUIRED_SERVICE_FIELDS = [
    "preventative_visit",
    "primary_care_visit",
    "specialist_visit",
    "labs",
    "imaging",
    "outpatient_services",
    "outpatient_rehabilitation_services",
    "inpatient_services",
    "emergency_room",
    "urgent_care",
    "tier_1_generic_drugs",
    "tier_2_preferred_brand_drugs",
    "tier_3_non_preferred_brand_drugs",
    "tier_4_specialty_drugs",
]

COINSURANCE_FIELDS = [
    "outpatient_services",
    "outpatient_services_after_deductible",
    "inpatient_services",
    "inpatient_services_after_deductible",
]


def validate_plan(data: dict[str, Any], file_path: str) -> list[ValidationError]:
    """Validate a plan definition."""
    errors = []

    # Check required fields
    for field in REQUIRED_PLAN_FIELDS:
        if field not in data or data[field] is None:
            errors.append(ValidationError(
                message=f"Missing required field '{field}'",
                file_path=file_path,
            ))

    # Check all service types have cost-sharing rules (before and after deductible)
    for service in REQUIRED_SERVICE_FIELDS:
        if service not in data:
            errors.append(ValidationError(
                message=f"Missing cost-sharing rule for '{service}'",
                file_path=file_path,
            ))
        after_key = f"{service}_after_deductible"
        if after_key not in data:
            errors.append(ValidationError(
                message=f"Missing cost-sharing rule for '{after_key}'",
                file_path=file_path,
            ))

    # Check deductible <= OOP max
    ded_ind = data.get("deductible_individual", 0)
    oop_ind = data.get("oop_max_individual", 0)
    if ded_ind and oop_ind and ded_ind > oop_ind:
        errors.append(ValidationError(
            message=f"Deductible (${ded_ind:,.0f}) exceeds OOP max (${oop_ind:,.0f})",
            file_path=file_path,
        ))

    # Check coinsurance values are 0-1
    for field in COINSURANCE_FIELDS:
        if field in data:
            value = data[field]
            if isinstance(value, (int, float)) and 0 < value <= 1:
                pass  # valid coinsurance
            elif isinstance(value, (int, float)) and value > 1:
                # Could be copay (valid) or invalid coinsurance
                # Heuristic: values > 1 and < 2 are likely meant to be coinsurance
                if value < 2:
                    errors.append(ValidationError(
                        message=f"Invalid coinsurance value '{value}' for {field}. Use 0-1 for percentage or >1 for copay.",
                        file_path=file_path,
                    ))

    return errors


def validate_profile(data: dict[str, Any], file_path: str) -> list[ValidationError]:
    """Validate a profile definition."""
    errors = []

    if "name" not in data or not data["name"]:
        errors.append(ValidationError(
            message="Missing required field 'name'",
            file_path=file_path,
        ))

    return errors


def validate_costs(data: dict[str, Any], file_path: str) -> list[ValidationError]:
    """Validate a costs definition."""
    errors = []
    # Costs are flexible - just check values are valid
    for key, value in data.items():
        if isinstance(value, str) and "-" in value:
            parts = value.split("-")
            try:
                low = float(parts[0].replace("$", "").replace(",", ""))
                high = float(parts[1].replace("$", "").replace(",", ""))
                if low > high:
                    errors.append(ValidationError(
                        message=f"Invalid range for {key}: {low} > {high}",
                        file_path=file_path,
                    ))
            except ValueError:
                errors.append(ValidationError(
                    message=f"Cannot parse cost range for {key}: {value}",
                    file_path=file_path,
                ))
    return errors


def validate_run_config(config: dict, config_path: Path) -> list[ValidationError]:
    """Validate a run configuration and check for duplicates."""
    errors = []

    # Check for duplicate plan names
    plan_names: dict[str, Path] = {}
    for plan_path in config.get("plans", []):
        with open(plan_path) as f:
            data = yaml.safe_load(f)
        name = data.get("plan_name", "")
        if name in plan_names:
            errors.append(ValidationError(
                message=f"Duplicate plan name '{name}'. First defined in: {plan_names[name]}",
                file_path=str(plan_path),
            ))
        else:
            plan_names[name] = plan_path

    # Check for duplicate people names
    people_names: dict[str, Path] = {}
    for person_path in config.get("people", []):
        with open(person_path) as f:
            data = yaml.safe_load(f)
        name = data.get("name", "")
        if name in people_names:
            errors.append(ValidationError(
                message=f"Duplicate person name '{name}'. First defined in: {people_names[name]}",
                file_path=str(person_path),
            ))
        else:
            people_names[name] = person_path

    return errors


def validate_run_config_file(config_path: Path) -> list[ValidationError]:
    """Validate a run config file and all referenced files.

    Checks that:
    1. The run config YAML is valid
    2. All referenced files exist (simulation, costs, plans, people)
    3. Referenced files are themselves valid
    """
    errors = []
    config_path = Path(config_path)

    # Load the run config
    try:
        with open(config_path) as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as e:
        errors.append(ValidationError(
            message=f"Invalid YAML: {e}",
            file_path=str(config_path),
        ))
        return errors

    if raw is None:
        errors.append(ValidationError(
            message="Empty run config file",
            file_path=str(config_path),
        ))
        return errors

    # Check required fields exist
    for field in ["simulation", "costs", "plans", "people"]:
        if field not in raw:
            errors.append(ValidationError(
                message=f"Missing required field '{field}'",
                file_path=str(config_path),
            ))

    # Check simulation file exists and is valid
    if "simulation" in raw:
        sim_path = Path(raw["simulation"])
        if not sim_path.exists():
            errors.append(ValidationError(
                message=f"Simulation file not found: {raw['simulation']}",
                file_path=str(config_path),
            ))

    # Check costs file exists and is valid
    if "costs" in raw:
        costs_path = Path(raw["costs"])
        if not costs_path.exists():
            errors.append(ValidationError(
                message=f"Costs file not found: {raw['costs']}",
                file_path=str(config_path),
            ))
        elif costs_path.exists():
            with open(costs_path) as f:
                try:
                    costs_data = yaml.safe_load(f)
                    if costs_data:
                        errors.extend(validate_costs(costs_data, str(costs_path)))
                except yaml.YAMLError as e:
                    errors.append(ValidationError(
                        message=f"Invalid YAML: {e}",
                        file_path=str(costs_path),
                    ))

    # Check plan files exist and are valid
    for plan_path_str in raw.get("plans", []):
        plan_path = Path(plan_path_str)
        if not plan_path.exists():
            errors.append(ValidationError(
                message=f"Plan file not found: {plan_path_str}",
                file_path=str(config_path),
            ))
        else:
            with open(plan_path) as f:
                try:
                    plan_data = yaml.safe_load(f)
                    if plan_data:
                        errors.extend(validate_plan(plan_data, str(plan_path)))
                except yaml.YAMLError as e:
                    errors.append(ValidationError(
                        message=f"Invalid YAML: {e}",
                        file_path=str(plan_path),
                    ))

    # Check profile files exist and are valid
    for profile_path_str in raw.get("people", []):
        profile_path = Path(profile_path_str)
        if not profile_path.exists():
            errors.append(ValidationError(
                message=f"Profile file not found: {profile_path_str}",
                file_path=str(config_path),
            ))
        else:
            with open(profile_path) as f:
                try:
                    profile_data = yaml.safe_load(f)
                    if profile_data:
                        errors.extend(validate_profile(profile_data, str(profile_path)))
                except yaml.YAMLError as e:
                    errors.append(ValidationError(
                        message=f"Invalid YAML: {e}",
                        file_path=str(profile_path),
                    ))

    return errors


def is_run_config(data: dict) -> bool:
    """Check if data looks like a run config file."""
    run_config_keys = {"simulation", "costs", "plans", "people"}
    return bool(run_config_keys & set(data.keys()))


def validate_directory(path: Path) -> list[ValidationError]:
    """Validate all files in a directory."""
    errors = []

    for yaml_file in path.rglob("*.yaml"):
        if yaml_file.name.startswith("."):
            continue

        with open(yaml_file) as f:
            try:
                data = yaml.safe_load(f)
            except yaml.YAMLError as e:
                errors.append(ValidationError(
                    message=f"Invalid YAML: {e}",
                    file_path=str(yaml_file),
                ))
                continue

        if data is None:
            continue

        # Determine file type by content or path
        if is_run_config(data):
            errors.extend(validate_run_config_file(yaml_file))
        elif "plan_name" in data:
            errors.extend(validate_plan(data, str(yaml_file)))
        elif "name" in data and any(
            k in data for k in ["primary_care_visit", "specialist_visit", "labs"]
        ):
            errors.extend(validate_profile(data, str(yaml_file)))
        elif any("-" in str(v) for v in data.values() if isinstance(v, str)):
            errors.extend(validate_costs(data, str(yaml_file)))

    return errors
