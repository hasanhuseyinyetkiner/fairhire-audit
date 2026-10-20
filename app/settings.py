"""Runtime configuration. Defaults are a loopback SQLite demo."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FAIRHIRE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "demo"
    database_url: str = "sqlite:///./data/fairhire.db"
    bind_host: str = "127.0.0.1"
    port: int = 8104
    allow_network_bind: bool = False
    data_retention_days: int = 30
    upload_dir: str = "./data/uploads"
    report_dir: str = "./data/reports"
    max_upload_bytes: int = 20 * 1024 * 1024
    max_rows: int = 50_000
    bootstrap_iterations: int = 1000
    bootstrap_max_iterations: int = 1000
    bootstrap_seed: int = 20261020
    small_group_min_n: int = 30
    stale_run_seconds: int = 900
    seed_demo: bool = True
    cors_origins: str = "http://127.0.0.1:5104,http://localhost:5104"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


def _absolute(path_str: str) -> str:
    path = Path(path_str)
    if not path.is_absolute():
        path = ROOT / path
    return str(path.resolve())


def _normalize_database_url(url: str) -> str:
    override = os.environ.get("DATABASE_URL")
    if override and "FAIRHIRE_DATABASE_URL" not in os.environ:
        url = override
    if not url.startswith("sqlite:///"):
        return url
    if url == "sqlite://":
        return url
    raw = url[len("sqlite:///") :]
    if raw == ":memory:":
        return url
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT / path
    return "sqlite:///" + path.resolve().as_posix()


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    return settings.model_copy(
        update={
            "database_url": _normalize_database_url(settings.database_url),
            "upload_dir": _absolute(settings.upload_dir),
            "report_dir": _absolute(settings.report_dir),
        }
    )


def enforce_bind(settings: Settings) -> None:
    """Refuse a non-loopback bind unless the operator opts in explicitly."""
    if settings.bind_host not in LOOPBACK_HOSTS and not settings.allow_network_bind:
        raise SystemExit(
            f"Refusing to bind {settings.bind_host}. Set FAIRHIRE_ALLOW_NETWORK_BIND=true to listen beyond loopback."
        )
