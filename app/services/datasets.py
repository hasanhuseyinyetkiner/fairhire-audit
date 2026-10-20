"""Dataset upload, synthetic files, mapping, and cascade deletion."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.prepare import prepare_frame
from app.domain.synthetic import PROFILES, build_profile, suggested_mapping
from app.errors import NotFoundError, ValidationFailure
from app.models import AuditReport, AuditRun, ColumnMapping, Dataset
from app.services.maintenance import retention_days
from app.services.storage import (
    contained,
    directory,
    display_name,
    load_table,
    store_bytes,
    unlink_quiet,
    validate_and_store,
)
from app.settings import get_settings

log = logging.getLogger("fairhire.datasets")


def _mapping_dict(mapping: ColumnMapping) -> dict:
    return {
        "y_true": mapping.y_true,
        "y_pred": mapping.y_pred,
        "y_pred_alt": mapping.y_pred_alt,
        "score": mapping.score,
        "score_semantics": mapping.score_semantics,
        "sensitive_columns": list(mapping.sensitive_columns or []),
        "sample_weight": mapping.sample_weight,
        "timestamp_column": mapping.timestamp_column,
        "positive_label": mapping.positive_label,
    }


def latest_mapping(session: Session, dataset_id: str) -> ColumnMapping | None:
    return session.scalar(
        select(ColumnMapping).where(ColumnMapping.dataset_id == dataset_id).order_by(ColumnMapping.created_at.desc())
    )


def latest_audit(session: Session, dataset_id: str) -> AuditRun | None:
    return session.scalar(
        select(AuditRun).where(AuditRun.dataset_id == dataset_id).order_by(AuditRun.created_at.desc())
    )


def dataset_payload(session: Session, dataset: Dataset) -> dict:
    mapping = latest_mapping(session, dataset.id)
    audit = latest_audit(session, dataset.id)
    return {
        "id": dataset.id,
        "name": dataset.name,
        "source": dataset.source,
        "synthetic_profile": dataset.synthetic_profile,
        "is_synthetic": dataset.is_synthetic,
        "original_filename": dataset.original_filename,
        "content_sha256": dataset.content_sha256,
        "row_count": dataset.row_count,
        "column_names": list(dataset.column_names),
        "created_at": dataset.created_at.isoformat(),
        "latest_audit_id": None if audit is None else audit.id,
        "latest_audit_status": None if audit is None else audit.status,
        "mapping": None if mapping is None else _mapping_dict(mapping),
    }


def get_dataset(session: Session, dataset_id: str) -> Dataset:
    dataset = session.get(Dataset, dataset_id)
    if dataset is None:
        raise NotFoundError("Dataset not found.")
    return dataset


def list_datasets(session: Session) -> dict:
    rows = session.scalars(select(Dataset).order_by(Dataset.created_at.desc())).all()
    return {"datasets": [dataset_payload(session, row) for row in rows]}


def profile_catalog() -> dict:
    profiles = []
    for key, meta in PROFILES.items():
        profiles.append(
            {
                "id": key,
                "title": meta["title"],
                "description": meta["description"],
                "row_count": int(len(build_profile(key))),
            }
        )
    return {"profiles": profiles}


def _insert_dataset(
    session: Session,
    *,
    name: str,
    source: str,
    profile: str | None,
    original_filename: str,
    path: Path,
    digest: str,
    frame: pd.DataFrame,
    synthetic: bool,
) -> Dataset:
    dataset = Dataset(
        name=name[:200],
        source=source,
        synthetic_profile=profile,
        original_filename=original_filename,
        stored_path=str(path),
        content_sha256=digest,
        row_count=int(len(frame)),
        column_names=[str(column) for column in frame.columns],
        is_synthetic=synthetic,
    )
    session.add(dataset)
    session.commit()
    log.info("dataset stored id=%s rows=%s source=%s", dataset.id, dataset.row_count, source)
    return dataset


def create_upload(session: Session, *, filename: str | None, raw: bytes, name: str | None) -> dict:
    path, digest, _suffix = validate_and_store(filename, raw)
    try:
        frame = load_table(path)
    except ValidationFailure:
        unlink_quiet(path)
        raise
    if len(frame) == 0:
        unlink_quiet(path)
        raise ValidationFailure("empty_dataset", "The file has no data rows.")
    dataset = _insert_dataset(
        session,
        name=(name or display_name(filename))[:200],
        source="upload",
        profile=None,
        original_filename=display_name(filename),
        path=path,
        digest=digest,
        frame=frame,
        synthetic=False,
    )
    return dataset_payload(session, dataset)


def create_synthetic(session: Session, profile: str, name: str | None) -> dict:
    try:
        frame = build_profile(profile)
    except KeyError as exc:
        raise ValidationFailure("unknown_profile", str(exc)) from exc
    raw = frame.to_csv(index=False).encode("utf-8")
    path, digest = store_bytes(raw, ".csv")
    title = PROFILES[profile]["title"]
    dataset = _insert_dataset(
        session,
        name=(name or title)[:200],
        source="synthetic",
        profile=profile,
        original_filename=f"{profile}.csv",
        path=path,
        digest=digest,
        frame=frame,
        synthetic=True,
    )
    mapping = suggested_mapping(profile)
    session.add(ColumnMapping(dataset_id=dataset.id, **mapping))
    session.commit()
    return dataset_payload(session, dataset)


def save_mapping(session: Session, dataset_id: str, mapping: dict) -> dict:
    dataset = get_dataset(session, dataset_id)
    frame = load_table(Path(dataset.stored_path))
    settings = get_settings()
    prepare_frame(
        frame,
        mapping,
        max_rows=settings.max_rows,
        min_n=settings.small_group_min_n,
    )
    current = latest_mapping(session, dataset.id)
    if current is None:
        current = ColumnMapping(dataset_id=dataset.id)
        session.add(current)
    current.y_true = mapping["y_true"]
    current.y_pred = mapping.get("y_pred")
    current.y_pred_alt = mapping.get("y_pred_alt")
    current.score = mapping.get("score")
    current.score_semantics = mapping.get("score_semantics")
    current.sensitive_columns = list(mapping["sensitive_columns"])
    current.sample_weight = mapping.get("sample_weight")
    current.timestamp_column = mapping.get("timestamp_column")
    current.positive_label = mapping["positive_label"]
    session.commit()
    log.info("mapping saved dataset=%s", dataset.id)
    return dataset_payload(session, dataset)


def column_profile(frame: pd.DataFrame) -> list[dict]:
    columns = []
    for name in frame.columns:
        series = frame[name]
        missing = int(series.isna().sum())
        numeric = pd.to_numeric(series, errors="coerce")
        inferred = "numeric" if int(numeric.notna().sum()) == int(series.notna().sum()) else "text"
        columns.append({"name": str(name), "missing": missing, "inferred_type": inferred})
    return columns


def quality(session: Session, dataset_id: str) -> dict:
    dataset = get_dataset(session, dataset_id)
    frame = load_table(Path(dataset.stored_path))
    mapping = latest_mapping(session, dataset.id)
    payload: dict = {
        "dataset_id": dataset.id,
        "row_count": int(len(frame)),
        "columns": column_profile(frame),
        "mapping": None if mapping is None else _mapping_dict(mapping),
        "errors": [],
        "warnings": [],
        "class_balance": None,
        "score": None,
        "groups": [],
    }
    if mapping is None:
        payload["warnings"].append("No column mapping is saved yet.")
        return payload
    settings = get_settings()
    prepared = prepare_frame(
        frame,
        _mapping_dict(mapping),
        max_rows=settings.max_rows,
        min_n=settings.small_group_min_n,
    )
    positives = int((prepared.y_true == 1).sum())
    negatives = int((prepared.y_true == 0).sum())
    payload["class_balance"] = {
        "positive": positives,
        "negative": negatives,
        "positive_rate": None if not prepared.row_count else positives / prepared.row_count,
        "single_class": positives == 0 or negatives == 0,
    }
    payload["warnings"] = list(prepared.warnings)
    if prepared.score is not None:
        payload["score"] = {
            "mapped": True,
            "semantics": prepared.score_semantics,
            "numeric": True,
            "min": float(prepared.score.min()),
            "max": float(prepared.score.max()),
            "outside_unit_interval": int(((prepared.score < 0) | (prepared.score > 1)).sum()),
        }
    for column, labels in prepared.groups.items():
        counted = pd.Series(labels).value_counts()
        payload["groups"].append(
            {
                "column": column,
                "levels": [{"value": str(level), "n": int(count)} for level, count in counted.items()],
            }
        )
    return payload


def preview(session: Session, dataset_id: str) -> dict:
    dataset = get_dataset(session, dataset_id)
    frame = load_table(Path(dataset.stored_path))
    head = frame.head(8)
    rows = []
    for record in head.to_dict(orient="records"):
        clean = {}
        for key, value in record.items():
            if value is None or (isinstance(value, float) and pd.isna(value)):
                clean[str(key)] = None
            elif hasattr(value, "item"):
                clean[str(key)] = value.item()
            else:
                clean[str(key)] = value if isinstance(value, (int, float, str, bool)) else str(value)
        rows.append(clean)
    return {
        "columns": [str(column) for column in frame.columns],
        "rows": rows,
        "row_count": int(len(frame)),
        "truncated": len(frame) > 8,
    }


def delete_dataset(session: Session, dataset_id: str) -> None:
    dataset = get_dataset(session, dataset_id)
    paths = [contained(directory("upload"), Path(dataset.stored_path))]
    runs = session.scalars(select(AuditRun).where(AuditRun.dataset_id == dataset.id)).all()
    report_root = directory("report")
    for run in runs:
        reports = session.scalars(select(AuditReport).where(AuditReport.audit_run_id == run.id)).all()
        for report in reports:
            paths.append(contained(report_root, Path(report.html_path)))
            paths.append(contained(report_root, Path(report.json_path)))
    session.delete(dataset)
    session.commit()
    for path in paths:
        unlink_quiet(path)
    log.info("dataset deleted id=%s", dataset_id)


def purge_expired(session: Session) -> int:
    from datetime import timedelta

    from app.services.maintenance import as_utc

    days = retention_days(session)
    cutoff = as_utc(datetime_now()) - timedelta(days=days)
    rows = session.scalars(select(Dataset)).all()
    expired = [row.id for row in rows if as_utc(row.created_at) < cutoff]
    for dataset_id in expired:
        delete_dataset(session, dataset_id)
    log.info("retention purge removed=%s days=%s", len(expired), days)
    return len(expired)


def datetime_now():
    from app.models import utcnow

    return utcnow()


def dataset_count(session: Session) -> int:
    return int(session.scalar(select(func.count()).select_from(Dataset)) or 0)
