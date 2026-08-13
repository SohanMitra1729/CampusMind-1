"""
app/core/exceptions.py — Custom Domain Exceptions & FastAPI Handlers
───────────────────────────────────────────────────────────────────
Provides clean, strongly-typed domain exceptions that map to HTTP status codes
without polluting services and routers with raw HTTP exceptions.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse


class AppException(Exception):
    """Base exception for all domain errors."""
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class NotFoundError(AppException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND)


class ValidationError(AppException):
    def __init__(self, message: str = "Invalid input data"):
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST)


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED)


class ForbiddenError(AppException):
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, status_code=status.HTTP_403_FORBIDDEN)


class ConflictError(AppException):
    def __init__(self, message: str = "Resource conflict"):
        super().__init__(message, status_code=status.HTTP_409_CONFLICT)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Global exception handler for all AppException subclasses."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )
