"""Turn a user table and a column mapping into arrays, or a precise error."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from app.errors import ValidationFailure


@dataclass
class Prepared:
    y_true: np.ndarray
    y_pred: np.ndarray
    y_pred_alt: np.ndarray | None
    score: np.ndarray | None
    weight: np.ndarray
    groups: dict[str, np.ndarray]
    score_semantics: str | None
    positive_label: str
    warnings: list[str] = field(default_factory=list)
    derived_prediction: bool = False
    row_count: int = 0


def _blank_missing(series: pd.Series) -> pd.Series:
    missing = series.isna()
    if series.dtype == object or pd.api.types.is_string_dtype(series):
        missing = missing | series.astype(str).str.strip().isin({"", "nan", "None"})
    return missing


def _column(df: pd.DataFrame, name: str | None, field: str, fields: dict[str, str]) -> str | None:
    if name is None or str(name).strip() == "":
        return None
    cleaned = str(name).strip()
    if cleaned not in df.columns:
        fields[field] = f"Column '{cleaned}' is not in the file."
        return None
    return cleaned


def _labels(series: pd.Series) -> list[str]:
    return [str(value).strip() for value in series.tolist()]


def _is_positive_mask(series: pd.Series, positive_label: str) -> np.ndarray:
    token = str(positive_label).strip()
    as_text = series.map(lambda value: str(value).strip())
    match = as_text.eq(token).to_numpy()
    numeric = pd.to_numeric(series, errors="coerce")
    try:
        token_number = float(token)
    except ValueError:
        token_number = None
    if token_number is not None:
        numeric_match = numeric.eq(token_number).fillna(False).to_numpy()
        match = match | numeric_match
    return match


def _encode_outcome(
    frame: pd.DataFrame,
    columns: list[str],
    positive_label: str,
    fields: dict[str, str],
) -> dict[str, np.ndarray]:
    present = [frame[column].dropna() for column in columns]
    combined = pd.concat(present, ignore_index=True) if present else pd.Series(dtype=object)
    tokens = {str(value).strip() for value in combined.tolist()}
    try:
        token_number = float(str(positive_label).strip())
    except ValueError:
        token_number = None
    normalized: set[str] = set()
    for token in tokens:
        if token == str(positive_label).strip():
            normalized.add("__positive__")
            continue
        if token_number is not None:
            try:
                if float(token) == token_number:
                    normalized.add("__positive__")
                    continue
            except ValueError:
                pass
        normalized.add(token)
    negatives = {item for item in normalized if item != "__positive__"}
    if len(negatives) > 1:
        fields["labels"] = (
            "More than two classes are present. This audit is binary. "
            f"{len(negatives) + (1 if '__positive__' in normalized else 0)} distinct labels were found. "
            "The label values are not shown."
        )
        return {}
    encoded: dict[str, np.ndarray] = {}
    for column in columns:
        series = frame[column]
        if bool(_blank_missing(series).any()):
            fields[column] = f"Column '{column}' has empty values. Rows were not dropped or imputed."
            continue
        positive = _is_positive_mask(series, positive_label)
        if not positive.any() and len(negatives) == 0:
            fields[column] = f"Column '{column}' has no usable values."
            continue
        encoded[column] = np.where(positive, 1, 0).astype(int)
    return encoded


def prepare_frame(df: pd.DataFrame, mapping: dict, *, max_rows: int, min_n: int) -> Prepared:
    fields: dict[str, str] = {}
    if df.shape[0] == 0:
        raise ValidationFailure("empty_dataset", "The file has no data rows.")
    if df.shape[0] > max_rows:
        raise ValidationFailure(
            "too_many_rows",
            f"The file has {int(df.shape[0])} rows. The maximum is {max_rows}.",
        )
    if df.columns.duplicated().any():
        raise ValidationFailure("duplicate_columns", "The file has duplicate column names.")

    y_true_name = _column(df, mapping.get("y_true"), "y_true", fields)
    y_pred_name = _column(df, mapping.get("y_pred"), "y_pred", fields)
    y_alt_name = _column(df, mapping.get("y_pred_alt"), "y_pred_alt", fields)
    score_name = _column(df, mapping.get("score"), "score", fields)
    weight_name = _column(df, mapping.get("sample_weight"), "sample_weight", fields)
    timestamp_name = _column(df, mapping.get("timestamp_column"), "timestamp_column", fields)
    sensitive = mapping.get("sensitive_columns") or []
    if not isinstance(sensitive, list) or not sensitive:
        fields["sensitive_columns"] = "Map at least one group column. The audit does not infer groups."
        sensitive_names: list[str] = []
    else:
        sensitive_names = []
        for index, name in enumerate(sensitive):
            cleaned = _column(df, str(name), f"sensitive_columns[{index}]", fields)
            if cleaned:
                sensitive_names.append(cleaned)
        if len(set(sensitive_names)) != len(sensitive_names):
            fields["sensitive_columns"] = "The same group column was mapped more than once."

    semantics = mapping.get("score_semantics")
    if semantics not in (None, "", "probability", "ranking_score"):
        fields["score_semantics"] = "Score semantics must be probability or ranking_score."
    if semantics == "":
        semantics = None
    if score_name is None and semantics in ("probability", "ranking_score"):
        fields["score"] = "A score semantic was declared but no score column was mapped."
    positive_label = str(mapping.get("positive_label") or "").strip()
    if not positive_label:
        fields["positive_label"] = "A positive label is required."

    if fields or y_true_name is None:
        if y_true_name is None and "y_true" not in fields:
            fields["y_true"] = "Map the actual-outcome column."
        raise ValidationFailure("invalid_mapping", "The mapping does not match this file.", fields)

    label_columns = [y_true_name]
    if y_pred_name:
        label_columns.append(y_pred_name)
    if y_alt_name:
        label_columns.append(y_alt_name)
    encoded = _encode_outcome(df, label_columns, positive_label, fields)

    score_array: np.ndarray | None = None
    if score_name is not None:
        numeric = pd.to_numeric(df[score_name], errors="coerce")
        original_missing = _blank_missing(df[score_name])
        non_numeric = numeric.isna() & ~original_missing
        if bool(original_missing.any()):
            fields["score"] = f"Score column '{score_name}' has empty values. Rows were not dropped."
        elif bool(non_numeric.any()):
            fields["score"] = f"Score column '{score_name}' is not numeric."
        else:
            score_array = numeric.to_numpy(dtype=float)
            if semantics == "probability":
                outside = int(((score_array < 0) | (score_array > 1)).sum())
                if outside:
                    fields["score"] = (
                        f"{outside} score values are outside [0, 1]. "
                        "A declared probability must lie in that interval. "
                        "The values are not shown. Declare ranking_score if this column is not a probability."
                    )
            elif semantics is None:
                fields["score_semantics"] = (
                    "Declare the score as probability or ranking_score. The lab stays closed until you do."
                )

    weight = np.ones(len(df), dtype=float)
    if weight_name is not None:
        numeric_weight = pd.to_numeric(df[weight_name], errors="coerce")
        if bool(numeric_weight.isna().any()):
            fields["sample_weight"] = f"Sample-weight column '{weight_name}' is not numeric."
        elif bool((numeric_weight < 0).any()):
            fields["sample_weight"] = "Sample weights must be non-negative. Values are not shown."
        elif float(numeric_weight.sum()) == 0:
            fields["sample_weight"] = "Sample weights sum to zero."
        else:
            weight = numeric_weight.to_numpy(dtype=float)

    groups: dict[str, np.ndarray] = {}
    for name in sensitive_names:
        series = df[name]
        if bool(_blank_missing(series).any()):
            fields[f"group:{name}"] = f"Group column '{name}' has empty values. Rows were not dropped."
            continue
        labels = np.array(_labels(series), dtype=object)
        if any(len(str(label)) > 200 for label in labels):
            fields[f"group:{name}"] = f"A label in '{name}' exceeds 200 characters."
            continue
        levels = set(labels.tolist())
        if len(levels) > 100:
            fields[f"group:{name}"] = f"Column '{name}' has {len(levels)} distinct groups. The maximum is 100."
            continue
        groups[name] = labels

    if fields:
        detail = " ".join(fields.values())
        raise ValidationFailure("invalid_data", detail, fields)

    warnings: list[str] = []
    derived = False
    if y_pred_name is None:
        if score_array is not None and semantics == "probability":
            y_pred = (score_array >= 0.5).astype(int)
            derived = True
            warnings.append(
                "No prediction column was mapped. y_pred was derived as score >= 0.5. "
                "That cutoff is an analysis assumption, not a deployed rule."
            )
        elif semantics == "ranking_score":
            raise ValidationFailure(
                "prediction_required",
                "A ranking score has no default cutoff. Map a prediction column.",
                {"y_pred": "Required when the score is a ranking score."},
            )
        else:
            raise ValidationFailure(
                "prediction_required",
                "Map a prediction column, or a probability score that can be cut at 0.5.",
                {"y_pred": "Required."},
            )
    else:
        y_pred = encoded[y_pred_name]

    y_true = encoded[y_true_name]
    y_alt = encoded[y_alt_name] if y_alt_name else None
    if len(np.unique(y_true)) < 2:
        warnings.append(
            "Actual outcomes contain only one class. Rates that need the missing class are undefined, not zero."
        )
    if len(np.unique(y_pred)) < 2:
        warnings.append("Predictions contain only one class.")

    positives = int((y_true == 1).sum())
    negatives = int((y_true == 0).sum())
    smaller = min(positives, negatives)
    if y_true.size and smaller / y_true.size < 0.2:
        warnings.append(
            "The outcome classes are imbalanced (the smaller class is under 20% of rows). "
            "Accuracy is a weak summary on this table."
        )
    for name, labels in groups.items():
        values, counts = np.unique(labels, return_counts=True)
        tiny = int((counts < min_n).sum())
        if tiny:
            warnings.append(
                f"{tiny} level(s) of column '{name}' are below the sample-size minimum "
                f"of {min_n}. Their rates will be withheld, not shown as zero."
            )
    if timestamp_name is not None:
        warnings.append(f"Timestamp column '{timestamp_name}' is mapped and is not used in any rate.")

    return Prepared(
        y_true=y_true,
        y_pred=y_pred,
        y_pred_alt=y_alt,
        score=score_array,
        weight=weight,
        groups=groups,
        score_semantics=semantics if score_array is not None else None,
        positive_label=positive_label,
        warnings=warnings,
        derived_prediction=derived,
        row_count=int(len(df)),
    )
