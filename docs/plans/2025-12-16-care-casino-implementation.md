# Care Casino Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Monte Carlo simulator that compares US healthcare plan costs based on user-defined usage profiles and outputs ranked recommendations with confidence intervals.

**Architecture:** YAML config defines profiles and households; CSV defines plan rules. EventGenerator creates dated healthcare events, PlanCalculator applies plan rules to compute costs, SimulationRunner orchestrates Monte Carlo iterations with adaptive convergence, OutputRenderer displays results.

**Tech Stack:** Python 3.11+, PyYAML, NumPy, pytest

---

## Task 1: Project Setup

**Files:**
- Create: `pyproject.toml`
- Create: `caca/__init__.py`
- Create: `tests/__init__.py`

**Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "caca"
version = "0.1.0"
description = "Care Casino - Monte Carlo healthcare cost simulator"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "pyyaml>=6.0",
    "numpy>=1.24",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
]

[project.scripts]
caca = "caca.cli:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

**Step 2: Create package init files**

`caca/__init__.py`:
```python
# PURPOSE: Care Casino - Monte Carlo healthcare cost simulator package
```

`tests/__init__.py`:
```python
# PURPOSE: Test package for Care Casino
```

**Step 3: Create virtual environment and install**

Run:
```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
```

**Step 4: Verify installation**

Run: `python -c "import caca; print('OK')"`
Expected: `OK`

**Step 5: Commit**

```bash
git add pyproject.toml caca/__init__.py tests/__init__.py
git commit -m "feat: initialize project structure with dependencies"
```

---

## Task 2: Normalize plans.csv to snake_case

**Files:**
- Modify: `plans.csv`

**Step 1: Transform plans.csv**

Replace the first column values (row names) with snake_case equivalents:

| Original | Snake case |
|----------|------------|
| Plan Name | plan_name |
| Plan URL | plan_url |
| Premium | premium |
| Deductible Individual | deductible_individual |
| Deductible Family | deductible_family |
| Deductible Rx Individual | deductible_rx_individual |
| Deductible Rx Family | deductible_rx_family |
| OOP Max Individual | oop_max_individual |
| OOP Max Family | oop_max_family |
| OOP Max Rx Individual | oop_max_rx_individual |
| OOP Max Rx Family | oop_max_rx_family |
| OOP Max per Rx | oop_max_per_rx |
| Preventative Visit | preventative_visit |
| Preventative Visit after deductible | preventative_visit_after_deductible |
| Primary Care Visit | primary_care_visit |
| Primary Care Visit after decuctible | primary_care_visit_after_deductible |
| Specialist Visit | specialist_visit |
| Specialist Visit after deductible | specialist_visit_after_deductible |
| Labs | labs |
| Labs after deductible | labs_after_deductible |
| Imaging | imaging |
| Imaging after deductible | imaging_after_deductible |
| Outpatient Services | outpatient_services |
| Outpatient Services after deductible | outpatient_services_after_deductible |
| Inpatient Services | inpatient_services |
| Inpatient Services after deductible | inpatient_services_after_deductible |
| Emergency Room | emergency_room |
| Emergency Room after deductible | emergency_room_after_deductible |
| Urgent Care | urgent_care |
| Urgent Care after deductible | urgent_care_after_deductible |
| Tier 1 Generic Drugs | tier_1_generic_drugs |
| Tier 1 Generic Drugs after deductible | tier_1_generic_drugs_after_deductible |
| Tier 2 Preferred Brand Drugs | tier_2_preferred_brand_drugs |
| Tier 2 Preferred Brand Drugs after deductible | tier_2_preferred_brand_drugs_after_deductible |
| Tier 3 Non-preferred Brand Drugs | tier_3_non_preferred_brand_drugs |
| Tier 3 Non-preferred Brand Drugs after deductible | tier_3_non_preferred_brand_drugs_after_deductible |
| Tier 4 Specialist Drugs | tier_4_specialty_drugs |
| Tier 4 Specialist Drugs after deductible | tier_4_specialty_drugs_after_deductible |

**Step 2: Verify CSV loads correctly**

Run: `python -c "import csv; r=csv.reader(open('plans.csv')); print([row[0] for row in r])"`
Expected: List starting with `['plan_name', 'plan_url', 'premium', ...]`

**Step 3: Commit**

```bash
git add plans.csv
git commit -m "refactor: normalize plans.csv row names to snake_case"
```

---

## Task 3: Create config.template.yaml

**Files:**
- Create: `config.template.yaml`

**Step 1: Write template file**

```yaml
# Care Casino Configuration Template
# Copy this file to config.yaml and customize for your situation

simulation:
  # Number of scenarios to simulate
  # Use "auto" for adaptive convergence, or a specific number like 10000
  iterations: auto

  # For auto mode: stop when 95% CI is within +/- this many dollars
  convergence_threshold_dollars: 100

  # For auto mode: safety limits
  max_iterations: 100000
  min_iterations: 1000

# Default costs for services when not specified in profiles
# Format: single value, range (min-max), or with $ prefix
defaults:
  costs:
    preventative_visit: 0
    primary_care_visit: 150-300
    specialist_visit: 200-500
    labs: 100-500
    imaging: 500-2500
    outpatient_services: 2000-15000
    inpatient_services: 15000-75000
    emergency_room: 1500-5000
    urgent_care: 150-400
    tier_1_generic_drugs: 10-50
    tier_2_preferred_brand_drugs: 50-200
    tier_3_non_preferred_brand_drugs: 150-500
    tier_4_specialty_drugs: 500-2000

# Usage profiles
# Each profile defines expected healthcare usage for a type of person
profiles:
  # Example: healthy adult with minimal healthcare needs
  healthy_adult:
    preventative_visit: 1
    primary_care_visit: 1-3
    specialist_visit: 0-2
    labs: 1-3
    imaging: { probability: 0.1 }
    emergency_room: { probability: 0.05 }
    urgent_care: { probability: 0.15, count: 1-2 }
    tier_1_generic_drugs: 0-6

  # Example: child with typical pediatric needs
  child:
    preventative_visit: 2
    primary_care_visit: 3-6
    specialist_visit: 1-3
    labs: 1-2
    urgent_care: { probability: 0.3, count: 1-2 }
    tier_1_generic_drugs: 2-6

  # Example: person with planned surgery
  planned_surgery:
    preventative_visit: 1
    primary_care_visit: 4-6
    specialist_visit:
      - { cost: 300, date: 2025-03-15, description: "pre-op consult" }
      - { cost: 300, date: 2025-05-01, description: "post-op follow-up" }
      - { count: 2-4 }
    labs:
      - { cost: 200, date: 2025-03-15, description: "pre-op bloodwork" }
      - { count: 2-4 }
    imaging:
      - { cost: 1500, date: 2025-03-15, description: "pre-op MRI" }
    inpatient_services:
      - { cost: 50000, date: 2025-04-01, description: "surgery" }
    tier_1_generic_drugs: 6-12

  # Example: person with chronic condition requiring specialty drugs
  chronic_condition:
    preventative_visit: 1
    primary_care_visit: 2-4
    specialist_visit: 4-6
    labs: 4-8
    tier_1_generic_drugs: 12
    tier_4_specialty_drugs:
      - { count: 12, cost: 800, description: "monthly injection" }

  # Uncovered services example (dental, vision, etc.)
  # These bypass plan rules and add directly to total cost
  # uncovered:
  #   - { cost: 1200, date: 2025-06-15, description: "dental crown" }
  #   - { cost: 150, count: 2, description: "dental cleanings" }

# Household members
# Assign one profile to each person (1-5 people)
household:
  - name: person1
    profile: healthy_adult
  # - name: person2
  #   profile: healthy_adult
  # - name: person3
  #   profile: child
```

**Step 2: Validate YAML syntax**

Run: `python -c "import yaml; yaml.safe_load(open('config.template.yaml')); print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add config.template.yaml
git commit -m "feat: add config template with all service categories"
```

---

## Task 4: Data Models

**Files:**
- Create: `caca/models.py`
- Create: `tests/test_models.py`

**Step 1: Write the failing test**

`tests/test_models.py`:
```python
# PURPOSE: Tests for data models

import pytest
from datetime import date
from caca.models import (
    Event,
    ServiceType,
    Person,
    Household,
    SimulationConfig,
    PlanRules,
    ScenarioResult,
    PlanResult,
)


class TestEvent:
    def test_create_event(self):
        event = Event(
            service_type=ServiceType.SPECIALIST_VISIT,
            cost=300.0,
            date=date(2025, 3, 15),
            person="alice",
            description="pre-op consult",
        )
        assert event.service_type == ServiceType.SPECIALIST_VISIT
        assert event.cost == 300.0
        assert event.date == date(2025, 3, 15)
        assert event.person == "alice"
        assert event.description == "pre-op consult"

    def test_event_without_description(self):
        event = Event(
            service_type=ServiceType.PRIMARY_CARE_VISIT,
            cost=200.0,
            date=date(2025, 6, 1),
            person="bob",
        )
        assert event.description is None


class TestServiceType:
    def test_service_types_exist(self):
        assert ServiceType.PREVENTATIVE_VISIT
        assert ServiceType.PRIMARY_CARE_VISIT
        assert ServiceType.SPECIALIST_VISIT
        assert ServiceType.LABS
        assert ServiceType.IMAGING
        assert ServiceType.OUTPATIENT_SERVICES
        assert ServiceType.INPATIENT_SERVICES
        assert ServiceType.EMERGENCY_ROOM
        assert ServiceType.URGENT_CARE
        assert ServiceType.TIER_1_GENERIC_DRUGS
        assert ServiceType.TIER_2_PREFERRED_BRAND_DRUGS
        assert ServiceType.TIER_3_NON_PREFERRED_BRAND_DRUGS
        assert ServiceType.TIER_4_SPECIALTY_DRUGS
        assert ServiceType.UNCOVERED

    def test_is_drug(self):
        assert ServiceType.TIER_1_GENERIC_DRUGS.is_drug() is True
        assert ServiceType.TIER_4_SPECIALTY_DRUGS.is_drug() is True
        assert ServiceType.PRIMARY_CARE_VISIT.is_drug() is False


class TestPerson:
    def test_create_person(self):
        person = Person(name="alice", profile="healthy_adult")
        assert person.name == "alice"
        assert person.profile == "healthy_adult"


class TestHousehold:
    def test_create_household(self):
        household = Household(
            members=[
                Person(name="alice", profile="planned_surgery"),
                Person(name="bob", profile="healthy_adult"),
            ]
        )
        assert len(household.members) == 2
        assert household.members[0].name == "alice"


class TestPlanRules:
    def test_create_plan_rules(self):
        rules = PlanRules(
            name="Test Plan",
            premium=1000.0,
            deductible_individual=1500.0,
            deductible_family=3000.0,
            oop_max_individual=5000.0,
            oop_max_family=10000.0,
            service_costs={},
            service_costs_after_deductible={},
        )
        assert rules.name == "Test Plan"
        assert rules.premium == 1000.0
        assert rules.deductible_individual == 1500.0


class TestScenarioResult:
    def test_create_scenario_result(self):
        result = ScenarioResult(
            scenario_id=1,
            events=[],
            plan_results={},
        )
        assert result.scenario_id == 1


class TestPlanResult:
    def test_create_plan_result(self):
        result = PlanResult(
            total_cost=5000.0,
            premium=3000.0,
            out_of_pocket=2000.0,
            deductible_hit_date=date(2025, 4, 15),
            oop_max_hit_date=None,
        )
        assert result.total_cost == 5000.0
        assert result.premium == 3000.0
        assert result.out_of_pocket == 2000.0
        assert result.deductible_hit_date == date(2025, 4, 15)
        assert result.oop_max_hit_date is None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL with import errors

**Step 3: Write minimal implementation**

`caca/models.py`:
```python
# PURPOSE: Data models for Care Casino simulation

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class ServiceType(Enum):
    """Types of healthcare services."""

    PREVENTATIVE_VISIT = "preventative_visit"
    PRIMARY_CARE_VISIT = "primary_care_visit"
    SPECIALIST_VISIT = "specialist_visit"
    LABS = "labs"
    IMAGING = "imaging"
    OUTPATIENT_SERVICES = "outpatient_services"
    INPATIENT_SERVICES = "inpatient_services"
    EMERGENCY_ROOM = "emergency_room"
    URGENT_CARE = "urgent_care"
    TIER_1_GENERIC_DRUGS = "tier_1_generic_drugs"
    TIER_2_PREFERRED_BRAND_DRUGS = "tier_2_preferred_brand_drugs"
    TIER_3_NON_PREFERRED_BRAND_DRUGS = "tier_3_non_preferred_brand_drugs"
    TIER_4_SPECIALTY_DRUGS = "tier_4_specialty_drugs"
    UNCOVERED = "uncovered"

    def is_drug(self) -> bool:
        """Return True if this service type is a prescription drug."""
        return self in (
            ServiceType.TIER_1_GENERIC_DRUGS,
            ServiceType.TIER_2_PREFERRED_BRAND_DRUGS,
            ServiceType.TIER_3_NON_PREFERRED_BRAND_DRUGS,
            ServiceType.TIER_4_SPECIALTY_DRUGS,
        )


@dataclass
class Event:
    """A single healthcare event."""

    service_type: ServiceType
    cost: float
    date: date
    person: str
    description: Optional[str] = None


@dataclass
class Person:
    """A household member."""

    name: str
    profile: str


@dataclass
class Household:
    """A household of people to simulate."""

    members: list[Person]


@dataclass
class SimulationConfig:
    """Configuration for the simulation run."""

    iterations: int | str  # int or "auto"
    convergence_threshold_dollars: float
    max_iterations: int
    min_iterations: int


@dataclass
class CostRange:
    """A range of possible costs."""

    min_cost: float
    max_cost: float


@dataclass
class PlanRules:
    """Rules for a healthcare plan."""

    name: str
    premium: float
    deductible_individual: float
    deductible_family: float
    oop_max_individual: float
    oop_max_family: float
    service_costs: dict[ServiceType, float]  # copay or coinsurance before deductible
    service_costs_after_deductible: dict[ServiceType, float]  # after deductible
    url: Optional[str] = None
    deductible_rx_individual: Optional[float] = None
    deductible_rx_family: Optional[float] = None
    oop_max_rx_individual: Optional[float] = None
    oop_max_rx_family: Optional[float] = None
    oop_max_per_rx: Optional[float] = None
    deductible_model: str = "individual_first"


@dataclass
class PlanResult:
    """Result of running one scenario through one plan."""

    total_cost: float
    premium: float
    out_of_pocket: float
    deductible_hit_date: Optional[date]
    oop_max_hit_date: Optional[date]


@dataclass
class ScenarioResult:
    """Result of one simulated year."""

    scenario_id: int
    events: list[Event]
    plan_results: dict[str, PlanResult]  # plan_name -> result
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add caca/models.py tests/test_models.py
git commit -m "feat: add data models for simulation"
```

---

## Task 5: Plan Loader

**Files:**
- Create: `caca/plan_loader.py`
- Create: `tests/test_plan_loader.py`

**Step 1: Write the failing test**

`tests/test_plan_loader.py`:
```python
# PURPOSE: Tests for CSV plan loading

import pytest
from io import StringIO
from caca.plan_loader import load_plans, parse_value
from caca.models import ServiceType


class TestParseValue:
    def test_parse_integer(self):
        assert parse_value("100") == 100.0

    def test_parse_float(self):
        assert parse_value("0.4") == 0.4

    def test_parse_with_dollar_sign(self):
        assert parse_value("$100") == 100.0

    def test_parse_with_percent(self):
        assert parse_value("40%") == 0.4

    def test_parse_with_comma(self):
        assert parse_value("8,650") == 8650.0

    def test_parse_empty(self):
        assert parse_value("") is None

    def test_parse_whitespace(self):
        assert parse_value("  ") is None


class TestLoadPlans:
    def test_load_single_plan(self):
        csv_content = """plan_name,test_plan
premium,1000
deductible_individual,2000
deductible_family,4000
oop_max_individual,5000
oop_max_family,10000
primary_care_visit,50
primary_care_visit_after_deductible,20
"""
        plans = load_plans(StringIO(csv_content))
        assert len(plans) == 1
        plan = plans[0]
        assert plan.name == "test_plan"
        assert plan.premium == 1000.0
        assert plan.deductible_individual == 2000.0
        assert plan.deductible_family == 4000.0
        assert plan.oop_max_individual == 5000.0
        assert plan.oop_max_family == 10000.0
        assert plan.service_costs[ServiceType.PRIMARY_CARE_VISIT] == 50.0
        assert plan.service_costs_after_deductible[ServiceType.PRIMARY_CARE_VISIT] == 20.0

    def test_load_multiple_plans(self):
        csv_content = """plan_name,plan_a,plan_b
premium,1000,2000
deductible_individual,2000,1000
deductible_family,4000,2000
oop_max_individual,5000,3000
oop_max_family,10000,6000
"""
        plans = load_plans(StringIO(csv_content))
        assert len(plans) == 2
        assert plans[0].name == "plan_a"
        assert plans[1].name == "plan_b"
        assert plans[0].premium == 1000.0
        assert plans[1].premium == 2000.0

    def test_coinsurance_value(self):
        csv_content = """plan_name,test_plan
premium,1000
deductible_individual,2000
deductible_family,4000
oop_max_individual,5000
oop_max_family,10000
imaging,1
imaging_after_deductible,0.4
"""
        plans = load_plans(StringIO(csv_content))
        plan = plans[0]
        # 1 means 100% patient responsibility
        assert plan.service_costs[ServiceType.IMAGING] == 1.0
        # 0.4 means 40% coinsurance
        assert plan.service_costs_after_deductible[ServiceType.IMAGING] == 0.4

    def test_rx_deductible(self):
        csv_content = """plan_name,test_plan
premium,1000
deductible_individual,2000
deductible_family,4000
deductible_rx_individual,500
deductible_rx_family,1000
oop_max_individual,5000
oop_max_family,10000
"""
        plans = load_plans(StringIO(csv_content))
        plan = plans[0]
        assert plan.deductible_rx_individual == 500.0
        assert plan.deductible_rx_family == 1000.0

    def test_empty_rx_deductible(self):
        csv_content = """plan_name,test_plan
premium,1000
deductible_individual,2000
deductible_family,4000
deductible_rx_individual,
deductible_rx_family,
oop_max_individual,5000
oop_max_family,10000
"""
        plans = load_plans(StringIO(csv_content))
        plan = plans[0]
        assert plan.deductible_rx_individual is None
        assert plan.deductible_rx_family is None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_plan_loader.py -v`
Expected: FAIL with import errors

**Step 3: Write minimal implementation**

`caca/plan_loader.py`:
```python
# PURPOSE: Load healthcare plan definitions from CSV

import csv
from typing import TextIO
from caca.models import PlanRules, ServiceType


def parse_value(value: str) -> float | None:
    """Parse a CSV value into a float, handling $, %, and commas."""
    value = value.strip()
    if not value:
        return None

    # Remove dollar sign
    if value.startswith("$"):
        value = value[1:]

    # Handle percentage
    if value.endswith("%"):
        return float(value[:-1]) / 100.0

    # Remove commas
    value = value.replace(",", "")

    return float(value)


# Map CSV row names to ServiceType
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
}


def load_plans(file: TextIO) -> list[PlanRules]:
    """Load plans from a CSV file."""
    reader = csv.reader(file)
    rows = list(reader)

    if not rows:
        return []

    # First row contains plan names
    header = rows[0]
    num_plans = len(header) - 1  # First column is row name

    # Initialize plan data
    plan_data: list[dict] = [{} for _ in range(num_plans)]

    # Parse each row
    for row in rows:
        if not row:
            continue
        row_name = row[0].strip()
        values = row[1:num_plans + 1]

        for i, value in enumerate(values):
            parsed = parse_value(value)
            plan_data[i][row_name] = parsed

    # Build PlanRules objects
    plans = []
    for i, data in enumerate(plan_data):
        service_costs: dict[ServiceType, float] = {}
        service_costs_after_deductible: dict[ServiceType, float] = {}

        for service_name, service_type in SERVICE_TYPE_MAP.items():
            if service_name in data and data[service_name] is not None:
                service_costs[service_type] = data[service_name]
            after_key = f"{service_name}_after_deductible"
            if after_key in data and data[after_key] is not None:
                service_costs_after_deductible[service_type] = data[after_key]

        plan = PlanRules(
            name=data.get("plan_name") or f"plan_{i}",
            premium=data.get("premium") or 0.0,
            deductible_individual=data.get("deductible_individual") or 0.0,
            deductible_family=data.get("deductible_family") or 0.0,
            oop_max_individual=data.get("oop_max_individual") or 0.0,
            oop_max_family=data.get("oop_max_family") or 0.0,
            service_costs=service_costs,
            service_costs_after_deductible=service_costs_after_deductible,
            url=data.get("plan_url"),
            deductible_rx_individual=data.get("deductible_rx_individual"),
            deductible_rx_family=data.get("deductible_rx_family"),
            oop_max_rx_individual=data.get("oop_max_rx_individual"),
            oop_max_rx_family=data.get("oop_max_rx_family"),
            oop_max_per_rx=data.get("oop_max_per_rx"),
            deductible_model=data.get("deductible_model") or "individual_first",
        )
        plans.append(plan)

    return plans
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_plan_loader.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add caca/plan_loader.py tests/test_plan_loader.py
git commit -m "feat: add CSV plan loader"
```

---

## Task 6: Config Loader

**Files:**
- Create: `caca/config_loader.py`
- Create: `tests/test_config_loader.py`

**Step 1: Write the failing test**

`tests/test_config_loader.py`:
```python
# PURPOSE: Tests for YAML config loading

import pytest
from io import StringIO
from caca.config_loader import load_config, parse_cost_range, parse_usage_entry
from caca.models import CostRange


class TestParseCostRange:
    def test_parse_single_value(self):
        result = parse_cost_range("500")
        assert result == CostRange(500.0, 500.0)

    def test_parse_range(self):
        result = parse_cost_range("100-500")
        assert result == CostRange(100.0, 500.0)

    def test_parse_with_dollar_signs(self):
        result = parse_cost_range("$100-$500")
        assert result == CostRange(100.0, 500.0)

    def test_parse_integer(self):
        result = parse_cost_range(500)
        assert result == CostRange(500.0, 500.0)


class TestParseUsageEntry:
    def test_simple_count(self):
        result = parse_usage_entry("2-5")
        assert result["count_min"] == 2
        assert result["count_max"] == 5
        assert result["probability"] == 1.0

    def test_single_count(self):
        result = parse_usage_entry("3")
        assert result["count_min"] == 3
        assert result["count_max"] == 3

    def test_integer_count(self):
        result = parse_usage_entry(3)
        assert result["count_min"] == 3
        assert result["count_max"] == 3

    def test_probability_only(self):
        result = parse_usage_entry({"probability": 0.05})
        assert result["probability"] == 0.05
        assert result["count_min"] == 1
        assert result["count_max"] == 1

    def test_probability_with_count(self):
        result = parse_usage_entry({"probability": 0.3, "count": "1-2"})
        assert result["probability"] == 0.3
        assert result["count_min"] == 1
        assert result["count_max"] == 2

    def test_scheduled_event(self):
        result = parse_usage_entry({"cost": 300, "date": "2025-03-15", "description": "pre-op"})
        assert result["cost"] == 300.0
        assert result["date"] == "2025-03-15"
        assert result["description"] == "pre-op"
        assert result["scheduled"] is True

    def test_scheduled_with_count(self):
        result = parse_usage_entry({"count": 12, "cost": 800})
        assert result["count_min"] == 12
        assert result["count_max"] == 12
        assert result["cost"] == 800.0


class TestLoadConfig:
    def test_load_minimal_config(self):
        yaml_content = """
simulation:
  iterations: 1000

defaults:
  costs:
    primary_care_visit: 200

profiles:
  test_profile:
    primary_care_visit: 2-3

household:
  - name: alice
    profile: test_profile
"""
        config = load_config(StringIO(yaml_content))
        assert config["simulation"]["iterations"] == 1000
        assert config["defaults"]["costs"]["primary_care_visit"] == CostRange(200.0, 200.0)
        assert config["household"][0]["name"] == "alice"

    def test_load_auto_iterations(self):
        yaml_content = """
simulation:
  iterations: auto
  convergence_threshold_dollars: 100
  max_iterations: 50000
  min_iterations: 500

defaults:
  costs: {}

profiles: {}

household: []
"""
        config = load_config(StringIO(yaml_content))
        assert config["simulation"]["iterations"] == "auto"
        assert config["simulation"]["convergence_threshold_dollars"] == 100
        assert config["simulation"]["max_iterations"] == 50000
        assert config["simulation"]["min_iterations"] == 500

    def test_profile_with_list_entries(self):
        yaml_content = """
simulation:
  iterations: 1000

defaults:
  costs: {}

profiles:
  surgery_person:
    specialist_visit:
      - { cost: 300, date: "2025-03-15" }
      - { count: 2-4 }

household: []
"""
        config = load_config(StringIO(yaml_content))
        profile = config["profiles"]["surgery_person"]
        assert len(profile["specialist_visit"]) == 2
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_config_loader.py -v`
Expected: FAIL with import errors

**Step 3: Write minimal implementation**

`caca/config_loader.py`:
```python
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
        "defaults": {"costs": {}},
        "profiles": {},
        "household": raw.get("household", []),
    }

    # Process default costs
    if "defaults" in raw and "costs" in raw["defaults"]:
        for service, cost in raw["defaults"]["costs"].items():
            config["defaults"]["costs"][service] = parse_cost_range(cost)

    # Process profiles
    if "profiles" in raw:
        for profile_name, profile in raw["profiles"].items():
            if profile:
                config["profiles"][profile_name] = process_profile(profile)

    return config
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_config_loader.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add caca/config_loader.py tests/test_config_loader.py
git commit -m "feat: add YAML config loader"
```

---

## Task 7: Distribution Strategy

**Files:**
- Create: `caca/distribution.py`
- Create: `tests/test_distribution.py`

**Step 1: Write the failing test**

`tests/test_distribution.py`:
```python
# PURPOSE: Tests for event distribution strategies

import pytest
from datetime import date
import numpy as np
from caca.distribution import DistributionStrategy, UniformDistribution


class TestUniformDistribution:
    def test_generates_dates_in_year(self):
        dist = UniformDistribution(seed=42)
        year = 2025
        dates = dist.generate_dates(year, count=100)

        assert len(dates) == 100
        for d in dates:
            assert d.year == year
            assert date(year, 1, 1) <= d <= date(year, 12, 31)

    def test_deterministic_with_seed(self):
        dist1 = UniformDistribution(seed=42)
        dist2 = UniformDistribution(seed=42)

        dates1 = dist1.generate_dates(2025, count=10)
        dates2 = dist2.generate_dates(2025, count=10)

        assert dates1 == dates2

    def test_different_with_different_seed(self):
        dist1 = UniformDistribution(seed=42)
        dist2 = UniformDistribution(seed=123)

        dates1 = dist1.generate_dates(2025, count=10)
        dates2 = dist2.generate_dates(2025, count=10)

        assert dates1 != dates2

    def test_generates_sorted_dates(self):
        dist = UniformDistribution(seed=42)
        dates = dist.generate_dates(2025, count=50)

        assert dates == sorted(dates)

    def test_zero_count(self):
        dist = UniformDistribution(seed=42)
        dates = dist.generate_dates(2025, count=0)

        assert dates == []


class TestDistributionStrategyInterface:
    def test_is_abstract(self):
        # DistributionStrategy should not be instantiable directly
        with pytest.raises(TypeError):
            DistributionStrategy()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_distribution.py -v`
Expected: FAIL with import errors

**Step 3: Write minimal implementation**

`caca/distribution.py`:
```python
# PURPOSE: Distribution strategies for random event date generation

from abc import ABC, abstractmethod
from datetime import date, timedelta
import numpy as np


class DistributionStrategy(ABC):
    """Abstract base class for event date distribution strategies."""

    @abstractmethod
    def generate_dates(self, year: int, count: int) -> list[date]:
        """Generate a sorted list of dates within the given year."""
        pass


class UniformDistribution(DistributionStrategy):
    """Uniform random distribution of events across the year."""

    def __init__(self, seed: int | None = None):
        self.rng = np.random.default_rng(seed)

    def generate_dates(self, year: int, count: int) -> list[date]:
        """Generate uniformly distributed dates within the year."""
        if count == 0:
            return []

        start = date(year, 1, 1)
        end = date(year, 12, 31)
        days_in_year = (end - start).days + 1

        # Generate random day offsets
        day_offsets = self.rng.integers(0, days_in_year, size=count)

        # Convert to dates and sort
        dates = [start + timedelta(days=int(offset)) for offset in day_offsets]
        dates.sort()

        return dates
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_distribution.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add caca/distribution.py tests/test_distribution.py
git commit -m "feat: add distribution strategy with uniform implementation"
```

---

## Task 8: Event Generator

**Files:**
- Create: `caca/event_generator.py`
- Create: `tests/test_event_generator.py`

**Step 1: Write the failing test**

`tests/test_event_generator.py`:
```python
# PURPOSE: Tests for healthcare event generation

import pytest
from datetime import date
from caca.event_generator import EventGenerator
from caca.distribution import UniformDistribution
from caca.models import ServiceType, CostRange, Event


class TestEventGenerator:
    def make_generator(self, seed=42):
        return EventGenerator(
            distribution=UniformDistribution(seed=seed),
            default_costs={
                "primary_care_visit": CostRange(150, 300),
                "specialist_visit": CostRange(200, 500),
                "emergency_room": CostRange(1500, 5000),
            },
            year=2025,
            seed=seed,
        )

    def test_generate_simple_count(self):
        gen = self.make_generator()
        profile = {
            "primary_care_visit": [
                {"count_min": 3, "count_max": 3, "probability": 1.0, "scheduled": False}
            ]
        }

        events = gen.generate_events("alice", profile)

        pcp_events = [e for e in events if e.service_type == ServiceType.PRIMARY_CARE_VISIT]
        assert len(pcp_events) == 3
        for e in pcp_events:
            assert e.person == "alice"
            assert 150 <= e.cost <= 300
            assert e.date.year == 2025

    def test_generate_count_range(self):
        gen = self.make_generator()
        profile = {
            "primary_care_visit": [
                {"count_min": 2, "count_max": 5, "probability": 1.0, "scheduled": False}
            ]
        }

        # Run multiple times to verify range
        counts = []
        for seed in range(100):
            gen = self.make_generator(seed=seed)
            events = gen.generate_events("alice", profile)
            counts.append(len(events))

        assert min(counts) >= 2
        assert max(counts) <= 5
        assert len(set(counts)) > 1  # Should have variety

    def test_generate_with_probability(self):
        profile = {
            "emergency_room": [
                {"count_min": 1, "count_max": 1, "probability": 0.5, "scheduled": False}
            ]
        }

        # Run many times to verify probability
        counts = []
        for seed in range(200):
            gen = self.make_generator(seed=seed)
            events = gen.generate_events("alice", profile)
            counts.append(len(events))

        # With 50% probability over 200 trials, expect roughly 100
        # Allow wide margin for randomness
        assert 60 <= sum(counts) <= 140

    def test_generate_scheduled_event(self):
        gen = self.make_generator()
        profile = {
            "specialist_visit": [
                {
                    "scheduled": True,
                    "date": "2025-03-15",
                    "cost": 300,
                    "description": "pre-op consult",
                    "count_min": 1,
                    "count_max": 1,
                }
            ]
        }

        events = gen.generate_events("alice", profile)

        assert len(events) == 1
        event = events[0]
        assert event.service_type == ServiceType.SPECIALIST_VISIT
        assert event.date == date(2025, 3, 15)
        assert event.cost == 300
        assert event.description == "pre-op consult"

    def test_generate_mixed_scheduled_and_random(self):
        gen = self.make_generator()
        profile = {
            "specialist_visit": [
                {
                    "scheduled": True,
                    "date": "2025-03-15",
                    "cost": 300,
                    "description": "pre-op",
                    "count_min": 1,
                    "count_max": 1,
                },
                {"count_min": 2, "count_max": 2, "probability": 1.0, "scheduled": False},
            ]
        }

        events = gen.generate_events("alice", profile)

        assert len(events) == 3
        scheduled = [e for e in events if e.description == "pre-op"]
        assert len(scheduled) == 1
        assert scheduled[0].date == date(2025, 3, 15)

    def test_generate_uncovered(self):
        gen = self.make_generator()
        profile = {
            "uncovered": [
                {
                    "scheduled": True,
                    "date": "2025-06-15",
                    "cost": 1200,
                    "description": "dental crown",
                    "count_min": 1,
                    "count_max": 1,
                }
            ]
        }

        events = gen.generate_events("alice", profile)

        assert len(events) == 1
        assert events[0].service_type == ServiceType.UNCOVERED
        assert events[0].cost == 1200

    def test_events_sorted_by_date(self):
        gen = self.make_generator()
        profile = {
            "primary_care_visit": [
                {"count_min": 10, "count_max": 10, "probability": 1.0, "scheduled": False}
            ],
            "specialist_visit": [
                {
                    "scheduled": True,
                    "date": "2025-06-15",
                    "cost": 300,
                    "count_min": 1,
                    "count_max": 1,
                }
            ],
        }

        events = gen.generate_events("alice", profile)

        dates = [e.date for e in events]
        assert dates == sorted(dates)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_event_generator.py -v`
Expected: FAIL with import errors

**Step 3: Write minimal implementation**

`caca/event_generator.py`:
```python
# PURPOSE: Generate healthcare events from usage profiles

from datetime import date
import numpy as np
from caca.distribution import DistributionStrategy
from caca.models import Event, ServiceType, CostRange


# Map service names to ServiceType enum
SERVICE_NAME_MAP = {
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
    "uncovered": ServiceType.UNCOVERED,
}


class EventGenerator:
    """Generates healthcare events from usage profiles."""

    def __init__(
        self,
        distribution: DistributionStrategy,
        default_costs: dict[str, CostRange],
        year: int,
        seed: int | None = None,
    ):
        self.distribution = distribution
        self.default_costs = default_costs
        self.year = year
        self.rng = np.random.default_rng(seed)

    def generate_events(self, person_name: str, profile: dict) -> list[Event]:
        """Generate all events for a person based on their profile."""
        events: list[Event] = []

        for service_name, entries in profile.items():
            service_type = SERVICE_NAME_MAP.get(service_name)
            if service_type is None:
                continue

            for entry in entries:
                events.extend(
                    self._generate_entry_events(person_name, service_type, service_name, entry)
                )

        # Sort by date
        events.sort(key=lambda e: e.date)
        return events

    def _generate_entry_events(
        self,
        person_name: str,
        service_type: ServiceType,
        service_name: str,
        entry: dict,
    ) -> list[Event]:
        """Generate events for a single profile entry."""
        events: list[Event] = []

        # Check probability
        probability = entry.get("probability", 1.0)
        if self.rng.random() > probability:
            return events

        # Determine count
        count_min = entry.get("count_min", 1)
        count_max = entry.get("count_max", 1)
        count = self.rng.integers(count_min, count_max + 1)

        # Generate dates
        if entry.get("scheduled") and "date" in entry:
            # Scheduled event with specific date
            dates = [self._parse_date(entry["date"])] * count
        else:
            # Random dates
            dates = self.distribution.generate_dates(self.year, count)

        # Generate events
        for event_date in dates:
            cost = self._determine_cost(entry, service_name)
            events.append(
                Event(
                    service_type=service_type,
                    cost=cost,
                    date=event_date,
                    person=person_name,
                    description=entry.get("description"),
                )
            )

        return events

    def _determine_cost(self, entry: dict, service_name: str) -> float:
        """Determine the cost for an event."""
        # Explicit cost in entry
        if "cost" in entry and entry["cost"] is not None:
            return float(entry["cost"])

        # Use default cost range
        if service_name in self.default_costs:
            cost_range = self.default_costs[service_name]
            return self.rng.uniform(cost_range.min_cost, cost_range.max_cost)

        # No cost info available
        return 0.0

    def _parse_date(self, date_str: str) -> date:
        """Parse a date string in YYYY-MM-DD format."""
        parts = date_str.split("-")
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_event_generator.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add caca/event_generator.py tests/test_event_generator.py
git commit -m "feat: add event generator from usage profiles"
```

---

## Task 9: Plan Calculator

**Files:**
- Create: `caca/plan_calculator.py`
- Create: `tests/test_plan_calculator.py`

**Step 1: Write the failing test**

`tests/test_plan_calculator.py`:
```python
# PURPOSE: Tests for plan cost calculation

import pytest
from datetime import date
from caca.plan_calculator import PlanCalculator
from caca.models import Event, ServiceType, PlanRules, PlanResult


def make_plan(
    name="Test Plan",
    premium=12000,
    deductible_individual=2000,
    deductible_family=4000,
    oop_max_individual=5000,
    oop_max_family=10000,
    **kwargs,
) -> PlanRules:
    """Helper to create a plan with defaults."""
    return PlanRules(
        name=name,
        premium=premium,
        deductible_individual=deductible_individual,
        deductible_family=deductible_family,
        oop_max_individual=oop_max_individual,
        oop_max_family=oop_max_family,
        service_costs=kwargs.get("service_costs", {}),
        service_costs_after_deductible=kwargs.get("service_costs_after_deductible", {}),
        deductible_rx_individual=kwargs.get("deductible_rx_individual"),
        deductible_rx_family=kwargs.get("deductible_rx_family"),
        oop_max_rx_individual=kwargs.get("oop_max_rx_individual"),
        oop_max_rx_family=kwargs.get("oop_max_rx_family"),
        oop_max_per_rx=kwargs.get("oop_max_per_rx"),
        deductible_model=kwargs.get("deductible_model", "individual_first"),
    )


def make_event(
    service_type=ServiceType.PRIMARY_CARE_VISIT,
    cost=200,
    day=15,
    person="alice",
) -> Event:
    """Helper to create an event."""
    return Event(
        service_type=service_type,
        cost=cost,
        date=date(2025, 1, day),
        person=person,
    )


class TestPlanCalculatorBasics:
    def test_premium_only_no_events(self):
        plan = make_plan(premium=12000)
        calc = PlanCalculator(plan, ["alice"])

        result = calc.calculate([])

        assert result.premium == 12000
        assert result.out_of_pocket == 0
        assert result.total_cost == 12000

    def test_preventative_visit_free(self):
        plan = make_plan(
            service_costs={ServiceType.PREVENTATIVE_VISIT: 0},
            service_costs_after_deductible={ServiceType.PREVENTATIVE_VISIT: 0},
        )
        calc = PlanCalculator(plan, ["alice"])

        events = [make_event(service_type=ServiceType.PREVENTATIVE_VISIT, cost=500)]
        result = calc.calculate(events)

        assert result.out_of_pocket == 0

    def test_copay_before_deductible(self):
        plan = make_plan(
            service_costs={ServiceType.PRIMARY_CARE_VISIT: 50},  # $50 copay
            service_costs_after_deductible={ServiceType.PRIMARY_CARE_VISIT: 50},
        )
        calc = PlanCalculator(plan, ["alice"])

        events = [make_event(cost=200)]
        result = calc.calculate(events)

        # Should pay $50 copay regardless of deductible
        assert result.out_of_pocket == 50

    def test_full_cost_before_deductible(self):
        plan = make_plan(
            deductible_individual=2000,
            service_costs={ServiceType.PRIMARY_CARE_VISIT: 1.0},  # 100% before deductible
            service_costs_after_deductible={ServiceType.PRIMARY_CARE_VISIT: 0.2},
        )
        calc = PlanCalculator(plan, ["alice"])

        events = [make_event(cost=500)]
        result = calc.calculate(events)

        # Should pay full $500, haven't hit deductible
        assert result.out_of_pocket == 500

    def test_coinsurance_after_deductible(self):
        plan = make_plan(
            deductible_individual=500,
            service_costs={ServiceType.PRIMARY_CARE_VISIT: 1.0},
            service_costs_after_deductible={ServiceType.PRIMARY_CARE_VISIT: 0.2},
        )
        calc = PlanCalculator(plan, ["alice"])

        events = [
            make_event(cost=500, day=1),   # Hits deductible exactly
            make_event(cost=1000, day=2),  # 20% coinsurance = $200
        ]
        result = calc.calculate(events)

        assert result.out_of_pocket == 500 + 200
        assert result.deductible_hit_date == date(2025, 1, 1)

    def test_oop_max_caps_costs(self):
        plan = make_plan(
            deductible_individual=1000,
            oop_max_individual=2000,
            service_costs={ServiceType.INPATIENT_SERVICES: 1.0},
            service_costs_after_deductible={ServiceType.INPATIENT_SERVICES: 0.2},
        )
        calc = PlanCalculator(plan, ["alice"])

        # $1000 to deductible, then 20% of $50000 = $10000, but capped at OOP max
        events = [make_event(service_type=ServiceType.INPATIENT_SERVICES, cost=51000)]
        result = calc.calculate(events)

        assert result.out_of_pocket == 2000
        assert result.oop_max_hit_date == date(2025, 1, 15)


class TestFamilyDeductibles:
    def test_individual_deductible_tracked_separately(self):
        plan = make_plan(
            deductible_individual=1000,
            deductible_family=2000,
            service_costs={ServiceType.PRIMARY_CARE_VISIT: 1.0},
            service_costs_after_deductible={ServiceType.PRIMARY_CARE_VISIT: 0.2},
        )
        calc = PlanCalculator(plan, ["alice", "bob"])

        events = [
            make_event(cost=1000, person="alice", day=1),  # Alice hits individual deductible
            make_event(cost=500, person="alice", day=2),   # Alice pays 20% = $100
            make_event(cost=500, person="bob", day=3),     # Bob hasn't hit deductible, pays full
        ]
        result = calc.calculate(events)

        # Alice: $1000 + $100 = $1100
        # Bob: $500
        assert result.out_of_pocket == 1600

    def test_family_deductible_individual_first_model(self):
        plan = make_plan(
            deductible_individual=1000,
            deductible_family=1500,
            service_costs={ServiceType.INPATIENT_SERVICES: 1.0},
            service_costs_after_deductible={ServiceType.INPATIENT_SERVICES: 0.2},
            deductible_model="individual_first",
        )
        calc = PlanCalculator(plan, ["alice", "bob"])

        # Alice has catastrophic event, exceeds family deductible alone
        events = [
            make_event(service_type=ServiceType.INPATIENT_SERVICES, cost=5000, person="alice", day=1),
            make_event(cost=500, person="bob", day=2),  # Bob should pay 20% since family deductible met
        ]
        result = calc.calculate(events)

        # Alice: $1500 (family deductible) + 20% of $3500 = $1500 + $700 = $2200
        # Bob: 20% of $500 = $100 (family deductible already met)
        assert result.out_of_pocket == 2300


class TestUncoveredServices:
    def test_uncovered_bypasses_plan(self):
        plan = make_plan()
        calc = PlanCalculator(plan, ["alice"])

        events = [
            make_event(service_type=ServiceType.UNCOVERED, cost=1000),
        ]
        result = calc.calculate(events)

        # Uncovered goes straight to OOP, doesn't count toward deductible
        assert result.out_of_pocket == 1000


class TestRxDeductibles:
    def test_separate_rx_deductible(self):
        plan = make_plan(
            deductible_individual=2000,
            deductible_rx_individual=500,
            service_costs={
                ServiceType.PRIMARY_CARE_VISIT: 1.0,
                ServiceType.TIER_1_GENERIC_DRUGS: 1.0,
            },
            service_costs_after_deductible={
                ServiceType.PRIMARY_CARE_VISIT: 0.2,
                ServiceType.TIER_1_GENERIC_DRUGS: 20,  # $20 copay after Rx deductible
            },
        )
        calc = PlanCalculator(plan, ["alice"])

        events = [
            make_event(service_type=ServiceType.TIER_1_GENERIC_DRUGS, cost=100, day=1),  # Toward Rx deductible
            make_event(service_type=ServiceType.TIER_1_GENERIC_DRUGS, cost=100, day=2),  # Toward Rx deductible
            make_event(service_type=ServiceType.TIER_1_GENERIC_DRUGS, cost=100, day=3),  # Toward Rx deductible
            make_event(service_type=ServiceType.TIER_1_GENERIC_DRUGS, cost=100, day=4),  # Toward Rx deductible
            make_event(service_type=ServiceType.TIER_1_GENERIC_DRUGS, cost=100, day=5),  # Toward Rx deductible, hits $500
            make_event(service_type=ServiceType.TIER_1_GENERIC_DRUGS, cost=100, day=6),  # After Rx deductible, $20 copay
        ]
        result = calc.calculate(events)

        # First 5 drugs: $500 (Rx deductible)
        # 6th drug: $20 copay
        assert result.out_of_pocket == 520
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_plan_calculator.py -v`
Expected: FAIL with import errors

**Step 3: Write minimal implementation**

`caca/plan_calculator.py`:
```python
# PURPOSE: Calculate costs for healthcare events under a plan's rules

from datetime import date
from caca.models import Event, ServiceType, PlanRules, PlanResult


class PlanCalculator:
    """Calculates healthcare costs for a set of events under a plan."""

    def __init__(self, plan: PlanRules, household_members: list[str]):
        self.plan = plan
        self.household_members = household_members

    def calculate(self, events: list[Event]) -> PlanResult:
        """Calculate total costs for a list of events."""
        # Track deductible progress per person
        individual_deductible_spent: dict[str, float] = {m: 0.0 for m in self.household_members}
        individual_oop_spent: dict[str, float] = {m: 0.0 for m in self.household_members}

        # Track Rx deductible separately if applicable
        individual_rx_deductible_spent: dict[str, float] = {m: 0.0 for m in self.household_members}
        individual_rx_oop_spent: dict[str, float] = {m: 0.0 for m in self.household_members}

        family_deductible_spent = 0.0
        family_oop_spent = 0.0
        family_rx_deductible_spent = 0.0
        family_rx_oop_spent = 0.0

        total_oop = 0.0
        deductible_hit_date: date | None = None
        oop_max_hit_date: date | None = None

        for event in events:
            # Handle uncovered services
            if event.service_type == ServiceType.UNCOVERED:
                total_oop += event.cost
                continue

            # Determine if this is an Rx service with separate deductible
            is_rx = event.service_type.is_drug()
            has_separate_rx_deductible = (
                is_rx and self.plan.deductible_rx_individual is not None
            )

            # Get relevant deductibles and OOP maxes
            if has_separate_rx_deductible:
                ind_deductible = self.plan.deductible_rx_individual
                fam_deductible = self.plan.deductible_rx_family or (ind_deductible * 2)
                ind_oop_max = self.plan.oop_max_rx_individual or self.plan.oop_max_individual
                fam_oop_max = self.plan.oop_max_rx_family or self.plan.oop_max_family
                ind_ded_spent = individual_rx_deductible_spent
                ind_oop = individual_rx_oop_spent
                fam_ded_spent = family_rx_deductible_spent
                fam_oop = family_rx_oop_spent
            else:
                ind_deductible = self.plan.deductible_individual
                fam_deductible = self.plan.deductible_family
                ind_oop_max = self.plan.oop_max_individual
                fam_oop_max = self.plan.oop_max_family
                ind_ded_spent = individual_deductible_spent
                ind_oop = individual_oop_spent
                fam_ded_spent = family_deductible_spent
                fam_oop = family_oop_spent

            person = event.person

            # Check if deductible is met (individual or family)
            individual_deductible_met = ind_ded_spent[person] >= ind_deductible
            family_deductible_met = (
                fam_ded_spent >= fam_deductible if isinstance(fam_ded_spent, float)
                else sum(fam_ded_spent.values()) >= fam_deductible
            )
            deductible_met = individual_deductible_met or family_deductible_met

            # Check if OOP max is met
            individual_oop_met = ind_oop[person] >= ind_oop_max
            family_oop_met = (
                fam_oop >= fam_oop_max if isinstance(fam_oop, float)
                else sum(fam_oop.values()) >= fam_oop_max
            )
            oop_max_met = individual_oop_met or family_oop_met

            if oop_max_met:
                # No more costs for this person/family
                patient_cost = 0.0
            else:
                # Determine patient cost based on plan rules
                patient_cost = self._calculate_patient_cost(
                    event, deductible_met, ind_deductible, ind_ded_spent[person]
                )

                # Cap at remaining OOP max
                remaining_ind_oop = ind_oop_max - ind_oop[person]
                remaining_fam_oop = fam_oop_max - (
                    fam_oop if isinstance(fam_oop, float) else sum(fam_oop.values())
                )
                patient_cost = min(patient_cost, remaining_ind_oop, remaining_fam_oop)

            # Update tracking
            total_oop += patient_cost

            if has_separate_rx_deductible:
                if not deductible_met:
                    # Portion going to deductible
                    deductible_portion = min(
                        patient_cost,
                        ind_deductible - individual_rx_deductible_spent[person]
                    )
                    individual_rx_deductible_spent[person] += deductible_portion
                    family_rx_deductible_spent += deductible_portion
                individual_rx_oop_spent[person] += patient_cost
                family_rx_oop_spent += patient_cost
            else:
                if not deductible_met:
                    deductible_portion = min(
                        patient_cost,
                        ind_deductible - individual_deductible_spent[person]
                    )
                    individual_deductible_spent[person] += deductible_portion
                    family_deductible_spent += deductible_portion

                    # Check if we just hit deductible
                    new_ind_met = individual_deductible_spent[person] >= ind_deductible
                    new_fam_met = family_deductible_spent >= fam_deductible
                    if (new_ind_met or new_fam_met) and deductible_hit_date is None:
                        deductible_hit_date = event.date

                individual_oop_spent[person] += patient_cost
                family_oop_spent += patient_cost

                # Check if we just hit OOP max
                new_ind_oop_met = individual_oop_spent[person] >= ind_oop_max
                new_fam_oop_met = family_oop_spent >= fam_oop_max
                if (new_ind_oop_met or new_fam_oop_met) and oop_max_hit_date is None:
                    oop_max_hit_date = event.date

        return PlanResult(
            total_cost=self.plan.premium + total_oop,
            premium=self.plan.premium,
            out_of_pocket=total_oop,
            deductible_hit_date=deductible_hit_date,
            oop_max_hit_date=oop_max_hit_date,
        )

    def _calculate_patient_cost(
        self,
        event: Event,
        deductible_met: bool,
        individual_deductible: float,
        individual_deductible_spent: float,
    ) -> float:
        """Calculate what the patient pays for a single event."""
        service_type = event.service_type
        cost = event.cost

        if deductible_met:
            # Use after-deductible cost sharing
            cost_share = self.plan.service_costs_after_deductible.get(service_type)
        else:
            cost_share = self.plan.service_costs.get(service_type)

        if cost_share is None:
            # No rule defined, assume full cost before deductible, 0 after
            return 0.0 if deductible_met else cost

        # Interpret cost share
        if cost_share <= 1.0:
            # Coinsurance (fraction)
            patient_cost = cost * cost_share
        else:
            # Copay (fixed dollar amount)
            patient_cost = min(cost_share, cost)

        # If not yet at deductible and paying full cost, track deductible progress
        if not deductible_met and cost_share == 1.0:
            # Full cost counts toward deductible
            remaining_deductible = individual_deductible - individual_deductible_spent
            if cost <= remaining_deductible:
                return cost
            else:
                # Part to deductible, part with post-deductible cost sharing
                after_deductible_cost = cost - remaining_deductible
                after_share = self.plan.service_costs_after_deductible.get(service_type, 0.0)
                if after_share <= 1.0:
                    patient_cost = remaining_deductible + (after_deductible_cost * after_share)
                else:
                    patient_cost = remaining_deductible + min(after_share, after_deductible_cost)
                return patient_cost

        return patient_cost
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_plan_calculator.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add caca/plan_calculator.py tests/test_plan_calculator.py
git commit -m "feat: add plan calculator for cost computation"
```

---

## Task 10: Simulation Runner

**Files:**
- Create: `caca/simulation_runner.py`
- Create: `tests/test_simulation_runner.py`

**Step 1: Write the failing test**

`tests/test_simulation_runner.py`:
```python
# PURPOSE: Tests for simulation runner

import pytest
from caca.simulation_runner import SimulationRunner
from caca.models import PlanRules, ServiceType, CostRange, SimulationConfig
from caca.distribution import UniformDistribution


def make_simple_plan(name: str, premium: float, deductible: float) -> PlanRules:
    return PlanRules(
        name=name,
        premium=premium,
        deductible_individual=deductible,
        deductible_family=deductible * 2,
        oop_max_individual=deductible * 2,
        oop_max_family=deductible * 4,
        service_costs={ServiceType.PRIMARY_CARE_VISIT: 1.0},
        service_costs_after_deductible={ServiceType.PRIMARY_CARE_VISIT: 0.2},
    )


class TestSimulationRunner:
    def test_run_fixed_iterations(self):
        plans = [
            make_simple_plan("cheap", 1000, 500),
            make_simple_plan("expensive", 2000, 100),
        ]
        profiles = {
            "test": {
                "primary_care_visit": [
                    {"count_min": 2, "count_max": 5, "probability": 1.0, "scheduled": False}
                ]
            }
        }
        household = [{"name": "alice", "profile": "test"}]
        default_costs = {"primary_care_visit": CostRange(100, 200)}

        runner = SimulationRunner(
            plans=plans,
            profiles=profiles,
            household=household,
            default_costs=default_costs,
            year=2025,
            seed=42,
        )

        results = runner.run(iterations=100)

        assert results.iterations == 100
        assert len(results.scenarios) == 100
        assert "cheap" in results.summary
        assert "expensive" in results.summary

    def test_convergence_tracking(self):
        plans = [make_simple_plan("test", 1000, 500)]
        profiles = {
            "test": {
                "primary_care_visit": [
                    {"count_min": 1, "count_max": 1, "probability": 1.0, "scheduled": False}
                ]
            }
        }
        household = [{"name": "alice", "profile": "test"}]
        default_costs = {"primary_care_visit": CostRange(100, 100)}  # Fixed cost

        runner = SimulationRunner(
            plans=plans,
            profiles=profiles,
            household=household,
            default_costs=default_costs,
            year=2025,
            seed=42,
        )

        results = runner.run(iterations=50)

        # With fixed cost, should converge quickly
        summary = results.summary["test"]
        assert summary["ci_95_high"] - summary["ci_95_low"] < 100

    def test_auto_convergence(self):
        plans = [make_simple_plan("test", 1000, 500)]
        profiles = {
            "test": {
                "primary_care_visit": [
                    {"count_min": 1, "count_max": 3, "probability": 1.0, "scheduled": False}
                ]
            }
        }
        household = [{"name": "alice", "profile": "test"}]
        default_costs = {"primary_care_visit": CostRange(100, 200)}

        runner = SimulationRunner(
            plans=plans,
            profiles=profiles,
            household=household,
            default_costs=default_costs,
            year=2025,
            seed=42,
        )

        results = runner.run(
            iterations="auto",
            convergence_threshold_dollars=50,
            min_iterations=100,
            max_iterations=10000,
        )

        assert results.converged is True
        assert results.iterations >= 100
        assert results.iterations <= 10000

    def test_plan_ranking(self):
        plans = [
            make_simple_plan("expensive", 5000, 100),  # High premium, low deductible
            make_simple_plan("cheap", 1000, 500),      # Low premium, high deductible
        ]
        profiles = {
            "light_user": {
                "primary_care_visit": [
                    {"count_min": 1, "count_max": 2, "probability": 1.0, "scheduled": False}
                ]
            }
        }
        household = [{"name": "alice", "profile": "light_user"}]
        default_costs = {"primary_care_visit": CostRange(100, 150)}

        runner = SimulationRunner(
            plans=plans,
            profiles=profiles,
            household=household,
            default_costs=default_costs,
            year=2025,
            seed=42,
        )

        results = runner.run(iterations=500)

        # For light users, cheap plan should win
        ranked = results.get_ranked_plans()
        assert ranked[0][0] == "cheap"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_simulation_runner.py -v`
Expected: FAIL with import errors

**Step 3: Write minimal implementation**

`caca/simulation_runner.py`:
```python
# PURPOSE: Monte Carlo simulation runner with adaptive convergence

from dataclasses import dataclass, field
import numpy as np
from caca.models import PlanRules, CostRange, ScenarioResult, PlanResult, Event
from caca.distribution import UniformDistribution
from caca.event_generator import EventGenerator
from caca.plan_calculator import PlanCalculator


@dataclass
class SimulationResults:
    """Results from a simulation run."""

    iterations: int
    converged: bool
    scenarios: list[ScenarioResult]
    summary: dict[str, dict]  # plan_name -> stats

    def get_ranked_plans(self) -> list[tuple[str, float]]:
        """Return plans ranked by expected cost (lowest first)."""
        ranked = [
            (name, stats["expected_cost"])
            for name, stats in self.summary.items()
        ]
        ranked.sort(key=lambda x: x[1])
        return ranked


class SimulationRunner:
    """Runs Monte Carlo simulations across multiple plans."""

    def __init__(
        self,
        plans: list[PlanRules],
        profiles: dict,
        household: list[dict],
        default_costs: dict[str, CostRange],
        year: int,
        seed: int | None = None,
    ):
        self.plans = plans
        self.profiles = profiles
        self.household = household
        self.default_costs = default_costs
        self.year = year
        self.seed = seed
        self.rng = np.random.default_rng(seed)

    def run(
        self,
        iterations: int | str = 1000,
        convergence_threshold_dollars: float = 100,
        min_iterations: int = 1000,
        max_iterations: int = 100000,
    ) -> SimulationResults:
        """Run the simulation."""
        auto_converge = iterations == "auto"
        target_iterations = max_iterations if auto_converge else iterations

        scenarios: list[ScenarioResult] = []
        plan_costs: dict[str, list[float]] = {p.name: [] for p in self.plans}

        converged = False
        batch_size = 100

        household_members = [m["name"] for m in self.household]

        i = 0
        while i < target_iterations:
            # Run a batch
            batch_end = min(i + batch_size, target_iterations)
            for scenario_id in range(i, batch_end):
                # Generate events for this scenario
                scenario_seed = self.rng.integers(0, 2**31)
                events = self._generate_scenario_events(scenario_seed)

                # Calculate costs for each plan
                plan_results: dict[str, PlanResult] = {}
                for plan in self.plans:
                    calc = PlanCalculator(plan, household_members)
                    result = calc.calculate(events)
                    plan_results[plan.name] = result
                    plan_costs[plan.name].append(result.total_cost)

                scenarios.append(ScenarioResult(
                    scenario_id=scenario_id,
                    events=events,
                    plan_results=plan_results,
                ))

            i = batch_end

            # Check convergence if auto mode and past minimum
            if auto_converge and i >= min_iterations:
                if self._check_convergence(plan_costs, convergence_threshold_dollars):
                    converged = True
                    break

        # Build summary statistics
        summary = self._build_summary(plan_costs)

        return SimulationResults(
            iterations=len(scenarios),
            converged=converged or not auto_converge,
            scenarios=scenarios,
            summary=summary,
        )

    def _generate_scenario_events(self, seed: int) -> list[Event]:
        """Generate all events for one scenario."""
        all_events: list[Event] = []

        distribution = UniformDistribution(seed=seed)
        generator = EventGenerator(
            distribution=distribution,
            default_costs=self.default_costs,
            year=self.year,
            seed=seed,
        )

        for member in self.household:
            profile_name = member["profile"]
            profile = self.profiles.get(profile_name, {})
            events = generator.generate_events(member["name"], profile)
            all_events.extend(events)

        # Sort all events by date
        all_events.sort(key=lambda e: e.date)
        return all_events

    def _check_convergence(
        self,
        plan_costs: dict[str, list[float]],
        threshold: float,
    ) -> bool:
        """Check if all plans have converged."""
        for costs in plan_costs.values():
            if len(costs) < 100:
                return False

            arr = np.array(costs)
            sem = np.std(arr, ddof=1) / np.sqrt(len(arr))
            ci_width = 2 * 1.96 * sem  # 95% CI width

            if ci_width > threshold:
                return False

        return True

    def _build_summary(self, plan_costs: dict[str, list[float]]) -> dict[str, dict]:
        """Build summary statistics for each plan."""
        summary = {}

        for plan_name, costs in plan_costs.items():
            arr = np.array(costs)
            mean = float(np.mean(arr))
            std = float(np.std(arr, ddof=1))
            sem = std / np.sqrt(len(arr))

            summary[plan_name] = {
                "expected_cost": mean,
                "std_dev": std,
                "ci_95_low": mean - 1.96 * sem,
                "ci_95_high": mean + 1.96 * sem,
                "min": float(np.min(arr)),
                "max": float(np.max(arr)),
                "percentiles": {
                    "10": float(np.percentile(arr, 10)),
                    "25": float(np.percentile(arr, 25)),
                    "50": float(np.percentile(arr, 50)),
                    "75": float(np.percentile(arr, 75)),
                    "90": float(np.percentile(arr, 90)),
                },
            }

        return summary
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_simulation_runner.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add caca/simulation_runner.py tests/test_simulation_runner.py
git commit -m "feat: add simulation runner with adaptive convergence"
```

---

## Task 11: Results Data Structure

**Files:**
- Create: `caca/results.py`
- Create: `tests/test_results.py`

**Step 1: Write the failing test**

`tests/test_results.py`:
```python
# PURPOSE: Tests for results data structure

import pytest
from datetime import date
from caca.results import ResultsStore
from caca.models import ScenarioResult, PlanResult, Event, ServiceType


class TestResultsStore:
    def test_create_store(self):
        store = ResultsStore(
            iterations=100,
            converged=True,
            convergence_threshold_dollars=100,
            household=[{"name": "alice", "profile": "test"}],
            plan_names=["plan_a", "plan_b"],
        )
        assert store.iterations == 100
        assert store.converged is True

    def test_add_scenario(self):
        store = ResultsStore(
            iterations=0,
            converged=False,
            convergence_threshold_dollars=100,
            household=[],
            plan_names=["test"],
        )

        scenario = ScenarioResult(
            scenario_id=0,
            events=[],
            plan_results={"test": PlanResult(
                total_cost=1000,
                premium=800,
                out_of_pocket=200,
                deductible_hit_date=None,
                oop_max_hit_date=None,
            )},
        )

        store.add_scenario(scenario)

        assert len(store.scenarios) == 1
        assert store.get_plan_costs("test") == [1000]

    def test_to_json(self):
        store = ResultsStore(
            iterations=1,
            converged=True,
            convergence_threshold_dollars=100,
            household=[{"name": "alice", "profile": "test"}],
            plan_names=["test_plan"],
        )

        store.add_scenario(ScenarioResult(
            scenario_id=0,
            events=[Event(
                service_type=ServiceType.PRIMARY_CARE_VISIT,
                cost=200,
                date=date(2025, 3, 15),
                person="alice",
                description="checkup",
            )],
            plan_results={"test_plan": PlanResult(
                total_cost=1200,
                premium=1000,
                out_of_pocket=200,
                deductible_hit_date=None,
                oop_max_hit_date=None,
            )},
        ))

        json_data = store.to_json()

        assert json_data["metadata"]["iterations"] == 1
        assert json_data["metadata"]["converged"] is True
        assert len(json_data["scenarios"]) == 1
        assert json_data["scenarios"][0]["events"][0]["service_type"] == "primary_care_visit"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_results.py -v`
Expected: FAIL with import errors

**Step 3: Write minimal implementation**

`caca/results.py`:
```python
# PURPOSE: Results storage and serialization

from dataclasses import dataclass, field
from datetime import datetime
from caca.models import ScenarioResult, Event


@dataclass
class ResultsStore:
    """Stores simulation results with serialization support."""

    iterations: int
    converged: bool
    convergence_threshold_dollars: float
    household: list[dict]
    plan_names: list[str]
    scenarios: list[ScenarioResult] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def add_scenario(self, scenario: ScenarioResult) -> None:
        """Add a scenario result."""
        self.scenarios.append(scenario)

    def get_plan_costs(self, plan_name: str) -> list[float]:
        """Get all costs for a specific plan."""
        return [
            s.plan_results[plan_name].total_cost
            for s in self.scenarios
            if plan_name in s.plan_results
        ]

    def to_json(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "metadata": {
                "iterations": self.iterations,
                "converged": self.converged,
                "convergence_threshold_dollars": self.convergence_threshold_dollars,
                "timestamp": self.timestamp.isoformat(),
            },
            "household": self.household,
            "plans": self.plan_names,
            "scenarios": [
                self._scenario_to_json(s) for s in self.scenarios
            ],
        }

    def _scenario_to_json(self, scenario: ScenarioResult) -> dict:
        """Convert a scenario to JSON."""
        return {
            "id": scenario.scenario_id,
            "events": [self._event_to_json(e) for e in scenario.events],
            "results_by_plan": {
                name: {
                    "total_cost": result.total_cost,
                    "premium": result.premium,
                    "out_of_pocket": result.out_of_pocket,
                    "deductible_hit_date": (
                        result.deductible_hit_date.isoformat()
                        if result.deductible_hit_date else None
                    ),
                    "oop_max_hit_date": (
                        result.oop_max_hit_date.isoformat()
                        if result.oop_max_hit_date else None
                    ),
                }
                for name, result in scenario.plan_results.items()
            },
        }

    def _event_to_json(self, event: Event) -> dict:
        """Convert an event to JSON."""
        return {
            "service_type": event.service_type.value,
            "cost": event.cost,
            "date": event.date.isoformat(),
            "person": event.person,
            "description": event.description,
        }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_results.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add caca/results.py tests/test_results.py
git commit -m "feat: add results store with JSON serialization"
```

---

## Task 12: Terminal Output Renderer

**Files:**
- Create: `caca/output/__init__.py`
- Create: `caca/output/terminal.py`
- Create: `tests/test_output_terminal.py`

**Step 1: Write the failing test**

`tests/test_output_terminal.py`:
```python
# PURPOSE: Tests for terminal output rendering

import pytest
from io import StringIO
from caca.output.terminal import TerminalRenderer


class TestTerminalRenderer:
    def test_render_header(self):
        renderer = TerminalRenderer()
        output = StringIO()

        renderer.render_header(
            output,
            household=[
                {"name": "alice", "profile": "healthy"},
                {"name": "bob", "profile": "chronic"},
            ],
            iterations=5000,
            converged=True,
            convergence_threshold=87,
        )

        result = output.getvalue()
        assert "Care Casino" in result
        assert "alice (healthy)" in result
        assert "bob (chronic)" in result
        assert "5,000" in result
        assert "converged" in result.lower()

    def test_render_rankings(self):
        renderer = TerminalRenderer()
        output = StringIO()

        summary = {
            "Plan A": {
                "expected_cost": 10000,
                "ci_95_low": 9500,
                "ci_95_high": 10500,
                "min": 8000,
                "max": 15000,
            },
            "Plan B": {
                "expected_cost": 12000,
                "ci_95_low": 11000,
                "ci_95_high": 13000,
                "min": 9000,
                "max": 18000,
            },
        }

        renderer.render_rankings(output, summary)

        result = output.getvalue()
        assert "Plan A" in result
        assert "Plan B" in result
        assert "$10,000" in result
        assert "1" in result  # Rank 1

    def test_render_histogram(self):
        renderer = TerminalRenderer()
        output = StringIO()

        costs = [10000, 10500, 11000, 10200, 10800] * 20

        renderer.render_histogram(output, "Test Plan", costs)

        result = output.getvalue()
        assert "Test Plan" in result
        # Should have some histogram characters
        assert any(c in result for c in "█▓▒░#")

    def test_format_currency(self):
        renderer = TerminalRenderer()
        assert renderer.format_currency(1234.56) == "$1,235"
        assert renderer.format_currency(1000000) == "$1,000,000"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_output_terminal.py -v`
Expected: FAIL with import errors

**Step 3: Write minimal implementation**

`caca/output/__init__.py`:
```python
# PURPOSE: Output rendering package
```

`caca/output/terminal.py`:
```python
# PURPOSE: Terminal output rendering with ASCII tables and histograms

from typing import TextIO
import sys


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
                    output.write("█")
                elif height > 0.5:
                    output.write("▓")
                elif height > 0.25:
                    output.write("▒")
                elif height > 0:
                    output.write("░")
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_output_terminal.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add caca/output/__init__.py caca/output/terminal.py tests/test_output_terminal.py
git commit -m "feat: add terminal output renderer"
```

---

## Task 13: JSON Export

**Files:**
- Create: `caca/output/json_export.py`
- Create: `tests/test_output_json.py`

**Step 1: Write the failing test**

`tests/test_output_json.py`:
```python
# PURPOSE: Tests for JSON export

import pytest
import json
from io import StringIO
from caca.output.json_export import JsonExporter
from caca.results import ResultsStore
from caca.models import ScenarioResult, PlanResult


class TestJsonExporter:
    def test_export_to_file(self):
        store = ResultsStore(
            iterations=10,
            converged=True,
            convergence_threshold_dollars=100,
            household=[{"name": "alice", "profile": "test"}],
            plan_names=["test_plan"],
        )

        for i in range(10):
            store.add_scenario(ScenarioResult(
                scenario_id=i,
                events=[],
                plan_results={"test_plan": PlanResult(
                    total_cost=1000 + i * 10,
                    premium=800,
                    out_of_pocket=200 + i * 10,
                    deductible_hit_date=None,
                    oop_max_hit_date=None,
                )},
            ))

        summary = {
            "test_plan": {
                "expected_cost": 1045,
                "ci_95_low": 1000,
                "ci_95_high": 1090,
                "min": 1000,
                "max": 1090,
                "percentiles": {"50": 1045},
            }
        }

        exporter = JsonExporter()
        output = StringIO()

        exporter.export(output, store, summary)

        result = json.loads(output.getvalue())
        assert result["metadata"]["iterations"] == 10
        assert result["summary"]["test_plan"]["expected_cost"] == 1045
        assert len(result["scenarios"]) == 10

    def test_export_minimal(self):
        store = ResultsStore(
            iterations=1,
            converged=False,
            convergence_threshold_dollars=100,
            household=[],
            plan_names=["a"],
        )

        exporter = JsonExporter()
        output = StringIO()

        exporter.export(output, store, {"a": {"expected_cost": 100}})

        result = json.loads(output.getvalue())
        assert "metadata" in result
        assert "summary" in result
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_output_json.py -v`
Expected: FAIL with import errors

**Step 3: Write minimal implementation**

`caca/output/json_export.py`:
```python
# PURPOSE: JSON export for simulation results

import json
from typing import TextIO
from caca.results import ResultsStore


class JsonExporter:
    """Exports simulation results to JSON."""

    def export(
        self,
        output: TextIO,
        store: ResultsStore,
        summary: dict[str, dict],
    ) -> None:
        """Export results to JSON."""
        data = store.to_json()
        data["summary"] = summary

        json.dump(data, output, indent=2)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_output_json.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add caca/output/json_export.py tests/test_output_json.py
git commit -m "feat: add JSON exporter"
```

---

## Task 14: CLI Entry Point

**Files:**
- Create: `caca/cli.py`
- Create: `tests/test_cli.py`

**Step 1: Write the failing test**

`tests/test_cli.py`:
```python
# PURPOSE: Tests for CLI entry point

import pytest
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch
from caca.cli import main, parse_args


class TestParseArgs:
    def test_minimal_args(self):
        args = parse_args(["config.yaml"])
        assert args.config == "config.yaml"
        assert args.plans == "plans.csv"
        assert args.json is None
        assert args.quiet is False

    def test_all_args(self):
        args = parse_args([
            "my_config.yaml",
            "--plans", "my_plans.csv",
            "--json", "output.json",
            "--quiet",
        ])
        assert args.config == "my_config.yaml"
        assert args.plans == "my_plans.csv"
        assert args.json == "output.json"
        assert args.quiet is True


class TestCLI:
    def test_missing_config_file(self, tmp_path):
        with pytest.raises(SystemExit):
            with patch.object(sys, "argv", ["caca", "nonexistent.yaml"]):
                main()

    def test_run_simulation(self, tmp_path):
        # Create minimal config
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
simulation:
  iterations: 10

defaults:
  costs:
    primary_care_visit: 200

profiles:
  test:
    primary_care_visit: 1

household:
  - name: alice
    profile: test
""")

        # Create minimal plans CSV
        plans_file = tmp_path / "plans.csv"
        plans_file.write_text("""plan_name,test_plan
premium,1000
deductible_individual,500
deductible_family,1000
oop_max_individual,2000
oop_max_family,4000
primary_care_visit,50
primary_care_visit_after_deductible,20
""")

        output = StringIO()
        with patch.object(sys, "stdout", output):
            with patch.object(sys, "argv", [
                "caca",
                str(config_file),
                "--plans", str(plans_file),
            ]):
                main()

        result = output.getvalue()
        assert "Care Casino" in result
        assert "test_plan" in result
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL with import errors

**Step 3: Write minimal implementation**

`caca/cli.py`:
```python
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
        renderer = TerminalRenderer()
        renderer.render_full_report(
            sys.stdout,
            config["household"],
            results.iterations,
            results.converged,
            convergence_threshold,
            results.summary,
            plan_costs,
        )

    # JSON output
    if args.json:
        exporter = JsonExporter()
        with open(args.json, "w") as f:
            exporter.export(f, store, results.summary)
        if not args.quiet:
            print(f"\nResults written to {args.json}")


if __name__ == "__main__":
    main()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add caca/cli.py tests/test_cli.py
git commit -m "feat: add CLI entry point"
```

---

## Task 15: Integration Test with Real Files

**Files:**
- Create: `tests/test_integration.py`

**Step 1: Write the integration test**

`tests/test_integration.py`:
```python
# PURPOSE: Integration tests using real plans.csv and config

import pytest
from pathlib import Path
from io import StringIO
from caca.cli import main
from unittest.mock import patch
import sys


@pytest.fixture
def project_root():
    """Get project root directory."""
    return Path(__file__).parent.parent


class TestIntegration:
    def test_full_simulation_with_template(self, project_root, tmp_path):
        """Test running simulation with template config."""
        # Create a test config based on template
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("""
simulation:
  iterations: 100

defaults:
  costs:
    preventative_visit: 0
    primary_care_visit: 150-300
    specialist_visit: 200-500
    labs: 100-500
    imaging: 500-2500
    emergency_room: 1500-5000
    urgent_care: 150-400
    inpatient_services: 15000-75000
    outpatient_services: 2000-15000
    tier_1_generic_drugs: 10-50
    tier_2_preferred_brand_drugs: 50-200
    tier_3_non_preferred_brand_drugs: 150-500
    tier_4_specialty_drugs: 500-2000

profiles:
  healthy_adult:
    preventative_visit: 1
    primary_care_visit: 2-4
    specialist_visit: 0-2
    labs: 1-3
    emergency_room: { probability: 0.05 }
    tier_1_generic_drugs: 0-6

  child:
    preventative_visit: 2
    primary_care_visit: 4-6
    specialist_visit: 1-2
    urgent_care: { probability: 0.3, count: 1-2 }

household:
  - name: alice
    profile: healthy_adult
  - name: bob
    profile: healthy_adult
  - name: charlie
    profile: child
""")

        plans_file = project_root / "plans.csv"
        json_output = tmp_path / "results.json"

        output = StringIO()
        with patch.object(sys, "stdout", output):
            with patch.object(sys, "argv", [
                "caca",
                str(config_file),
                "--plans", str(plans_file),
                "--json", str(json_output),
            ]):
                main()

        result = output.getvalue()

        # Verify terminal output
        assert "Care Casino" in result
        assert "alice (healthy_adult)" in result
        assert "100" in result  # iterations

        # Verify JSON was created
        assert json_output.exists()

        # Verify all plans are in output
        assert "BS Bronze 60 HDHP PPO" in result or "bs_bronze_60_hdhp_ppo" in result.lower()

    def test_planned_surgery_scenario(self, project_root, tmp_path):
        """Test with planned surgery for one family member."""
        config_file = tmp_path / "surgery_config.yaml"
        config_file.write_text("""
simulation:
  iterations: 100

defaults:
  costs:
    primary_care_visit: 200
    specialist_visit: 350
    labs: 250
    imaging: 1500
    inpatient_services: 50000

profiles:
  healthy_adult:
    primary_care_visit: 2
    preventative_visit: 1

  surgery_patient:
    primary_care_visit: 4
    specialist_visit:
      - { cost: 350, date: "2025-03-01", description: "pre-op consult" }
      - { cost: 350, date: "2025-05-01", description: "post-op follow-up" }
    labs:
      - { cost: 250, date: "2025-03-01", description: "pre-op bloodwork" }
    imaging:
      - { cost: 1500, date: "2025-03-01", description: "MRI" }
    inpatient_services:
      - { cost: 50000, date: "2025-04-01", description: "knee replacement" }

household:
  - name: patient
    profile: surgery_patient
  - name: spouse
    profile: healthy_adult
""")

        plans_file = project_root / "plans.csv"

        output = StringIO()
        with patch.object(sys, "stdout", output):
            with patch.object(sys, "argv", [
                "caca",
                str(config_file),
                "--plans", str(plans_file),
            ]):
                main()

        result = output.getvalue()

        # With a $50k surgery, costs should be substantial
        assert "Care Casino" in result
        # Should see plan rankings
        assert "Rank" in result
```

**Step 2: Run test to verify it passes**

Run: `pytest tests/test_integration.py -v`
Expected: Tests PASS (may need plans.csv to be normalized first)

**Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "feat: add integration tests"
```

---

## Task 16: Final Verification and Documentation

**Step 1: Run all tests**

Run: `pytest -v --cov=caca`
Expected: All tests PASS with good coverage

**Step 2: Test CLI manually**

Run:
```bash
cp config.template.yaml config.yaml
# Edit config.yaml to set up your household
caca config.yaml --json results.json
```

**Step 3: Commit any final fixes**

```bash
git add -A
git commit -m "chore: final verification and cleanup"
```

---

## Summary

This plan implements Care Casino in 16 tasks:

1. Project setup (pyproject.toml, package structure)
2. Normalize plans.csv to snake_case
3. Create config template
4. Data models
5. Plan loader (CSV parsing)
6. Config loader (YAML parsing)
7. Distribution strategy (uniform dates)
8. Event generator (profiles to events)
9. Plan calculator (apply plan rules)
10. Simulation runner (Monte Carlo loop)
11. Results store (data structure)
12. Terminal renderer (ASCII output)
13. JSON exporter
14. CLI entry point
15. Integration tests
16. Final verification

Each task follows TDD: write failing test, implement, verify, commit.
