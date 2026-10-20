"""Isolate every test from the developer's demo database."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def isolate_environment(tmp_path, monkeypatch):
    postgres = os.environ.get("TEST_DATABASE_URL")
    if postgres:
        monkeypatch.setenv("FAIRHIRE_DATABASE_URL", postgres)
    else:
        database = tmp_path / "fairhire.db"
        monkeypatch.setenv("FAIRHIRE_DATABASE_URL", f"sqlite:///{database.as_posix()}")
    monkeypatch.setenv("FAIRHIRE_UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("FAIRHIRE_REPORT_DIR", str(tmp_path / "reports"))
    monkeypatch.setenv("FAIRHIRE_SEED_DEMO", "false")
    monkeypatch.setenv("FAIRHIRE_APP_ENV", "test")
    monkeypatch.setenv("FAIRHIRE_BOOTSTRAP_ITERATIONS", "40")
    monkeypatch.setenv("FAIRHIRE_BIND_HOST", "127.0.0.1")
    monkeypatch.setenv("FAIRHIRE_ALLOW_NETWORK_BIND", "false")
    from app.db import reset_engine
    from app.settings import get_settings

    get_settings.cache_clear()
    reset_engine()
    yield
    reset_engine()
    get_settings.cache_clear()


@pytest.fixture
def client():
    from app.db import truncate_data_tables
    from app.main import app
    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        if os.environ.get("TEST_DATABASE_URL"):
            truncate_data_tables()
        yield test_client
