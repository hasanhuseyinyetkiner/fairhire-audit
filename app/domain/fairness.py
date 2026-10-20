"""Fairlearn 0.15 wrappers.

Point estimates for disparity summaries come from Fairlearn. Group rates are
computed from explicit counts and checked against MetricFrame. A disagreement
raises. A non-finite Fairlearn value is withheld, not replaced with zero.
"""

from __future__ import annotations

import math

import numpy as np
from fairlearn.metrics import (
    MetricFrame,
    count,
    demographic_parity_difference,
    equal_opportunity_difference,
    equalized_odds_difference,
    false_negative_rate,
    false_positive_rate,
    selection_rate,
    true_positive_rate,
)

FAIRLEARN_RATE_NAMES = {
    "selection_rate": selection_rate,
    "recall": true_positive_rate,
    "fpr": false_positive_rate,
    "fnr": false_negative_rate,
}


class FairlearnMismatch(RuntimeError):
    """Our count-based rate and Fairlearn MetricFrame disagreed."""


def _finite(value: object) -> float | None:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def metric_frame_rates(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    sensitive: np.ndarray,
    sample_weight: np.ndarray,
) -> dict[str, dict[str, float | None]]:
    """Return {group_value: {metric_name: rate or None, 'count': n}}."""
    # pos_label stays at the Fairlearn default. For {0, 1} labels that default is 1.
    # Do not put pos_label in sample_params: MetricFrame broadcasts it into a column.
    sample_params = {name: {"sample_weight": sample_weight} for name in FAIRLEARN_RATE_NAMES}
    frame = MetricFrame(
        metrics={**FAIRLEARN_RATE_NAMES, "count": count},
        y_true=y_true,
        y_pred=y_pred,
        sensitive_features=sensitive,
        sample_params=sample_params,
    )
    table = frame.by_group
    out: dict[str, dict[str, float | None]] = {}
    for raw_index in table.index:
        label = str(raw_index)
        row: dict[str, float | None] = {}
        for name in (*FAIRLEARN_RATE_NAMES, "count"):
            row[name] = _finite(table.loc[raw_index, name])
        out[label] = row
    return out


def _call(fn, y_true, y_pred, sensitive, sample_weight) -> tuple[float | None, str | None]:
    kwargs = {
        "sensitive_features": sensitive,
        "method": "between_groups",
        "sample_weight": sample_weight,
    }
    if fn is equalized_odds_difference:
        kwargs["agg"] = "worst_case"
    try:
        value = fn(y_true, y_pred, **kwargs)
    except Exception as exc:
        raise RuntimeError(f"Fairlearn {fn.__name__} failed: {type(exc).__name__}") from exc
    number = _finite(value)
    if number is None:
        return None, "fairlearn_undefined"
    return number, None


def disparity_values(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    sensitive: np.ndarray,
    sample_weight: np.ndarray,
) -> dict[str, tuple[float | None, str | None]]:
    return {
        "demographic_parity_difference": _call(demographic_parity_difference, y_true, y_pred, sensitive, sample_weight),
        "equal_opportunity_difference": _call(equal_opportunity_difference, y_true, y_pred, sensitive, sample_weight),
        "equalized_odds_difference": _call(equalized_odds_difference, y_true, y_pred, sensitive, sample_weight),
    }


def assert_matches_metric_frame(
    our_value: float | None,
    fairlearn_value: float | None,
    *,
    denominator: float | None,
) -> None:
    """When the denominator is positive, the two implementations must agree."""
    if denominator is None or denominator == 0:
        return
    if our_value is None or fairlearn_value is None:
        raise FairlearnMismatch("A defined rate was missing from one implementation.")
    if not math.isclose(our_value, fairlearn_value, rel_tol=1e-8, abs_tol=1e-8):
        raise FairlearnMismatch("A group rate disagreed with Fairlearn MetricFrame.")
