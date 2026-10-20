"""Upload storage. Internal names are random. User paths are never joined."""

from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

import pandas as pd

from app.errors import ValidationFailure
from app.settings import get_settings


def directory(kind: str) -> Path:
    settings = get_settings()
    root = Path(settings.upload_dir if kind == "upload" else settings.report_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def contained(root: Path, path: Path) -> Path:
    resolved_root = root.resolve()
    resolved = path.resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise ValidationFailure("unsafe_path", "A stored file escaped its directory.")
    return resolved


def display_name(filename: str | None) -> str:
    base = Path(filename or "upload").name
    cleaned = "".join(ch if ch.isprintable() and ch not in "\\/:" else "_" for ch in base)
    return cleaned[:180] or "upload"


def _suffix(filename: str | None) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix not in {".csv", ".parquet"}:
        raise ValidationFailure(
            "unsupported_type",
            "Upload a .csv or .parquet file.",
            {"file": "Allowed extensions are .csv and .parquet."},
        )
    return suffix


def validate_and_store(filename: str | None, raw: bytes) -> tuple[Path, str, str]:
    settings = get_settings()
    if not raw:
        raise ValidationFailure("empty_dataset", "The file is empty.")
    if len(raw) > settings.max_upload_bytes:
        raise ValidationFailure(
            "file_too_large",
            f"The file exceeds the {settings.max_upload_bytes} byte limit.",
        )
    suffix = _suffix(filename)
    if suffix == ".csv":
        if raw.startswith(b"PAR1"):
            raise ValidationFailure(
                "wrong_type",
                "This file looks like Parquet. Upload it with a .parquet extension.",
            )
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValidationFailure("unreadable_csv", "CSV files must be UTF-8 text.") from exc
    else:
        if not raw.startswith(b"PAR1"):
            raise ValidationFailure(
                "unreadable_parquet",
                "The file does not start with Parquet magic bytes.",
            )
    digest = hashlib.sha256(raw).hexdigest()
    path = directory("upload") / f"{uuid4().hex}{suffix}"
    path.write_bytes(raw)
    return path, digest, suffix


def store_bytes(raw: bytes, suffix: str) -> tuple[Path, str]:
    digest = hashlib.sha256(raw).hexdigest()
    path = directory("upload") / f"{uuid4().hex}{suffix}"
    path.write_bytes(raw)
    return path, digest


def load_table(path: Path) -> pd.DataFrame:
    path = contained(directory("upload"), path)
    try:
        if path.suffix == ".csv":
            frame = pd.read_csv(path)
        elif path.suffix == ".parquet":
            frame = pd.read_parquet(path, engine="pyarrow")
        else:
            raise ValidationFailure("unsupported_type", "Upload a .csv or .parquet file.")
    except ValidationFailure:
        raise
    except pd.errors.EmptyDataError as exc:
        raise ValidationFailure("empty_dataset", "The file has no data rows.") from exc
    except Exception as exc:
        kind = "CSV" if path.suffix == ".csv" else "Parquet"
        raise ValidationFailure("unreadable_file", f"The file could not be parsed as {kind}.") from exc
    frame.columns = [str(column).strip() for column in frame.columns]
    if len(frame.columns) > 100:
        raise ValidationFailure("too_many_columns", "The file has more than 100 columns.")
    return frame


def unlink_quiet(path: Path | None) -> None:
    if path is None:
        return
    if path.exists():
        path.unlink()
