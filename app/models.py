"""Normalized audit records. Deleting a dataset cascades to every derived row."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return str(uuid4())


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200))
    source: Mapped[str] = mapped_column(String(32))
    synthetic_profile: Mapped[str | None] = mapped_column(String(80))
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(500))
    content_sha256: Mapped[str] = mapped_column(String(64))
    row_count: Mapped[int] = mapped_column(Integer)
    column_names: Mapped[list] = mapped_column(JSON)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    mappings: Mapped[list[ColumnMapping]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan", passive_deletes=True
    )
    audits: Mapped[list[AuditRun]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan", passive_deletes=True
    )


class ColumnMapping(Base):
    __tablename__ = "column_mappings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), index=True)
    y_true: Mapped[str] = mapped_column(String(200))
    y_pred: Mapped[str | None] = mapped_column(String(200))
    y_pred_alt: Mapped[str | None] = mapped_column(String(200))
    score: Mapped[str | None] = mapped_column(String(200))
    score_semantics: Mapped[str | None] = mapped_column(String(32))
    sensitive_columns: Mapped[list] = mapped_column(JSON)
    sample_weight: Mapped[str | None] = mapped_column(String(200))
    timestamp_column: Mapped[str | None] = mapped_column(String(200))
    positive_label: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    dataset: Mapped[Dataset] = relationship(back_populates="mappings")
    audits: Mapped[list[AuditRun]] = relationship(
        back_populates="mapping", cascade="all, delete-orphan", passive_deletes=True
    )


class AuditRun(Base):
    __tablename__ = "audit_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), index=True)
    mapping_id: Mapped[str] = mapped_column(ForeignKey("column_mappings.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="running")
    failure_code: Mapped[str | None] = mapped_column(String(64))
    failure_reason: Mapped[str | None] = mapped_column(Text)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    seed: Mapped[int] = mapped_column(Integer)
    bootstrap_iterations: Mapped[int] = mapped_column(Integer)
    bootstrap_iterations_requested: Mapped[int] = mapped_column(Integer)
    bootstrap_capped: Mapped[bool] = mapped_column(Boolean, default=False)
    small_group_min_n: Mapped[int] = mapped_column(Integer)
    code_version: Mapped[str] = mapped_column(String(32))
    git_sha: Mapped[str | None] = mapped_column(String(40))
    fairlearn_version: Mapped[str] = mapped_column(String(32))
    sklearn_version: Mapped[str] = mapped_column(String(32))
    numpy_version: Mapped[str] = mapped_column(String(32))
    scipy_version: Mapped[str] = mapped_column(String(32))
    pandas_version: Mapped[str] = mapped_column(String(32))
    mapping_snapshot: Mapped[dict] = mapped_column(JSON)
    result_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    dataset: Mapped[Dataset] = relationship(back_populates="audits")
    mapping: Mapped[ColumnMapping] = relationship(back_populates="audits")
    metrics: Mapped[list[AuditMetric]] = relationship(
        back_populates="audit_run", cascade="all, delete-orphan", passive_deletes=True
    )
    group_metrics: Mapped[list[GroupMetric]] = relationship(
        back_populates="audit_run", cascade="all, delete-orphan", passive_deletes=True
    )
    intervals: Mapped[list[ConfidenceInterval]] = relationship(
        back_populates="audit_run", cascade="all, delete-orphan", passive_deletes=True
    )
    scenarios: Mapped[list[ThresholdScenario]] = relationship(
        back_populates="audit_run", cascade="all, delete-orphan", passive_deletes=True
    )
    reports: Mapped[list[AuditReport]] = relationship(
        back_populates="audit_run", cascade="all, delete-orphan", passive_deletes=True
    )


class AuditMetric(Base):
    __tablename__ = "audit_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    audit_run_id: Mapped[str] = mapped_column(ForeignKey("audit_runs.id", ondelete="CASCADE"), index=True)
    scope: Mapped[str] = mapped_column(String(32))
    group_column: Mapped[str | None] = mapped_column(String(200))
    name: Mapped[str] = mapped_column(String(80))
    label: Mapped[str] = mapped_column(String(160))
    value: Mapped[float | None] = mapped_column(Float)
    numerator: Mapped[float | None] = mapped_column(Float)
    denominator: Mapped[float | None] = mapped_column(Float)
    undefined_reason: Mapped[str | None] = mapped_column(String(80))
    formula: Mapped[str] = mapped_column(Text)
    sample_size: Mapped[float | None] = mapped_column(Float)
    detail: Mapped[dict | None] = mapped_column(JSON)

    audit_run: Mapped[AuditRun] = relationship(back_populates="metrics")


class GroupMetric(Base):
    __tablename__ = "group_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    audit_run_id: Mapped[str] = mapped_column(ForeignKey("audit_runs.id", ondelete="CASCADE"), index=True)
    group_column: Mapped[str] = mapped_column(String(200))
    group_value: Mapped[str] = mapped_column(String(200))
    is_intersection: Mapped[bool] = mapped_column(Boolean, default=False)
    sample_size: Mapped[int] = mapped_column(Integer)
    suppressed: Mapped[bool] = mapped_column(Boolean, default=False)
    suppression_reason: Mapped[str | None] = mapped_column(String(80))
    metric_name: Mapped[str] = mapped_column(String(80))
    label: Mapped[str] = mapped_column(String(160))
    value: Mapped[float | None] = mapped_column(Float)
    numerator: Mapped[float | None] = mapped_column(Float)
    denominator: Mapped[float | None] = mapped_column(Float)
    undefined_reason: Mapped[str | None] = mapped_column(String(80))
    formula: Mapped[str] = mapped_column(Text)

    audit_run: Mapped[AuditRun] = relationship(back_populates="group_metrics")


class ConfidenceInterval(Base):
    __tablename__ = "confidence_intervals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    audit_run_id: Mapped[str] = mapped_column(ForeignKey("audit_runs.id", ondelete="CASCADE"), index=True)
    metric_name: Mapped[str] = mapped_column(String(80))
    group_column: Mapped[str | None] = mapped_column(String(200))
    group_value: Mapped[str | None] = mapped_column(String(200))
    point: Mapped[float | None] = mapped_column(Float)
    lower: Mapped[float | None] = mapped_column(Float)
    upper: Mapped[float | None] = mapped_column(Float)
    iterations: Mapped[int] = mapped_column(Integer)
    valid_replicates: Mapped[int] = mapped_column(Integer)
    seed: Mapped[int] = mapped_column(Integer)
    method: Mapped[str] = mapped_column(String(80))
    sampling_unit: Mapped[str] = mapped_column(String(40))
    undefined_reason: Mapped[str | None] = mapped_column(String(80))

    audit_run: Mapped[AuditRun] = relationship(back_populates="intervals")


class ThresholdScenario(Base):
    __tablename__ = "threshold_scenarios"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    audit_run_id: Mapped[str] = mapped_column(ForeignKey("audit_runs.id", ondelete="CASCADE"), index=True)
    threshold: Mapped[float] = mapped_column(Float)
    score_semantics: Mapped[str] = mapped_column(String(32))
    results: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    audit_run: Mapped[AuditRun] = relationship(back_populates="scenarios")


class AuditReport(Base):
    __tablename__ = "audit_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    audit_run_id: Mapped[str] = mapped_column(ForeignKey("audit_runs.id", ondelete="CASCADE"), index=True)
    html_path: Mapped[str] = mapped_column(String(500))
    json_path: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    audit_run: Mapped[AuditRun] = relationship(back_populates="reports")


class AuditSetting(Base):
    __tablename__ = "audit_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
