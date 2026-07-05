# PURPOSE: Tests for terminal output rendering

import pytest
from io import StringIO
from caca.output.terminal import TerminalRenderer


class TestTerminalRenderer:
    def test_render_header(self):
        renderer = TerminalRenderer()
        output = StringIO()

        renderer.render_header(
            output,
            household=[
                {"name": "alice", "profile": "healthy"},
                {"name": "bob", "profile": "chronic"},
            ],
            iterations=5000,
            converged=True,
            convergence_threshold=87,
        )

        result = output.getvalue()
        assert "Care Casino" in result
        assert "alice (healthy)" in result
        assert "bob (chronic)" in result
        assert "5,000" in result
        assert "converged" in result.lower()

    def test_render_rankings(self):
        renderer = TerminalRenderer()
        output = StringIO()

        summary = {
            "Plan A": {
                "expected_cost": 10000,
                "ci_95_low": 9500,
                "ci_95_high": 10500,
                "min": 8000,
                "max": 15000,
            },
            "Plan B": {
                "expected_cost": 12000,
                "ci_95_low": 11000,
                "ci_95_high": 13000,
                "min": 9000,
                "max": 18000,
            },
        }

        renderer.render_rankings(output, summary)

        result = output.getvalue()
        assert "Plan A" in result
        assert "Plan B" in result
        assert "$10,000" in result
        assert "1" in result  # Rank 1

    def test_render_histogram(self):
        renderer = TerminalRenderer()
        output = StringIO()

        costs = [10000, 10500, 11000, 10200, 10800] * 20

        renderer.render_histogram(output, "Test Plan", costs)

        result = output.getvalue()
        assert "Test Plan" in result
        # Should have some histogram characters
        assert any(c in result for c in "=")

    def test_format_currency(self):
        renderer = TerminalRenderer()
        assert renderer.format_currency(1234.56) == "$1,235"
        assert renderer.format_currency(1000000) == "$1,000,000"


class TestPlanHighlightsCombo:
    def test_copay_plus_coinsurance_renders_without_crashing(self):
        from caca.models import PlanRules, ServiceType, CostShare

        plan = PlanRules(
            name="Combo Plan",
            premium=4000,
            deductible_individual=0,
            deductible_family=0,
            oop_max_individual=5000,
            oop_max_family=10000,
            service_costs={ServiceType.EMERGENCY_ROOM: CostShare(250, 0.10)},
            service_costs_after_deductible={
                ServiceType.EMERGENCY_ROOM: CostShare(250, 0.10)
            },
        )
        renderer = TerminalRenderer()
        output = StringIO()

        renderer._render_plan_highlights(output, plan, {})

        text = output.getvalue()
        assert "Emergency Room" in text
        assert "$250" in text
        assert "10% coinsurance" in text


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
