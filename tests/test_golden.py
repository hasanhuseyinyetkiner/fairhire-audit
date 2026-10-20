"""Hand-computed rates and Fairlearn 0.15 comparisons."""

import numpy as np
import pytest
from app.domain.compute import compute_analysis
from app.domain.definitions import CONFUSION_CONVENTION
from app.domain.fairness import disparity_values, metric_frame_rates
from app.domain.prepare import prepare_frame
from app.domain.rates import counts_from_arrays, metrics_from_counts
from app.domain.synthetic import (
    different_accuracy_similar_error_rates,
    similar_accuracy_different_errors,
)
from sklearn.metrics import brier_score_loss, confusion_matrix

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


def _by_name(metrics):
    return {metric["name"]: metric for metric in metrics}


def _repeat(y_true, y_pred, group, n):
    return (
        np.full(n, y_true, dtype=int),
        np.full(n, y_pred, dtype=int),
        np.full(n, group, dtype=object),
    )


def test_hand_counted_two_group_rates_and_fairlearn():
    parts = [
        _repeat(1, 1, "group_a", 40),
        _repeat(1, 0, "group_a", 10),
        _repeat(0, 1, "group_a", 10),
        _repeat(0, 0, "group_a", 40),
        _repeat(1, 1, "group_b", 30),
        _repeat(1, 0, "group_b", 20),
        _repeat(0, 0, "group_b", 50),
    ]
    y_true = np.concatenate([part[0] for part in parts])
    y_pred = np.concatenate([part[1] for part in parts])
    groups = np.concatenate([part[2] for part in parts])
    weight = np.ones(len(y_true))

    counts = counts_from_arrays(y_true, y_pred, weight)
    assert (counts.tn, counts.fp, counts.fn, counts.tp) == (90, 10, 30, 70)
    matrix = confusion_matrix(y_true, y_pred, labels=[0, 1])
    assert matrix[0, 0] == 90
    assert matrix[0, 1] == 10
    assert matrix[1, 0] == 30
    assert matrix[1, 1] == 70
    assert "TN" in CONFUSION_CONVENTION

    overall = _by_name(metrics_from_counts(counts, sample_size=200))
    assert overall["accuracy"]["value"] == pytest.approx(160 / 200)
    assert overall["precision"]["value"] == pytest.approx(70 / 80)
    assert overall["recall"]["value"] == pytest.approx(70 / 100)
    assert overall["fpr"]["value"] == pytest.approx(10 / 100)
    assert overall["fnr"]["value"] == pytest.approx(30 / 100)
    assert overall["balanced_accuracy"]["value"] == pytest.approx((0.70 + 0.90) / 2)

    mask_a = groups == "group_a"
    group_a = _by_name(metrics_from_counts(counts_from_arrays(y_true[mask_a], y_pred[mask_a])))
    assert group_a["accuracy"]["value"] == pytest.approx(0.80)
    assert group_a["fpr"]["value"] == pytest.approx(0.20)
    assert group_a["fnr"]["value"] == pytest.approx(0.20)
    assert group_a["recall"]["value"] == pytest.approx(0.80)

    mask_b = groups == "group_b"
    group_b = _by_name(metrics_from_counts(counts_from_arrays(y_true[mask_b], y_pred[mask_b])))
    assert group_b["accuracy"]["value"] == pytest.approx(0.80)
    assert group_b["fpr"]["value"] == 0.0
    assert group_b["fpr"]["undefined_reason"] is None
    assert group_b["fnr"]["value"] == pytest.approx(0.40)
    assert group_b["precision"]["value"] == pytest.approx(1.0)
    assert group_b["recall"]["value"] == pytest.approx(0.60)

    frame = metric_frame_rates(y_true, y_pred, groups, weight)
    assert frame["group_a"]["recall"] == pytest.approx(0.80)
    assert frame["group_b"]["fpr"] == pytest.approx(0.0)
    assert frame["group_a"]["count"] == pytest.approx(100)

    disparities = disparity_values(y_true, y_pred, groups, weight)
    assert disparities["demographic_parity_difference"][0] == pytest.approx(0.20)
    assert disparities["equal_opportunity_difference"][0] == pytest.approx(0.20)
    assert disparities["equalized_odds_difference"][0] == pytest.approx(0.20)


def test_undefined_denominator_is_not_zero():
    y_true = np.ones(4, dtype=int)
    y_pred = np.ones(4, dtype=int)
    metrics = _by_name(metrics_from_counts(counts_from_arrays(y_true, y_pred)))
    assert metrics["accuracy"]["value"] == pytest.approx(1.0)
    assert metrics["recall"]["value"] == pytest.approx(1.0)
    assert metrics["fnr"]["value"] == 0.0
    assert metrics["fpr"]["value"] is None
    assert metrics["fpr"]["undefined_reason"] == "undefined_denominator"
    assert metrics["tnr"]["value"] is None
    assert metrics["balanced_accuracy"]["value"] is None
    assert "not a zero" in metrics["fpr"]["message"]


def test_sample_weights_change_precision():
    y_true = np.array([1, 0])
    y_pred = np.array([1, 1])
    weight = np.array([1.0, 3.0])
    metrics = _by_name(metrics_from_counts(counts_from_arrays(y_true, y_pred, weight), sample_size=2))
    assert metrics["precision"]["value"] == pytest.approx(0.25)
    assert metrics["precision"]["numerator"] == pytest.approx(1)
    assert metrics["precision"]["denominator"] == pytest.approx(4)


def test_synthetic_profile_matches_hand_story():
    frame = similar_accuracy_different_errors()
    prepared = prepare_frame(frame, MAPPING, max_rows=10_000, min_n=30)
    analysis = compute_analysis(prepared, seed=20261020, iterations=80, cap=1000, min_n=30)
    assert analysis["sample_size"] == 204
    confusion = analysis["confusion_matrix"]
    assert (confusion["tn"], confusion["fp"], confusion["fn"], confusion["tp"]) == (91, 11, 31, 71)

    groups = {row["group_value"]: row for row in analysis["groups"][0]["groups"]}
    assert groups["group_a"]["sample_size"] == 100
    assert _by_name(groups["group_a"]["metrics"])["accuracy"]["value"] == pytest.approx(0.80)
    assert _by_name(groups["group_b"]["metrics"])["fpr"]["value"] == 0.0
    assert groups["group_c"]["suppressed"] is True
    assert groups["group_c"]["sample_size"] == 4
    assert _by_name(groups["group_c"]["metrics"])["fpr"]["value"] is None
    assert _by_name(groups["group_c"]["metrics"])["accuracy"]["numerator"] is None

    disparities = {item["name"]: item for item in analysis["groups"][0]["disparities"]}
    opportunity = disparities["equal_opportunity_difference"]
    assert opportunity["value"] == pytest.approx(0.20)
    assert opportunity["groups_excluded"] == ["group_c"]
    assert opportunity["groups_included"] == ["group_a", "group_b"]
    # Including the tiny group would pull equal opportunity from 0.20 to 0.30
    # and equalized odds from 0.20 to 0.50. The published figure must not do that.
    assert disparities["equalized_odds_difference"]["value"] == pytest.approx(0.20)
    assert disparities["demographic_parity_difference"]["value"] == pytest.approx(0.20)

    gate = analysis["score_gate"]
    assert gate["enabled"] is True
    assert gate["calibrated"] is False
    assert gate["brier_score"] == pytest.approx(33.75 / 204)
    sklearn_brier = brier_score_loss(prepared.y_true, prepared.score, sample_weight=prepared.weight, pos_label=1)
    assert gate["brier_score"] == pytest.approx(sklearn_brier)
    bins = {round(item["bin_start"], 1): item for item in gate["reliability"]}
    assert bins[0.0]["count"] == 0
    assert bins[0.0]["observed_rate"] is None
    assert bins[0.2]["count"] == 122
    assert bins[0.2]["observed_rate"] == pytest.approx(31 / 122)
    assert bins[0.7]["count"] == 82
    assert bins[0.7]["observed_rate"] == pytest.approx(71 / 82)

    fpr_interval = next(
        item
        for item in analysis["confidence_intervals"]
        if item["metric_name"] == "fpr" and item["group_value"] == "group_b"
    )
    assert fpr_interval["point"] == 0.0
    assert fpr_interval["lower"] == 0.0
    assert fpr_interval["upper"] == 0.0
    withheld = next(
        item
        for item in analysis["confidence_intervals"]
        if item["metric_name"] == "fpr" and item["group_value"] == "group_c"
    )
    assert withheld["lower"] is None
    assert withheld["undefined_reason"] == "small_group"


def test_second_profile_same_error_rates_different_accuracy():
    frame = different_accuracy_similar_error_rates()
    prepared = prepare_frame(frame, MAPPING, max_rows=10_000, min_n=30)
    analysis = compute_analysis(prepared, seed=1, iterations=40, cap=1000, min_n=30)
    groups = {row["group_value"]: row for row in analysis["groups"][0]["groups"]}
    metrics_a = _by_name(groups["group_a"]["metrics"])
    metrics_b = _by_name(groups["group_b"]["metrics"])
    assert metrics_a["recall"]["value"] == pytest.approx(0.90)
    assert metrics_b["recall"]["value"] == pytest.approx(0.90)
    assert metrics_a["fpr"]["value"] == pytest.approx(0.40)
    assert metrics_b["fpr"]["value"] == pytest.approx(0.40)
    assert metrics_a["accuracy"]["value"] == pytest.approx(0.87)
    assert metrics_b["accuracy"]["value"] == pytest.approx(0.63)
    disparities = {item["name"]: item for item in analysis["groups"][0]["disparities"]}
    assert disparities["equal_opportunity_difference"]["value"] == pytest.approx(0.0)
    assert disparities["equalized_odds_difference"]["value"] == pytest.approx(0.0)
    assert disparities["demographic_parity_difference"]["value"] == pytest.approx(0.40)
    assert any("can conflict" in warning for warning in analysis["warnings"])


def test_bootstrap_is_seeded_and_capped():
    frame = similar_accuracy_different_errors()
    prepared = prepare_frame(frame, MAPPING, max_rows=10_000, min_n=30)
    first = compute_analysis(prepared, seed=11, iterations=60, cap=1000, min_n=30)
    second = compute_analysis(prepared, seed=11, iterations=60, cap=1000, min_n=30)
    third = compute_analysis(prepared, seed=12, iterations=60, cap=1000, min_n=30)
    capped = compute_analysis(prepared, seed=11, iterations=5000, cap=80, min_n=30)

    def accuracy_ci(analysis):
        return next(
            item
            for item in analysis["confidence_intervals"]
            if item["metric_name"] == "accuracy" and item["group_column"] is None
        )

    assert accuracy_ci(first)["lower"] == accuracy_ci(second)["lower"]
    assert accuracy_ci(first)["upper"] == accuracy_ci(second)["upper"]
    assert accuracy_ci(first)["seed"] == 11
    assert accuracy_ci(first)["method"] == "percentile"
    assert accuracy_ci(first)["sampling_unit"] == "row"
    assert (accuracy_ci(first)["lower"], accuracy_ci(first)["upper"]) != (
        accuracy_ci(third)["lower"],
        accuracy_ci(third)["upper"],
    )
    assert capped["bootstrap_capped"] is True
    assert capped["bootstrap_iterations"] == 80
    assert accuracy_ci(capped)["iterations"] == 80
    assert any("capped" in warning for warning in capped["warnings"])
