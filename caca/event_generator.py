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
