# PURPOSE: Tests for healthcare event generation

import pytest
from datetime import date
from caca.event_generator import EventGenerator
from caca.distribution import UniformDistribution
from caca.models import ServiceType, CostRange, Event


class TestEventGenerator:
    def make_generator(self, seed=42):
        return EventGenerator(
            distribution=UniformDistribution(seed=seed),
            default_costs={
                "primary_care_visit": CostRange(150, 300),
                "specialist_visit": CostRange(200, 500),
                "emergency_room": CostRange(1500, 5000),
            },
            year=2025,
            seed=seed,
        )

    def test_generate_simple_count(self):
        gen = self.make_generator()
        profile = {
            "primary_care_visit": [
                {"count_min": 3, "count_max": 3, "probability": 1.0, "scheduled": False}
            ]
        }

        events = gen.generate_events("alice", profile)

        pcp_events = [e for e in events if e.service_type == ServiceType.PRIMARY_CARE_VISIT]
        assert len(pcp_events) == 3
        for e in pcp_events:
            assert e.person == "alice"
            assert 150 <= e.cost <= 300
            assert e.date.year == 2025

    def test_generate_count_range(self):
        gen = self.make_generator()
        profile = {
            "primary_care_visit": [
                {"count_min": 2, "count_max": 5, "probability": 1.0, "scheduled": False}
            ]
        }

        # Run multiple times to verify range
        counts = []
        for seed in range(100):
            gen = self.make_generator(seed=seed)
            events = gen.generate_events("alice", profile)
            counts.append(len(events))

        assert min(counts) >= 2
        assert max(counts) <= 5
        assert len(set(counts)) > 1  # Should have variety

    def test_generate_with_probability(self):
        profile = {
            "emergency_room": [
                {"count_min": 1, "count_max": 1, "probability": 0.5, "scheduled": False}
            ]
        }

        # Run many times to verify probability
        counts = []
        for seed in range(200):
            gen = self.make_generator(seed=seed)
            events = gen.generate_events("alice", profile)
            counts.append(len(events))

        # With 50% probability over 200 trials, expect roughly 100
        # Allow wide margin for randomness
        assert 60 <= sum(counts) <= 140

    def test_generate_scheduled_event(self):
        gen = self.make_generator()
        profile = {
            "specialist_visit": [
                {
                    "scheduled": True,
                    "date": "2025-03-15",
                    "cost": 300,
                    "description": "pre-op consult",
                    "count_min": 1,
                    "count_max": 1,
                }
            ]
        }

        events = gen.generate_events("alice", profile)

        assert len(events) == 1
        event = events[0]
        assert event.service_type == ServiceType.SPECIALIST_VISIT
        assert event.date == date(2025, 3, 15)
        assert event.cost == 300
        assert event.description == "pre-op consult"

    def test_generate_mixed_scheduled_and_random(self):
        gen = self.make_generator()
        profile = {
            "specialist_visit": [
                {
                    "scheduled": True,
                    "date": "2025-03-15",
                    "cost": 300,
                    "description": "pre-op",
                    "count_min": 1,
                    "count_max": 1,
                },
                {"count_min": 2, "count_max": 2, "probability": 1.0, "scheduled": False},
            ]
        }

        events = gen.generate_events("alice", profile)

        assert len(events) == 3
        scheduled = [e for e in events if e.description == "pre-op"]
        assert len(scheduled) == 1
        assert scheduled[0].date == date(2025, 3, 15)

    def test_generate_uncovered(self):
        gen = self.make_generator()
        profile = {
            "uncovered": [
                {
                    "scheduled": True,
                    "date": "2025-06-15",
                    "cost": 1200,
                    "description": "dental crown",
                    "count_min": 1,
                    "count_max": 1,
                }
            ]
        }

        events = gen.generate_events("alice", profile)

        assert len(events) == 1
        assert events[0].service_type == ServiceType.UNCOVERED
        assert events[0].cost == 1200

    def test_events_sorted_by_date(self):
        gen = self.make_generator()
        profile = {
            "primary_care_visit": [
                {"count_min": 10, "count_max": 10, "probability": 1.0, "scheduled": False}
            ],
            "specialist_visit": [
                {
                    "scheduled": True,
                    "date": "2025-06-15",
                    "cost": 300,
                    "count_min": 1,
                    "count_max": 1,
                }
            ],
        }

        events = gen.generate_events("alice", profile)

        dates = [e.date for e in events]
        assert dates == sorted(dates)
