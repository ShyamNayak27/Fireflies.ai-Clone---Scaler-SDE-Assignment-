"""RFC-7807 problem+json error handling.

Every error response has the same shape, so the frontend has exactly one error
type to handle instead of a different ad-hoc JSON shape per endpoint.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class NotFoundError(Exception):
    def __init__(self, resource: str, identifier: object) -> None:
        self.resource = resource
        self.identifier = identifier
        super().__init__(f"{resource} {identifier} not found")


class ConflictError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def _problem(status_code: int, title: str, detail: str, type_: str = "about:blank") -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        media_type="application/problem+json",
        content={"type": type_, "title": title, "status": status_code, "detail": detail},
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def _not_found(_req: Request, exc: NotFoundError) -> JSONResponse:
        return _problem(
            status.HTTP_404_NOT_FOUND,
            "Not Found",
            str(exc),
            type_="/problems/not-found",
        )

    @app.exception_handler(ConflictError)
    async def _conflict(_req: Request, exc: ConflictError) -> JSONResponse:
        return _problem(
            status.HTTP_409_CONFLICT, "Conflict", exc.message, type_="/problems/conflict"
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_req: Request, exc: RequestValidationError) -> JSONResponse:
        return _problem(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Validation Error",
            str(exc.errors()),
            type_="/problems/validation",
        )
