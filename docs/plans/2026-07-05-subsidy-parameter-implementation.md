# Subsidy Parameter + `--gross` Flag Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional per-plan `subsidy:` field so the simulator prices plans on what the household actually pays by default, and on full price under a new `--gross` flag, replacing the two-directory subsidy split.

**Architecture:** `subsidy` is stored on `PlanRules` (annualized like `premium`). A single `PlanRules.effective_premium(gross)` helper is the one source of truth for net-vs-gross, consumed by the calculator, runner, CLI, and terminal. A `gross` boolean threads CLI → runner → calculator. Directory split collapses into one real `plans/2026/`.

**Tech Stack:** Python 3.13, pytest, PyYAML, numpy. Run tests with `.venv/bin/pytest`.

## Global Constraints

- `premium` and `subsidy` are stored **annualized** (monthly value × 12) on `PlanRules`; the loader does the ×12.
- Net premium = `premium − subsidy`; gross premium = `premium`. Out-of-pocket is never affected by subsidy.
- Bare scalar cost-shares and existing plan files keep their meaning; this work is additive.
- Seeded subsidy values (monthly, in plan files): the 5 `bs-aca-*` plans = `1612`; `bs-platinum-full-ppo-offex` = `2640`; PERS/Bigcorp = omitted (0).
- TDD for all code: write failing test, watch it fail, minimal code, watch it pass, commit.

## Spec deviation (discovered during planning)

The spec's **Caching** section is dropped: `cmd_generate` never invokes the `CacheManager` (the `--no-cache`/`--cache-dir` args are parsed but unused), so there is no cache read/write path and no net/gross collision to guard against. No task implements it.

---

### Task 1: `subsidy` field and `effective_premium` helper on PlanRules

**Files:**
- Modify: `caca/models.py` (the `PlanRules` dataclass)
- Test: `tests/test_models.py`

**Interfaces:**
- Produces: `PlanRules.subsidy: float` (default `0.0`); `PlanRules.effective_premium(gross: bool = False) -> float` returning `premium if gross else premium - subsidy`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_models.py`:

```python
def test_plan_rules_subsidy_defaults_to_zero():
    from caca.models import PlanRules
    plan = PlanRules(
        name="P", premium=12000, deductible_individual=0, deductible_family=0,
        oop_max_individual=5000, oop_max_family=10000,
        service_costs={}, service_costs_after_deductible={},
    )
    assert plan.subsidy == 0.0
    assert plan.effective_premium(gross=False) == 12000
    assert plan.effective_premium(gross=True) == 12000


def test_effective_premium_subtracts_subsidy_when_net():
    from caca.models import PlanRules
    plan = PlanRules(
        name="P", premium=12000, deductible_individual=0, deductible_family=0,
        oop_max_individual=5000, oop_max_family=10000,
        service_costs={}, service_costs_after_deductible={}, subsidy=9000,
    )
    assert plan.effective_premium(gross=False) == 3000
    assert plan.effective_premium(gross=True) == 12000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_models.py -k subsidy -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'subsidy'` / `AttributeError: 'PlanRules' object has no attribute 'effective_premium'`.

- [ ] **Step 3: Write minimal implementation**

In `caca/models.py`, in the `PlanRules` dataclass, add a field after `deductible_model` and a method:

```python
    deductible_model: str = "individual_first"
    subsidy: float = 0.0

    def effective_premium(self, gross: bool = False) -> float:
        """Return the premium the household pays: full price under gross,
        otherwise net of the third-party subsidy."""
        return self.premium if gross else self.premium - self.subsidy
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_models.py -k subsidy -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add caca/models.py tests/test_models.py
git commit -m "feat: add subsidy field and effective_premium to PlanRules"
```

---

### Task 2: Loader parses and annualizes `subsidy`

**Files:**
- Modify: `caca/loaders/plan_loader.py` (the `load_plan_yaml` return)
- Test: `tests/test_loaders_plan.py`

**Interfaces:**
- Consumes: `PlanRules.subsidy` (Task 1).
- Produces: `load_plan_yaml` sets `subsidy` = monthly value × 12; 0.0 when the key is absent.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_loaders_plan.py`:

```python
class TestLoadSubsidy:
    def test_subsidy_annualized(self):
        yaml_content = """
plan_name: Subsidized Plan
premium: 2000
subsidy: 1500
deductible_individual: 0
deductible_family: 0
oop_max_individual: 5000
oop_max_family: 10000
"""
        plan = load_plan_yaml(StringIO(yaml_content))
        assert plan.premium == 24000
        assert plan.subsidy == 18000

    def test_subsidy_defaults_to_zero_when_absent(self):
        yaml_content = """
plan_name: No Subsidy
premium: 2000
deductible_individual: 0
deductible_family: 0
oop_max_individual: 5000
oop_max_family: 10000
"""
        plan = load_plan_yaml(StringIO(yaml_content))
        assert plan.subsidy == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_loaders_plan.py::TestLoadSubsidy -v`
Expected: FAIL — `assert 0.0 == 18000` (loader doesn't read `subsidy` yet).

- [ ] **Step 3: Write minimal implementation**

In `caca/loaders/plan_loader.py`, inside `load_plan_yaml`, near where `monthly_premium` is computed, add:

```python
    monthly_subsidy = parse_cost_value(data.get("subsidy")) or 0.0
```

and in the `PlanRules(...)` construction add the keyword argument:

```python
        subsidy=monthly_subsidy * 12,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_loaders_plan.py::TestLoadSubsidy -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add caca/loaders/plan_loader.py tests/test_loaders_plan.py
git commit -m "feat: parse subsidy from plan YAML"
```

---

### Task 3: Validation rejects `subsidy > premium`

**Files:**
- Modify: `caca/validation.py` (the `validate_plan` function)
- Test: `tests/test_validation.py`

**Interfaces:**
- Consumes: raw plan `data` dict (monthly values).
- Produces: a `ValidationError` when `subsidy < 0` or `subsidy > premium`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_validation.py`:

```python
class TestValidateSubsidy:
    def test_subsidy_within_premium_passes(self):
        plan_data = complete_plan_data(premium=2000, subsidy=1500)
        assert validate_plan(plan_data, "test.yaml") == []

    def test_subsidy_equal_to_premium_passes(self):
        plan_data = complete_plan_data(premium=2000, subsidy=2000)
        assert validate_plan(plan_data, "test.yaml") == []

    def test_subsidy_exceeding_premium_rejected(self):
        plan_data = complete_plan_data(premium=2000, subsidy=2500)
        errors = validate_plan(plan_data, "test.yaml")
        assert len(errors) == 1
        assert "subsidy" in errors[0].message.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_validation.py::TestValidateSubsidy -v`
Expected: FAIL on `test_subsidy_exceeding_premium_rejected` — `assert 0 == 1` (no check yet).

- [ ] **Step 3: Write minimal implementation**

In `caca/validation.py`, inside `validate_plan`, before `return errors`, add:

```python
    # Subsidy cannot be negative or exceed the premium (net premium >= 0)
    subsidy = data.get("subsidy")
    premium = data.get("premium")
    if isinstance(subsidy, (int, float)):
        if subsidy < 0:
            errors.append(ValidationError(
                message=f"Invalid subsidy '{subsidy}': must not be negative",
                file_path=file_path,
            ))
        elif isinstance(premium, (int, float)) and subsidy > premium:
            errors.append(ValidationError(
                message=f"Subsidy (${subsidy:,.2f}) exceeds premium (${premium:,.2f})",
                file_path=file_path,
            ))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_validation.py::TestValidateSubsidy -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add caca/validation.py tests/test_validation.py
git commit -m "feat: validate subsidy does not exceed premium"
```

---

### Task 4: Calculator prices on the effective premium

**Files:**
- Modify: `caca/plan_calculator.py` (`PlanCalculator.__init__`, `calculate`)
- Test: `tests/test_plan_calculator.py`

**Interfaces:**
- Consumes: `PlanRules.effective_premium(gross)` (Task 1).
- Produces: `PlanCalculator(plan, household_members, gross: bool = False)`; `PlanResult.premium` and `total_cost` use the effective premium.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_plan_calculator.py`:

```python
class TestSubsidyPricing:
    def test_net_total_subtracts_subsidy(self):
        plan = make_plan(premium=12000, subsidy=9000)
        calc = PlanCalculator(plan, ["alice"])  # gross defaults to False
        result = calc.calculate([])
        assert result.premium == 3000
        assert result.total_cost == 3000

    def test_gross_total_uses_full_premium(self):
        plan = make_plan(premium=12000, subsidy=9000)
        calc = PlanCalculator(plan, ["alice"], gross=True)
        result = calc.calculate([])
        assert result.premium == 12000
        assert result.total_cost == 12000
```

Also extend the `make_plan` helper in that file so it forwards `subsidy`: add `subsidy=kwargs.get("subsidy", 0.0),` to the `PlanRules(...)` call inside `make_plan`.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_plan_calculator.py::TestSubsidyPricing -v`
Expected: FAIL — `PlanCalculator.__init__() got an unexpected keyword argument 'gross'` and/or `assert 12000 == 3000`.

- [ ] **Step 3: Write minimal implementation**

In `caca/plan_calculator.py`:

Change the constructor:

```python
    def __init__(self, plan: PlanRules, household_members: list[str], gross: bool = False):
        self.plan = plan
        self.household_members = household_members
        self.gross = gross
```

In `calculate`, replace the `PlanResult(...)` return so premium and total use the effective premium:

```python
        effective_premium = self.plan.effective_premium(self.gross)
        return PlanResult(
            total_cost=effective_premium + total_oop,
            premium=effective_premium,
            out_of_pocket=total_oop,
            deductible_hit_date=deductible_hit_date,
            oop_max_hit_date=oop_max_hit_date,
            event_costs=event_costs,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_plan_calculator.py -v`
Expected: PASS (new tests and all existing calculator tests).

- [ ] **Step 5: Commit**

```bash
git add caca/plan_calculator.py tests/test_plan_calculator.py
git commit -m "feat: price plans on effective (net/gross) premium"
```

---

### Task 5: Runner threads the `gross` flag to the calculator

**Files:**
- Modify: `caca/simulation_runner.py` (`SimulationRunner.__init__`, the calculator call in `run`)
- Test: `tests/test_simulation_runner.py`

**Interfaces:**
- Consumes: `PlanCalculator(plan, members, gross=...)` (Task 4).
- Produces: `SimulationRunner(..., gross: bool = False)` applied to every plan calculation.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_simulation_runner.py` (follow the file's existing construction of `PlanRules`/`SimulationRunner`; use an empty-usage household so out-of-pocket is 0 and only premium remains):

```python
def test_runner_gross_flag_controls_premium():
    from caca.models import PlanRules
    from caca.simulation_runner import SimulationRunner

    plan = PlanRules(
        name="Subsidized", premium=12000, deductible_individual=0, deductible_family=0,
        oop_max_individual=5000, oop_max_family=10000,
        service_costs={}, service_costs_after_deductible={}, subsidy=9000,
    )
    household = [{"name": "alice", "profile": "empty"}]

    net_runner = SimulationRunner(
        plans=[plan], profiles={"empty": {}}, household=household,
        default_costs={}, year=2025, seed=1,
    )
    net = net_runner.run(iterations=10, min_iterations=10)
    assert net.summary["Subsidized"]["expected_cost"] == 3000

    gross_runner = SimulationRunner(
        plans=[plan], profiles={"empty": {}}, household=household,
        default_costs={}, year=2025, seed=1, gross=True,
    )
    gross = gross_runner.run(iterations=10, min_iterations=10)
    assert gross.summary["Subsidized"]["expected_cost"] == 12000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_simulation_runner.py::test_runner_gross_flag_controls_premium -v`
Expected: FAIL — `SimulationRunner.__init__() got an unexpected keyword argument 'gross'`.

- [ ] **Step 3: Write minimal implementation**

In `caca/simulation_runner.py`, add `gross` to the constructor signature and store it:

```python
        year: int,
        seed: int | None = None,
        gross: bool = False,
    ):
```
```python
        self.seed = seed
        self.gross = gross
        self.rng = np.random.default_rng(seed)
```

In `run`, change the calculator construction:

```python
                    calc = PlanCalculator(plan, household_members, gross=self.gross)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_simulation_runner.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add caca/simulation_runner.py tests/test_simulation_runner.py
git commit -m "feat: thread gross flag through simulation runner"
```

---

### Task 6: `--gross` CLI flag, lens header, and subsidy in breakdown

**Files:**
- Modify: `caca/cli.py` (`parse_args`, `cmd_generate`)
- Modify: `caca/output/terminal.py` (`render_full_report`, `render_header`, `render_breakdown`)
- Test: `tests/test_output_terminal.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `SimulationRunner(..., gross=...)` (Task 5), `PlanRules.effective_premium(gross)` (Task 1), `PlanRules.subsidy`.
- Produces: `render_full_report(..., gross: bool = False)`; `render_header(..., gross: bool = False)`; `render_breakdown(..., gross: bool = False)`; CLI `--gross` flag.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_output_terminal.py`:

```python
class TestLensHeader:
    def test_net_lens_header(self):
        renderer = TerminalRenderer()
        output = StringIO()
        renderer.render_header(output, [{"name": "a", "profile": "a"}], 100, True, 100, gross=False)
        assert "what you pay (net of subsidy)" in output.getvalue()

    def test_gross_lens_header(self):
        renderer = TerminalRenderer()
        output = StringIO()
        renderer.render_header(output, [{"name": "a", "profile": "a"}], 100, True, 100, gross=True)
        assert "full price (gross)" in output.getvalue()
```

Add to `tests/test_cli.py` (follow the file's existing subprocess/`parse_args` pattern; this asserts the flag parses):

```python
def test_gross_flag_parses():
    from caca.cli import parse_args
    args = parse_args(["generate", "run.yaml", "--gross"])
    assert args.gross is True

def test_gross_defaults_false():
    from caca.cli import parse_args
    args = parse_args(["generate", "run.yaml"])
    assert args.gross is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_output_terminal.py::TestLensHeader tests/test_cli.py -k gross -v`
Expected: FAIL — `render_header() got an unexpected keyword argument 'gross'` and `AttributeError: 'Namespace' object has no attribute 'gross'`.

- [ ] **Step 3: Write minimal implementation**

In `caca/cli.py` `parse_args`, add to the generate subparser (next to `--quiet`):

```python
    gen_parser.add_argument(
        "--gross",
        action="store_true",
        help="Price plans at full premium, ignoring subsidies",
    )
```

In `caca/cli.py` `cmd_generate`, pass `gross` to the runner:

```python
    runner = SimulationRunner(
        plans=config["plans"],
        profiles=profiles,
        household=household,
        default_costs=config["costs"],
        year=2025,
        gross=args.gross,
    )
```

pass `gross` to the full report:

```python
        renderer.render_full_report(
            sys.stdout,
            household,
            results.iterations,
            results.converged,
            sim_params["convergence_threshold_dollars"],
            results.summary,
            plan_costs,
            gross=args.gross,
        )
```

and in the breakdown loop pass the effective premium and gross:

```python
                renderer.render_breakdown(
                    f,
                    plan.name,
                    results.scenarios,
                    plan.effective_premium(args.gross),
                    plan_rules=plan,
                    gross=args.gross,
                )
```

In `caca/output/terminal.py`, add `gross` to `render_full_report` (default `False`) and forward it:

```python
    def render_full_report(
        self,
        output: TextIO,
        household: list[dict],
        iterations: int,
        converged: bool,
        convergence_threshold: float,
        summary: dict[str, dict],
        plan_costs: dict[str, list[float]],
        gross: bool = False,
    ) -> None:
        """Render the complete report."""
        self.render_header(output, household, iterations, converged, convergence_threshold, gross=gross)
```

Add `gross` to `render_header` (default `False`) and emit the lens line right before its final `output.write("\n")`:

```python
    def render_header(
        self,
        output: TextIO,
        household: list[dict],
        iterations: int,
        converged: bool,
        convergence_threshold: float,
        gross: bool = False,
    ) -> None:
```
```python
        lens = "full price (gross)" if gross else "what you pay (net of subsidy)"
        output.write(f"Premiums: {lens}\n")
        output.write("\n")
```

Add `gross` to `render_breakdown` (default `False`) by extending its signature:

```python
    def render_breakdown(
        self,
        output: TextIO,
        plan_name: str,
        scenarios: list,
        plan_premium: float,
        plan_rules: "PlanRules | None" = None,
        highlight_thresholds: dict | None = None,
        gross: bool = False,
    ) -> None:
```

Add a helper method on `TerminalRenderer` for the premium label:

```python
    def _premium_label(self, plan_rules, gross: bool) -> str:
        subsidy = getattr(plan_rules, "subsidy", 0) or 0
        if gross or subsidy <= 0:
            return "Annual Premium"
        return f"Annual Premium (net of {self.format_currency(subsidy)} subsidy)"
```

Replace both literal `'Annual Premium'` labels in `render_breakdown` (the single-scenario branch and the two-scenario branch) with `self._premium_label(plan_rules, gross)`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_output_terminal.py tests/test_cli.py -v`
Expected: PASS (new and existing).

- [ ] **Step 5: Commit**

```bash
git add caca/cli.py caca/output/terminal.py tests/test_output_terminal.py tests/test_cli.py
git commit -m "feat: add --gross flag, premium lens header, and subsidy in breakdown"
```

---

### Task 7: Collapse the directory split and seed subsidy values

**Files:**
- Delete: `plans/2026` (symlink), `plans/2026-with-subsidy/` (directory)
- Move: `plans/2026-no-subsidy/` → `plans/2026/`
- Modify: the 5 `plans/2026/bs-aca-*.yaml` files (add `subsidy: 1612`); `plans/2026/bs-platinum-full-ppo-offex.yaml` (add `subsidy: 2640`)

This is a data/config task (no unit test); it is verified by `caca validate` and a generate run.

- [ ] **Step 1: Consolidate the directory**

```bash
cd .
rm plans/2026                      # remove the symlink
rm -rf plans/2026-with-subsidy     # obsolete placeholder premiums
mv plans/2026-no-subsidy plans/2026
ls plans/                          # expect only: 2026
ls plans/2026/                     # expect 9 plan .yaml files incl. bs-platinum-full-ppo-offex.yaml
```

- [ ] **Step 2: Add subsidy to the five ACA plans**

For each of `bs-aca-bronze-60-hdhp-ppo.yaml`, `bs-aca-bronze-60-ppo.yaml`, `bs-aca-gold-80-trio-hmo.yaml`, `bs-aca-silver-70-ppo.yaml`, `bs-aca-silver-70-trio-hmo.yaml`, add this line immediately after the `premium:` line:

```yaml
# subsidy: estimated enhanced-APTC for a example household at ~an example income (~450% FPL,
# 8.5%-of-income cap on a ~$2,462 benchmark Silver). Shared household credit;
# applies only if enhanced ACA subsidies are extended. Use --gross for the no-subsidy world.
subsidy: 1612
```

- [ ] **Step 3: Add subsidy to the Platinum plan**

In `plans/2026/bs-platinum-full-ppo-offex.yaml`, immediately after the `premium: 2984` line, add:

```yaml
# subsidy: employer contribution (total premium $2,984/mo, a third party pays part of it,
# leaving the a small share/mo employee share as the net premium).
subsidy: 2640
```

- [ ] **Step 4: Validate**

Run: `.venv/bin/caca validate plans/`
Expected: `✓ All files valid`

- [ ] **Step 5: Commit**

```bash
git add plans/2026
git commit -m "data: collapse subsidy directory split and seed subsidy values"
```

---

### Task 8: Wire Platinum into the run-configs and verify net/gross end-to-end

**Files:**
- Modify: `examples/calzones-full.yaml`, `examples/calzones-middle.yaml`, `examples/calzones-minimal.yaml` (add the Platinum plan to each `plans:` list)

Verification task — confirms the whole feature works against real data.

- [ ] **Step 1: Add Platinum to each run-config**

In each of the three `examples/calzones-*.yaml` files, add this line to the `plans:` list (after the `cf-bigcorp-...` line):

```yaml
  - plans/2026/bs-platinum-full-ppo-offex.yaml
```

- [ ] **Step 2: Run the net (default) comparison**

Run: `.venv/bin/caca generate examples/calzones-full.yaml`
Expected: header line `Premiums: what you pay (net of subsidy)`; Platinum ranks #1 (net premium $4,128/yr); the five ACA plans show reduced totals vs their full premiums.

- [ ] **Step 3: Run the gross comparison**

Run: `.venv/bin/caca generate examples/calzones-full.yaml --gross`
Expected: header line `Premiums: full price (gross)`; Platinum's premium rises to $35,808/yr ($2,984×12) and it no longer dominates; the five ACA plans return to their full-premium totals from the pre-subsidy baseline.

- [ ] **Step 4: Full suite green**

Run: `.venv/bin/caca validate plans/ profiles/ costs/ examples/ && .venv/bin/pytest -q`
Expected: `✓ All files valid` and all tests pass.

- [ ] **Step 5: Commit**

```bash
git add examples/calzones-full.yaml examples/calzones-middle.yaml examples/calzones-minimal.yaml
git commit -m "config: add Platinum plan to calzones run configs"
```

---

## Self-Review

**Spec coverage:** data model → Task 1; loader ×12 → Task 2; validation → Task 3; calculation/effective premium → Task 4; runner threading → Task 5; CLI `--gross` + lens header + breakdown subsidy line → Task 6; directory migration + seeded values → Task 7; end-to-end net/gross verification + run-config wiring → Task 8. Caching requirement intentionally dropped (documented deviation — cache is unused in the generate path).

**Placeholder scan:** none — every code step contains concrete code and exact commands.

**Type consistency:** `effective_premium(gross: bool)` defined in Task 1 and consumed identically in Tasks 4/6; `gross` keyword is consistent across `PlanCalculator` (Task 4), `SimulationRunner` (Task 5), `render_full_report`/`render_header`/`render_breakdown` and CLI (Task 6); `subsidy` field name consistent across model, loader, validation, terminal.
