# PURPOSE: Load healthcare plan definitions from CSV

import csv
from typing import TextIO, Any
from caca.models import PlanRules, ServiceType


# Rows that contain string values, not numbers
STRING_ROWS = {"plan_name", "plan_url", "deductible_model"}


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
            if row_name in STRING_ROWS:
                # Keep string values as-is
                plan_data[i][row_name] = value.strip() if value.strip() else None
            else:
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
