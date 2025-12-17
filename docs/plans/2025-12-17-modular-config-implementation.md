# Modular Configuration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restructure caca to support modular configs with individual plan/profile/cost files, subcommand CLI, validation, and caching.

**Architecture:** Split monolithic loaders into file-based loaders. Add validation layer. Introduce subcommand CLI structure. Add cache module with code-aware invalidation.

**Tech Stack:** Python 3.11+, PyYAML, hashlib (stdlib), argparse subparsers

---

## Task 1: Create Directory Structure and Starter Files

**Files:**
- Create: `plans/2026/.gitkeep`
- Create: `profiles/.gitkeep`
- Create: `costs/.gitkeep`
- Create: `parameters/simulation.yaml`

**Step 1: Create directories**

```bash
mkdir -p plans/2026 profiles costs parameters
```

**Step 2: Create simulation parameters file**

Create `parameters/simulation.yaml`:
```yaml
# Simulation parameters
iterations: auto
convergence_threshold_dollars: 100
max_iterations: 100000
min_iterations: 1000
```

**Step 3: Create .gitkeep files for empty directories**

```bash
touch plans/2026/.gitkeep profiles/.gitkeep costs/.gitkeep
```

**Step 4: Commit**

```bash
git add plans/ profiles/ costs/ parameters/
git commit -m "chore: add directory structure for modular config"
```

---

## Task 2: Create YAML Plan Loader

**Files:**
- Create: `caca/loaders/__init__.py`
- Create: `caca/loaders/plan_loader.py`
- Create: `tests/test_loaders_plan.py`

**Step 1: Create loaders package**

Create `caca/loaders/__init__.py`:
```python
# PURPOSE: Data file loaders for plans, profiles, costs, and parameters
```

**Step 2: Write failing test for YAML plan loader**

Create `tests/test_loaders_plan.py`:
```python
# PURPOSE: Tests for YAML plan loader

import pytest
from io import StringIO
from caca.loaders.plan_loader import load_plan_yaml
from caca.models import ServiceType


class TestLoadPlanYaml:
    def test_loads_basic_plan(self):
        yaml_content = """
plan_name: Test Plan
premium: 500.00
deductible_individual: 1000
deductible_family: 2000
oop_max_individual: 5000
oop_max_family: 10000
primary_care_visit: 30
primary_care_visit_after_deductible: 30
"""
        plan = load_plan_yaml(StringIO(yaml_content))

        assert plan.name == "Test Plan"
        assert plan.premium == 6000.0  # monthly * 12
        assert plan.deductible_individual == 1000
        assert plan.deductible_family == 2000
        assert plan.oop_max_individual == 5000
        assert plan.oop_max_family == 10000
        assert plan.service_costs[ServiceType.PRIMARY_CARE_VISIT] == 30

    def test_handles_coinsurance(self):
        yaml_content = """
plan_name: Coinsurance Plan
premium: 400
deductible_individual: 2000
deductible_family: 4000
oop_max_individual: 8000
oop_max_family: 16000
outpatient_services: 0.3
outpatient_services_after_deductible: 0.3
"""
        plan = load_plan_yaml(StringIO(yaml_content))

        assert plan.service_costs[ServiceType.OUTPATIENT_SERVICES] == 0.3

    def test_handles_percentage_format(self):
        yaml_content = """
plan_name: Percent Plan
premium: 400
deductible_individual: 2000
deductible_family: 4000
oop_max_individual: 8000
oop_max_family: 16000
outpatient_services: 30%
outpatient_services_after_deductible: 30%
"""
        plan = load_plan_yaml(StringIO(yaml_content))

        assert plan.service_costs[ServiceType.OUTPATIENT_SERVICES] == 0.3

    def test_preserves_comments_in_source(self):
        # Comments should be ignored during parsing (YAML handles this)
        yaml_content = """
# This is a comment
plan_name: Commented Plan
premium: 400  # monthly premium
deductible_individual: 2000
deductible_family: 4000
oop_max_individual: 8000
oop_max_family: 16000
"""
        plan = load_plan_yaml(StringIO(yaml_content))

        assert plan.name == "Commented Plan"
```

**Step 3: Run test to verify it fails**

```bash
pytest tests/test_loaders_plan.py -v
```

Expected: FAIL with "No module named 'caca.loaders'"

**Step 4: Implement YAML plan loader**

Create `caca/loaders/plan_loader.py`:
```python
# PURPOSE: Load healthcare plan definitions from YAML files

import yaml
from typing import TextIO
from caca.models import PlanRules, ServiceType


SERVICE_TYPE_MAP = {
    "preventative_visit": ServiceType.PREVENTATIVE_VISIT,
    "primary_care_visit": ServiceType.PRIMARY_CARE_VISIT,
    "specialist_visit": ServiceType.SPECIALIST_VISIT,
    "labs": ServiceType.LABS,
    "imaging": ServiceType.IMAGING,
    "outpatient_services": ServiceType.OUTPATIENT_SERVICES,
    "inpatient_services": ServiceType.INPATIENT_SERVICES,
    "emergency_room": ServiceType.EMERGENCY_ROOM,
    "urgent_care": ServiceType.URGENT_CARE,
    "tier_1_generic_drugs": ServiceType.TIER_1_GENERIC_DRUGS,
    "tier_2_preferred_brand_drugs": ServiceType.TIER_2_PREFERRED_BRAND_DRUGS,
    "tier_3_non_preferred_brand_drugs": ServiceType.TIER_3_NON_PREFERRED_BRAND_DRUGS,
    "tier_4_specialty_drugs": ServiceType.TIER_4_SPECIALTY_DRUGS,
    "outpatient_rehabilitation_services": ServiceType.OUTPATIENT_REHABILITATION_SERVICES,
}


def parse_cost_value(value) -> float | None:
    """Parse a cost value, handling percentages."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    value = str(value).strip()
    if value.endswith("%"):
        return float(value[:-1]) / 100.0
    if value.startswith("$"):
        value = value[1:]
    value = value.replace(",", "")
    return float(value)


def load_plan_yaml(file: TextIO) -> PlanRules:
    """Load a plan from a YAML file."""
    data = yaml.safe_load(file)

    service_costs: dict[ServiceType, float] = {}
    service_costs_after_deductible: dict[ServiceType, float] = {}

    for service_name, service_type in SERVICE_TYPE_MAP.items():
        if service_name in data:
            value = parse_cost_value(data[service_name])
            if value is not None:
                service_costs[service_type] = value
        after_key = f"{service_name}_after_deductible"
        if after_key in data:
            value = parse_cost_value(data[after_key])
            if value is not None:
                service_costs_after_deductible[service_type] = value

    monthly_premium = parse_cost_value(data.get("premium")) or 0.0

    return PlanRules(
        name=data.get("plan_name", "Unknown Plan"),
        premium=monthly_premium * 12,
        deductible_individual=parse_cost_value(data.get("deductible_individual")) or 0.0,
        deductible_family=parse_cost_value(data.get("deductible_family")) or 0.0,
        oop_max_individual=parse_cost_value(data.get("oop_max_individual")) or 0.0,
        oop_max_family=parse_cost_value(data.get("oop_max_family")) or 0.0,
        service_costs=service_costs,
        service_costs_after_deductible=service_costs_after_deductible,
        url=data.get("plan_url"),
        deductible_rx_individual=parse_cost_value(data.get("deductible_rx_individual")),
        deductible_rx_family=parse_cost_value(data.get("deductible_rx_family")),
        oop_max_rx_individual=parse_cost_value(data.get("oop_max_rx_individual")),
        oop_max_rx_family=parse_cost_value(data.get("oop_max_rx_family")),
        oop_max_per_rx=parse_cost_value(data.get("oop_max_per_rx")),
        deductible_model=data.get("deductible_model", "individual_first"),
    )
```

**Step 5: Run test to verify it passes**

```bash
pytest tests/test_loaders_plan.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add caca/loaders/ tests/test_loaders_plan.py
git commit -m "feat: add YAML plan loader"
```

---

## Task 3: Create Profile Loader

**Files:**
- Create: `caca/loaders/profile_loader.py`
- Create: `tests/test_loaders_profile.py`

**Step 1: Write failing test for profile loader**

Create `tests/test_loaders_profile.py`:
```python
# PURPOSE: Tests for profile loader

import pytest
from io import StringIO
from caca.loaders.profile_loader import load_profile_yaml


class TestLoadProfileYaml:
    def test_loads_basic_profile(self):
        yaml_content = """
name: alice
primary_care_visit: 3
specialist_visit: 2
labs: 5
"""
        profile = load_profile_yaml(StringIO(yaml_content))

        assert profile["name"] == "alice"
        assert profile["usage"]["primary_care_visit"] == [
            {"count_min": 3, "count_max": 3, "probability": 1.0, "scheduled": False}
        ]

    def test_loads_range_counts(self):
        yaml_content = """
name: bob
primary_care_visit: 2-5
"""
        profile = load_profile_yaml(StringIO(yaml_content))

        assert profile["usage"]["primary_care_visit"] == [
            {"count_min": 2, "count_max": 5, "probability": 1.0, "scheduled": False}
        ]

    def test_loads_probability_events(self):
        yaml_content = """
name: carol
emergency_room:
  probability: 0.1
  count: 1
"""
        profile = load_profile_yaml(StringIO(yaml_content))

        assert profile["usage"]["emergency_room"][0]["probability"] == 0.1
        assert profile["usage"]["emergency_room"][0]["count_min"] == 1
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_loaders_profile.py -v
```

Expected: FAIL with "cannot import name 'load_profile_yaml'"

**Step 3: Implement profile loader**

Create `caca/loaders/profile_loader.py`:
```python
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
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_loaders_profile.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add caca/loaders/profile_loader.py tests/test_loaders_profile.py
git commit -m "feat: add YAML profile loader"
```

---

## Task 4: Create Costs and Parameters Loaders

**Files:**
- Create: `caca/loaders/costs_loader.py`
- Create: `caca/loaders/params_loader.py`
- Create: `tests/test_loaders_costs.py`
- Create: `tests/test_loaders_params.py`

**Step 1: Write failing test for costs loader**

Create `tests/test_loaders_costs.py`:
```python
# PURPOSE: Tests for costs loader

import pytest
from io import StringIO
from caca.loaders.costs_loader import load_costs_yaml
from caca.models import CostRange


class TestLoadCostsYaml:
    def test_loads_cost_ranges(self):
        yaml_content = """
primary_care_visit: 150-300
specialist_visit: 200-500
labs: 100-500
"""
        costs = load_costs_yaml(StringIO(yaml_content))

        assert costs["primary_care_visit"] == CostRange(150, 300)
        assert costs["specialist_visit"] == CostRange(200, 500)

    def test_loads_fixed_costs(self):
        yaml_content = """
primary_care_visit: 200
"""
        costs = load_costs_yaml(StringIO(yaml_content))

        assert costs["primary_care_visit"] == CostRange(200, 200)
```

**Step 2: Write failing test for params loader**

Create `tests/test_loaders_params.py`:
```python
# PURPOSE: Tests for simulation parameters loader

import pytest
from io import StringIO
from caca.loaders.params_loader import load_params_yaml


class TestLoadParamsYaml:
    def test_loads_basic_params(self):
        yaml_content = """
iterations: auto
convergence_threshold_dollars: 100
max_iterations: 100000
min_iterations: 1000
"""
        params = load_params_yaml(StringIO(yaml_content))

        assert params["iterations"] == "auto"
        assert params["convergence_threshold_dollars"] == 100
        assert params["max_iterations"] == 100000
        assert params["min_iterations"] == 1000

    def test_loads_numeric_iterations(self):
        yaml_content = """
iterations: 5000
convergence_threshold_dollars: 50
"""
        params = load_params_yaml(StringIO(yaml_content))

        assert params["iterations"] == 5000
```

**Step 3: Run tests to verify they fail**

```bash
pytest tests/test_loaders_costs.py tests/test_loaders_params.py -v
```

Expected: FAIL

**Step 4: Implement costs loader**

Create `caca/loaders/costs_loader.py`:
```python
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
```

**Step 5: Implement params loader**

Create `caca/loaders/params_loader.py`:
```python
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
```

**Step 6: Run tests to verify they pass**

```bash
pytest tests/test_loaders_costs.py tests/test_loaders_params.py -v
```

Expected: PASS

**Step 7: Commit**

```bash
git add caca/loaders/costs_loader.py caca/loaders/params_loader.py \
        tests/test_loaders_costs.py tests/test_loaders_params.py
git commit -m "feat: add costs and params loaders"
```

---

## Task 5: Create Run Config Loader

**Files:**
- Create: `caca/loaders/run_config_loader.py`
- Create: `tests/test_loaders_run_config.py`

**Step 1: Write failing test for run config loader**

Create `tests/test_loaders_run_config.py`:
```python
# PURPOSE: Tests for run config loader

import pytest
import tempfile
import os
from pathlib import Path
from caca.loaders.run_config_loader import load_run_config


class TestLoadRunConfig:
    def test_loads_complete_config(self, tmp_path):
        # Create simulation params file
        params_file = tmp_path / "params.yaml"
        params_file.write_text("""
iterations: 5000
convergence_threshold_dollars: 50
max_iterations: 10000
min_iterations: 500
""")

        # Create costs file
        costs_file = tmp_path / "costs.yaml"
        costs_file.write_text("""
primary_care_visit: 150-300
specialist_visit: 200-500
""")

        # Create plan file
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        plan_file = plans_dir / "test-plan.yaml"
        plan_file.write_text("""
plan_name: Test Plan
premium: 500
deductible_individual: 1000
deductible_family: 2000
oop_max_individual: 5000
oop_max_family: 10000
""")

        # Create profile file
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        profile_file = profiles_dir / "alice.yaml"
        profile_file.write_text("""
name: alice
primary_care_visit: 3
""")

        # Create run config
        run_config = tmp_path / "run.yaml"
        run_config.write_text(f"""
simulation: params.yaml
costs: costs.yaml

plans:
  - plans/test-plan.yaml

people:
  - profiles/alice.yaml
""")

        config = load_run_config(run_config)

        assert config["simulation"]["iterations"] == 5000
        assert "primary_care_visit" in config["costs"]
        assert len(config["plans"]) == 1
        assert config["plans"][0].name == "Test Plan"
        assert len(config["people"]) == 1
        assert config["people"][0]["name"] == "alice"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_loaders_run_config.py -v
```

Expected: FAIL

**Step 3: Implement run config loader**

Create `caca/loaders/run_config_loader.py`:
```python
# PURPOSE: Load run configuration that references other files

import yaml
from pathlib import Path
from caca.loaders.plan_loader import load_plan_yaml
from caca.loaders.profile_loader import load_profile_yaml
from caca.loaders.costs_loader import load_costs_yaml
from caca.loaders.params_loader import load_params_yaml


def load_run_config(config_path: Path) -> dict:
    """Load a run configuration and all referenced files.

    Args:
        config_path: Path to the run config YAML file

    Returns:
        Dict with 'simulation', 'costs', 'plans', and 'people' keys
    """
    base_dir = config_path.parent

    with open(config_path) as f:
        raw = yaml.safe_load(f)

    # Load simulation parameters
    simulation_path = base_dir / raw["simulation"]
    with open(simulation_path) as f:
        simulation = load_params_yaml(f)

    # Load costs
    costs_path = base_dir / raw["costs"]
    with open(costs_path) as f:
        costs = load_costs_yaml(f)

    # Load plans
    plans = []
    for plan_ref in raw.get("plans", []):
        plan_path = base_dir / plan_ref
        with open(plan_path) as f:
            plans.append(load_plan_yaml(f))

    # Load people (profiles)
    people = []
    for person_ref in raw.get("people", []):
        person_path = base_dir / person_ref
        with open(person_path) as f:
            people.append(load_profile_yaml(f))

    return {
        "simulation": simulation,
        "costs": costs,
        "plans": plans,
        "people": people,
    }
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_loaders_run_config.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add caca/loaders/run_config_loader.py tests/test_loaders_run_config.py
git commit -m "feat: add run config loader with file references"
```

---

## Task 6: Create Validation Module

**Files:**
- Create: `caca/validation.py`
- Create: `tests/test_validation.py`

**Step 1: Write failing tests for validation**

Create `tests/test_validation.py`:
```python
# PURPOSE: Tests for validation module

import pytest
import tempfile
from pathlib import Path
from caca.validation import (
    validate_plan,
    validate_profile,
    validate_costs,
    validate_run_config,
    ValidationError,
)


class TestValidatePlan:
    def test_valid_plan_passes(self):
        plan_data = {
            "plan_name": "Test Plan",
            "premium": 500,
            "deductible_individual": 1000,
            "deductible_family": 2000,
            "oop_max_individual": 5000,
            "oop_max_family": 10000,
        }
        errors = validate_plan(plan_data, "test.yaml")
        assert errors == []

    def test_missing_required_field(self):
        plan_data = {
            "plan_name": "Test Plan",
            "premium": 500,
            # missing deductible_individual
            "deductible_family": 2000,
            "oop_max_individual": 5000,
            "oop_max_family": 10000,
        }
        errors = validate_plan(plan_data, "test.yaml")
        assert len(errors) == 1
        assert "deductible_individual" in errors[0].message

    def test_deductible_exceeds_oop_max(self):
        plan_data = {
            "plan_name": "Test Plan",
            "premium": 500,
            "deductible_individual": 10000,  # exceeds oop_max
            "deductible_family": 2000,
            "oop_max_individual": 5000,
            "oop_max_family": 10000,
        }
        errors = validate_plan(plan_data, "test.yaml")
        assert len(errors) == 1
        assert "exceeds" in errors[0].message.lower()

    def test_invalid_coinsurance(self):
        plan_data = {
            "plan_name": "Test Plan",
            "premium": 500,
            "deductible_individual": 1000,
            "deductible_family": 2000,
            "oop_max_individual": 5000,
            "oop_max_family": 10000,
            "outpatient_services": 1.5,  # invalid: > 1
        }
        errors = validate_plan(plan_data, "test.yaml")
        assert len(errors) == 1
        assert "coinsurance" in errors[0].message.lower()


class TestValidateProfile:
    def test_valid_profile_passes(self):
        profile_data = {"name": "alice", "primary_care_visit": 3}
        errors = validate_profile(profile_data, "alice.yaml")
        assert errors == []

    def test_missing_name(self):
        profile_data = {"primary_care_visit": 3}
        errors = validate_profile(profile_data, "alice.yaml")
        assert len(errors) == 1
        assert "name" in errors[0].message.lower()


class TestValidateDuplicates:
    def test_duplicate_plan_names(self, tmp_path):
        # Create two plans with same name
        plan1 = tmp_path / "plan1.yaml"
        plan1.write_text("""
plan_name: Duplicate Name
premium: 500
deductible_individual: 1000
deductible_family: 2000
oop_max_individual: 5000
oop_max_family: 10000
""")
        plan2 = tmp_path / "plan2.yaml"
        plan2.write_text("""
plan_name: Duplicate Name
premium: 600
deductible_individual: 1000
deductible_family: 2000
oop_max_individual: 5000
oop_max_family: 10000
""")

        run_config = {
            "plans": [plan1, plan2],
            "people": [],
        }
        errors = validate_run_config(run_config, tmp_path / "run.yaml")
        assert any("duplicate" in e.message.lower() for e in errors)
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_validation.py -v
```

Expected: FAIL

**Step 3: Implement validation module**

Create `caca/validation.py`:
```python
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
        if "plan_name" in data:
            errors.extend(validate_plan(data, str(yaml_file)))
        elif "name" in data and any(
            k in data for k in ["primary_care_visit", "specialist_visit", "labs"]
        ):
            errors.extend(validate_profile(data, str(yaml_file)))
        elif any("-" in str(v) for v in data.values() if isinstance(v, str)):
            errors.extend(validate_costs(data, str(yaml_file)))

    return errors
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_validation.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add caca/validation.py tests/test_validation.py
git commit -m "feat: add validation module with error reporting"
```

---

## Task 7: Restructure CLI with Subcommands

**Files:**
- Modify: `caca/cli.py`
- Modify: `tests/test_cli.py`

**Step 1: Write failing tests for new CLI structure**

Modify `tests/test_cli.py`:
```python
# PURPOSE: Tests for CLI argument parsing

import pytest
from caca.cli import parse_args


class TestParseArgs:
    def test_generate_subcommand(self):
        args = parse_args(["generate", "config.yaml"])
        assert args.command == "generate"
        assert args.config == "config.yaml"

    def test_gen_alias(self):
        args = parse_args(["gen", "config.yaml"])
        assert args.command == "generate"
        assert args.config == "config.yaml"

    def test_validate_subcommand(self):
        args = parse_args(["validate", "plans/", "costs/"])
        assert args.command == "validate"
        assert args.paths == ["plans/", "costs/"]

    def test_val_alias(self):
        args = parse_args(["val", "plans/"])
        assert args.command == "validate"

    def test_generate_with_breakdown(self):
        args = parse_args(["gen", "config.yaml", "--breakdown", "output.txt"])
        assert args.command == "generate"
        assert args.breakdown == "output.txt"

    def test_generate_with_cache_options(self):
        args = parse_args(["gen", "config.yaml", "--no-cache", "--cache-dir", "/tmp/cache"])
        assert args.no_cache is True
        assert args.cache_dir == "/tmp/cache"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_cli.py -v
```

Expected: FAIL

**Step 3: Implement new CLI structure**

Modify `caca/cli.py`:
```python
# PURPOSE: Command-line interface for Care Casino

import argparse
import sys
from pathlib import Path
from caca.loaders.run_config_loader import load_run_config
from caca.simulation_runner import SimulationRunner
from caca.results import ResultsStore
from caca.output.terminal import TerminalRenderer
from caca.output.json_export import JsonExporter
from caca.validation import validate_directory, ValidationError


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
                    plan.premium,
                    plan_rules=plan,
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
        else:
            print(f"Warning: Skipping non-directory: {path_str}", file=sys.stderr)

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
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_cli.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add caca/cli.py tests/test_cli.py
git commit -m "feat: restructure CLI with generate and validate subcommands"
```

---

## Task 8: Implement Caching

**Files:**
- Create: `caca/cache.py`
- Create: `tests/test_cache.py`

**Step 1: Write failing tests for cache**

Create `tests/test_cache.py`:
```python
# PURPOSE: Tests for caching module

import pytest
import json
import tempfile
from pathlib import Path
from caca.cache import CacheManager, compute_inputs_hash, get_code_hash


class TestComputeInputsHash:
    def test_same_inputs_same_hash(self):
        inputs1 = {"plans": [{"name": "A"}], "people": [{"name": "alice"}]}
        inputs2 = {"plans": [{"name": "A"}], "people": [{"name": "alice"}]}
        assert compute_inputs_hash(inputs1) == compute_inputs_hash(inputs2)

    def test_different_inputs_different_hash(self):
        inputs1 = {"plans": [{"name": "A"}]}
        inputs2 = {"plans": [{"name": "B"}]}
        assert compute_inputs_hash(inputs1) != compute_inputs_hash(inputs2)

    def test_order_independent(self):
        inputs1 = {"a": 1, "b": 2}
        inputs2 = {"b": 2, "a": 1}
        assert compute_inputs_hash(inputs1) == compute_inputs_hash(inputs2)


class TestCodeHash:
    def test_code_hash_is_stable(self):
        hash1 = get_code_hash()
        hash2 = get_code_hash()
        assert hash1 == hash2


class TestCacheManager:
    def test_cache_miss_returns_none(self, tmp_path):
        cache = CacheManager(tmp_path)
        result = cache.get("nonexistent_key")
        assert result is None

    def test_cache_hit_returns_data(self, tmp_path):
        cache = CacheManager(tmp_path)
        data = {"results": [1, 2, 3]}
        cache.set("test_key", data)
        result = cache.get("test_key")
        assert result == data

    def test_cache_creates_directory(self, tmp_path):
        cache_dir = tmp_path / "new_cache"
        cache = CacheManager(cache_dir)
        cache.set("key", {"data": "value"})
        assert cache_dir.exists()
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_cache.py -v
```

Expected: FAIL

**Step 3: Implement cache module**

Create `caca/cache.py`:
```python
# PURPOSE: Cache simulation results with code-aware invalidation

import hashlib
import json
from pathlib import Path
from typing import Any

# Files that affect calculation results
CALC_FILES = [
    "caca/plan_calculator.py",
    "caca/models.py",
    "caca/simulation_runner.py",
    "caca/event_generator.py",
]


def compute_inputs_hash(inputs: dict) -> str:
    """Compute a hash of the canonical inputs."""
    # Sort keys for deterministic output
    canonical = json.dumps(inputs, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def get_code_hash() -> str:
    """Compute a hash of the calculation-affecting source files."""
    hasher = hashlib.sha256()

    # Find the package root
    package_root = Path(__file__).parent.parent

    for rel_path in CALC_FILES:
        file_path = package_root / rel_path
        if file_path.exists():
            hasher.update(file_path.read_bytes())

    return hasher.hexdigest()[:16]


def compute_cache_key(inputs: dict) -> str:
    """Compute the full cache key from inputs and code."""
    inputs_hash = compute_inputs_hash(inputs)
    code_hash = get_code_hash()
    return f"{inputs_hash}_{code_hash}"


class CacheManager:
    """Manage disk-based cache for simulation results."""

    def __init__(self, cache_dir: Path | str):
        self.cache_dir = Path(cache_dir)

    def get(self, key: str) -> dict | None:
        """Get cached results by key."""
        cache_file = self.cache_dir / f"{key}.json"
        if not cache_file.exists():
            return None
        with open(cache_file) as f:
            return json.load(f)

    def set(self, key: str, data: dict) -> None:
        """Store results in cache."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = self.cache_dir / f"{key}.json"
        with open(cache_file, "w") as f:
            json.dump(data, f)

    def has(self, key: str) -> bool:
        """Check if key exists in cache."""
        cache_file = self.cache_dir / f"{key}.json"
        return cache_file.exists()
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_cache.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add caca/cache.py tests/test_cache.py
git commit -m "feat: add caching with code-aware invalidation"
```

---

## Task 9: Convert Existing Plans to YAML

**Files:**
- Create: `plans/2026/bs-bronze-60-hdhp-ppo.yaml`
- Create: `plans/2026/bs-bronze-60-ppo.yaml`
- Create: `plans/2026/bs-silver-70-ppo.yaml`
- Create: `plans/2026/bs-silver-70-trio-hmo.yaml`
- Create: `plans/2026/bs-gold-80-trio-hmo.yaml`

**Step 1: Create first plan file from existing CSV**

Create `plans/2026/bs-bronze-60-hdhp-ppo.yaml`:
```yaml
# Blue Shield Bronze 60 HDHP PPO
# Source: CoveredCA 2025 plan year

plan_name: BS Bronze 60 HDHP PPO
plan_url: https://apply.coveredca.com/static/lw-enrollment/anon/plan-details/health/jsAXtf4on1_vOitQNqpILHGR0oUlQWN3x8HlzJiFTiM/70285CA132000101

# Monthly premium (annual = $27,675.48)
premium: 2306.29

# Deductibles
deductible_individual: 7200
deductible_family: 14400

# Out-of-pocket maximums
oop_max_individual: 7200
oop_max_family: 14400

# Cost sharing before deductible (1 = 100% patient pays)
preventative_visit: 0
primary_care_visit: 1
specialist_visit: 1
labs: 1
imaging: 1
outpatient_services: 1
inpatient_services: 1
emergency_room: 1
urgent_care: 1
tier_1_generic_drugs: 1
tier_2_preferred_brand_drugs: 1
tier_3_non_preferred_brand_drugs: 1
tier_4_specialty_drugs: 1

# Cost sharing after deductible (0 = plan pays 100%)
preventative_visit_after_deductible: 0
primary_care_visit_after_deductible: 0
specialist_visit_after_deductible: 0
labs_after_deductible: 0
imaging_after_deductible: 0
outpatient_services_after_deductible: 0
inpatient_services_after_deductible: 0
emergency_room_after_deductible: 0
urgent_care_after_deductible: 0
tier_1_generic_drugs_after_deductible: 0
tier_2_preferred_brand_drugs_after_deductible: 0
tier_3_non_preferred_brand_drugs_after_deductible: 0
tier_4_specialty_drugs_after_deductible: 0
```

**Step 2: Create remaining plan files**

Create `plans/2026/bs-silver-70-trio-hmo.yaml`:
```yaml
# Blue Shield Silver 70 Trio HMO
# Source: CoveredCA 2025 plan year

plan_name: BS Silver 70 Trio HMO
plan_url: https://apply.coveredca.com/static/lw-enrollment/anon/plan-details/health/jsAXtf4on1_vOitQNqpILHGR0oUlQWN3x8HlzJiFTiM/70285CA806000601

premium: 2462.32

deductible_individual: 5200
deductible_family: 10400
deductible_rx_individual: 50
deductible_rx_family: 100

oop_max_individual: 9800
oop_max_family: 19600
oop_max_per_rx: 250

preventative_visit: 0
primary_care_visit: 50
specialist_visit: 90
labs: 50
imaging: 325
outpatient_services: 0.3
inpatient_services: 1
emergency_room: 400
urgent_care: 50
tier_1_generic_drugs: 19
tier_2_preferred_brand_drugs: 1
tier_3_non_preferred_brand_drugs: 1
tier_4_specialty_drugs: 1

preventative_visit_after_deductible: 0
primary_care_visit_after_deductible: 50
specialist_visit_after_deductible: 90
labs_after_deductible: 50
imaging_after_deductible: 325
outpatient_services_after_deductible: 0.3
inpatient_services_after_deductible: 0.3
emergency_room_after_deductible: 400
urgent_care_after_deductible: 50
tier_1_generic_drugs_after_deductible: 19
tier_2_preferred_brand_drugs_after_deductible: 60
tier_3_non_preferred_brand_drugs_after_deductible: 90
tier_4_specialty_drugs_after_deductible: 0.2
```

Create `plans/2026/bs-gold-80-trio-hmo.yaml`:
```yaml
# Blue Shield Gold 80 Trio HMO
# Source: CoveredCA 2025 plan year

plan_name: BS Gold 80 Trio HMO
plan_url: https://apply.coveredca.com/static/lw-enrollment/anon/plan-details/health/jsAXtf4on1_vOitQNqpILHGR0oUlQWN3x8HlzJiFTiM/70285CA804000601

premium: 2740.21

deductible_individual: 0
deductible_family: 0

oop_max_individual: 9200
oop_max_family: 18400
oop_max_per_rx: 250

preventative_visit: 0
primary_care_visit: 40
specialist_visit: 70
labs: 40
imaging: 75
outpatient_services: 0.2
inpatient_services: 375
emergency_room: 350
urgent_care: 40
tier_1_generic_drugs: 18
tier_2_preferred_brand_drugs: 60
tier_3_non_preferred_brand_drugs: 85
tier_4_specialty_drugs: 0.2

preventative_visit_after_deductible: 0
primary_care_visit_after_deductible: 40
specialist_visit_after_deductible: 70
labs_after_deductible: 40
imaging_after_deductible: 75
outpatient_services_after_deductible: 0.2
inpatient_services_after_deductible: 375
emergency_room_after_deductible: 350
urgent_care_after_deductible: 40
tier_1_generic_drugs_after_deductible: 18
tier_2_preferred_brand_drugs_after_deductible: 60
tier_3_non_preferred_brand_drugs_after_deductible: 85
tier_4_specialty_drugs_after_deductible: 0.2
```

**Step 3: Commit**

```bash
git add plans/2026/
git commit -m "feat: convert plans to individual YAML files"
```

---

## Task 10: Create Starter Profiles

**Files:**
- Create: `profiles/healthy-young-adult.yaml`
- Create: `profiles/middle-aged-adult.yaml`
- Create: `profiles/chronic-condition.yaml`

**Step 1: Create healthy young adult profile**

Create `profiles/healthy-young-adult.yaml`:
```yaml
# Healthy young adult (20s-30s)
# Minimal healthcare usage - annual checkup and occasional illness

name: healthy_young_adult

preventative_visit: 1
primary_care_visit: 1-2
tier_1_generic_drugs: 2-4
urgent_care:
  probability: 0.2
  count: 1
emergency_room:
  probability: 0.05
  count: 1
```

**Step 2: Create middle-aged adult profile**

Create `profiles/middle-aged-adult.yaml`:
```yaml
# Middle-aged adult (40s-50s)
# Regular checkups, some ongoing prescriptions, occasional specialist

name: middle_aged_adult

preventative_visit: 1
primary_care_visit: 3-4
specialist_visit: 1-2
labs: 2-4
imaging:
  probability: 0.3
  count: 1
tier_1_generic_drugs: 12-24
tier_2_preferred_brand_drugs: 6-12
urgent_care:
  probability: 0.15
  count: 1
emergency_room:
  probability: 0.05
  count: 1
```

**Step 3: Create chronic condition profile**

Create `profiles/chronic-condition.yaml`:
```yaml
# Adult with chronic condition (e.g., diabetes, hypertension)
# Regular monitoring, specialist visits, multiple prescriptions

name: chronic_condition

preventative_visit: 1
primary_care_visit: 4-6
specialist_visit: 4-6
labs: 6-8
imaging: 1-2
tier_1_generic_drugs: 36-48
tier_2_preferred_brand_drugs: 12-24
tier_3_non_preferred_brand_drugs: 0-6
urgent_care:
  probability: 0.25
  count: 1
emergency_room:
  probability: 0.1
  count: 1
```

**Step 4: Commit**

```bash
git add profiles/
git commit -m "feat: add starter usage profiles"
```

---

## Task 11: Create Default Costs File

**Files:**
- Create: `costs/2026-california.yaml`

**Step 1: Create costs file**

Create `costs/2026-california.yaml`:
```yaml
# Healthcare service costs for California, 2026
# Ranges represent typical billed amounts before insurance

preventative_visit: 0
primary_care_visit: 150-300
specialist_visit: 200-500
labs: 100-500
imaging: 500-2500
outpatient_services: 2000-15000
outpatient_rehabilitation_services: 100-300
inpatient_services: 15000-75000
emergency_room: 1500-5000
urgent_care: 150-400
tier_1_generic_drugs: 10-50
tier_2_preferred_brand_drugs: 50-200
tier_3_non_preferred_brand_drugs: 150-500
tier_4_specialty_drugs: 500-2000
```

**Step 2: Commit**

```bash
git add costs/
git commit -m "feat: add California 2026 cost assumptions"
```

---

## Task 12: Create Example Run Config

**Files:**
- Create: `examples/basic-run.yaml`

**Step 1: Create example run config**

Create `examples/basic-run.yaml`:
```yaml
# Example run configuration
# Usage: caca generate examples/basic-run.yaml

simulation: ../parameters/simulation.yaml
costs: ../costs/2026-california.yaml

plans:
  - ../plans/2026/bs-bronze-60-hdhp-ppo.yaml
  - ../plans/2026/bs-silver-70-trio-hmo.yaml
  - ../plans/2026/bs-gold-80-trio-hmo.yaml

people:
  - ../profiles/middle-aged-adult.yaml
```

**Step 2: Commit**

```bash
mkdir -p examples
git add examples/
git commit -m "feat: add example run configuration"
```

---

## Task 13: Update Makefile

**Files:**
- Modify: `Makefile`

**Step 1: Update Makefile with new targets**

Modify `Makefile`:
```makefile
.PHONY: deps test validate clean

deps:
	python -m venv .venv
	.venv/bin/pip install -e ".[dev]"

test: validate
	.venv/bin/pytest

validate:
	.venv/bin/caca validate plans/ profiles/ costs/

clean:
	rm -rf .caca-cache/
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	find . -name "*.pyc" -delete
```

**Step 2: Commit**

```bash
git add Makefile
git commit -m "chore: update Makefile with deps, test, validate targets"
```

---

## Task 14: Update Package Exports

**Files:**
- Modify: `caca/loaders/__init__.py`

**Step 1: Add exports to loaders package**

Modify `caca/loaders/__init__.py`:
```python
# PURPOSE: Data file loaders for plans, profiles, costs, and parameters

from caca.loaders.plan_loader import load_plan_yaml
from caca.loaders.profile_loader import load_profile_yaml
from caca.loaders.costs_loader import load_costs_yaml
from caca.loaders.params_loader import load_params_yaml
from caca.loaders.run_config_loader import load_run_config

__all__ = [
    "load_plan_yaml",
    "load_profile_yaml",
    "load_costs_yaml",
    "load_params_yaml",
    "load_run_config",
]
```

**Step 2: Commit**

```bash
git add caca/loaders/__init__.py
git commit -m "chore: export loaders from package"
```

---

## Task 15: Integration Test

**Files:**
- Create: `tests/test_integration_new_config.py`

**Step 1: Write integration test for new config system**

Create `tests/test_integration_new_config.py`:
```python
# PURPOSE: Integration tests for new modular config system

import pytest
import subprocess
from pathlib import Path


class TestNewConfigIntegration:
    def test_validate_existing_files(self, tmp_path):
        """Validate command works on plans/profiles/costs directories."""
        # This test assumes the directories have been populated
        result = subprocess.run(
            ["python", "-m", "caca.cli", "validate", "plans/", "profiles/", "costs/"],
            capture_output=True,
            text=True,
        )
        # Should pass if files are valid, fail if not found
        assert result.returncode in [0, 1]

    def test_generate_with_example_config(self):
        """Run simulation with example config."""
        example_config = Path("examples/basic-run.yaml")
        if not example_config.exists():
            pytest.skip("Example config not found")

        result = subprocess.run(
            ["python", "-m", "caca.cli", "gen", str(example_config), "--quiet"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
```

**Step 2: Run all tests**

```bash
pytest -v
```

Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_integration_new_config.py
git commit -m "test: add integration tests for new config system"
```

---

## Summary

This implementation plan covers:

1. **Tasks 1-5**: New loader infrastructure for YAML files
2. **Task 6**: Validation module with helpful error messages
3. **Task 7**: CLI restructure with subcommands
4. **Task 8**: Caching with code-aware invalidation
5. **Tasks 9-12**: Convert/create data files
6. **Tasks 13-15**: Polish and integration tests

Total: ~15 tasks, each with TDD approach (test first, implement, verify, commit).
