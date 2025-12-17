# Modular Configuration Design

This document describes the redesign of caca's configuration system to support
community contributions and web service deployment.

## Goals

1. Make it easy for non-coders to contribute plan definitions
2. Enable composable configs from reusable pieces
3. Support caching for web service deployment
4. Validate contributions automatically in CI

## File Structure

```
plans/
  2026/
    bs-silver-70-hmo.yaml
    bs-gold-80-hmo.yaml
    ...
profiles/
  healthy-young-adult.yaml
  expecting-couple/
    alice.yaml
    bob.yaml
  middle-aged-adult.yaml
  ...
costs/
  2026-california.yaml
  ...
parameters/
  simulation.yaml
```

### Plan Files

Plans use simple `key: value` format with `#` comments. This is valid YAML but
can be documented as plain text for non-technical contributors.

```yaml
# BS Silver 70 Trio HMO
# Source: CoveredCA SBC dated 2024-10-15

plan_name: BS Silver 70 Trio HMO
premium: 2462.32

# Deductibles (SBC page 2)
deductible_individual: 5200
deductible_family: 10400

# Out-of-pocket maximums
oop_max_individual: 9800
oop_max_family: 19600

# Cost sharing (before deductible)
primary_care_visit: 50
specialist_visit: 90
labs: 50

# Cost sharing (after deductible)
primary_care_visit_after_deductible: 50
specialist_visit_after_deductible: 90
```

### Profile Files

Each person has their own file with expected annual usage:

```yaml
# profiles/expecting-couple/alice.yaml
name: alice

primary_care_visit: 6
specialist_visit: 8
labs: 12
imaging: 3
tier_1_generic_drugs: 12
```

### Cost Files

Define expected costs for each service type:

```yaml
# costs/2026-california.yaml
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
```

### Simulation Parameters

```yaml
# parameters/simulation.yaml
iterations: auto
convergence_threshold_dollars: 100
max_iterations: 100000
min_iterations: 1000
```

## Run Configuration

The run config references all pieces by file path:

```yaml
# estimates.yaml
simulation: parameters/simulation.yaml
costs: costs/2026-california.yaml

plans:
  - plans/2026/bs-silver-70-hmo.yaml
  - plans/2026/bs-gold-80-hmo.yaml

people:
  - profiles/expecting-couple/alice.yaml
  - profiles/expecting-couple/bob.yaml
```

## CLI Structure

Two subcommands with short aliases:

```bash
caca generate config.yaml       # run simulation
caca gen config.yaml            # short form

caca validate plans/ costs/     # validate data files
caca val plans/ costs/          # short form
```

### Generate Flags

- `--breakdown FILE` - Write detailed per-plan breakdowns to file
- `--json FILE` - Write JSON results
- `--quiet` - Suppress terminal output
- `--no-cache` - Skip cache lookup, force fresh simulation
- `--cache-dir DIR` - Override cache location (default: `.caca-cache/`)

## Validation

The `validate` subcommand checks:

1. **File existence** - All referenced files must exist
2. **Required fields** - Plans need `plan_name`, `premium`, `oop_max_individual`, etc.
3. **Uniqueness** - No duplicate plan names, no duplicate people names
4. **Completeness** - Every service type used in a profile must have a cost defined
5. **Consistency** - Coinsurance values between 0-1, copays positive, deductible ≤ OOP max

### Error Message Format

```
Error: File not found: plans/2026/bs-silver-70-hmo.yaml
  Referenced in: run.yaml, line 8

Error: Missing required field 'oop_max_individual'
  In: plans/2026/bs-bronze-60-ppo.yaml

Error: Duplicate plan name 'BS Gold 80 HMO'
  First defined in: plans/2026/bs-gold-80-hmo.yaml
  Also defined in: plans/2026/bs-gold-80-hmo-copy.yaml

Error: No cost defined for 'imaging'
  Used by profile: profiles/alice.yaml
  Define it in: costs/2026-california.yaml

Error: Deductible ($10,000) exceeds OOP max ($8,000)
  In: plans/2026/broken-plan.yaml
```

## Caching

Results are cached to disk for web service performance.

### Cache Key

The cache key is a SHA256 hash of:

1. Canonical inputs (all referenced files, comments stripped, keys sorted)
2. Hash of calculation-affecting source files

```python
CALC_FILES = [
    "caca/plan_calculator.py",
    "caca/models.py",
    "caca/simulation_runner.py",
    "caca/event_generator.py",
]

cache_key = sha256(canonical_inputs_json + hash_of_calc_files)
```

### Cache Storage

Flat JSON files in `.caca-cache/`:

```
.caca-cache/
  a3f8b2c1...json
  e7d4f9a0...json
```

Cache is invalidated when:
- Any input changes (plans, profiles, costs, simulation params, people)
- Any calculation-affecting source file changes

## Makefile

```makefile
.PHONY: deps test validate

deps:
	python -m venv .venv
	.venv/bin/pip install -e ".[dev]"

test: validate
	.venv/bin/pytest

validate:
	.venv/bin/caca validate plans/ profiles/ costs/
```

## Starter Profiles

Initial set of example profiles to include:

- `healthy-young-adult.yaml` - Minimal usage, annual checkup only
- `middle-aged-adult.yaml` - Regular checkups, some prescriptions
- `expecting-couple/` - Higher OB/GYN, labs, imaging usage
- `chronic-condition.yaml` - Regular specialist visits, multiple prescriptions
- `family-with-kids.yaml` - Pediatric visits, urgent care, common illnesses
