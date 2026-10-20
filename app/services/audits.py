"""Run an audit off the request thread and persist every derived row."""

from __future__ import annotations

import importlib.metadata as metadata
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import __version__
from app.db import session_scope
from app.domain.bootstrap import resolve_iterations
from app.domain.compute import apply_threshold, compute_analysis
from app.domain.definitions import BOOTSTRAP_METHOD, BOOTSTRAP_SAMPLING_UNIT, CANNOT_CONCLUDE
from app.domain.fairness import FairlearnMismatch
from app.domain.prepare import Prepared, prepare_frame
from app.domain.report_html import render_report_html
from app.errors import AppError, NotFoundError, ValidationFailure
from app.models import (
    AuditMetric,
    AuditReport,
    AuditRun,
    ConfidenceInterval,
    Dataset,
    GroupMetric,
    ThresholdScenario,
    utcnow,
)
from app.services.datasets import _mapping_dict, latest_mapping
from app.services.storage import contained, directory, load_table
from app.settings import ROOT, get_settings

log = logging.getLogger("fairhire.audits")

REPORT_STATEMENT = (
    "This report records descriptive metrics. It is not a certificate of fairness, compliance, or fitness for use."
)
THRESHOLD_NOTE = (
    "This is a simulation on the uploaded scores. It does not change a deployed model, "
    "rank people, or make a hiring decision. These are point estimates with no bootstrap interval."
)


def library_versions() -> dict[str, str]:
    return {
        "fairlearn_version": metadata.version("fairlearn"),
        "sklearn_version": metadata.version("scikit-learn"),
        "numpy_version": metadata.version("numpy"),
        "scipy_version": metadata.version("scipy"),
        "pandas_version": metadata.version("pandas"),
    }


def git_sha() -> str | None:
    try:
        output = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = output.strip()
    return value or None


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def start_run(
    session: Session,
    dataset: Dataset,
    *,
    iterations: int | None,
    seed: int | None,
    min_n: int | None,
) -> str:
    mapping = latest_mapping(session, dataset.id)
    if mapping is None:
        raise ValidationFailure(
            "mapping_required",
            "Save a column mapping before running an audit.",
        )
    settings = get_settings()
    requested = settings.bootstrap_iterations if iterations is None else iterations
    used, capped = resolve_iterations(requested, settings.bootstrap_max_iterations)
    versions = library_versions()
    run = AuditRun(
        dataset_id=dataset.id,
        mapping_id=mapping.id,
        status="running",
        heartbeat_at=utcnow(),
        seed=settings.bootstrap_seed if seed is None else seed,
        bootstrap_iterations=used,
        bootstrap_iterations_requested=requested,
        bootstrap_capped=capped,
        small_group_min_n=settings.small_group_min_n if min_n is None else min_n,
        code_version=__version__,
        git_sha=git_sha(),
        mapping_snapshot=_mapping_dict(mapping),
        **versions,
    )
    session.add(run)
    session.commit()
    log.info("audit running id=%s dataset=%s", run.id, dataset.id)
    return run.id


def _touch(run_id: str) -> None:
    with session_scope() as session:
        run = session.get(AuditRun, run_id)
        if run is not None:
            run.heartbeat_at = utcnow()
            session.commit()


def _mark_failed(run_id: str, code: str, reason: str) -> None:
    with session_scope() as session:
        run = session.get(AuditRun, run_id)
        if run is None:
            return
        run.status = "failed"
        run.failure_code = code
        run.failure_reason = reason
        run.finished_at = utcnow()
        run.heartbeat_at = run.finished_at
        session.commit()


def _load_prepared(run: AuditRun) -> tuple[Prepared, dict]:
    dataset = run.dataset
    frame = load_table(Path(dataset.stored_path))
    mapping = dict(run.mapping_snapshot)
    settings = get_settings()
    prepared = prepare_frame(
        frame,
        mapping,
        max_rows=settings.max_rows,
        min_n=run.small_group_min_n,
    )
    return prepared, mapping


def _assemble(meta: dict, analysis: dict, finished: datetime) -> dict:
    mapping = meta["mapping"]
    return {
        "id": meta["id"],
        "dataset_id": meta["dataset_id"],
        "status": "succeeded",
        "failure_reason": None,
        "failure_code": None,
        "decision_engine": False,
        "sample_size": analysis["sample_size"],
        "confusion_matrix": analysis["confusion_matrix"],
        "metrics": analysis["metrics"],
        "comparison": analysis["comparison"],
        "groups": analysis["groups"],
        "confidence_intervals": analysis["confidence_intervals"],
        "score_gate": analysis["score_gate"],
        "warnings": analysis["warnings"],
        "assumptions": analysis["assumptions"],
        "cannot_conclude": analysis["cannot_conclude"],
        "provenance": {
            "dataset_id": meta["dataset_id"],
            "dataset_name": meta["dataset_name"],
            "is_synthetic": meta["is_synthetic"],
            "synthetic_profile": meta["synthetic_profile"],
            "content_sha256": meta["content_sha256"],
            "row_count": meta["row_count"],
            "code_version": meta["code_version"],
            "git_sha": meta["git_sha"],
            "fairlearn_version": meta["fairlearn_version"],
            "sklearn_version": meta["sklearn_version"],
            "numpy_version": meta["numpy_version"],
            "scipy_version": meta["scipy_version"],
            "pandas_version": meta["pandas_version"],
            "seed": meta["seed"],
            "bootstrap_iterations": analysis["bootstrap_iterations"],
            "bootstrap_iterations_requested": analysis["bootstrap_iterations_requested"],
            "bootstrap_capped": analysis["bootstrap_capped"],
            "bootstrap_method": BOOTSTRAP_METHOD,
            "sampling_unit": BOOTSTRAP_SAMPLING_UNIT,
            "small_group_min_n": meta["min_n"],
            "positive_label": mapping.get("positive_label"),
            "score_semantics": mapping.get("score_semantics"),
            "mapping": mapping,
            "started_at": _iso(meta["started_at"]),
            "finished_at": _iso(finished),
        },
    }


def _persist_rows(session: Session, run: AuditRun, payload: dict) -> None:
    for metric in payload["metrics"]:
        session.add(
            AuditMetric(
                audit_run_id=run.id,
                scope="overall",
                name=metric["name"],
                label=metric["label"],
                value=metric["value"],
                numerator=metric["numerator"],
                denominator=metric["denominator"],
                undefined_reason=metric["undefined_reason"],
                formula=metric["formula"],
                sample_size=metric["sample_size"],
            )
        )
    comparison = payload["comparison"]
    for metric in comparison["metrics"]:
        session.add(
            AuditMetric(
                audit_run_id=run.id,
                scope="comparison",
                name=metric["name"],
                label=metric["label"],
                value=metric["value"],
                numerator=metric["numerator"],
                denominator=metric["denominator"],
                undefined_reason=metric["undefined_reason"],
                formula=metric["formula"],
                sample_size=metric["sample_size"],
            )
        )
    for column in payload["groups"]:
        for disparity in column["disparities"]:
            session.add(
                AuditMetric(
                    audit_run_id=run.id,
                    scope="disparity",
                    group_column=column["column"],
                    name=disparity["name"],
                    label=disparity["label"],
                    value=disparity["value"],
                    undefined_reason=disparity["undefined_reason"],
                    formula=disparity["formula"],
                    detail={
                        "groups_included": disparity["groups_included"],
                        "groups_excluded": disparity["groups_excluded"],
                        "method": disparity["method"],
                    },
                )
            )
        for group in column["groups"]:
            for metric in group["metrics"]:
                session.add(
                    GroupMetric(
                        audit_run_id=run.id,
                        group_column=group["group_column"],
                        group_value=group["group_value"],
                        is_intersection=bool(column["intersection"]),
                        sample_size=group["sample_size"],
                        suppressed=group["suppressed"],
                        suppression_reason=group["suppression_reason"],
                        metric_name=metric["name"],
                        label=metric["label"],
                        value=metric["value"],
                        numerator=metric["numerator"],
                        denominator=metric["denominator"],
                        undefined_reason=metric["undefined_reason"],
                        formula=metric["formula"],
                    )
                )
    for interval in payload["confidence_intervals"]:
        session.add(
            ConfidenceInterval(
                audit_run_id=run.id,
                metric_name=interval["metric_name"],
                group_column=interval["group_column"],
                group_value=interval["group_value"],
                point=interval["point"],
                lower=interval["lower"],
                upper=interval["upper"],
                iterations=interval["iterations"],
                valid_replicates=interval["valid_replicates"],
                seed=interval["seed"],
                method=interval["method"],
                sampling_unit=interval["sampling_unit"],
                undefined_reason=interval["undefined_reason"],
            )
        )


def _write_reports(run_id: str, payload: dict, finished: datetime) -> tuple[Path, Path]:
    root = directory("report")
    html_path = contained(root, root / f"{run_id}.html")
    json_path = contained(root, root / f"{run_id}.json")
    document = {
        "report_kind": "fairhire_audit",
        "statement": REPORT_STATEMENT,
        "decision_engine": False,
        "generated_at": _iso(finished),
        "audit": payload,
    }
    json_path.write_text(json.dumps(document, indent=2, allow_nan=False), encoding="utf-8")
    html_path.write_text(render_report_html(document), encoding="utf-8")
    return html_path, json_path


def _snapshot(run: AuditRun) -> dict:
    dataset = run.dataset
    return {
        "id": run.id,
        "dataset_id": dataset.id,
        "dataset_name": dataset.name,
        "dataset_path": dataset.stored_path,
        "is_synthetic": dataset.is_synthetic,
        "synthetic_profile": dataset.synthetic_profile,
        "content_sha256": dataset.content_sha256,
        "row_count": dataset.row_count,
        "mapping": dict(run.mapping_snapshot),
        "seed": run.seed,
        "requested": run.bootstrap_iterations_requested,
        "min_n": run.small_group_min_n,
        "code_version": run.code_version,
        "git_sha": run.git_sha,
        "fairlearn_version": run.fairlearn_version,
        "sklearn_version": run.sklearn_version,
        "numpy_version": run.numpy_version,
        "scipy_version": run.scipy_version,
        "pandas_version": run.pandas_version,
        "started_at": run.started_at,
    }


def execute_audit(run_id: str) -> None:
    with session_scope() as session:
        run = session.get(AuditRun, run_id)
        if run is None:
            raise NotFoundError("Audit not found.")
        run.status = "running"
        run.started_at = utcnow()
        run.heartbeat_at = run.started_at
        session.commit()
        meta = _snapshot(run)
    try:
        frame = load_table(Path(meta["dataset_path"]))
        prepared = prepare_frame(
            frame,
            meta["mapping"],
            max_rows=get_settings().max_rows,
            min_n=meta["min_n"],
        )
        analysis = compute_analysis(
            prepared,
            seed=meta["seed"],
            iterations=meta["requested"],
            cap=get_settings().bootstrap_max_iterations,
            min_n=meta["min_n"],
            on_progress=lambda: _touch(run_id),
        )
        finished = utcnow()
        payload = json.loads(json.dumps(_assemble(meta, analysis, finished), allow_nan=False))
        html_path, json_path = _write_reports(run_id, payload, finished)
        with session_scope() as session:
            run = session.get(AuditRun, run_id)
            if run is None:
                raise NotFoundError("Audit not found.")
            run.status = "succeeded"
            run.finished_at = finished
            run.heartbeat_at = finished
            run.failure_code = None
            run.failure_reason = None
            run.bootstrap_iterations = analysis["bootstrap_iterations"]
            run.bootstrap_capped = analysis["bootstrap_capped"]
            run.result_json = payload
            _persist_rows(session, run, payload)
            session.add(
                AuditReport(
                    audit_run_id=run.id,
                    html_path=str(html_path),
                    json_path=str(json_path),
                )
            )
            session.commit()
    except ValidationFailure as exc:
        _mark_failed(run_id, exc.code, exc.message)
        exc.fields["audit_id"] = run_id
        raise
    except FairlearnMismatch as exc:
        _mark_failed(
            run_id,
            "metric_mismatch",
            "Rates disagreed with Fairlearn MetricFrame. No figures were published.",
        )
        raise AppError(
            "metric_mismatch",
            "Rates disagreed with Fairlearn MetricFrame. No figures were published.",
            status_code=500,
        ) from exc
    except AppError:
        raise
    except Exception as exc:
        _mark_failed(run_id, "audit_failed", "The audit failed before producing metrics.")
        log.error("audit %s failed: %s", run_id, type(exc).__name__)
        raise AppError(
            "audit_failed",
            "The audit failed before producing metrics.",
            status_code=500,
        ) from exc
    log.info("audit succeeded id=%s", run_id)


def get_run(session: Session, audit_id: str) -> AuditRun:
    run = session.get(AuditRun, audit_id)
    if run is None:
        raise NotFoundError("Audit not found.")
    return run


def audit_payload(session: Session, audit_id: str) -> dict:
    run = get_run(session, audit_id)
    if run.result_json:
        return run.result_json
    return {
        "id": run.id,
        "dataset_id": run.dataset_id,
        "status": run.status,
        "failure_reason": run.failure_reason,
        "failure_code": run.failure_code,
        "decision_engine": False,
        "sample_size": None,
        "confusion_matrix": None,
        "metrics": [],
        "comparison": None,
        "groups": [],
        "confidence_intervals": [],
        "score_gate": None,
        "warnings": [],
        "assumptions": [],
        "cannot_conclude": list(CANNOT_CONCLUDE) if run.status == "succeeded" else [],
        "provenance": None,
    }


def intersection_labels(groups: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    keys = list(groups)
    combined = np.array(groups[keys[0]], dtype=object)
    for key in keys[1:]:
        combined = np.array(
            [f"{left} × {right}" for left, right in zip(combined, groups[key], strict=True)],
            dtype=object,
        )
    if len(set(combined.tolist())) > 200:
        raise ValidationFailure(
            "too_many_intersections",
            "The intersection has more than 200 cells. Narrow the group columns.",
        )
    return {" × ".join(keys): combined}


def group_view(session: Session, audit_id: str, *, intersection: bool) -> dict:
    run = get_run(session, audit_id)
    if run.status != "succeeded" or not run.result_json:
        raise ValidationFailure("audit_not_ready", "The audit has no group results yet.")
    if not intersection:
        return {
            "audit_id": run.id,
            "intersection": False,
            "available": True,
            "note": "Intervals for these groups are in the audit payload.",
            "groups": run.result_json["groups"],
            "cannot_conclude": run.result_json["cannot_conclude"],
        }
    sensitive = list(run.mapping_snapshot.get("sensitive_columns") or [])
    if len(sensitive) < 2:
        return {
            "audit_id": run.id,
            "intersection": True,
            "available": False,
            "note": "Intersection needs two or more sensitive columns in the mapping.",
            "groups": [],
            "cannot_conclude": run.result_json["cannot_conclude"],
        }
    prepared, _mapping = _load_prepared(run)
    crossed = intersection_labels(prepared.groups)
    analysis = compute_analysis(
        prepared,
        seed=run.seed,
        iterations=run.bootstrap_iterations_requested,
        cap=get_settings().bootstrap_max_iterations,
        min_n=run.small_group_min_n,
        intersection_labels=crossed,
    )
    return {
        "audit_id": run.id,
        "intersection": True,
        "available": True,
        "note": (
            "Intersection cells are smaller and easier to re-identify. "
            "Cells below the sample-size minimum are suppressed. This is not an anonymity proof. "
            "Bootstrap intervals for the intersection are included."
        ),
        "groups": analysis["groups"],
        "cannot_conclude": analysis["cannot_conclude"],
    }


def create_threshold(session: Session, audit_id: str, threshold: float) -> dict:
    run = get_run(session, audit_id)
    if run.status != "succeeded":
        raise ValidationFailure("audit_not_ready", "Run a successful audit before the threshold lab.")
    prepared, _mapping = _load_prepared(run)
    gate = prepared.score_semantics
    from app.domain.compute import score_gate

    gate_payload = score_gate(prepared)
    if not gate_payload["enabled"]:
        raise ValidationFailure("threshold_closed", gate_payload["reason"])
    try:
        analysis = apply_threshold(prepared, threshold, min_n=run.small_group_min_n)
    except ValueError as exc:
        raise ValidationFailure("threshold_closed", "Threshold Lab is closed.") from exc
    result = {
        "threshold": threshold,
        "score_semantics": gate,
        "note": THRESHOLD_NOTE,
        "point_estimates_only": True,
        "sample_size": analysis["sample_size"],
        "confusion_matrix": analysis["confusion_matrix"],
        "metrics": analysis["metrics"],
        "groups": analysis["groups"],
        "decision_engine": False,
    }
    scenario = ThresholdScenario(
        audit_run_id=run.id,
        threshold=threshold,
        score_semantics=str(gate),
        results=json.loads(json.dumps(result, allow_nan=False)),
    )
    session.add(scenario)
    session.commit()
    result["id"] = scenario.id
    result["audit_id"] = run.id
    return result


def read_report(session: Session, audit_id: str, kind: str) -> tuple[bytes, str]:
    run = get_run(session, audit_id)
    report = session.scalar(select(AuditReport).where(AuditReport.audit_run_id == run.id))
    if report is None:
        raise NotFoundError("Report not found.")
    path = Path(report.html_path if kind == "html" else report.json_path)
    path = contained(directory("report"), path)
    if not path.exists():
        raise NotFoundError("Report file not found.")
    media = "text/html; charset=utf-8" if kind == "html" else "application/json"
    return path.read_bytes(), media
