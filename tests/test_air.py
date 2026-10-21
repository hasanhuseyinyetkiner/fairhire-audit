"""Adverse impact ratio, contingency tables, and zero-edge handling."""

import math

import numpy as np
import pytest
from app.domain.air import (
    FOUR_FIFTHS_THRESHOLD,
    adverse_impact_ratio,
    build_selection_audit,
    fisher_on_contingency,
    pick_reference,
)
from app.domain.compute import compute_analysis
from app.domain.prepare import prepare_frame
from app.domain.synthetic import similar_accuracy_different_errors

MAPPING = {
    "y_true": "y_true",
    "y_pred": "y_pred",
    "y_pred_alt": None,
    "score": "score",
    "score_semantics": "probability",
    "sensitive_columns": ["group"],
    "sample_weight": "sample_weight",
    "timestamp_column": None,
    "positive_label": "1",
}


def test_air_zero_focal_selections_is_zero_not_nan():
    value, reason = adverse_impact_ratio(0.0, 0.5)
    assert value == 0.0
    assert reason is None
    assert not math.isnan(value)


def test_air_zero_reference_rate_is_undefined_not_nan():
    value, reason = adverse_impact_ratio(0.2, 0.0)
    assert value is None
    assert reason == "undefined_denominator"


def test_air_both_zero_is_undefined_not_nan():
    value, reason = adverse_impact_ratio(0.0, 0.0)
    assert value is None
    assert reason == "undefined_denominator"


def test_air_undefined_inputs_never_nan():
    for left, right in [(None, 0.5), (0.5, None), (float("nan"), 0.5), (0.5, float("inf"))]:
        value, reason = adverse_impact_ratio(left, right)
        assert value is None
        assert reason == "undefined_denominator"


def test_air_classic_ratio():
    value, reason = adverse_impact_ratio(0.4, 0.5)
    assert reason is None
    assert value == pytest.approx(0.8)
    assert value == pytest.approx(FOUR_FIFTHS_THRESHOLD)


def test_pick_reference_highest_then_lexicographic_tie():
    assert pick_reference({"b": 0.3, "a": 0.5}) == "a"
    assert pick_reference({"b": 0.5, "a": 0.5}) == "a"
    assert pick_reference({"only": None}) is None


def test_fisher_on_known_table():
    # Identical selection rates → high p-value; odds ratio ~ 1.
    result = fisher_on_contingency(40, 60, 40, 60)
    assert result["undefined_reason"] is None
    assert result["odds_ratio"] == pytest.approx(1.0)
    assert result["p_value"] == pytest.approx(1.0)


def test_build_selection_audit_zero_applicants_group_skipped():
    # Eligible labels with one group having zero weight should not emit NaN AIR.
    y_pred = np.array([1, 0, 1, 0], dtype=int)
    labels = np.array(["a", "a", "b", "b"], dtype=object)
    weight = np.ones(4)
    audit = build_selection_audit(
        column="group",
        included=["a", "b"],
        y_pred=y_pred,
        labels=labels,
        weight=weight,
        selection_rates={"a": 0.5, "b": 0.5},
    )
    assert audit["reference_group"] == "a"
    assert audit["cmh_available"] is False
    assert "Mantel" in audit["cmh_note"]
    assert len(audit["pairs"]) == 1
    pair = audit["pairs"][0]
    assert pair["value"] == pytest.approx(1.0)
    assert pair["below_four_fifths"] is False
    assert pair["contingency"]["matrix"] == [[1.0, 1.0], [1.0, 1.0]]
    assert math.isfinite(pair["fisher_exact"]["p_value"])


def test_synthetic_air_matches_selection_rates():
    frame = similar_accuracy_different_errors()
    prepared = prepare_frame(frame, MAPPING, max_rows=10_000, min_n=30)
    analysis = compute_analysis(prepared, seed=20261020, iterations=80, cap=1000, min_n=30)
    column = analysis["groups"][0]
    audit = column["selection_audit"]
    groups = {row["group_value"]: row for row in column["groups"]}
    rate_a = next(m["value"] for m in groups["group_a"]["metrics"] if m["name"] == "selection_rate")
    rate_b = next(m["value"] for m in groups["group_b"]["metrics"] if m["name"] == "selection_rate")
    # Hand story: group_a sel = 50/100, group_b sel = 30/100 → reference a, AIR = 0.6
    assert rate_a == pytest.approx(0.5)
    assert rate_b == pytest.approx(0.3)
    assert audit["reference_group"] == "group_a"
    pair = audit["pairs"][0]
    assert pair["focal_group"] == "group_b"
    assert pair["value"] == pytest.approx(0.6)
    assert pair["below_four_fifths"] is True
    assert pair["contingency"]["focal_selected"] == pytest.approx(30)
    assert pair["contingency"]["reference_selected"] == pytest.approx(50)

    air_ci = next(
        item
        for item in analysis["confidence_intervals"]
        if item["metric_name"] == "adverse_impact_ratio" and item["group_value"] == "group_b:group_a"
    )
    assert air_ci["point"] == pytest.approx(0.6)
    assert air_ci["lower"] is not None
    assert air_ci["upper"] is not None
    assert air_ci["lower"] <= air_ci["point"] <= air_ci["upper"]


def test_zero_selections_in_group_air_is_zero():
    # Focal: zero selections; reference: 10/20 selected.
    y_pred = np.zeros(40, dtype=int)
    labels = np.array(["focal"] * 20 + ["ref"] * 20, dtype=object)
    y_pred[20:30] = 1
    weight = np.ones(40)
    audit = build_selection_audit(
        column="group",
        included=["focal", "ref"],
        y_pred=y_pred,
        labels=labels,
        weight=weight,
        selection_rates={"focal": 0.0, "ref": 0.5},
    )
    assert audit["reference_group"] == "ref"
    pair = audit["pairs"][0]
    assert pair["value"] == 0.0
    assert pair["undefined_reason"] is None
    assert pair["below_four_fifths"] is True
    assert not math.isnan(pair["value"])
