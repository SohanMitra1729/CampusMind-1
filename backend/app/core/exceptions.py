"""
app/core/exceptions.py — Custom Domain Exceptions & FastAPI Handlers
───────────────────────────────────────────────────────────────────
Provides:
  - AppException: base domain exception with HTTP status code
  - app_exception_handler: global FastAPI handler for AppException

Usage in services/routers:
    from app.core.exceptions import AppException
    raise AppException("Something went wrong", status_code=400)

Or raise subclasses as you add them:
    raise AppException("Not found", status_code=404)
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse


class AppException(Exception):
    """
    Base exception for all CampusMind domain errors.
    Automatically caught by the global exception handler registered in main.py.
    """
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Global exception handler for all AppException instances."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )
