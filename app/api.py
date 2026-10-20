"""HTTP routes."""

from __future__ import annotations

import importlib.metadata as metadata

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app import __version__
from app.db import database_ready, get_db, session_scope
from app.schemas import AuditCreate, MappingIn, SyntheticIn, ThresholdIn
from app.services.audits import (
    audit_payload,
    create_threshold,
    execute_audit,
    group_view,
    read_report,
    start_run,
)
from app.services.datasets import (
    create_synthetic,
    create_upload,
    dataset_payload,
    delete_dataset,
    get_dataset,
    list_datasets,
    preview,
    profile_catalog,
    quality,
    save_mapping,
)
from app.settings import LOOPBACK_HOSTS, get_settings

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/ready")
def ready() -> dict:
    if not database_ready():
        raise HTTPException(status_code=503, detail="Database is not ready.")
    return {"status": "ready"}


@router.get("/api/meta")
def meta() -> dict:
    settings = get_settings()
    demo = settings.app_env == "demo"
    return {
        "name": "FairHire Audit",
        "version": __version__,
        "app_env": settings.app_env,
        "demo": demo,
        "banner": "Local demo · synthetic data" if demo else None,
        "bind_host": settings.bind_host,
        "loopback_only": settings.bind_host in LOOPBACK_HOSTS,
        "retention_days": settings.data_retention_days,
        "bootstrap_cap": settings.bootstrap_max_iterations,
        "small_group_min_n": settings.small_group_min_n,
        "fairlearn_version": metadata.version("fairlearn"),
        "decision_engine": False,
    }


@router.get("/api/synthetic-profiles")
def synthetic_profiles() -> dict:
    return profile_catalog()


@router.get("/api/datasets")
def datasets(session: Session = Depends(get_db)) -> dict:
    return list_datasets(session)


@router.post("/api/datasets")
async def upload_dataset(
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
) -> dict:
    settings = get_settings()
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > settings.max_upload_bytes:
            raise HTTPException(status_code=413, detail="The file exceeds the upload limit.")
        chunks.append(chunk)
    raw = b"".join(chunks)
    filename = file.filename

    def work() -> dict:
        with session_scope() as session:
            return create_upload(session, filename=filename, raw=raw, name=name)

    return await run_in_threadpool(work)


@router.post("/api/datasets/synthetic")
async def synthetic_dataset(body: SyntheticIn) -> dict:
    def work() -> dict:
        with session_scope() as session:
            return create_synthetic(session, body.profile, body.name)

    return await run_in_threadpool(work)


@router.get("/api/datasets/{dataset_id}")
def dataset_detail(dataset_id: str, session: Session = Depends(get_db)) -> dict:
    return dataset_payload(session, get_dataset(session, dataset_id))


@router.get("/api/datasets/{dataset_id}/preview")
def dataset_preview(dataset_id: str, session: Session = Depends(get_db)) -> dict:
    return preview(session, dataset_id)


@router.get("/api/datasets/{dataset_id}/quality")
def dataset_quality(dataset_id: str, session: Session = Depends(get_db)) -> dict:
    return quality(session, dataset_id)


@router.post("/api/datasets/{dataset_id}/mapping")
def put_mapping(dataset_id: str, body: MappingIn, session: Session = Depends(get_db)) -> dict:
    return save_mapping(session, dataset_id, body.model_dump())


@router.delete("/api/datasets/{dataset_id}")
def remove_dataset(dataset_id: str, session: Session = Depends(get_db)) -> dict:
    delete_dataset(session, dataset_id)
    return {"deleted": dataset_id}


@router.post("/api/audits")
async def create_audit(body: AuditCreate, session: Session = Depends(get_db)) -> dict:
    dataset = get_dataset(session, body.dataset_id)
    run_id = start_run(
        session,
        dataset,
        iterations=body.bootstrap_iterations,
        seed=body.seed,
        min_n=body.small_group_min_n,
    )
    await run_in_threadpool(execute_audit, run_id)
    with session_scope() as fresh:
        return audit_payload(fresh, run_id)


@router.get("/api/audits/{audit_id}")
def get_audit(audit_id: str, session: Session = Depends(get_db)) -> dict:
    return audit_payload(session, audit_id)


@router.get("/api/audits/{audit_id}/groups")
async def get_groups(audit_id: str, intersection: bool = False) -> dict:
    def work() -> dict:
        with session_scope() as fresh:
            return group_view(fresh, audit_id, intersection=intersection)

    return await run_in_threadpool(work)


@router.post("/api/audits/{audit_id}/threshold-scenarios")
async def threshold_scenario(audit_id: str, body: ThresholdIn) -> dict:
    def work() -> dict:
        with session_scope() as fresh:
            return create_threshold(fresh, audit_id, body.threshold)

    return await run_in_threadpool(work)


@router.get("/api/audits/{audit_id}/report.html")
def report_html(audit_id: str, session: Session = Depends(get_db)) -> Response:
    body, media = read_report(session, audit_id, "html")
    return Response(content=body, media_type=media)


@router.get("/api/audits/{audit_id}/report.json")
def report_json(audit_id: str, session: Session = Depends(get_db)) -> Response:
    body, media = read_report(session, audit_id, "json")
    return Response(content=body, media_type=media)
