"""
Error Handling
==============
Custom exceptions + FastAPI global exception handlers.
Ensures ALL errors return consistent JSON with proper HTTP codes.
"""

import logging
import traceback
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


# ── Custom Exceptions ──────────────────────────────────────────────────────────

class AppError(Exception):
    """Base application error."""
    def __init__(self, message: str, status_code: int = 500, code: str = "INTERNAL_ERROR"):
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, resource: str = "Resource"):
        super().__init__(f"{resource} not found", 404, "NOT_FOUND")


class AuthError(AppError):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, 401, "AUTH_ERROR")


class ForbiddenError(AppError):
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, 403, "FORBIDDEN")


class ValidationError(AppError):
    def __init__(self, message: str):
        super().__init__(message, 422, "VALIDATION_ERROR")


class FileProcessingError(AppError):
    def __init__(self, message: str):
        super().__init__(message, 422, "FILE_PROCESSING_ERROR")


class RateLimitError(AppError):
    def __init__(self):
        super().__init__("Too many requests. Please try again later.", 429, "RATE_LIMIT")


class GroqAPIError(AppError):
    def __init__(self, message: str = "LLM API error"):
        super().__init__(message, 502, "LLM_ERROR")


# ── Error Response Builder ─────────────────────────────────────────────────────

def error_response(status_code: int, message: str, code: str = "ERROR", details: dict = None) -> JSONResponse:
    body = {"success": False, "error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=body)


# ── Handler Registration ───────────────────────────────────────────────────────

def register_exception_handlers(app: FastAPI):
    """Register all exception handlers on the FastAPI app."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        logger.warning("AppError [%s]: %s — %s %s", exc.code, exc.message, request.method, request.url.path)
        return error_response(exc.status_code, exc.message, exc.code)

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException):
        return error_response(exc.status_code, str(exc.detail), "HTTP_ERROR")

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        errors = [{"field": ".".join(str(x) for x in e["loc"]), "msg": e["msg"]} for e in exc.errors()]
        logger.warning("Validation error on %s: %s", request.url.path, errors)
        return error_response(422, "Request validation failed", "VALIDATION_ERROR", {"errors": errors})

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        logger.error(
            "Unhandled exception on %s %s:\n%s",
            request.method, request.url.path,
            traceback.format_exc()
        )
        return error_response(500, "An unexpected server error occurred", "INTERNAL_ERROR")
