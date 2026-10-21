#!/usr/bin/env python3
"""Fail if local markdown links (files, directories, anchors within files) are broken."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
SKIP_PREFIXES = ("http://", "https://", "mailto:", "#")


def check_file(md: Path) -> list[str]:
    errors: list[str] = []
    text = md.read_text(encoding="utf-8")
    for match in LINK_RE.finditer(text):
        raw = match.group(2).strip()
        if raw.startswith(SKIP_PREFIXES) or raw.startswith("`"):
            continue
        target, _, _fragment = raw.partition("#")
        if not target:
            continue
        path = (md.parent / target).resolve()
        try:
            path.relative_to(ROOT)
        except ValueError:
            errors.append(f"{md.relative_to(ROOT)}: escapes repo → {raw}")
            continue
        if not path.exists():
            errors.append(f"{md.relative_to(ROOT)}: missing {raw}")
    return errors


def main() -> int:
    errors: list[str] = []
    for md in ROOT.rglob("*.md"):
        if "node_modules" in md.parts or ".venv" in md.parts:
            continue
        errors.extend(check_file(md))
    if errors:
        print("Broken local markdown links:")
        for err in errors:
            print(f"  - {err}")
        return 1
    print(f"OK: local markdown links resolved under {ROOT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
