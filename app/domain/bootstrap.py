"""Seeded, capped, row-level percentile bootstrap.

The sampling unit is the row. One NumPy Generator draw is shared by every
metric in the run. Percentiles use scipy.stats.scoreatpercentile.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from scipy.stats import scoreatpercentile

from app.domain.definitions import (
    BOOTSTRAP_CONFIDENCE,
    BOOTSTRAP_METHOD,
    BOOTSTRAP_SAMPLING_UNIT,
    CI_METRIC_NAMES,
    DISPARITY_NAMES,
    METRIC_LABELS,
    MIN_FINITE_REPLICATES,
    message_for,
)

Progress = Callable[[], None]


def _div(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    out = np.full(numerator.shape, np.nan, dtype=float)
    ok = denominator > 0
    out[ok] = numerator[ok] / denominator[ok]
    return out


def _counts(y_true: np.ndarray, y_pred: np.ndarray, weight: np.ndarray) -> tuple[np.ndarray, ...]:
    positive = y_true == 1
    predicted = y_pred == 1
    tp = (weight * (positive & predicted)).sum(axis=1)
    fn = (weight * (positive & ~predicted)).sum(axis=1)
    fp = (weight * (~positive & predicted)).sum(axis=1)
    tn = (weight * (~positive & ~predicted)).sum(axis=1)
    return tp, fp, tn, fn


def _rate_samples(tp, fp, tn, fn) -> dict[str, np.ndarray]:
    n = tp + fp + tn + fn
    recall = _div(tp, tp + fn)
    tnr = _div(tn, tn + fp)
    balanced = np.where(np.isfinite(recall) & np.isfinite(tnr), (recall + tnr) / 2, np.nan)
    return {
        "accuracy": _div(tp + tn, n),
        "balanced_accuracy": balanced,
        "precision": _div(tp, tp + fp),
        "recall": recall,
        "fpr": _div(fp, fp + tn),
        "fnr": _div(fn, fn + tp),
        "selection_rate": _div(tp + fp, n),
    }


def _max_minus_min(stack: np.ndarray) -> np.ndarray:
    finite = np.isfinite(stack)
    count = finite.sum(axis=0)
    safe_max = np.where(finite, stack, -np.inf).max(axis=0)
    safe_min = np.where(finite, stack, np.inf).min(axis=0)
    diff = safe_max - safe_min
    diff = np.where(count >= 2, diff, np.nan)
    return diff


def _interval(samples: np.ndarray) -> tuple[float | None, float | None, int, str | None]:
    clean = samples[np.isfinite(samples)]
    valid = int(clean.size)
    if valid < MIN_FINITE_REPLICATES:
        return None, None, valid, "too_few_finite_replicates"
    lower, upper = scoreatpercentile(clean, [2.5, 97.5])
    return float(lower), float(upper), valid, None


def _record(
    *,
    metric_name: str,
    group_column: str | None,
    group_value: str | None,
    point: float | None,
    samples: np.ndarray | None,
    iterations: int,
    iterations_requested: int,
    capped: bool,
    seed: int,
    forced_reason: str | None = None,
) -> dict:
    if forced_reason is not None or point is None or samples is None:
        reason = forced_reason or "undefined_denominator"
        lower = upper = None
        valid = 0
    else:
        lower, upper, valid, reason = _interval(samples)
    return {
        "metric_name": metric_name,
        "label": METRIC_LABELS[metric_name],
        "group_column": group_column,
        "group_value": group_value,
        "point": point,
        "lower": lower,
        "upper": upper,
        "iterations": iterations,
        "iterations_requested": iterations_requested,
        "capped": capped,
        "valid_replicates": valid,
        "seed": seed,
        "method": BOOTSTRAP_METHOD,
        "sampling_unit": BOOTSTRAP_SAMPLING_UNIT,
        "confidence": BOOTSTRAP_CONFIDENCE,
        "undefined_reason": reason,
        "message": message_for(reason),
    }


def resolve_iterations(requested: int, cap: int) -> tuple[int, bool]:
    if requested < 1:
        raise ValueError("Bootstrap iterations must be at least 1.")
    if cap < 1:
        raise ValueError("Bootstrap cap must be at least 1.")
    used = min(requested, cap)
    return used, requested > cap


def bootstrap_intervals(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    weight: np.ndarray,
    groups: dict[str, np.ndarray],
    *,
    points: dict[tuple[str | None, str | None, str], float | None],
    eligible: dict[str, list[str]],
    suppressed: dict[str, list[str]],
    seed: int,
    iterations: int,
    iterations_requested: int,
    capped: bool,
    on_progress: Progress | None = None,
    chunk_size: int = 100,
) -> list[dict]:
    """points key is (group_column or None, group_value or None, metric_name)."""
    rng = np.random.default_rng(seed)
    n = int(len(y_true))
    overall_samples = {name: np.full(iterations, np.nan) for name in CI_METRIC_NAMES}
    group_samples: dict[tuple[str, str, str], np.ndarray] = {}
    for column, values in eligible.items():
        for value in values:
            for name in CI_METRIC_NAMES:
                group_samples[(column, value, name)] = np.full(iterations, np.nan)
    disparity_samples = {(column, name): np.full(iterations, np.nan) for column in eligible for name in DISPARITY_NAMES}

    position = 0
    while position < iterations:
        size = min(chunk_size, iterations - position)
        index = rng.integers(0, n, size=(size, n))
        yt = y_true[index]
        yp = y_pred[index]
        w = weight[index]
        overall = _rate_samples(*_counts(yt, yp, w))
        for name in CI_METRIC_NAMES:
            overall_samples[name][position : position + size] = overall[name]

        for column, values in groups.items():
            grown = values[index]
            eligible_values = eligible.get(column, [])
            sel_rows = []
            tpr_rows = []
            fpr_rows = []
            for value in eligible_values:
                mask = grown == value
                tp, fp, tn, fn = _counts(yt, yp, w * mask)
                rates = _rate_samples(tp, fp, tn, fn)
                for name in CI_METRIC_NAMES:
                    group_samples[(column, value, name)][position : position + size] = rates[name]
                sel_rows.append(rates["selection_rate"])
                tpr_rows.append(rates["recall"])
                fpr_rows.append(rates["fpr"])
            if eligible_values:
                selection_diff = _max_minus_min(np.vstack(sel_rows))
                tpr_diff = _max_minus_min(np.vstack(tpr_rows))
                fpr_diff = _max_minus_min(np.vstack(fpr_rows))
                eod = np.where(
                    np.isfinite(tpr_diff) & np.isfinite(fpr_diff),
                    np.maximum(tpr_diff, fpr_diff),
                    np.nan,
                )
                disparity_samples[(column, "demographic_parity_difference")][position : position + size] = (
                    selection_diff
                )
                disparity_samples[(column, "equal_opportunity_difference")][position : position + size] = tpr_diff
                disparity_samples[(column, "equalized_odds_difference")][position : position + size] = eod
        position += size
        if on_progress is not None:
            on_progress()

    records: list[dict] = []
    for name in CI_METRIC_NAMES:
        records.append(
            _record(
                metric_name=name,
                group_column=None,
                group_value=None,
                point=points.get((None, None, name)),
                samples=overall_samples[name],
                iterations=iterations,
                iterations_requested=iterations_requested,
                capped=capped,
                seed=seed,
            )
        )
    for column, values in eligible.items():
        for value in values:
            for name in CI_METRIC_NAMES:
                records.append(
                    _record(
                        metric_name=name,
                        group_column=column,
                        group_value=value,
                        point=points.get((column, value, name)),
                        samples=group_samples[(column, value, name)],
                        iterations=iterations,
                        iterations_requested=iterations_requested,
                        capped=capped,
                        seed=seed,
                    )
                )
        for name in DISPARITY_NAMES:
            records.append(
                _record(
                    metric_name=name,
                    group_column=column,
                    group_value=None,
                    point=points.get((column, None, name)),
                    samples=disparity_samples[(column, name)],
                    iterations=iterations,
                    iterations_requested=iterations_requested,
                    capped=capped,
                    seed=seed,
                )
            )
    for column, values in suppressed.items():
        for value in values:
            for name in CI_METRIC_NAMES:
                records.append(
                    _record(
                        metric_name=name,
                        group_column=column,
                        group_value=value,
                        point=None,
                        samples=None,
                        iterations=iterations,
                        iterations_requested=iterations_requested,
                        capped=capped,
                        seed=seed,
                        forced_reason="small_group",
                    )
                )
    return records
