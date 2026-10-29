"""Offline checks for the public benchmark adapter."""

import numpy as np
import pandas as pd
import pytest
from scripts.adult_benchmark import COLUMNS, count_overlapping_test_rows, load_file, run


def test_benchmark_reconciles_group_confusion_counts():
    n = 120
    frame = pd.DataFrame(
        {
            "age": np.arange(n) + 20,
            "education_num": np.tile([5, 10, 15], 40),
            "hours": np.tile([30, 40, 50, 60], 30),
            "sex": np.where(np.arange(n) % 2, "Female", "Male"),
            "income": np.where(np.arange(n) >= 60, ">50K", "<=50K"),
        }
    )
    result = run(frame, frame)
    for group in result.values():
        assert group["n"] == 60
        assert sum(group[key] for key in ("tn", "fp", "fn", "tp")) == 60
        assert group["selection_rate"] == pytest.approx((group["tp"] + group["fp"]) / 60)


def test_changed_source_is_rejected(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return b"changed data"

    monkeypatch.setattr("scripts.adult_benchmark.urllib.request.urlopen", lambda *a, **kw: Response())
    with pytest.raises(ValueError, match="SHA-256"):
        load_file("adult.data")


def test_overlap_counts_test_rows_without_multiplying_duplicates():
    row = {column: "same" for column in COLUMNS}
    other = {column: "different" for column in COLUMNS}
    train = pd.DataFrame([row, row])
    test = pd.DataFrame([row, row, other])
    assert count_overlapping_test_rows(train, test) == 2
