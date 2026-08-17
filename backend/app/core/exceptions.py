"""
app/core/exceptions.py — Custom Domain Exceptions & FastAPI Handlers
───────────────────────────────────────────────────────────────────
Provides standard domain exceptions and global FastAPI exception handlers.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.core.logger import logger


class AppException(Exception):
    """
    Base domain exception for all CampusMind errors.
    Automatically caught by the global exception handler registered in main.py.
    """
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: dict = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}


class ValidationException(AppException):
    """Raised when client input fails business validation rules (400)."""
    def __init__(self, message: str, detail: dict = None):
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class UnauthorizedException(AppException):
    """Raised when authentication fails or is missing (401)."""
    def __init__(self, message: str = "Invalid or expired credentials.", detail: dict = None):
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class ForbiddenException(AppException):
    """Raised when an authenticated user lacks permission (403)."""
    def __init__(self, message: str = "Access denied.", detail: dict = None):
        super().__init__(message, status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class NotFoundException(AppException):
    """Raised when a requested resource is not found (404)."""
    def __init__(self, message: str = "Resource not found.", detail: dict = None):
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ConflictException(AppException):
    """Raised when an action conflicts with existing state e.g. duplicate vote (409)."""
    def __init__(self, message: str = "Request conflict.", detail: dict = None):
        super().__init__(message, status_code=status.HTTP_409_CONFLICT, detail=detail)


class InternalServerErrorException(AppException):
    """Raised for unexpected internal server errors (500)."""
    def __init__(self, message: str = "An internal error occurred.", detail: dict = None):
        super().__init__(message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


# ── Global FastAPI Exception Handlers ───────────────────────────────────────────

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Global handler for domain-specific AppException subclasses."""
    logger.warning(
        f"[{exc.status_code}] {request.method} {request.url.path} — {exc.message}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, **(exc.detail or {})},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Global handler for FastAPI / Pydantic request validation errors."""
    errors = exc.errors()
    first_msg = errors[0].get("msg", "Invalid request body.") if errors else "Validation error."
    first_loc = " -> ".join(str(loc) for loc in errors[0].get("loc", [])) if errors else ""
    formatted_msg = f"{first_msg} (at {first_loc})" if first_loc else first_msg

    logger.warning(
        f"[422 Validation Error] {request.method} {request.url.path} — {formatted_msg}"
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": formatted_msg, "errors": errors},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global catch-all for any unhandled Python exceptions.
    Logs the full stack trace on the server while returning a safe, sanitized message.
    """
    logger.exception(
        f"[500 Internal Error] Unhandled exception on {request.method} {request.url.path}: {exc}"
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please try again later."},
    )
