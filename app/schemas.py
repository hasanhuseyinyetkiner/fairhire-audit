"""Request bodies. Audit responses are dicts validated against these models."""

from __future__ import annotations

import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MappingIn(BaseModel):
    y_true: str
    y_pred: str | None = None
    y_pred_alt: str | None = None
    score: str | None = None
    score_semantics: Literal["probability", "ranking_score"] | None = None
    sensitive_columns: list[str] = Field(min_length=1)
    sample_weight: str | None = None
    timestamp_column: str | None = None
    positive_label: str = "1"


class SyntheticIn(BaseModel):
    profile: str
    name: str | None = None


class AuditCreate(BaseModel):
    dataset_id: str
    bootstrap_iterations: int | None = Field(default=None, ge=1)
    seed: int | None = Field(default=None, ge=0)
    small_group_min_n: int | None = Field(default=None, ge=1, le=100_000)


class ThresholdIn(BaseModel):
    threshold: float

    @field_validator("threshold")
    @classmethod
    def finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("Threshold must be a finite number.")
        return value


class ErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    error: str
    detail: str
    fields: dict[str, Any] = Field(default_factory=dict)
