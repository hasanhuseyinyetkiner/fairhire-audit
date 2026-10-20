"""Seed the local demo with deterministic synthetic audits."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.services.audits import execute_audit, start_run
from app.services.datasets import create_synthetic, dataset_count, get_dataset

log = logging.getLogger("fairhire.seed")

DEMO_PROFILES = (
    "similar_accuracy_different_errors",
    "different_accuracy_similar_error_rates",
)


def seed_if_empty(session: Session) -> list[str]:
    if dataset_count(session):
        return []
    audit_ids: list[str] = []
    for profile in DEMO_PROFILES:
        payload = create_synthetic(session, profile, None)
        dataset = get_dataset(session, payload["id"])
        audit_id = start_run(session, dataset, iterations=None, seed=None, min_n=None)
        execute_audit(audit_id)
        audit_ids.append(audit_id)
    log.info("demo seed created audits=%s", len(audit_ids))
    return audit_ids
