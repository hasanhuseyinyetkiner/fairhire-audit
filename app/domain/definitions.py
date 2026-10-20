"""Metric names, formulas, and the sentences the API returns with them.

Formulas here are the ones the service computes. Fairlearn disparity formulas
match Fairlearn 0.15 with method='between_groups' and, for equalized odds,
agg='worst_case'.
"""

CONFUSION_CONVENTION = (
    "Rows are the actual class and columns are the predicted class, in order "
    "[negative, positive]. Cell (0,0) is TN, (0,1) is FP, (1,0) is FN, and "
    "(1,1) is TP. The positive class is the declared positive label. This matches "
    "sklearn.metrics.confusion_matrix(..., labels=[negative, positive])."
)

MESSAGES: dict[str, str] = {
    "undefined_denominator": ("Undefined because the denominator is zero. This is not a zero rate."),
    "small_group": ("Withheld because the group is below the sample-size minimum. This is not a zero rate."),
    "too_few_finite_replicates": ("Interval withheld because too many resamples had an undefined denominator."),
    "fewer_than_two_eligible_groups": (
        "Difference withheld because fewer than two groups meet the sample-size minimum."
    ),
    "empty_bin": "No rows in this bin. The observed rate is undefined, not zero.",
    "small_bin": "This bin has fewer than 5 rows. The rate is defined and unstable.",
    "fairlearn_undefined": ("Fairlearn returned a non-finite value. The figure is withheld rather than shown as zero."),
    "comparison_undefined": ("The difference is undefined because one of the two rates is undefined. It is not zero."),
}

METRIC_LABELS: dict[str, str] = {
    "accuracy": "Accuracy",
    "balanced_accuracy": "Balanced accuracy",
    "precision": "Precision",
    "recall": "Recall (true positive rate)",
    "fpr": "False positive rate",
    "fnr": "False negative rate",
    "tnr": "True negative rate (specificity)",
    "selection_rate": "Selection rate",
    "demographic_parity_difference": "Demographic parity difference",
    "equal_opportunity_difference": "Equal opportunity difference",
    "equalized_odds_difference": "Equalized odds difference",
}

FORMULAS: dict[str, str] = {
    "accuracy": "(TP + TN) / (TP + TN + FP + FN)",
    "balanced_accuracy": "(TPR + TNR) / 2. Undefined if TPR or TNR has a zero denominator.",
    "precision": "TP / (TP + FP)",
    "recall": "TP / (TP + FN)",
    "fpr": "FP / (FP + TN)",
    "fnr": "FN / (FN + TP)",
    "tnr": "TN / (TN + FP)",
    "selection_rate": "(TP + FP) / N",
    "demographic_parity_difference": (
        "Largest group selection rate minus smallest group selection rate, "
        "Fairlearn demographic_parity_difference(method='between_groups') "
        "on groups at or above the sample-size minimum."
    ),
    "equal_opportunity_difference": (
        "Largest group true positive rate minus smallest group true positive rate, "
        "Fairlearn equal_opportunity_difference(method='between_groups') "
        "on groups at or above the sample-size minimum."
    ),
    "equalized_odds_difference": (
        "The greater of the true-positive-rate difference and the false-positive-rate "
        "difference, Fairlearn equalized_odds_difference(method='between_groups', "
        "agg='worst_case') on groups at or above the sample-size minimum."
    ),
}

BRIER_FORMULA = (
    "Mean of (score - y_true)^2 over rows, weighted when sample weights are mapped. "
    "This is the binary Brier score. It is descriptive evidence. It is not a calibration certificate."
)

BOOTSTRAP_METHOD = "percentile"
BOOTSTRAP_SAMPLING_UNIT = "row"
BOOTSTRAP_CONFIDENCE = (
    "Paired row resampling with replacement. Interval is the 2.5 and 97.5 percentiles "
    "of finite replicates (scipy.stats.scoreatpercentile). NumPy Generator supplies the "
    "draws. The interval is uncertainty under this procedure, not proof of fairness."
)

CANNOT_CONCLUDE: list[str] = [
    "These figures do not certify legal compliance, fairness, or fitness for an employment decision.",
    (
        "A rate difference does not identify its cause. Selection into the dataset, label bias, "
        "unobserved confounding, and base-rate differences can produce the same numbers."
    ),
    (
        "A confidence interval is resampling uncertainty under the stated bootstrap procedure. "
        "It is not proof that a disparity is real, absent, or acceptable."
    ),
    "Suppressed cells are withheld. A withheld rate is not a zero.",
    "This tool does not rank people, set a production threshold, or automate a hiring outcome.",
    (
        "Protected attributes are used only when you supply them for an audit. "
        "The system does not infer them from names or other proxies."
    ),
]

ASSUMPTIONS: list[str] = [
    (
        "Rows are the bootstrap sampling unit and are treated as exchangeable. "
        "Clustered rows make these intervals too narrow."
    ),
    (
        "The positive class is the declared positive label. "
        "Counts use the confusion-matrix convention in this payload."
    ),
    (
        "Demographic parity, equalized odds, and equal opportunity can disagree. "
        "Meeting one says nothing about the others."
    ),
    "No causal, legal, or policy conclusion is computed.",
    "A mapped timestamp column is stored in the mapping and is not used in any rate.",
    (
        "Overall metrics include every row. Group rates below the sample-size minimum "
        "are withheld, and those rows stay in the overall totals."
    ),
    (
        "Disparity summaries use only groups that meet the sample-size minimum. "
        "Excluded groups are listed and are not entered as zero."
    ),
]

OVERALL_METRIC_NAMES = (
    "accuracy",
    "balanced_accuracy",
    "precision",
    "recall",
    "fpr",
    "fnr",
    "tnr",
    "selection_rate",
)

GROUP_METRIC_NAMES = OVERALL_METRIC_NAMES

CI_METRIC_NAMES = (
    "accuracy",
    "balanced_accuracy",
    "precision",
    "recall",
    "fpr",
    "fnr",
    "selection_rate",
)

DISPARITY_NAMES = (
    "demographic_parity_difference",
    "equal_opportunity_difference",
    "equalized_odds_difference",
)

MIN_FINITE_REPLICATES = 50


def message_for(code: str | None) -> str | None:
    if code is None:
        return None
    return MESSAGES[code]
