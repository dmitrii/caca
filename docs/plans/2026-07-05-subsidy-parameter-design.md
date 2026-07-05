# Subsidy Parameter + `--gross` Flag — Design

Date: 2026-07-05
Status: Approved (pending spec review)

## Summary

Add an optional per-plan `subsidy:` field representing the monthly premium paid by
a third party (an employer contribution, or an ACA advance premium tax credit).
The simulation prices plans on what the household actually pays
(`premium - subsidy`) by default, and on the full premium when run with a new
`--gross` flag. This replaces the parallel `plans/2026-no-subsidy/` and
`plans/2026-with-subsidy/` directories with a single `plans/2026/` directory.

## Motivation

- The household is weighing an employer Platinum plan whose $2,984/mo premium is
  largely paid by a third party, leaving a small employee share. Comparing
  that a small share against the *full* premiums of marketplace plans is apples-to-oranges
  unless the model makes the subsidy explicit.
- A third party covering part of a premium is the same mechanism whether it is an
  employer contribution or a government APTC. One `subsidy` concept covers both.
- The two-directory split (`no-subsidy` / `with-subsidy`) duplicated every plan
  file and carried placeholder `$999.99` premiums in the subsidized copies. A
  per-plan `subsidy` value plus a run-time lens removes the duplication.

### Real use cases for the two lenses

- **Net (default):** what the household actually pays given current subsidies.
- **Gross (`--gross`):** COBRA after a layoff (former employer plan at full
  price), or ACA enhanced-subsidy lapse / income above the eligibility cliff.

## Background / current state

- `PlanRules.premium` is stored annualized (monthly value × 12) by the loader.
- The copay + coinsurance combined cost-share feature ("Option B") is already
  implemented on this branch; it is a prerequisite for the Platinum plan but
  independent of this subsidy work.
- The Platinum plan file already exists at
  `plans/2026-no-subsidy/bs-platinum-full-ppo-offex.yaml`; this work relocates it
  into the consolidated `plans/2026/` and adds its `subsidy` value.

## Design

### Data model

- New optional plan field `subsidy:` — monthly dollars a third party pays toward
  the premium. Omitted ⇒ 0.
- `PlanRules` gains `subsidy: float`, annualized (× 12) at load time like
  `premium`. Semantics: `net_premium = premium - subsidy`; `premium` remains the
  full/gross price.

### Calculation

- The run carries a `gross: bool`. Effective premium =
  `premium` when `gross` else `premium - subsidy`.
- `PlanResult.total_cost = effective_premium + out_of_pocket`. Out-of-pocket is
  unaffected (subsidies move only premium).
- `PlanResult.premium` reflects the effective premium so the breakdown's
  "Annual Premium" line stays consistent with the total.

### CLI

- Add `--gross` to the `generate` subcommand (default off = net). Flows to the
  simulation runner and into the calculator.

### Loader + validation

- Loader parses `subsidy` (monthly) → × 12, stores on `PlanRules`.
- Validation: `0 <= subsidy <= premium` (net premium cannot be negative);
  otherwise a validation error.

### Output

- Terminal report header states the lens explicitly:
  - net: `Premiums: what you pay (net of subsidy)`
  - gross: `Premiums: full price (gross)`
- The per-plan breakdown shows a `Subsidy` line when the plan's subsidy is
  non-zero (and the lens is net), so the gross premium remains visible.

### Caching

- The `gross` flag joins the cache-key inputs so net and gross runs do not
  collide. Subsidy values already ride along in the plan-content hash.

### Directory migration

- Collapse the split into a single real `plans/2026/` directory containing the
  current `no-subsidy` files plus the relocated Platinum plan.
- Delete the `plans/2026 -> 2026-no-subsidy` symlink and the
  `plans/2026-with-subsidy/` directory (its `$999.99` placeholder premiums are
  obsolete under this model).
- Run-config plan lists already reference `plans/2026/...`, so they need no path
  changes.

### Seeded subsidy values

| Plan(s) | `subsidy:` (monthly) | Basis |
|---|---|---|
| 5 ACA marketplace plans (Bronze 60 HDHP, Bronze 60 PPO, Silver 70 Trio, Silver 70 PPO, Gold 80 Trio) | 1612 | Estimated enhanced-APTC for a example household at ~an example income (~450% FPL, 8.5% cap on a ~$2,462 benchmark Silver). Same shared household credit applied to all five. |
| BS Platinum Full PPO 0/0 OffEx | 2640 | Employer contribution |
| BS PERS Gold PPO, BS PERS Access+ HMO, CF Bigcorp Blue Preferred Gold PPO | 0 (omitted) | No applicable third-party premium subsidy |

The ACA `1612` figure is an estimate, commented in each file with its derivation
and the explicit "enhanced subsidies extended" assumption. Under original ACA
rules (post-lapse), a household at ~450% FPL is over the 400% cliff and would
receive `$0` — represented by `--gross`.

## Non-goals (YAGNI)

- No COBRA 102% load factor. Model the exact amount as data if needed.
- No multiple named subsidy scenarios. Editing `subsidy:` values plus `--gross`
  covers the current use cases.
- No income-driven subsidy computation inside the tool. Subsidy amounts are
  inputs, not derived.

## Testing (TDD)

- Calculator: net total uses `premium - subsidy`; gross total uses full premium.
- Loader: `subsidy` parsed and annualized (× 12); default 0 when omitted.
- Validation: `subsidy > premium` rejected; `subsidy == premium` allowed.
- Cache: gross and net runs produce different cache keys.
- Terminal: header text reflects the active lens; breakdown shows a `Subsidy`
  line when non-zero.
