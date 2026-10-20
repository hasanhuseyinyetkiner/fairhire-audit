"""Confusion counts and rates.

Undefined rates are None. A computed zero is a real zero and stays zero.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.domain.definitions import FORMULAS, METRIC_LABELS, OVERALL_METRIC_NAMES, message_for


@dataclass(frozen=True)
class Counts:
    tp: float
    fp: float
    tn: float
    fn: float

    @property
    def n(self) -> float:
        return self.tp + self.fp + self.tn + self.fn

    @property
    def support_positive(self) -> float:
        return self.tp + self.fn

    @property
    def support_negative(self) -> float:
        return self.tn + self.fp

    @property
    def predicted_positive(self) -> float:
        return self.tp + self.fp


def counts_from_arrays(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    sample_weight: np.ndarray | None = None,
) -> Counts:
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    if sample_weight is None:
        weight = np.ones(len(y_true), dtype=float)
    else:
        weight = np.asarray(sample_weight, dtype=float)
    positive = y_true == 1
    predicted = y_pred == 1
    tp = float(weight[positive & predicted].sum())
    fn = float(weight[positive & ~predicted].sum())
    fp = float(weight[~positive & predicted].sum())
    tn = float(weight[~positive & ~predicted].sum())
    return Counts(tp=tp, fp=fp, tn=tn, fn=fn)


def _rate(numerator: float, denominator: float) -> tuple[float | None, str | None]:
    if denominator == 0:
        return None, "undefined_denominator"
    return numerator / denominator, None


def _metric(
    name: str,
    value: float | None,
    numerator: float | None,
    denominator: float | None,
    reason: str | None,
    sample_size: float,
) -> dict:
    return {
        "name": name,
        "label": METRIC_LABELS[name],
        "value": value,
        "numerator": numerator,
        "denominator": denominator,
        "undefined_reason": reason,
        "message": message_for(reason),
        "formula": FORMULAS[name],
        "sample_size": sample_size,
    }


def metrics_from_counts(counts: Counts, *, sample_size: float | None = None) -> list[dict]:
    size = float(counts.n if sample_size is None else sample_size)
    accuracy, accuracy_reason = _rate(counts.tp + counts.tn, counts.n)
    precision, precision_reason = _rate(counts.tp, counts.predicted_positive)
    recall, recall_reason = _rate(counts.tp, counts.support_positive)
    fpr, fpr_reason = _rate(counts.fp, counts.support_negative)
    fnr, fnr_reason = _rate(counts.fn, counts.support_positive)
    tnr, tnr_reason = _rate(counts.tn, counts.support_negative)
    selection, selection_reason = _rate(counts.predicted_positive, counts.n)
    if recall is None or tnr is None:
        balanced: float | None = None
        balanced_reason: str | None = "undefined_denominator"
        balanced_num: float | None = None
        balanced_den: float | None = None
    else:
        balanced = (recall + tnr) / 2
        balanced_reason = None
        balanced_num = recall + tnr
        balanced_den = 2.0

    rows = {
        "accuracy": _metric("accuracy", accuracy, counts.tp + counts.tn, counts.n, accuracy_reason, size),
        "balanced_accuracy": _metric("balanced_accuracy", balanced, balanced_num, balanced_den, balanced_reason, size),
        "precision": _metric(
            "precision",
            precision,
            counts.tp,
            counts.predicted_positive,
            precision_reason,
            size,
        ),
        "recall": _metric("recall", recall, counts.tp, counts.support_positive, recall_reason, size),
        "fpr": _metric("fpr", fpr, counts.fp, counts.support_negative, fpr_reason, size),
        "fnr": _metric("fnr", fnr, counts.fn, counts.support_positive, fnr_reason, size),
        "tnr": _metric("tnr", tnr, counts.tn, counts.support_negative, tnr_reason, size),
        "selection_rate": _metric(
            "selection_rate",
            selection,
            counts.predicted_positive,
            counts.n,
            selection_reason,
            size,
        ),
    }
    return [rows[name] for name in OVERALL_METRIC_NAMES]


def blank_metrics(sample_size: float, reason: str) -> list[dict]:
    """Withhold every rate. Numerators stay hidden so a rate cannot be rebuilt."""
    return [_metric(name, None, None, None, reason, sample_size) for name in OVERALL_METRIC_NAMES]
