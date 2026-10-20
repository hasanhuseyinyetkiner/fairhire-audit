"""Retention purge and the stale-run reaper."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditRun, AuditSetting, utcnow
from app.settings import get_settings


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def ensure_settings(session: Session) -> None:
    key = "data_retention_days"
    value = str(get_settings().data_retention_days)
    row = session.get(AuditSetting, key)
    if row is None:
        session.add(AuditSetting(key=key, value=value))
    else:
        row.value = value
    session.commit()


def retention_days(session: Session) -> int:
    row = session.get(AuditSetting, "data_retention_days")
    if row is None:
        return get_settings().data_retention_days
    return int(row.value)


def reap_stale_runs(session: Session, *, now: datetime | None = None, stale_seconds: int) -> int:
    moment = now or utcnow()
    cutoff = moment - timedelta(seconds=stale_seconds)
    runs = session.scalars(select(AuditRun).where(AuditRun.status == "running")).all()
    found = 0
    for run in runs:
        heartbeat = None if run.heartbeat_at is None else as_utc(run.heartbeat_at)
        if heartbeat is None or heartbeat < cutoff:
            run.status = "failed"
            run.failure_code = "stale_run_reaped"
            run.failure_reason = f"stale_run_reaped: heartbeat older than {stale_seconds} seconds"
            run.finished_at = moment
            found += 1
    session.commit()
    return found
