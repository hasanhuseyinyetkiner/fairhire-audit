"""Loopback entry point: python -m app."""

from __future__ import annotations

import uvicorn

from app.main import configure_logging
from app.settings import enforce_bind, get_settings


def main() -> None:
    configure_logging()
    settings = get_settings()
    enforce_bind(settings)
    uvicorn.run("app.main:app", host=settings.bind_host, port=settings.port)


if __name__ == "__main__":
    main()
