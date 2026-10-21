"""Statistical edge cases: zero denominators, tiny/empty groups, bootstrap degeneracy."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from app.domain.air import adverse_impact_ratio, build_selection_audit
from app.domain.bootstrap import _interval, bootstrap_intervals
from app.domain.compute import compute_analysis, confusion_payload
from app.domain.definitions import MIN_FINITE_REPLICATES, OVERALL_METRIC_NAMES
from app.domain.prepare import prepare_frame
from app.domain.rates import Counts, blank_metrics, counts_from_arrays, metrics_from_counts
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


def _by_name(metrics):
    return {metric["name"]: metric for metric in metrics}


def test_zero_n_all_rates_undefined_not_nan_or_zero():
    metrics = _by_name(metrics_from_counts(Counts(tp=0, fp=0, tn=0, fn=0)))
    for name in OVERALL_METRIC_NAMES:
        row = metrics[name]
        assert row["value"] is None, name
        assert row["undefined_reason"] == "undefined_denominator", name
        assert row["message"] and "not a zero" in row["message"].lower()


def test_no_predicted_positives_precision_undefined_selection_real_zero():
    y_true = np.array([1, 1, 0, 0], dtype=int)
    y_pred = np.array([0, 0, 0, 0], dtype=int)
    metrics = _by_name(metrics_from_counts(counts_from_arrays(y_true, y_pred)))
    assert metrics["selection_rate"]["value"] == 0.0
    assert metrics["selection_rate"]["undefined_reason"] is None
    assert metrics["precision"]["value"] is None
    assert metrics["precision"]["undefined_reason"] == "undefined_denominator"
    assert metrics["recall"]["value"] == 0.0
    assert metrics["fnr"]["value"] == 1.0


def test_no_positives_recall_fnr_undefined_fpr_defined():
    y_true = np.zeros(5, dtype=int)
    y_pred = np.array([1, 0, 0, 0, 0], dtype=int)
    metrics = _by_name(metrics_from_counts(counts_from_arrays(y_true, y_pred)))
    assert metrics["recall"]["value"] is None
    assert metrics["fnr"]["value"] is None
    assert metrics["recall"]["undefined_reason"] == "undefined_denominator"
    assert metrics["fpr"]["value"] == pytest.approx(0.2)
    assert metrics["selection_rate"]["value"] == pytest.approx(0.2)
    assert metrics["balanced_accuracy"]["value"] is None


def test_no_negatives_fpr_tnr_undefined_recall_real_one():
    y_true = np.ones(4, dtype=int)
    y_pred = np.ones(4, dtype=int)
    metrics = _by_name(metrics_from_counts(counts_from_arrays(y_true, y_pred)))
    assert metrics["fpr"]["value"] is None
    assert metrics["tnr"]["value"] is None
    assert metrics["fpr"]["undefined_reason"] == "undefined_denominator"
    assert metrics["recall"]["value"] == 1.0
    assert metrics["fnr"]["value"] == 0.0
    assert metrics["selection_rate"]["value"] == 1.0


def test_blank_metrics_hide_numerators():
    rows = blank_metrics(sample_size=3, reason="small_group")
    assert len(rows) == len(OVERALL_METRIC_NAMES)
    for row in rows:
        assert row["value"] is None
        assert row["numerator"] is None
        assert row["denominator"] is None
        assert row["undefined_reason"] == "small_group"
        assert row["sample_size"] == 3


def test_tiny_group_n4_suppressed_rates_null_not_zero():
    frame = similar_accuracy_different_errors()
    prepared = prepare_frame(frame, MAPPING, max_rows=10_000, min_n=30)
    analysis = compute_analysis(prepared, seed=7, iterations=40, cap=1000, min_n=30)
    groups = {row["group_value"]: row for row in analysis["groups"][0]["groups"]}
    tiny = groups["group_c"]
    assert tiny["sample_size"] == 4
    assert tiny["sample_size"] <= 4
    assert tiny["suppressed"] is True
    for metric in tiny["metrics"]:
        assert metric["value"] is None
        assert metric["undefined_reason"] == "small_group"
        assert metric["numerator"] is None
        assert metric["denominator"] is None


def test_fewer_than_two_eligible_groups_disparities_undefined():
    # Two labels, but only one meets min_n=5 (other has n=3).
    y_true = np.array([1, 0, 1, 0, 1, 1, 0, 0], dtype=int)
    y_pred = np.array([1, 0, 1, 1, 0, 1, 0, 0], dtype=int)
    group = np.array(["big"] * 5 + ["tiny"] * 3, dtype=object)
    weight = np.ones(8)
    frame = pd.DataFrame(
        {
            "y_true": y_true,
            "y_pred": y_pred,
            "score": np.linspace(0.1, 0.9, 8),
            "group": group,
            "sample_weight": weight,
        }
    )
    prepared = prepare_frame(frame, MAPPING, max_rows=10_000, min_n=5)
    analysis = compute_analysis(prepared, seed=1, iterations=20, cap=1000, min_n=5)
    column = analysis["groups"][0]
    groups = {row["group_value"]: row for row in column["groups"]}
    assert groups["tiny"]["suppressed"] is True
    assert groups["big"]["suppressed"] is False
    for disparity in column["disparities"]:
        assert disparity["value"] is None
        assert disparity["undefined_reason"] == "fewer_than_two_eligible_groups"
    assert column["selection_audit"]["pairs"] == []


def test_empty_weight_group_yields_undefined_air_not_nan():
    # Label "empty" is listed but has zero weight → n=0; AIR stays undefined.
    y_pred = np.array([1, 0, 1, 0], dtype=int)
    labels = np.array(["a", "a", "empty", "empty"], dtype=object)
    weight = np.array([1.0, 1.0, 0.0, 0.0])
    audit = build_selection_audit(
        column="group",
        included=["a", "empty"],
        y_pred=y_pred,
        labels=labels,
        weight=weight,
        selection_rates={"a": 0.5, "empty": None},
    )
    assert audit["reference_group"] == "a"
    pair = audit["pairs"][0]
    assert pair["focal_group"] == "empty"
    assert pair["value"] is None
    assert pair["undefined_reason"] == "undefined_denominator"
    assert pair["below_four_fifths"] is False
    assert pair["focal_n"] == 0.0


def test_bootstrap_interval_degeneracy_too_few_finite():
    """Direct gate: fewer than MIN_FINITE_REPLICATES finite draws → withhold bounds."""
    all_nan = np.full(80, np.nan)
    lower, upper, valid, reason = _interval(all_nan)
    assert lower is None and upper is None
    assert valid == 0
    assert reason == "too_few_finite_replicates"

    sparse = np.array([0.1] * (MIN_FINITE_REPLICATES - 1) + [np.nan] * 40)
    lower, upper, valid, reason = _interval(sparse)
    assert valid == MIN_FINITE_REPLICATES - 1
    assert reason == "too_few_finite_replicates"
    assert lower is None and upper is None

    enough = np.array([0.1] * MIN_FINITE_REPLICATES + [np.nan] * 10)
    lower, upper, valid, reason = _interval(enough)
    assert valid == MIN_FINITE_REPLICATES
    assert reason is None
    assert lower is not None and upper is not None


def test_tiny_sample_bootstrap_honesty_wide_or_withheld():
    """n=8 overall: CIs must stay honest — either wide or withheld, never fake precision."""
    y_true = np.array([1, 1, 1, 0, 0, 0, 1, 0], dtype=int)
    y_pred = np.array([1, 0, 1, 0, 1, 0, 1, 0], dtype=int)
    weight = np.ones(8)
    group = np.array(["a", "a", "a", "a", "b", "b", "b", "b"], dtype=object)
    frame = pd.DataFrame(
        {
            "y_true": y_true,
            "y_pred": y_pred,
            "score": np.linspace(0.2, 0.9, 8),
            "group": group,
            "sample_weight": weight,
        }
    )
    prepared = prepare_frame(frame, MAPPING, max_rows=10_000, min_n=4)
    analysis = compute_analysis(prepared, seed=20261020, iterations=80, cap=1000, min_n=4)
    overall_acc = next(
        item
        for item in analysis["confidence_intervals"]
        if item["metric_name"] == "accuracy" and item["group_column"] is None
    )
    if overall_acc["lower"] is None or overall_acc["upper"] is None:
        assert overall_acc["undefined_reason"] in {
            "too_few_finite_replicates",
            "undefined_denominator",
        }
    else:
        width = overall_acc["upper"] - overall_acc["lower"]
        # Tiny n must not report a near-delta CI that implies false certainty.
        assert width >= 0.05
    for group_row in analysis["groups"][0]["groups"]:
        if group_row["sample_size"] < 4:
            assert group_row["suppressed"] is True
            for metric in group_row["metrics"]:
                assert metric["value"] is None
                assert metric["undefined_reason"] == "small_group"


def test_bootstrap_point_none_forces_undefined_not_fake_zero():
    n = 20
    y_true = np.ones(n, dtype=int)
    y_pred = np.ones(n, dtype=int)
    weight = np.ones(n)
    groups = {"g": np.full(n, "only", dtype=object)}
    # Overall FPR is undefined (no negatives); point is None.
    points = {
        (None, None, "fpr"): None,
        (None, None, "accuracy"): 1.0,
        (None, None, "balanced_accuracy"): None,
        (None, None, "precision"): 1.0,
        (None, None, "recall"): 1.0,
        (None, None, "fnr"): 0.0,
        (None, None, "selection_rate"): 1.0,
        ("g", "only", "fpr"): None,
        ("g", "only", "accuracy"): 1.0,
        ("g", "only", "balanced_accuracy"): None,
        ("g", "only", "precision"): 1.0,
        ("g", "only", "recall"): 1.0,
        ("g", "only", "fnr"): 0.0,
        ("g", "only", "selection_rate"): 1.0,
        ("g", None, "demographic_parity_difference"): None,
        ("g", None, "equal_opportunity_difference"): None,
        ("g", None, "equalized_odds_difference"): None,
    }
    records = bootstrap_intervals(
        y_true,
        y_pred,
        weight,
        groups,
        points=points,
        eligible={"g": ["only"]},
        suppressed={"g": []},
        seed=3,
        iterations=60,
        iterations_requested=60,
        capped=False,
    )
    fpr_ci = next(
        item for item in records if item["metric_name"] == "fpr" and item["group_column"] is None
    )
    assert fpr_ci["point"] is None
    assert fpr_ci["lower"] is None
    assert fpr_ci["upper"] is None
    assert fpr_ci["undefined_reason"] == "undefined_denominator"
    assert fpr_ci["valid_replicates"] == 0


def test_golden_confusion_selection_rate_and_air():
    """Independent hand counts for confusion, selection rate, and AIR."""
    # idx:  0  1  2  3  4  5  6
    # grp:  A  A  A  B  B  B  B
    # true: 1  1  0  0  0  1  0
    # pred: 1  1  0  1  0  0  0
    # TN=3, FP=1, FN=1, TP=2; A sel=2/3; B sel=1/4; AIR=(1/4)/(2/3)=0.375
    y_true = np.array([1, 1, 0, 0, 0, 1, 0], dtype=int)
    y_pred = np.array([1, 1, 0, 1, 0, 0, 0], dtype=int)
    labels = np.array(["A", "A", "A", "B", "B", "B", "B"], dtype=object)
    weight = np.ones(7)

    counts = counts_from_arrays(y_true, y_pred)
    assert (counts.tn, counts.fp, counts.fn, counts.tp) == (3, 1, 1, 2)
    payload = confusion_payload(counts)
    assert payload["matrix"] == [[3, 1], [1, 2]]
    assert payload["tn"] == 3 and payload["tp"] == 2

    metrics = _by_name(metrics_from_counts(counts))
    assert metrics["selection_rate"]["value"] == pytest.approx(3 / 7)
    assert metrics["selection_rate"]["numerator"] == pytest.approx(3)
    assert metrics["selection_rate"]["denominator"] == pytest.approx(7)
    assert metrics["recall"]["value"] == pytest.approx(2 / 3)
    assert metrics["precision"]["value"] == pytest.approx(2 / 3)
    assert metrics["accuracy"]["value"] == pytest.approx(5 / 7)

    rate_a = 2 / 3
    rate_b = 1 / 4
    air, reason = adverse_impact_ratio(rate_b, rate_a)
    assert reason is None
    assert air == pytest.approx(0.375)
    assert air < 0.80

    audit = build_selection_audit(
        column="group",
        included=["A", "B"],
        y_pred=y_pred,
        labels=labels,
        weight=weight,
        selection_rates={"A": rate_a, "B": rate_b},
    )
    assert audit["reference_group"] == "A"
    pair = audit["pairs"][0]
    assert pair["focal_group"] == "B"
    assert pair["value"] == pytest.approx(0.375)
    assert pair["below_four_fifths"] is True
    assert pair["focal_selection_rate"] == pytest.approx(rate_b)
    assert pair["reference_selection_rate"] == pytest.approx(rate_a)
    assert pair["contingency"]["matrix"] == [[1.0, 3.0], [2.0, 1.0]]
