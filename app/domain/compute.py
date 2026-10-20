"""Assemble overall metrics, Fairlearn disparities, and bootstrap intervals."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from app.domain.bootstrap import bootstrap_intervals, resolve_iterations
from app.domain.definitions import (
    ASSUMPTIONS,
    BRIER_FORMULA,
    CANNOT_CONCLUDE,
    CONFUSION_CONVENTION,
    DISPARITY_NAMES,
    FORMULAS,
    METRIC_LABELS,
    message_for,
)
from app.domain.fairness import (
    assert_matches_metric_frame,
    disparity_values,
    metric_frame_rates,
)
from app.domain.prepare import Prepared
from app.domain.rates import blank_metrics, counts_from_arrays, metrics_from_counts

Progress = Callable[[], None]


def confusion_payload(counts) -> dict:
    return {
        "labels": [0, 1],
        "matrix": [
            [counts.tn, counts.fp],
            [counts.fn, counts.tp],
        ],
        "tn": counts.tn,
        "fp": counts.fp,
        "fn": counts.fn,
        "tp": counts.tp,
        "convention": CONFUSION_CONVENTION,
    }


def _group_blocks(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    groups: dict[str, np.ndarray],
    weight: np.ndarray,
    min_n: int,
    *,
    intersection: bool,
) -> tuple[list[dict], dict[str, list[str]], dict[str, list[str]], dict]:
    columns: list[dict] = []
    eligible: dict[str, list[str]] = {}
    suppressed: dict[str, list[str]] = {}
    points: dict[tuple[str | None, str | None, str], float | None] = {}

    for column, labels in groups.items():
        values = sorted(set(labels.tolist()), key=str)
        frame_rates: dict[str, dict[str, float | None]] | None = None
        group_rows = []
        included: list[str] = []
        excluded: list[str] = []
        for value in values:
            mask = labels == value
            sample_size = int(mask.sum())
            if sample_size < min_n:
                excluded.append(str(value))
                group_rows.append(
                    {
                        "group_column": column,
                        "group_value": str(value),
                        "sample_size": sample_size,
                        "suppressed": True,
                        "suppression_reason": "small_group",
                        "message": message_for("small_group"),
                        "metrics": blank_metrics(sample_size, "small_group"),
                    }
                )
                continue
            included.append(str(value))
            counts = counts_from_arrays(y_true[mask], y_pred[mask], weight[mask])
            metrics = metrics_from_counts(counts, sample_size=sample_size)
            group_rows.append(
                {
                    "group_column": column,
                    "group_value": str(value),
                    "sample_size": sample_size,
                    "suppressed": False,
                    "suppression_reason": None,
                    "message": None,
                    "metrics": metrics,
                    "_mask_value": str(value),
                }
            )
            for metric in metrics:
                points[(column, str(value), metric["name"])] = metric["value"]

        if included:
            eligible_mask = np.isin(labels, np.array(included, dtype=object))
            frame_rates = metric_frame_rates(
                y_true[eligible_mask],
                y_pred[eligible_mask],
                labels[eligible_mask],
                weight[eligible_mask],
            )
            for row in group_rows:
                if row["suppressed"]:
                    continue
                fairlearn_row = frame_rates.get(row["group_value"], {})
                counted = fairlearn_row.get("count")
                if counted is not None and int(counted) != row["sample_size"]:
                    raise RuntimeError("Fairlearn group count disagreed with the row count.")
                for metric in row["metrics"]:
                    if metric["name"] not in ("selection_rate", "recall", "fpr", "fnr"):
                        continue
                    assert_matches_metric_frame(
                        metric["value"],
                        fairlearn_row.get(metric["name"]),
                        denominator=metric["denominator"],
                    )
        for row in group_rows:
            row.pop("_mask_value", None)

        disparities = _disparities(y_true, y_pred, labels, weight, included, excluded, column, points)
        eligible[column] = included
        suppressed[column] = excluded
        columns.append(
            {
                "column": column,
                "intersection": intersection,
                "groups": group_rows,
                "disparities": disparities,
            }
        )
    return columns, eligible, suppressed, points


def _disparities(y_true, y_pred, labels, weight, included, excluded, column, points) -> list[dict]:
    rows = []
    if len(included) < 2:
        for name in DISPARITY_NAMES:
            points[(column, None, name)] = None
            rows.append(
                {
                    "name": name,
                    "label": METRIC_LABELS[name],
                    "value": None,
                    "undefined_reason": "fewer_than_two_eligible_groups",
                    "message": message_for("fewer_than_two_eligible_groups"),
                    "formula": FORMULAS[name],
                    "method": "fairlearn",
                    "groups_included": included,
                    "groups_excluded": excluded,
                }
            )
        return rows
    mask = np.isin(labels, np.array(included, dtype=object))
    values = disparity_values(y_true[mask], y_pred[mask], labels[mask], weight[mask])
    for name in DISPARITY_NAMES:
        value, reason = values[name]
        points[(column, None, name)] = value
        rows.append(
            {
                "name": name,
                "label": METRIC_LABELS[name],
                "value": value,
                "undefined_reason": reason,
                "message": message_for(reason),
                "formula": FORMULAS[name],
                "method": "fairlearn",
                "groups_included": included,
                "groups_excluded": excluded,
            }
        )
    return rows


def _conflict_warning(disparities: list[dict]) -> str | None:
    defined = [(item["label"], item["value"]) for item in disparities if item["value"] is not None]
    if len(defined) < 2:
        return None
    zeros = [label for label, value in defined if abs(value) < 1e-12]
    nonzeros = [label for label, value in defined if abs(value) >= 1e-12]
    if zeros and nonzeros:
        return (
            f"{', '.join(zeros)} is zero while {', '.join(nonzeros)} is not. "
            "Fairness criteria can conflict. A zero is not a certificate, and a "
            "nonzero difference is not a legal finding."
        )
    return None


def score_gate(prepared: Prepared) -> dict:
    score = prepared.score
    semantics = prepared.score_semantics
    if score is None or semantics is None:
        reason = (
            "Threshold Lab is closed. Map a numeric score and declare it as probability or ranking_score."
            if score is None
            else "Threshold Lab is closed until the score semantic is declared."
        )
        return _gate(False, semantics, reason, None, None)
    if semantics == "probability":
        if np.any(score < 0) or np.any(score > 1):
            return _gate(
                False,
                semantics,
                "Threshold Lab is closed. Declared probabilities must lie in [0, 1].",
                None,
                None,
            )
        brier = float(np.average((score - prepared.y_true) ** 2, weights=prepared.weight))
        return _gate(
            True,
            semantics,
            (
                "Threshold Lab is open because the score column is numeric, you declared "
                "it as a probability, and every value lies in [0, 1]. Declaring a "
                "probability is not a calibration result. The Brier score and reliability "
                "table are descriptive only. This system does not label the score calibrated."
            ),
            brier,
            reliability_table(prepared.y_true, score, prepared.weight),
        )
    if semantics == "ranking_score":
        return _gate(
            True,
            semantics,
            (
                "Threshold Lab is open because the score column is numeric and you "
                "declared it as a ranking score. A ranking score is not a probability. "
                "The lab simulates a cutoff. It does not show calibration and it does "
                "not deploy a decision."
            ),
            None,
            None,
        )
    return _gate(False, semantics, "Threshold Lab is closed.", None, None)


def _gate(enabled: bool, semantics, reason: str, brier, reliability) -> dict:
    return {
        "enabled": enabled,
        "semantics": semantics,
        "reason": reason,
        "brier_score": brier,
        "brier_formula": BRIER_FORMULA,
        "reliability": reliability,
        "calibrated": False,
    }


def reliability_table(y_true: np.ndarray, score: np.ndarray, weight: np.ndarray) -> list[dict]:
    edges = np.linspace(0.0, 1.0, 11)
    indexes = np.digitize(score, edges[1:-1], right=False)
    rows = []
    for index in range(10):
        mask = indexes == index
        count = int(mask.sum())
        start = float(edges[index])
        end = float(edges[index + 1])
        if count == 0:
            rows.append(
                {
                    "bin_start": start,
                    "bin_end": end,
                    "count": 0,
                    "mean_predicted": None,
                    "observed_rate": None,
                    "undefined_reason": "empty_bin",
                    "message": message_for("empty_bin"),
                    "small_bin": False,
                }
            )
            continue
        mean_predicted = float(np.average(score[mask], weights=weight[mask]))
        observed = float(np.average(y_true[mask], weights=weight[mask]))
        small = count < 5
        rows.append(
            {
                "bin_start": start,
                "bin_end": end,
                "count": count,
                "mean_predicted": mean_predicted,
                "observed_rate": observed,
                "undefined_reason": "small_bin" if small else None,
                "message": message_for("small_bin") if small else None,
                "small_bin": small,
            }
        )
    return rows


def _comparison(prepared: Prepared) -> dict:
    if prepared.y_pred_alt is None:
        return {
            "available": False,
            "reason": "No second prediction column was mapped.",
            "metrics": [],
            "deltas": [],
        }
    primary_counts = counts_from_arrays(prepared.y_true, prepared.y_pred, prepared.weight)
    alternate_counts = counts_from_arrays(prepared.y_true, prepared.y_pred_alt, prepared.weight)
    primary = metrics_from_counts(primary_counts, sample_size=prepared.row_count)
    alternate = metrics_from_counts(alternate_counts, sample_size=prepared.row_count)
    deltas = []
    for left, right in zip(primary, alternate, strict=True):
        if left["value"] is None or right["value"] is None:
            delta = None
            reason = "comparison_undefined"
        else:
            delta = left["value"] - right["value"]
            reason = None
        deltas.append(
            {
                "name": left["name"],
                "label": left["label"],
                "primary": left["value"],
                "alternate": right["value"],
                "delta": delta,
                "undefined_reason": reason,
                "message": message_for(reason),
                "formula": "Primary rate minus alternate rate, on the same rows and labels.",
            }
        )
    return {
        "available": True,
        "reason": (
            "Both prediction columns were scored on the same rows. "
            "Delta is primary minus alternate. This is not a model-selection decision."
        ),
        "metrics": alternate,
        "deltas": deltas,
    }


def apply_threshold(prepared: Prepared, threshold: float, *, min_n: int) -> dict:
    if prepared.score is None or not score_gate(prepared)["enabled"]:
        raise ValueError("threshold_closed")
    predicted = (prepared.score >= threshold).astype(int)
    altered = Prepared(
        y_true=prepared.y_true,
        y_pred=predicted,
        y_pred_alt=None,
        score=prepared.score,
        weight=prepared.weight,
        groups=prepared.groups,
        score_semantics=prepared.score_semantics,
        positive_label=prepared.positive_label,
        warnings=[],
        derived_prediction=True,
        row_count=prepared.row_count,
    )
    analysis = compute_analysis(
        altered,
        seed=0,
        iterations=1,
        cap=1,
        min_n=min_n,
        with_bootstrap=False,
    )
    return analysis


def compute_analysis(
    prepared: Prepared,
    *,
    seed: int,
    iterations: int,
    cap: int,
    min_n: int,
    on_progress: Progress | None = None,
    with_bootstrap: bool = True,
    intersection_labels: dict[str, np.ndarray] | None = None,
) -> dict:
    used, capped = resolve_iterations(iterations, cap) if with_bootstrap else (0, False)
    counts = counts_from_arrays(prepared.y_true, prepared.y_pred, prepared.weight)
    metrics = metrics_from_counts(counts, sample_size=prepared.row_count)
    group_source = intersection_labels if intersection_labels is not None else prepared.groups
    columns, eligible, suppressed_map, points = _group_blocks(
        prepared.y_true,
        prepared.y_pred,
        group_source,
        prepared.weight,
        min_n,
        intersection=intersection_labels is not None,
    )
    for metric in metrics:
        points[(None, None, metric["name"])] = metric["value"]

    warnings = list(prepared.warnings)
    if capped:
        warnings.append(f"Bootstrap iterations were capped at {cap}. {iterations} were requested and {used} were run.")
    for column in columns:
        conflict = _conflict_warning(column["disparities"])
        if conflict:
            warnings.append(conflict)
        if any(group["suppressed"] for group in column["groups"]):
            warnings.append(
                f"Column '{column['column']}' has suppressed levels. "
                "Disparity summaries skip them. Skipping them is not the same as a zero rate."
            )

    intervals: list[dict] = []
    if with_bootstrap:
        intervals = bootstrap_intervals(
            prepared.y_true,
            prepared.y_pred,
            prepared.weight,
            group_source,
            points=points,
            eligible=eligible,
            suppressed=suppressed_map,
            seed=seed,
            iterations=used,
            iterations_requested=iterations,
            capped=capped,
            on_progress=on_progress,
        )

    return {
        "sample_size": prepared.row_count,
        "confusion_matrix": confusion_payload(counts),
        "metrics": metrics,
        "comparison": _comparison(prepared),
        "groups": columns,
        "confidence_intervals": intervals,
        "score_gate": score_gate(prepared),
        "warnings": warnings,
        "assumptions": list(ASSUMPTIONS),
        "cannot_conclude": list(CANNOT_CONCLUDE),
        "bootstrap_iterations": used,
        "bootstrap_iterations_requested": iterations if with_bootstrap else 0,
        "bootstrap_capped": capped,
    }
