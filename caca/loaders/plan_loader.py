# PURPOSE: Load healthcare plan definitions from YAML files

import yaml
from typing import TextIO
from caca.models import PlanRules, ServiceType, CostShare


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


def parse_cost_value(value) -> float | CostShare | None:
    """Parse a cost value, handling percentages and combined copay + coinsurance."""
    if value is None:
        return None
    if isinstance(value, dict):
        return CostShare(
            copay=parse_cost_value(value.get("copay")) or 0.0,
            coinsurance=parse_cost_value(value.get("coinsurance")) or 0.0,
        )
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
