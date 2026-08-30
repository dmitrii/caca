# Care Casino (`caca`)

A Monte Carlo simulator for comparing the **total annual cost of health insurance
plans** for a given household. You describe each plan's cost-sharing rules, each
person's expected healthcare usage, and a table of typical service costs; `caca`
simulates many possible years and reports the expected annual cost (premium +
out-of-pocket) of every plan, ranked, with the spread across scenarios.

> **Disclaimer.** This is an educational modeling tool, not financial or medical
> advice. Plan data and cost assumptions are illustrative and may be inaccurate
> or out of date. Always verify against official plan documents before making
> decisions.

## How it works

Four kinds of input feed one simulation:

| Input | Directory | What it is |
|-------|-----------|------------|
| **Plans** | `plans/` | A plan's premium, deductibles, out-of-pocket maxes, and per-service cost-sharing. |
| **Profiles** | `profiles/` | A person's expected yearly healthcare usage (visits, drugs, procedures). |
| **Costs** | `costs/` | Typical *billed* prices per service (ranges), used when a profile doesn't pin a cost. |
| **Simulation** | `parameters/` | Iteration count / convergence settings. |

A **run configuration** (`examples/*.yaml`) ties these together: it lists the
plans to compare and the people in the household. Each simulated year draws
random usage and costs, runs every person's events through every plan's rules,
and totals premium + out-of-pocket. Thousands of years give an expected cost and
a distribution per plan.

## Requirements

- Python **3.11+**
- `make` (optional, for convenience targets)

Dependencies (`pyyaml`, `numpy`, plus `fastapi`/`uvicorn`/`jinja2` reserved for a
planned web UI) install automatically in the steps below.

## Quick start

After cloning:

```bash
make deps        # creates a .venv and installs caca in it
```

(or manually: `python -m venv .venv && .venv/bin/pip install -e ".[dev]"`)

**Run for a single person:**

```bash
.venv/bin/caca generate examples/basic-run.yaml
```

**Run for a family:**

```bash
.venv/bin/caca generate examples/calzones-full.yaml
```

You'll get a ranked table of plans by expected annual cost, 95% confidence
intervals, best/worst-case years, and an ASCII cost distribution per plan.

Useful flags:

- `--gross` — price every plan at its full premium, ignoring subsidies (see
  [Subsidies](#subsidies)).
- `--breakdown out.txt` — write a per-service cost breakdown for each plan.
- `--json out.json` — write full results as JSON.

Validate all data files without running a simulation:

```bash
make validate    # or: .venv/bin/caca validate plans/ profiles/ costs/ examples/
```

## Repository layout

```
caca/         simulator source
plans/2026/   plan definitions (one YAML per plan)
profiles/     usage profiles (one YAML per person-scenario)
costs/        billed-cost tables
parameters/   simulation settings
examples/     runnable run-configurations
docs/         design notes and reference plan documents
tests/        test suite
```

## Making changes

### Adding or editing a plan

Each file in `plans/2026/` is one plan. Money fields are **monthly** where noted;
cost-sharing fields accept three forms:

- a number **≤ 1.0** → **coinsurance** (a fraction, e.g. `0.2` = 20%)
- a number **> 1.0** → a flat **copay** in dollars (e.g. `45`)
- a mapping `{ copay: N, coinsurance: M }` → **both** (you pay the copay plus
  coinsurance on the remainder, capped at the billed amount)

You may also write `"30%"` for coinsurance or `"$45"` for a copay. Every service
has a base value and an `_after_deductible` value (they're often equal for
copay-based plans).

```yaml
plan_name: Example Silver PPO
premium: 500                 # monthly; annualized as x12
subsidy: 0                   # optional monthly premium help (employer/APTC); default 0

deductible_individual: 2000
deductible_family: 4000
oop_max_individual: 8000
oop_max_family: 16000
# optional: deductible_rx_individual/family, oop_max_rx_individual/family,
#           oop_max_per_rx, deductible_model

preventative_visit: 0
primary_care_visit: 30
specialist_visit: 60
labs: 0.2                              # 20% coinsurance
imaging: 250
outpatient_services: 0.3
outpatient_rehabilitation_services: 40
inpatient_services: 0.3
emergency_room: { copay: 250, coinsurance: 0.10 }
urgent_care: 40
tier_1_generic_drugs: 15
tier_2_preferred_brand_drugs: 50
tier_3_non_preferred_brand_drugs: 90
tier_4_specialty_drugs: 0.2

# ...and each of the above again with an `_after_deductible` suffix.
```

The 14 recognized services are: `preventative_visit`, `primary_care_visit`,
`specialist_visit`, `labs`, `imaging`, `outpatient_services`,
`outpatient_rehabilitation_services`, `inpatient_services`, `emergency_room`,
`urgent_care`, and drug tiers 1–4 (`tier_1_generic_drugs` …
`tier_4_specialty_drugs`).

### Adding or editing a profile (a person's assumptions)

Each file in `profiles/` describes **one person's expected usage for a year**. A
profile has a `name` and one entry per service. Each entry is a *number of
occurrences*, and the model draws a cost for each occurrence from the cost table
(`costs/`) unless you pin one.

```yaml
name: example_person

# A count (fixed) or a range "min-max" — how many times per year:
primary_care_visit: 2-3
preventative_visit: 1

# A probabilistic event (happens with the given chance):
emergency_room: { probability: 0.05 }
urgent_care: { probability: 0.1, count: 1-2 }

# Fixed count with an explicit per-occurrence cost and a label:
specialist_visit:
  - { count: 2, cost: 350, description: "specialist visits" }

# A scheduled event on a specific date (always occurs, count 1):
outpatient_services:
  - { cost: 25000, date: "2025-04-01", description: "scheduled surgery" }

# Costs the plan never covers (paid in full, don't count toward OOP max):
uncovered:
  - { count: 4, cost: 375, description: "medication (not covered)" }
```

Entry semantics:

- **count**: `N` or `"min-max"` — occurrences per simulated year (a range is
  drawn uniformly each year).
- **probability**: chance the entry happens at all (default `1.0`).
- **cost**: fixed billed amount per occurrence; if omitted, drawn from the
  service's range in `costs/`.
- **date**: pins a scheduled event to `YYYY-MM-DD` (forces count 1); otherwise
  dates are random within the simulated year.
- **description**: label shown in `--breakdown` output.
- **uncovered**: bypasses all plan rules — the person pays the full cost, and it
  does not accrue toward any deductible or out-of-pocket max.

Profiles ship in three intensities (`-minimal`, `-middle`, `-full`) so you can
model a light, typical, or heavy year. A run-config lists the same profile file
more than once for multiple similar people (names are auto-numbered).

## Subsidies

`subsidy` is an optional per-plan monthly amount a third party pays toward the
premium (an employer contribution, or an ACA advance premium tax credit). By
default the report shows **what you pay** (`premium − subsidy`); the `--gross`
flag prices every plan at its **full premium**, which is the right lens for
comparing list prices, or for a COBRA / subsidy-lapse scenario. The report
header states which lens is active.

## Testing

```bash
make test        # validates data files, then runs the pytest suite
```

## Known limitations

The model deliberately simplifies real plans. Notable gaps:

- **Imaging vs. X-rays**: X-rays often have a different cost from imaging; the
  model uses a single `imaging` category.
- **Outpatient services**: ACA plans split these into ~3 categories, boiled down
  to one here.
- **In-network only**: cost-shares model participating-provider pricing.
- **Per-prescription caps** (e.g. specialty drugs "up to $X/prescription") are
  recorded but not enforced by the calculator.
- Plan-specific quirks not fully captured include the BS Gold 80 Trio HMO's
  per-day $375 inpatient copay, and the BS PERS Gold PPO's tier-4 drug handling
  and separate inpatient/outpatient deductibles.

## Roadmap

- A web UI (design notes in `docs/plans/`; dependencies are already declared).

## License

BSD 2-Clause — see [LICENSE](LICENSE).
