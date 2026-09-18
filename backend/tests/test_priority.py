"""Tests for PriorityScorer weighted score calculations."""

import pytest
from app.optimizer.priority import PriorityScorer


def test_priority_scorer_default_weights():
    """Verify weighted priority score calculation with standard weights."""
    # 0.35 * 0.8 + 0.40 * 0.5 + 0.15 * 0.6 + 0.10 * 0.4 = 0.28 + 0.20 + 0.09 + 0.04 = 0.61
    score = PriorityScorer.calculate_priority(
        soc_urgency=0.8,
        departure_urgency=0.5,
        energy_deficit_score=0.6,
        waiting_score=0.4,
        w_soc=0.35,
        w_departure=0.40,
        w_deficit=0.15,
        w_waiting=0.10,
    )
    assert score == 0.61


def test_priority_scorer_bounds():
    """Verify priority score remains bounded within [0.0, 1.0]."""
    score_zero = PriorityScorer.calculate_priority(0.0, 0.0, 0.0, 0.0)
    assert score_zero == 0.0

    score_max = PriorityScorer.calculate_priority(1.0, 1.0, 1.0, 1.0)
    assert score_max == 1.0


def test_priority_scorer_invalid_weights_sum():
    """Verify weights not summing to 1.0 raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        PriorityScorer.calculate_priority(
            soc_urgency=0.5,
            departure_urgency=0.5,
            energy_deficit_score=0.5,
            waiting_score=0.5,
            w_soc=0.5,
            w_departure=0.5,
            w_deficit=0.5,
            w_waiting=0.5,
        )
    assert "must sum to 1.0" in str(exc_info.value)


def test_priority_scorer_negative_weight_raises():
    """Verify negative weights raise ValueError."""
    with pytest.raises(ValueError):
        PriorityScorer.calculate_priority(
            soc_urgency=0.5,
            departure_urgency=0.5,
            energy_deficit_score=0.5,
            waiting_score=0.5,
            w_soc=-0.1,
            w_departure=0.6,
            w_deficit=0.3,
            w_waiting=0.2,
        )
