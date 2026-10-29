"""Reproduce an aggregate-only audit of UCI Adult; no individual records are saved."""

import hashlib
import io
import json
import urllib.request

import numpy as np
import pandas as pd
from app.domain.compute import compute_analysis
from app.domain.prepare import prepare_frame
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

BASE = "https://archive.ics.uci.edu/ml/machine-learning-databases/adult/"
HASHES = {
    "adult.data": "5b00264637dbfec36bdeaab5676b0b309ff9eb788d63554ca0a249491c86603d",
    "adult.test": "a2a9044bc167a35b2361efbabec64e89d69ce82d9790d2980119aac5fd7e9c05",
}
COLUMNS = [
    "age",
    "workclass",
    "fnlwgt",
    "education",
    "education_num",
    "marital",
    "occupation",
    "relationship",
    "race",
    "sex",
    "capital_gain",
    "capital_loss",
    "hours",
    "country",
    "income",
]
FEATURES = ["age", "education_num", "hours"]


def load_file(name):
    with urllib.request.urlopen(BASE + name, timeout=30) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != HASHES[name]:
        raise ValueError(f"Unexpected SHA-256 for {name}; inspect the source before updating the pin")
    frame = pd.read_csv(io.BytesIO(data), names=COLUMNS, skipinitialspace=True, comment="|")
    frame["income"] = frame["income"].str.strip().str.rstrip(".")
    if not set(frame["income"].unique()) <= {"<=50K", ">50K"}:
        raise ValueError("Unexpected income labels")
    return frame


def count_overlapping_test_rows(train, test):
    """Count test rows exactly matching any training row after label normalization."""
    training = pd.MultiIndex.from_frame(train[COLUMNS])
    testing = pd.MultiIndex.from_frame(test[COLUMNS])
    return int(testing.isin(training).sum())


def run(train, test):
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, random_state=0))
    model.fit(train[FEATURES], (train["income"] == ">50K").astype(int))
    actual = (test["income"] == ">50K").astype(int).to_numpy()
    predicted = model.predict(test[FEATURES]).astype(int)
    frame = pd.DataFrame({"actual": actual, "predicted": predicted, "sex": test["sex"].to_numpy()})
    prepared = prepare_frame(
        frame,
        {"y_true": "actual", "y_pred": "predicted", "positive_label": "1", "sensitive_columns": ["sex"]},
        max_rows=len(frame),
        min_n=30,
    )
    audit = compute_analysis(prepared, seed=0, iterations=1, cap=1, min_n=30, with_bootstrap=False)
    result = {}
    for group in audit["groups"][0]["groups"]:
        label = group["group_value"]
        mask = frame["sex"].to_numpy() == label
        y, p = actual[mask], predicted[mask]
        counts = {
            "tn": int(np.sum((y == 0) & (p == 0))),
            "fp": int(np.sum((y == 0) & (p == 1))),
            "fn": int(np.sum((y == 1) & (p == 0))),
            "tp": int(np.sum((y == 1) & (p == 1))),
        }
        metrics = {m["name"]: m["value"] for m in group["metrics"]}
        # Independent direct counts validate the audit rates, including denominators.
        assert np.isclose(metrics["selection_rate"], (counts["tp"] + counts["fp"]) / len(y))
        assert np.isclose(metrics["fnr"], counts["fn"] / (counts["fn"] + counts["tp"]))
        assert np.isclose(metrics["fpr"], counts["fp"] / (counts["fp"] + counts["tn"]))
        result[label] = {
            "n": len(y),
            **counts,
            "selection_rate": metrics["selection_rate"],
            "fnr": metrics["fnr"],
            "fpr": metrics["fpr"],
        }
    return result


if __name__ == "__main__":
    train = load_file("adult.data")
    test = load_file("adult.test")
    print(json.dumps({
        "data_quality": {"test_rows_matching_training_values": count_overlapping_test_rows(train, test)},
        "groups": run(train, test),
    }, indent=2))
