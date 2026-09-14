"""Structured application errors and FastAPI exception handlers.

Every error response follows 06_API_CONTRACT.md §9:

    {"error": {"code": ..., "message": ..., "requestId": ..., "details": ...}}

Stack traces and server filesystem paths are never included.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.errors")


class ErrorCode:
    INVALID_REQUEST = "INVALID_REQUEST"
    NOT_FOUND = "NOT_FOUND"
    SCENARIO_NOT_FOUND = "SCENARIO_NOT_FOUND"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    MODEL_NOT_COMPATIBLE = "MODEL_NOT_COMPATIBLE"
    MODEL_VALIDATION_FAILED = "MODEL_VALIDATION_FAILED"
    RAINFALL_NOT_FOUND = "RAINFALL_NOT_FOUND"
    RAINFALL_VALIDATION_FAILED = "RAINFALL_VALIDATION_FAILED"
    UNSUPPORTED_PARAMETER = "UNSUPPORTED_PARAMETER"
    INVALID_PARAMETER = "INVALID_PARAMETER"
    SIMULATION_NOT_FOUND = "SIMULATION_NOT_FOUND"
    SIMULATION_NOT_COMPLETED = "SIMULATION_NOT_COMPLETED"
    SIMULATION_FAILED = "SIMULATION_FAILED"
    SIMULATION_TIMEOUT = "SIMULATION_TIMEOUT"
    SIMULATION_INTERRUPTED = "SIMULATION_INTERRUPTED"
    SWMM_UNAVAILABLE = "SWMM_UNAVAILABLE"
    RESULT_NOT_FOUND = "RESULT_NOT_FOUND"
    PROCESSING_FAILED = "PROCESSING_FAILED"
    GEOSPATIAL_ERROR = "GEOSPATIAL_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppError(Exception):
    """An error with a stable machine-readable code and a safe public message."""

    status_code: int = 500

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int | None = None,
        details: Any = None,
        simulation_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.details = details
        self.simulation_id = simulation_id


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


class UnprocessableError(AppError):
    status_code = 422


class ServiceUnavailableError(AppError):
    status_code = 503


def error_body(
    code: str,
    message: str,
    request: Request | None,
    details: Any = None,
    simulation_id: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "code": code,
        "message": message,
        "requestId": getattr(request.state, "request_id", None) if request is not None else None,
        "details": details,
    }
    if simulation_id:
        body["simulationId"] = simulation_id
    return {"error": body}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError) -> JSONResponse:
        if exc.status_code >= 500:
            logger.error("app_error code=%s message=%s", exc.code, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(exc.code, exc.message, request, exc.details, exc.simulation_id),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {
                "field": ".".join(str(p) for p in err.get("loc", []) if p != "body"),
                "message": err.get("msg"),
                "type": err.get("type"),
            }
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=error_body(ErrorCode.INVALID_REQUEST, "The request is invalid.", request, details),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = ErrorCode.NOT_FOUND if exc.status_code == 404 else ErrorCode.INVALID_REQUEST
        message = "The requested resource does not exist." if exc.status_code == 404 else str(exc.detail)
        return JSONResponse(status_code=exc.status_code, content=error_body(code, message, request))

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_error path=%s", request.url.path)
        return JSONResponse(
            status_code=500,
            content=error_body(ErrorCode.INTERNAL_ERROR, "An internal server error occurred.", request),
        )
