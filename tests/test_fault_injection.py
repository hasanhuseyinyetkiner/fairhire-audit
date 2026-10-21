"""Fault injection: malformed uploads, empty groups, concurrent threshold posts."""

from __future__ import annotations

import concurrent.futures

import pytest

PROFILE = "similar_accuracy_different_errors"


def _map_and_audit(client, dataset_id: str, *, iterations: int = 30):
    mapped = client.post(
        f"/api/datasets/{dataset_id}/mapping",
        json={
            "y_true": "y_true",
            "y_pred": "y_pred",
            "score": "score",
            "score_semantics": "probability",
            "sensitive_columns": ["group"],
            "positive_label": "1",
        },
    )
    assert mapped.status_code == 200, mapped.text
    audit = client.post(
        "/api/audits",
        json={"dataset_id": dataset_id, "bootstrap_iterations": iterations, "seed": 9},
    )
    assert audit.status_code == 200, audit.text
    return audit.json()


def test_malformed_csv_rejected_without_500(client):
    garbage = client.post(
        "/api/datasets",
        files={"file": ("broken.csv", b"\xff\xfe\x00not,csv\n\x00\x01", "text/csv")},
    )
    assert garbage.status_code in {400, 422}
    assert garbage.status_code != 500

    jagged = client.post(
        "/api/datasets",
        files={
            "file": (
                "jagged.csv",
                b"y_true,y_pred,group\n1,0\n1,0,a,extra\n",
                "text/csv",
            )
        },
    )
    assert jagged.status_code in {400, 422}
    assert "error" in jagged.json()


def test_empty_group_column_values_rejected_without_500(client):
    # Blank group cells must fail mapping (422), not invent zeros or 500.
    rows = ["y_true,y_pred,score,group"]
    rows.extend(["1,1,0.8,keep"] * 40)
    rows.extend(["0,0,0.2,"] * 5)
    raw = ("\n".join(rows) + "\n").encode()
    uploaded = client.post("/api/datasets", files={"file": ("empty_group.csv", raw, "text/csv")})
    assert uploaded.status_code == 200, uploaded.text
    mapped = client.post(
        f"/api/datasets/{uploaded.json()['id']}/mapping",
        json={
            "y_true": "y_true",
            "y_pred": "y_pred",
            "score": "score",
            "score_semantics": "probability",
            "sensitive_columns": ["group"],
            "positive_label": "1",
        },
    )
    assert mapped.status_code == 422
    body = mapped.json()
    assert body["error"] == "invalid_data"
    assert "empty" in body["detail"].lower()
    assert mapped.status_code != 500


def test_concurrent_threshold_requests_remain_consistent(client):
    created = client.post("/api/datasets/synthetic", json={"profile": PROFILE}).json()
    audit = _map_and_audit(client, created["id"], iterations=40)
    audit_id = audit["id"]
    assert audit["score_gate"]["enabled"] is True

    thresholds = [0.2, 0.4, 0.5, 0.6, 0.8]

    def post_one(value: float):
        response = client.post(
            f"/api/audits/{audit_id}/threshold-scenarios",
            json={"threshold": value},
        )
        return value, response.status_code, response.json()

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(post_one, thresholds))

    for value, status, payload in results:
        assert status == 200, payload
        assert payload["threshold"] == pytest.approx(value)
        assert payload["point_estimates_only"] is True
        assert payload["decision_engine"] is False
        assert payload["sample_size"] == audit["sample_size"]
        names = {item["name"] for item in payload["metrics"]}
        assert "accuracy" in names
        assert "selection_rate" in names


def test_meta_exposes_methodology_and_null_semantics(client):
    body = client.get("/api/meta").json()
    assert body["methodology_version"]
    assert body["decision_engine"] is False
    assert body["cmh_available"] is False
    assert "not implemented" in body["cmh_note"].lower() or "not" in body["cmh_note"].lower()
    assert "null" in body["null_not_zero"].lower()
    assert "zero" in body["null_not_zero"].lower()
    assert body["ci_meaning"]
