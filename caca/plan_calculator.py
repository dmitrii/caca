# PURPOSE: Calculate costs for healthcare events under a plan's rules

from datetime import date
from caca.models import Event, EventCost, ServiceType, PlanRules, PlanResult, CostShare


class PlanCalculator:
    """Calculates healthcare costs for a set of events under a plan."""

    def __init__(self, plan: PlanRules, household_members: list[str], gross: bool = False):
        self.plan = plan
        self.household_members = household_members
        self.gross = gross

    def calculate(self, events: list[Event]) -> PlanResult:
        """Calculate total costs for a list of events."""
        # Track deductible and OOP progress per person for medical
        med_deductible_spent: dict[str, float] = {m: 0.0 for m in self.household_members}
        med_oop_spent: dict[str, float] = {m: 0.0 for m in self.household_members}

        # Track Rx deductible and OOP separately if applicable
        rx_deductible_spent: dict[str, float] = {m: 0.0 for m in self.household_members}
        rx_oop_spent: dict[str, float] = {m: 0.0 for m in self.household_members}

        total_oop = 0.0
        deductible_hit_date: date | None = None
        oop_max_hit_date: date | None = None
        event_costs: list[EventCost] = []

        for event in events:
            # Handle uncovered services - bypass all plan rules
            if event.service_type == ServiceType.UNCOVERED:
                total_oop += event.cost
                event_costs.append(EventCost(
                    event=event,
                    provider_cost=event.cost,
                    patient_cost=event.cost,
                    plan_cost=0.0,
                    deductible_applied=0.0,
                ))
                continue

            person = event.person

            # Determine if this is an Rx service with separate deductible
            is_rx = event.service_type.is_drug()
            has_separate_rx_deductible = (
                is_rx and self.plan.deductible_rx_individual is not None
            )

            # Select appropriate tracking dicts and limits
            if has_separate_rx_deductible:
                deductible_spent = rx_deductible_spent
                oop_spent = rx_oop_spent
                ind_deductible = self.plan.deductible_rx_individual
                fam_deductible = self.plan.deductible_rx_family or (ind_deductible * 2)
                ind_oop_max = self.plan.oop_max_rx_individual or self.plan.oop_max_individual
                fam_oop_max = self.plan.oop_max_rx_family or self.plan.oop_max_family
            else:
                deductible_spent = med_deductible_spent
                oop_spent = med_oop_spent
                ind_deductible = self.plan.deductible_individual
                fam_deductible = self.plan.deductible_family
                ind_oop_max = self.plan.oop_max_individual
                fam_oop_max = self.plan.oop_max_family

            # Calculate family totals
            family_deductible_total = sum(deductible_spent.values())
            family_oop_total = sum(oop_spent.values())

            # Check if deductible is already met
            individual_deductible_met = deductible_spent[person] >= ind_deductible
            family_deductible_met = family_deductible_total >= fam_deductible
            deductible_met = individual_deductible_met or family_deductible_met

            # Check if OOP max is already met
            individual_oop_met = oop_spent[person] >= ind_oop_max
            family_oop_met = family_oop_total >= fam_oop_max
            oop_max_met = individual_oop_met or family_oop_met

            if oop_max_met:
                # No more costs - plan pays everything
                patient_cost = 0.0
                deductible_contribution = 0.0
            else:
                # Calculate patient cost for this event
                patient_cost = self._calculate_event_cost(
                    event=event,
                    deductible_met=deductible_met,
                    ind_deductible=ind_deductible,
                    deductible_spent_person=deductible_spent[person],
                )

                # Cap at remaining OOP max (individual and family)
                remaining_ind_oop = ind_oop_max - oop_spent[person]
                remaining_fam_oop = fam_oop_max - family_oop_total
                patient_cost = min(patient_cost, remaining_ind_oop, remaining_fam_oop)

                # Calculate deductible contribution for this event
                if not deductible_met:
                    deductible_contribution = min(
                        patient_cost,
                        ind_deductible - deductible_spent[person],
                    )
                else:
                    deductible_contribution = 0.0

            # Build EventCost record
            event_costs.append(EventCost(
                event=event,
                provider_cost=event.cost,
                patient_cost=patient_cost,
                plan_cost=event.cost - patient_cost,
                deductible_applied=deductible_contribution,
            ))

            # Update tracking
            total_oop += patient_cost
            oop_spent[person] += patient_cost

            # Update deductible tracking (only count toward deductible if not yet met)
            if not deductible_met and deductible_contribution > 0:
                deductible_spent[person] += deductible_contribution

                # Check if we just hit deductible
                new_family_total = sum(deductible_spent.values())
                new_ind_met = deductible_spent[person] >= ind_deductible
                new_fam_met = new_family_total >= fam_deductible
                if (new_ind_met or new_fam_met) and deductible_hit_date is None:
                    deductible_hit_date = event.date

            # Check if we just hit OOP max
            new_family_oop = sum(oop_spent.values())
            new_ind_oop_met = oop_spent[person] >= ind_oop_max
            new_fam_oop_met = new_family_oop >= fam_oop_max
            if (new_ind_oop_met or new_fam_oop_met) and oop_max_hit_date is None:
                oop_max_hit_date = event.date

        effective_premium = self.plan.effective_premium(self.gross)
        return PlanResult(
            total_cost=effective_premium + total_oop,
            premium=effective_premium,
            out_of_pocket=total_oop,
            deductible_hit_date=deductible_hit_date,
            oop_max_hit_date=oop_max_hit_date,
            event_costs=event_costs,
        )

    def _calculate_event_cost(
        self,
        event: Event,
        deductible_met: bool,
        ind_deductible: float,
        deductible_spent_person: float,
    ) -> float:
        """Calculate what the patient pays for a single event."""
        service_type = event.service_type
        cost = event.cost

        # Get cost sharing rule
        if deductible_met:
            cost_share = self.plan.service_costs_after_deductible.get(service_type)
        else:
            cost_share = self.plan.service_costs.get(service_type)

        if cost_share is None:
            # No rule defined - assume full cost before deductible, 0 after
            return 0.0 if deductible_met else cost

        # Combined copay + coinsurance
        if isinstance(cost_share, CostShare):
            return cost_share.patient_cost(cost)

        # Interpret cost share value
        if cost_share <= 1.0:
            # Coinsurance (0.0 = 0%, 1.0 = 100%)
            if cost_share == 1.0 and not deductible_met:
                # Full cost goes toward deductible
                remaining_deductible = ind_deductible - deductible_spent_person
                if cost <= remaining_deductible:
                    return cost
                else:
                    # Part goes to deductible, rest uses post-deductible cost sharing
                    after_deductible_portion = cost - remaining_deductible
                    after_share = self.plan.service_costs_after_deductible.get(service_type, 0.0)
                    if after_share <= 1.0:
                        return remaining_deductible + (after_deductible_portion * after_share)
                    else:
                        return remaining_deductible + min(after_share, after_deductible_portion)
            return cost * cost_share
        else:
            # Copay (fixed dollar amount)
            return min(cost_share, cost)
