from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, PlainSerializer

from app.utils.timeutil import to_iso_z

IsoDateTime = Annotated[datetime, PlainSerializer(to_iso_z, return_type=str)]


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class OpenModel(BaseModel):
    """Response model that documents key fields but allows additional provenance fields."""

    model_config = ConfigDict(extra="allow")


class ErrorBody(ApiModel):
    code: str
    message: str
    requestId: str | None = None
    details: Any = None
    simulationId: str | None = None


class ErrorResponse(ApiModel):
    error: ErrorBody


class Quantity(OpenModel):
    value: float | int | str | None
    unit: str
    source: str
    description: str | None = None
    methodVersion: str | None = None
