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
