"""Adverse impact ratio (AIR / 4/5ths) and pairwise selection contingency tables.

AIR = selection_rate(focal) / selection_rate(reference).

Reference is the eligible group with the highest selection rate (ties broken by
label sort order). The classic 0.80 threshold is reported as a descriptive flag
only — not a legal finding, compliance certificate, or causal claim.

Zero / empty handling (never NaN):
- Zero applicants in either cell group → undefined (`undefined_denominator`).
- Reference selection rate == 0 → undefined (`undefined_denominator`).
- Focal selections == 0 with reference rate > 0 → AIR = 0.0 (defined).
- Both selection rates == 0 → undefined (`undefined_denominator`).

Fisher's exact test is optional descriptive association evidence on the 2×2
selection table (scipy.stats.fisher_exact, two-sided). Cochran–Mantel–Haenszel
across strata is not implemented — see docs/MODEL_CARD.md and docs/LIMITATIONS.md.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.stats import fisher_exact

from app.domain.definitions import FORMULAS, METRIC_LABELS, message_for

FOUR_FIFTHS_THRESHOLD = 0.80


def _finite(value: float | None) -> float | None:
    if value is None:
        return None
    if not math.isfinite(value):
        return None
    return float(value)


def selection_counts(
    y_pred: np.ndarray,
    mask: np.ndarray,
    weight: np.ndarray,
) -> tuple[float, float, float]:
    """Return (selected, not_selected, n) under sample weights for a group mask."""
    w = weight[mask]
    n = float(w.sum())
    selected = float(w[y_pred[mask] == 1].sum())
    not_selected = n - selected
    return selected, not_selected, n


def adverse_impact_ratio(
    focal_rate: float | None,
    reference_rate: float | None,
) -> tuple[float | None, str | None]:
    """Compute AIR with explicit undefined reasons. Never returns NaN."""
    if focal_rate is None or reference_rate is None:
        return None, "undefined_denominator"
    if not math.isfinite(focal_rate) or not math.isfinite(reference_rate):
        return None, "undefined_denominator"
    if reference_rate == 0.0:
        return None, "undefined_denominator"
    if focal_rate == 0.0:
        return 0.0, None
    value = focal_rate / reference_rate
    if not math.isfinite(value):
        return None, "undefined_denominator"
    return float(value), None


def pick_reference(selection_rates: dict[str, float | None]) -> str | None:
    """Highest finite selection rate; ties → lexicographically first label."""
    ranked = [
        (label, rate)
        for label, rate in selection_rates.items()
        if rate is not None and math.isfinite(rate)
    ]
    if not ranked:
        return None
    best_rate = max(rate for _, rate in ranked)
    candidates = sorted(label for label, rate in ranked if rate == best_rate)
    return candidates[0]


def contingency_table(
    *,
    focal_selected: float,
    focal_not_selected: float,
    reference_selected: float,
    reference_not_selected: float,
    focal: str,
    reference: str,
) -> dict[str, Any]:
    return {
        "rows": [focal, reference],
        "columns": ["selected", "not_selected"],
        "matrix": [
            [focal_selected, focal_not_selected],
            [reference_selected, reference_not_selected],
        ],
        "focal_selected": focal_selected,
        "focal_not_selected": focal_not_selected,
        "reference_selected": reference_selected,
        "reference_not_selected": reference_not_selected,
    }


def fisher_on_contingency(
    focal_selected: float,
    focal_not_selected: float,
    reference_selected: float,
    reference_not_selected: float,
) -> dict[str, Any]:
    """Two-sided Fisher exact on integer cell counts. Descriptive only."""
    table = [
        [int(round(focal_selected)), int(round(focal_not_selected))],
        [int(round(reference_selected)), int(round(reference_not_selected))],
    ]
    # Weighted fractional cells → skip rather than invent integers.
    cells = [focal_selected, focal_not_selected, reference_selected, reference_not_selected]
    if any(abs(c - round(c)) > 1e-9 for c in cells):
        return {
            "odds_ratio": None,
            "p_value": None,
            "undefined_reason": "non_integer_weights",
            "message": "Fisher exact skipped because sample weights produced non-integer cells.",
            "method": "scipy.stats.fisher_exact",
            "note": (
                "Descriptive association test on the 2×2 selection table. "
                "Not a legal finding or compliance certificate."
            ),
        }
    if any(c < 0 for c in cells):
        return {
            "odds_ratio": None,
            "p_value": None,
            "undefined_reason": "invalid_counts",
            "message": "Fisher exact skipped because a cell count was negative.",
            "method": "scipy.stats.fisher_exact",
            "note": (
                "Descriptive association test on the 2×2 selection table. "
                "Not a legal finding or compliance certificate."
            ),
        }
    odds, p_value = fisher_exact(table, alternative="two-sided")
    return {
        "odds_ratio": _finite(float(odds)),
        "p_value": _finite(float(p_value)),
        "undefined_reason": None,
        "message": None,
        "method": "scipy.stats.fisher_exact",
        "note": (
            "Descriptive association test on the 2×2 selection table. "
            "Not a legal finding or compliance certificate."
        ),
    }


def build_selection_audit(
    *,
    column: str,
    included: list[str],
    y_pred: np.ndarray,
    labels: np.ndarray,
    weight: np.ndarray,
    selection_rates: dict[str, float | None],
) -> dict[str, Any]:
    """Pairwise AIR vs reference + contingency + Fisher for eligible groups."""
    reference = pick_reference(selection_rates)
    pairs: list[dict[str, Any]] = []
    if reference is None or len(included) < 2:
        return {
            "column": column,
            "reference_group": reference,
            "four_fifths_threshold": FOUR_FIFTHS_THRESHOLD,
            "pairs": pairs,
            "note": (
                "AIR / 4/5ths requires at least two eligible groups with a defined "
                "reference selection rate. Cochran–Mantel–Haenszel across strata is not computed."
            ),
            "cmh_available": False,
            "cmh_note": (
                "Cochran–Mantel–Haenszel is not implemented: the product does not yet "
                "accept a multi-stratum design (e.g. job family × group) required for a "
                "sound CMH estimate. Do not treat its absence as a zero association."
            ),
        }

    ref_mask = labels == reference
    ref_sel, ref_not, ref_n = selection_counts(y_pred, ref_mask, weight)
    ref_rate = selection_rates.get(reference)

    for focal in included:
        if focal == reference:
            continue
        foc_mask = labels == focal
        foc_sel, foc_not, foc_n = selection_counts(y_pred, foc_mask, weight)
        foc_rate = selection_rates.get(focal)
        air, reason = adverse_impact_ratio(foc_rate, ref_rate)
        below = air is not None and air < FOUR_FIFTHS_THRESHOLD
        contingency = contingency_table(
            focal_selected=foc_sel,
            focal_not_selected=foc_not,
            reference_selected=ref_sel,
            reference_not_selected=ref_not,
            focal=focal,
            reference=reference,
        )
        fisher = fisher_on_contingency(foc_sel, foc_not, ref_sel, ref_not)
        pairs.append(
            {
                "name": "adverse_impact_ratio",
                "label": METRIC_LABELS["adverse_impact_ratio"],
                "focal_group": focal,
                "reference_group": reference,
                "value": air,
                "undefined_reason": reason,
                "message": message_for(reason),
                "formula": FORMULAS["adverse_impact_ratio"],
                "four_fifths_threshold": FOUR_FIFTHS_THRESHOLD,
                "below_four_fifths": below,
                "focal_selection_rate": foc_rate,
                "reference_selection_rate": ref_rate,
                "focal_n": foc_n,
                "reference_n": ref_n,
                "contingency": contingency,
                "fisher_exact": fisher,
            }
        )

    return {
        "column": column,
        "reference_group": reference,
        "four_fifths_threshold": FOUR_FIFTHS_THRESHOLD,
        "pairs": pairs,
        "note": (
            "AIR is the focal / reference selection-rate ratio. Reference = highest "
            "eligible selection rate. below_four_fifths is a descriptive 0.80 flag only — "
            "not a legal finding. Cochran–Mantel–Haenszel across strata is not computed."
        ),
        "cmh_available": False,
        "cmh_note": (
            "Cochran–Mantel–Haenszel is not implemented: the product does not yet "
            "accept a multi-stratum design (e.g. job family × group) required for a "
            "sound CMH estimate. Do not treat its absence as a zero association."
        ),
    }
