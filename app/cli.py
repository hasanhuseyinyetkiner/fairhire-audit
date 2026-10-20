"""Maintenance commands. `python -m app.cli purge` and `python -m app.cli seed`."""

from __future__ import annotations

import argparse

from app.db import session_scope
from app.main import upgrade_database
from app.services.datasets import purge_expired
from app.services.maintenance import ensure_settings
from app.services.seed import seed_if_empty
from app.settings import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(prog="fairhire")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("purge", help="Delete datasets older than the retention setting.")
    sub.add_parser("seed", help="Load synthetic demo audits when the database is empty.")
    args = parser.parse_args()
    settings = get_settings()
    from pathlib import Path

    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.report_dir).mkdir(parents=True, exist_ok=True)
    upgrade_database()
    with session_scope() as session:
        ensure_settings(session)
        if args.command == "purge":
            removed = purge_expired(session)
            print(f"purged {removed}")
        elif args.command == "seed":
            created = seed_if_empty(session)
            print(f"seeded {len(created)}")


if __name__ == "__main__":
    main()
