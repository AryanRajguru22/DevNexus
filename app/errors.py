"""API error envelope (docs/TEAM_CONTRACT.md section 5). SHARED FILE (owner: Aryan)."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details if details is not None else {}


def not_authenticated(message: str = "Missing or unknown X-User-Id header") -> ApiError:
    return ApiError(401, "not_authenticated", message)


def forbidden(message: str) -> ApiError:
    return ApiError(403, "forbidden", message)


def not_found(what: str) -> ApiError:
    return ApiError(404, "not_found", f"{what} not found")


def invalid_transition(message: str, **details: Any) -> ApiError:
    return ApiError(409, "invalid_transition", message, details)


def retry_limit_exceeded(message: str, **details: Any) -> ApiError:
    return ApiError(409, "retry_limit_exceeded", message, details)


def agent_inactive(agent_type: str) -> ApiError:
    return ApiError(409, "agent_inactive", f"The '{agent_type}' agent is not active in this project's pipeline")


def validation_error(message: str, code: str = "validation_error", details: Any = None) -> ApiError:
    return ApiError(422, code, message, details)


def _envelope(status: int, code: str, message: str, details: Any = None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "details": details if details is not None else {}}},
    )


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return _envelope(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields = [
            {"field": ".".join(str(p) for p in e["loc"] if p != "body"), "message": e["msg"]} for e in exc.errors()
        ]
        return _envelope(422, "validation_error", "Request validation failed", fields)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
        return _envelope(exc.status_code, code, str(exc.detail))
