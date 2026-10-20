"""Upload, audit, deletion, score gate, parquet, and report tests."""

from __future__ import annotations

import io
from datetime import timedelta

import pandas as pd
import pytest

PROFILE = "similar_accuracy_different_errors"


def _metric(metrics, name):
    return next(item for item in metrics if item["name"] == name)


def _groups(payload):
    return {row["group_value"]: row for row in payload["groups"][0]["groups"]}


def test_meta_is_not_a_decision_engine(client):
    response = client.get("/api/meta")
    assert response.status_code == 200
    body = response.json()
    assert body["decision_engine"] is False
    assert body["demo"] is False
    assert body["banner"] is None
    assert body["fairlearn_version"]
    ready = client.get("/ready")
    assert ready.status_code == 200
    assert client.get("/health").json()["status"] == "ok"


def test_empty_and_header_only_csv_are_rejected(client):
    empty = client.post("/api/datasets", files={"file": ("empty.csv", b"", "text/csv")})
    assert empty.status_code == 422
    header = client.post(
        "/api/datasets",
        files={"file": ("header.csv", b"y_true,y_pred,group\n", "text/csv")},
    )
    assert header.status_code == 422
    assert header.json()["error"] == "empty_dataset"


def test_missing_column_and_bad_probability_and_ranking_score(client):
    created = client.post("/api/datasets/synthetic", json={"profile": PROFILE}).json()
    missing = client.post(
        f"/api/datasets/{created['id']}/mapping",
        json={
            "y_true": "not_a_column",
            "y_pred": "y_pred",
            "sensitive_columns": ["group"],
            "positive_label": "1",
        },
    )
    assert missing.status_code == 422
    assert "not_a_column" in missing.json()["fields"]["y_true"]

    rows = "\n".join(["1,1,1.5,a"] * 40)
    raw = f"y_true,y_pred,score,group\n{rows}\n".encode()
    uploaded = client.post("/api/datasets", files={"file": ("scores.csv", raw, "text/csv")})
    assert uploaded.status_code == 200
    dataset_id = uploaded.json()["id"]
    rejected = client.post(
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
    assert rejected.status_code == 422
    assert "outside [0, 1]" in rejected.json()["detail"]
    ranking = client.post(
        f"/api/datasets/{dataset_id}/mapping",
        json={
            "y_true": "y_true",
            "y_pred": "y_pred",
            "score": "score",
            "score_semantics": "ranking_score",
            "sensitive_columns": ["group"],
            "positive_label": "1",
        },
    )
    assert ranking.status_code == 200
    audit = client.post(
        "/api/audits",
        json={"dataset_id": dataset_id, "bootstrap_iterations": 40, "small_group_min_n": 30},
    )
    assert audit.status_code == 200
    gate = audit.json()["score_gate"]
    assert gate["enabled"] is True
    assert gate["semantics"] == "ranking_score"
    assert gate["brier_score"] is None
    assert gate["calibrated"] is False
    closed = client.post(
        "/api/datasets/synthetic",
        json={"profile": "different_accuracy_similar_error_rates"},
    ).json()
    # Drop the score by remapping without it. The lab must close.
    client.post(
        f"/api/datasets/{closed['id']}/mapping",
        json={
            "y_true": "y_true",
            "y_pred": "y_pred",
            "sensitive_columns": ["group"],
            "positive_label": "1",
        },
    )
    no_score = client.post(
        "/api/audits",
        json={"dataset_id": closed["id"], "bootstrap_iterations": 20},
    ).json()
    assert no_score["score_gate"]["enabled"] is False
    denied = client.post(
        f"/api/audits/{no_score['id']}/threshold-scenarios",
        json={"threshold": 0.5},
    )
    assert denied.status_code == 422
    assert denied.json()["error"] == "threshold_closed"


def test_single_class_does_not_invent_a_zero_fpr(client):
    body = "y_true,y_pred,group\n" + "1,1,only\n" * 40
    uploaded = client.post("/api/datasets", files={"file": ("single.csv", body.encode(), "text/csv")}).json()
    mapped = client.post(
        f"/api/datasets/{uploaded['id']}/mapping",
        json={
            "y_true": "y_true",
            "y_pred": "y_pred",
            "sensitive_columns": ["group"],
            "positive_label": "1",
        },
    )
    assert mapped.status_code == 200
    audit = client.post(
        "/api/audits",
        json={"dataset_id": uploaded["id"], "bootstrap_iterations": 20},
    )
    assert audit.status_code == 200
    metrics = {item["name"]: item for item in audit.json()["metrics"]}
    assert metrics["accuracy"]["value"] == pytest.approx(1.0)
    assert metrics["fpr"]["value"] is None
    assert metrics["fpr"]["undefined_reason"] == "undefined_denominator"
    assert metrics["balanced_accuracy"]["value"] is None
    assert "not a zero" in metrics["fpr"]["message"]


def test_defining_workflow_report_and_threshold(client):
    created = client.post(
        "/api/datasets/synthetic",
        json={"profile": PROFILE, "name": "<img src=x onerror=alert(1)>"},
    )
    assert created.status_code == 200
    dataset = created.json()
    assert dataset["is_synthetic"] is True
    assert dataset["mapping"]["sensitive_columns"] == ["group"]
    preview = client.get(f"/api/datasets/{dataset['id']}/preview")
    assert preview.status_code == 200
    assert preview.json()["row_count"] == 204
    quality = client.get(f"/api/datasets/{dataset['id']}/quality").json()
    assert quality["class_balance"]["positive"] == 102

    audit = client.post(
        "/api/audits",
        json={"dataset_id": dataset["id"], "bootstrap_iterations": 80, "seed": 11},
    )
    assert audit.status_code == 200, audit.text
    body = audit.json()
    assert body["status"] == "succeeded"
    assert body["decision_engine"] is False
    assert body["confusion_matrix"]["tn"] == 91
    assert body["confusion_matrix"]["tp"] == 71
    groups = _groups(body)
    assert groups["group_a"]["sample_size"] == 100
    assert _metric(groups["group_a"]["metrics"], "accuracy")["value"] == pytest.approx(0.8)
    assert _metric(groups["group_b"]["metrics"], "fpr")["value"] == 0.0
    assert groups["group_c"]["suppressed"] is True
    assert _metric(groups["group_c"]["metrics"], "accuracy")["value"] is None
    disparities = {item["name"]: item for item in body["groups"][0]["disparities"]}
    assert disparities["equal_opportunity_difference"]["value"] == pytest.approx(0.2)
    assert disparities["equal_opportunity_difference"]["groups_excluded"] == ["group_c"]
    assert body["score_gate"]["enabled"] is True
    assert body["score_gate"]["calibrated"] is False
    assert body["score_gate"]["brier_score"] == pytest.approx(33.75 / 204)
    assert any("do not certify" in line for line in body["cannot_conclude"])
    assert body["provenance"]["seed"] == 11
    assert body["provenance"]["fairlearn_version"]

    listed = client.get(f"/api/audits/{body['id']}/groups").json()
    assert listed["available"] is True
    intersection = client.get(f"/api/audits/{body['id']}/groups?intersection=true").json()
    assert intersection["available"] is False

    at_half = client.post(
        f"/api/audits/{body['id']}/threshold-scenarios",
        json={"threshold": 0.5},
    ).json()
    assert at_half["point_estimates_only"] is True
    assert "does not change a deployed model" in at_half["note"]
    assert _metric(at_half["metrics"], "accuracy")["value"] == pytest.approx(
        _metric(body["metrics"], "accuracy")["value"]
    )
    at_high = client.post(
        f"/api/audits/{body['id']}/threshold-scenarios",
        json={"threshold": 0.9},
    ).json()
    high_metrics = {item["name"]: item for item in at_high["metrics"]}
    assert high_metrics["precision"]["value"] is None
    assert high_metrics["recall"]["value"] == 0.0

    report = client.get(f"/api/audits/{body['id']}/report.html")
    assert report.status_code == 200
    assert "What this cannot conclude" in report.text
    assert "Not a certificate" in report.text
    assert "bias-free" not in report.text.lower()
    assert "<img" not in report.text
    assert "&lt;img" in report.text
    document = client.get(f"/api/audits/{body['id']}/report.json").json()
    assert document["decision_engine"] is False
    assert document["audit"]["confusion_matrix"]["tp"] == 71

    from importlib.metadata import version

    from app.db import session_scope
    from app.models import AuditMetric

    with session_scope() as session:
        stored = session.query(AuditMetric).filter_by(name="accuracy", scope="overall").one()
        assert stored.value == pytest.approx(_metric(body["metrics"], "accuracy")["value"])
    assert version("fairlearn") == body["provenance"]["fairlearn_version"]


def test_bootstrap_cap_and_cascade_delete(client):
    created = client.post("/api/datasets/synthetic", json={"profile": PROFILE}).json()
    audit = client.post(
        "/api/audits",
        json={"dataset_id": created["id"], "bootstrap_iterations": 5000, "seed": 3},
    )
    assert audit.status_code == 200
    provenance = audit.json()["provenance"]
    assert provenance["bootstrap_capped"] is True
    assert provenance["bootstrap_iterations"] == 1000
    assert provenance["bootstrap_iterations_requested"] == 5000
    client.post(
        f"/api/audits/{audit.json()['id']}/threshold-scenarios",
        json={"threshold": 0.4},
    )

    from pathlib import Path

    from app.db import session_scope
    from app.models import (
        AuditMetric,
        AuditReport,
        AuditRun,
        ConfidenceInterval,
        Dataset,
        GroupMetric,
        ThresholdScenario,
    )

    with session_scope() as session:
        dataset = session.get(Dataset, created["id"])
        stored = Path(dataset.stored_path)
        report = session.query(AuditReport).one()
        html_path = Path(report.html_path)
        json_path = Path(report.json_path)
        assert stored.exists()
        assert html_path.exists()
    deleted = client.delete(f"/api/datasets/{created['id']}")
    assert deleted.status_code == 200
    assert client.get(f"/api/datasets/{created['id']}").status_code == 404
    assert client.get(f"/api/audits/{audit.json()['id']}").status_code == 404
    assert not stored.exists()
    assert not html_path.exists()
    assert not json_path.exists()
    with session_scope() as session:
        assert session.query(Dataset).count() == 0
        assert session.query(AuditRun).count() == 0
        assert session.query(AuditMetric).count() == 0
        assert session.query(GroupMetric).count() == 0
        assert session.query(ConfidenceInterval).count() == 0
        assert session.query(ThresholdScenario).count() == 0
        assert session.query(AuditReport).count() == 0


def test_parquet_upload_and_audit(client):
    frame = pd.DataFrame(
        {
            "y_true": [1] * 20 + [0] * 20 + [1] * 20 + [0] * 20,
            "y_pred": [1] * 20 + [0] * 20 + [1] * 10 + [0] * 10 + [0] * 20,
            "group": ["left"] * 40 + ["right"] * 40,
        }
    )
    buffer = io.BytesIO()
    frame.to_parquet(buffer, engine="pyarrow", index=False)
    uploaded = client.post(
        "/api/datasets",
        files={"file": ("eval.parquet", buffer.getvalue(), "application/octet-stream")},
    )
    assert uploaded.status_code == 200, uploaded.text
    dataset_id = uploaded.json()["id"]
    assert uploaded.json()["row_count"] == 80
    mapped = client.post(
        f"/api/datasets/{dataset_id}/mapping",
        json={
            "y_true": "y_true",
            "y_pred": "y_pred",
            "sensitive_columns": ["group"],
            "positive_label": "1",
        },
    )
    assert mapped.status_code == 200
    audit = client.post(
        "/api/audits",
        json={"dataset_id": dataset_id, "bootstrap_iterations": 30, "small_group_min_n": 30},
    )
    assert audit.status_code == 200
    assert audit.json()["sample_size"] == 80
    assert audit.json()["score_gate"]["enabled"] is False


def test_reaper_and_retention(client):
    from app.db import session_scope
    from app.models import AuditRun, AuditSetting, Dataset, utcnow
    from app.services.datasets import purge_expired
    from app.services.maintenance import reap_stale_runs

    created = client.post("/api/datasets/synthetic", json={"profile": PROFILE}).json()
    with session_scope() as session:
        dataset = session.get(Dataset, created["id"])
        mapping_id = dataset.mappings[0].id
        stale = AuditRun(
            dataset_id=dataset.id,
            mapping_id=mapping_id,
            status="running",
            heartbeat_at=utcnow() - timedelta(hours=2),
            seed=1,
            bootstrap_iterations=10,
            bootstrap_iterations_requested=10,
            bootstrap_capped=False,
            small_group_min_n=30,
            code_version="0.1.0",
            fairlearn_version="test",
            sklearn_version="test",
            numpy_version="test",
            scipy_version="test",
            pandas_version="test",
            mapping_snapshot={"y_true": "y_true"},
        )
        fresh = AuditRun(
            dataset_id=dataset.id,
            mapping_id=mapping_id,
            status="running",
            heartbeat_at=utcnow(),
            seed=1,
            bootstrap_iterations=10,
            bootstrap_iterations_requested=10,
            bootstrap_capped=False,
            small_group_min_n=30,
            code_version="0.1.0",
            fairlearn_version="test",
            sklearn_version="test",
            numpy_version="test",
            scipy_version="test",
            pandas_version="test",
            mapping_snapshot={"y_true": "y_true"},
        )
        session.add(stale)
        session.add(fresh)
        session.commit()
        stale_id = stale.id
        fresh_id = fresh.id
        found = reap_stale_runs(session, stale_seconds=60)
        assert found == 1
        assert session.get(AuditRun, stale_id).status == "failed"
        assert "stale_run_reaped" in session.get(AuditRun, stale_id).failure_reason
        assert session.get(AuditRun, fresh_id).status == "running"
        session.get(AuditSetting, "data_retention_days").value = "1"
        dataset.created_at = utcnow() - timedelta(days=3)
        session.commit()
        dataset_id = dataset.id
    with session_scope() as session:
        assert purge_expired(session) >= 1
    with session_scope() as session:
        assert session.get(Dataset, dataset_id) is None
        assert session.query(AuditRun).count() == 0


def test_migration_matches_models(client):
    from app.db import Base, get_engine
    from sqlalchemy import inspect

    names = set(inspect(get_engine()).get_table_names())
    assert set(Base.metadata.tables) <= names


def test_bind_policy():
    from app.settings import Settings, enforce_bind

    refused = Settings(bind_host="0.0.0.0", allow_network_bind=False)
    with pytest.raises(SystemExit, match="Refusing to bind"):
        enforce_bind(refused)
    enforce_bind(Settings(bind_host="0.0.0.0", allow_network_bind=True))
    enforce_bind(Settings(bind_host="127.0.0.1", allow_network_bind=False))


@pytest.mark.postgres
def test_postgres_when_configured():
    import os

    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url.startswith("postgresql"):
        pytest.skip("TEST_DATABASE_URL is not PostgreSQL")
    from app.db import session_scope
    from sqlalchemy import text

    with session_scope() as session:
        version = session.execute(text("select version()")).scalar()
    assert "PostgreSQL" in str(version)
