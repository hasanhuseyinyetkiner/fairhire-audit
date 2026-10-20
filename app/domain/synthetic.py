"""Deterministic synthetic evaluation tables. No names and no personal data."""

from __future__ import annotations

import numpy as np
import pandas as pd

PROFILES: dict[str, dict[str, str]] = {
    "similar_accuracy_different_errors": {
        "title": "Similar accuracy, different error rates",
        "description": (
            "Synthetic rows only. There are no names and no personal data. "
            "group_a and group_b each have 100 rows and accuracy 0.80, with different "
            "false-positive and false-negative rates. group_c has 4 rows, so its rates "
            "are suppressed under the default minimum of 30. The labels are arbitrary ids, "
            "not real populations."
        ),
    },
    "different_accuracy_similar_error_rates": {
        "title": "Similar error rates, different accuracy",
        "description": (
            "Synthetic rows only. There are no names and no personal data. "
            "group_a and group_b share a true positive rate of 0.90 and a false positive "
            "rate of 0.40. Their outcome base rates differ, so accuracy is 0.87 and 0.63. "
            "The labels are arbitrary ids, not real populations."
        ),
    },
}


def _block(group: str, y_true: int, y_pred: int, n: int) -> pd.DataFrame:
    if n <= 0:
        raise ValueError("A synthetic block must contain rows.")
    site = np.array(["east"] * n, dtype=object)
    site[n // 2 :] = "west"
    return pd.DataFrame(
        {
            "y_true": np.full(n, y_true, dtype=int),
            "y_pred": np.full(n, y_pred, dtype=int),
            "score": np.full(n, 0.75 if y_pred == 1 else 0.25, dtype=float),
            "group": np.full(n, group, dtype=object),
            "site": site,
            "sample_weight": np.ones(n, dtype=float),
        }
    )


def similar_accuracy_different_errors() -> pd.DataFrame:
    parts = [
        _block("group_a", 1, 1, 40),
        _block("group_a", 1, 0, 10),
        _block("group_a", 0, 1, 10),
        _block("group_a", 0, 0, 40),
        _block("group_b", 1, 1, 30),
        _block("group_b", 1, 0, 20),
        _block("group_b", 0, 0, 50),
        _block("group_c", 1, 1, 1),
        _block("group_c", 1, 0, 1),
        _block("group_c", 0, 1, 1),
        _block("group_c", 0, 0, 1),
    ]
    return pd.concat(parts, ignore_index=True)


def different_accuracy_similar_error_rates() -> pd.DataFrame:
    parts = [
        _block("group_a", 1, 1, 81),
        _block("group_a", 1, 0, 9),
        _block("group_a", 0, 1, 4),
        _block("group_a", 0, 0, 6),
        _block("group_b", 1, 1, 9),
        _block("group_b", 1, 0, 1),
        _block("group_b", 0, 1, 36),
        _block("group_b", 0, 0, 54),
    ]
    return pd.concat(parts, ignore_index=True)


BUILDERS = {
    "similar_accuracy_different_errors": similar_accuracy_different_errors,
    "different_accuracy_similar_error_rates": different_accuracy_similar_error_rates,
}


def build_profile(profile: str) -> pd.DataFrame:
    try:
        builder = BUILDERS[profile]
    except KeyError as exc:
        known = ", ".join(sorted(BUILDERS))
        raise KeyError(f"Unknown synthetic profile. Known profiles: {known}.") from exc
    return builder()


def suggested_mapping(profile: str) -> dict:
    if profile not in BUILDERS:
        raise KeyError(profile)
    return {
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
