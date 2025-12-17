# Care Casino (caca) - Design Document

A Monte Carlo simulator for comparing US healthcare plan costs.

## Overview

Care Casino helps users select the best healthcare plan by simulating thousands of possible healthcare usage scenarios and calculating expected annual costs across multiple plans. It accounts for premiums, deductibles, copays, coinsurance, and out-of-pocket maximums.

## Configuration File Structure

The simulator is configured via a YAML file specifying simulation parameters, default costs, usage profiles, and household composition.

### Simulation Parameters

```yaml
simulation:
  iterations: auto              # or a specific number like 10000
  convergence_threshold_dollars: 100  # stop when CI is within ±$100
  max_iterations: 100000        # safety cap for 'auto' mode
  min_iterations: 1000          # always run at least this many
```

When `iterations: auto`, the simulator runs until plan rankings stabilize and confidence intervals fall below the threshold.

### Default Costs

Default cost ranges for services when not specified in profiles:

```yaml
defaults:
  costs:
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
```

### Profiles

Profiles define healthcare usage patterns. They support three syntaxes:

**Shorthand for simple counts:**
```yaml
primary_care_visit: 1-3        # 1 to 3 visits, random cost from defaults
tier_1_generic_drugs: 12       # exactly 12, random cost from defaults
```

**Probability for rare events:**
```yaml
emergency_room: { probability: 0.05 }           # 5% chance of 1 visit
emergency_room: { probability: 0.05, count: 2 } # 5% chance of 2 visits
```

**Scheduled events with known costs/dates:**
```yaml
specialist_visit:
  - { cost: 300, date: 2025-03-15, description: "pre-op consult" }
  - { cost: 300, date: 2025-05-01, description: "post-op follow-up" }
  - { count: 2-4 }  # additional random visits

inpatient_services:
  - { cost: 50000, date: 2025-04-01, description: "knee replacement" }

tier_4_specialty_drugs:
  - { count: 12, cost: 800, description: "Humira monthly" }
```

**Uncovered services** (bypass plan rules, add directly to total):
```yaml
uncovered:
  - { cost: 1200, date: 2025-06-15, description: "dental crown" }
  - { cost: 150, count: 2, description: "dental cleanings" }
```

All event entries support an optional `description` field for clarity in output.

### Household

Assign profiles to household members (1-5 people):

```yaml
household:
  - name: alice
    profile: planned_surgery
  - name: bob
    profile: healthy_adult
  - name: charlie
    profile: child
```

### Complete Example

```yaml
simulation:
  iterations: auto
  convergence_threshold_dollars: 100
  max_iterations: 100000
  min_iterations: 1000

defaults:
  costs:
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
    primary_care_visit: 1-3
    preventative_visit: 1
    specialist_visit: 0-2
    labs: 1-3
    emergency_room: { probability: 0.05 }
    tier_1_generic_drugs: 0-6

  child:
    primary_care_visit: 3-6
    preventative_visit: 2
    specialist_visit: 1-3
    urgent_care: { probability: 0.3, count: 1-2 }

  planned_surgery:
    primary_care_visit: 4-6
    specialist_visit:
      - { cost: 300, date: 2025-03-15, description: "pre-op consult" }
      - { cost: 300, date: 2025-05-01, description: "post-op follow-up" }
      - { count: 2-4 }
    imaging: { cost: 1500, date: 2025-03-15, description: "pre-op MRI" }
    inpatient_services: { cost: 50000, date: 2025-04-01, description: "knee replacement" }

household:
  - name: alice
    profile: planned_surgery
  - name: bob
    profile: healthy_adult
  - name: charlie
    profile: child
```

## Plans CSV Structure

Plans are defined in a CSV file with plans as columns and attributes as rows. Values use snake_case naming.

### Value Conventions

- Values 0-1: Coinsurance (e.g., `0.4` = patient pays 40%)
- Values > 1: Copay in dollars (e.g., `60` = $60 copay)
- `1` in "before deductible" row: 100% patient responsibility until deductible met
- Empty cell: Not applicable / falls under general deductible
- Values may include `$` prefix or `%` suffix for clarity

### Structure

```csv
plan_name,bs_bronze_60_hdhp_ppo,bs_bronze_60_ppo,bs_silver_70_ppo,...
plan_url,...
premium,...
deductible_individual,7200,5800,5200,...
deductible_family,14400,11600,10400,...
deductible_rx_individual,,450,50,...
deductible_rx_family,,900,100,...
oop_max_individual,7200,9800,9800,...
oop_max_family,14400,19600,19600,...
oop_max_rx_individual,,,,...
oop_max_rx_family,,,,...
oop_max_per_rx,,500,250,...
deductible_model,individual_first,individual_first,individual_first,...
preventative_visit,0,0,0,...
preventative_visit_after_deductible,0,0,0,...
primary_care_visit,1,60,50,...
primary_care_visit_after_deductible,0,0,0,...
specialist_visit,1,1,90,...
specialist_visit_after_deductible,0,95,0,...
...
```

### Deductible Models

The optional `deductible_model` row specifies how family deductibles accumulate:

- `individual_first` (default): Each person contributes toward their individual deductible, but one person can single-handedly satisfy the family deductible with catastrophic costs.
- `embedded_individual`: No single person can contribute more than the individual deductible amount toward the family total.

## Architecture

### Components

1. **ConfigLoader** - Parses YAML config, validates structure, resolves profile references

2. **PlanLoader** - Parses CSV, normalizes values (handles `$`, `%`, commas in numbers)

3. **EventGenerator** - Takes household + profiles, produces a list of dated healthcare events for one simulated year
   - Uses a `DistributionStrategy` interface for random date assignment
   - Scheduled events with dates are placed exactly
   - Random events are distributed according to strategy

4. **DistributionStrategy** - Pluggable interface for event date distribution
   - `UniformDistribution` (initial implementation): Events equally likely any day
   - Future: `ClusteredDistribution`, `FrontLoadedDistribution`

5. **PlanCalculator** - Takes a list of events and a plan, calculates total annual cost
   - Tracks individual and family deductible accumulation
   - Tracks individual and family OOP max accumulation
   - Applies correct copay/coinsurance based on deductible status
   - Handles Rx-specific deductibles and OOP maxes when present

6. **SimulationRunner** - Orchestrates the Monte Carlo loop
   - Generates N scenarios (each scenario = one possible year of events)
   - Runs each scenario through each plan
   - Collects results into a `ResultsStore` data structure
   - Implements adaptive convergence if `iterations: auto`

7. **ResultsStore** - Rich data structure preserving per-scenario detail
   - Per-scenario: events, per-plan costs, when deductibles were hit, etc.
   - Aggregates: means, percentiles, confidence intervals per plan

8. **OutputRenderer** - Consumes ResultsStore, produces output
   - `TerminalRenderer` - ASCII tables and histograms
   - `JsonRenderer` - Full data export

### Data Flow

```
Config + Plans CSV
       |
       v
  [EventGenerator] --> N scenarios (lists of dated events)
       |
       v
  [PlanCalculator] --> per-scenario, per-plan costs
       |
       v
  [ResultsStore] --> aggregated statistics
       |
       v
  [OutputRenderer] --> terminal display + JSON file
```

## Output Format

### Terminal Output

```
Care Casino - Healthcare Plan Simulator
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Household: alice (planned_surgery), bob (healthy_adult), charlie (child)
Scenarios simulated: 8,432 (converged at +/-$87)

Plan Rankings (by expected annual cost)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Rank  Plan                      Expected    95% CI           Best    Worst
-------------------------------------------------------------------------------
 1    BS PERS Access+ HMO       $41,823    $40,200-$43,500  $38,100  $46,200
 2    BS PERS Gold PPO          $43,105    $41,800-$44,400  $39,500  $51,300
 3    BS Silver 70 PPO          $47,892    $45,100-$50,700  $41,200  $58,400
 4    BS Bronze 60 PPO          $52,340    $48,900-$55,800  $44,600  $63,100
 5    BS Bronze 60 HDHP PPO     $54,215    $50,100-$58,300  $45,800  $71,200

Cost Distribution
━━━━━━━━━━━━━━━━━━
BS PERS Access+ HMO
$38k |########################################| $46k
     |    ..################..    |

BS PERS Gold PPO
$39k |################################################| $51k
     |   ..####################..      |
```

### JSON Export

```json
{
  "metadata": {
    "iterations": 8432,
    "converged": true,
    "convergence_threshold_dollars": 100,
    "timestamp": "2025-12-16T10:30:00Z"
  },
  "household": [...],
  "plans": [...],
  "summary": {
    "bs_pers_access_hmo": {
      "expected_cost": 41823,
      "ci_95_low": 40200,
      "ci_95_high": 43500,
      "min": 38100,
      "max": 46200,
      "percentiles": { "10": 39200, "25": 40100, "50": 41500, "75": 42800, "90": 44100 }
    }
  },
  "scenarios": [
    {
      "id": 1,
      "events": [...],
      "results_by_plan": {
        "bs_pers_access_hmo": {
          "total_cost": 42150,
          "premium": 37322,
          "out_of_pocket": 4828,
          "deductible_hit_date": null,
          "oop_max_hit_date": null
        }
      }
    }
  ]
}
```

## File Structure

```
caca/
├── plans.csv                    # input: plan definitions
├── config.yaml                  # input: simulation config (user creates)
├── config.template.yaml         # template with all services listed
├── caca/
│   ├── __init__.py
│   ├── cli.py                   # entry point, argument parsing
│   ├── config_loader.py         # YAML parsing and validation
│   ├── plan_loader.py           # CSV parsing and normalization
│   ├── event_generator.py       # produces dated events from profiles
│   ├── distribution.py          # DistributionStrategy interface + UniformDistribution
│   ├── plan_calculator.py       # applies plan rules to events
│   ├── simulation_runner.py     # Monte Carlo loop + convergence
│   ├── results.py               # ResultsStore data structure
│   └── output/
│       ├── __init__.py
│       ├── terminal.py          # ASCII tables and histograms
│       └── json_export.py       # JSON serialization
├── tests/
│   └── ...
├── pyproject.toml               # project config, dependencies
└── docs/
    └── plans/
        └── 2025-12-16-care-casino-design.md
```

## CLI Usage

```bash
# basic run
caca config.yaml

# with explicit plans file
caca config.yaml --plans plans.csv

# output options
caca config.yaml --json results.json
caca config.yaml --json results.json --quiet  # JSON only, no terminal output
```

## Implementation Notes

- Python implementation using standard library where possible
- NumPy for efficient random sampling and statistics
- PyYAML for config parsing
- Designed for extensibility: pluggable distribution strategies and output renderers
- Rich per-scenario data preserved for future visualization enhancements
