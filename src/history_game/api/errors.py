"""Centralized RFC 9457 ProblemDetails error handlers for FastAPI."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from history_game.domain.exceptions import (
    DomainError,
    EntityNotFoundError,
    InvalidGameActionError,
    SessionAlreadyCompletedError,
)


def _problem_response(
    *,
    status_code: int,
    code: str,
    title: str,
    detail: str,
    instance: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        media_type="application/problem+json",
        content={
            "type": f"https://chronoquest.local/problems/{code}",
            "title": title,
            "status": status_code,
            "detail": detail,
            "instance": instance,
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register domain and validation exception translators returning RFC 9457 ProblemDetails."""

    @app.exception_handler(EntityNotFoundError)
    async def handle_not_found(request: Request, exc: EntityNotFoundError) -> JSONResponse:
        return _problem_response(
            status_code=status.HTTP_404_NOT_FOUND,
            code=exc.code,
            title="Resource Not Found",
            detail=exc.message,
            instance=str(request.url.path),
        )

    @app.exception_handler(SessionAlreadyCompletedError)
    async def handle_session_completed(
        request: Request, exc: SessionAlreadyCompletedError
    ) -> JSONResponse:
        return _problem_response(
            status_code=status.HTTP_409_CONFLICT,
            code=exc.code,
            title="Session Already Completed",
            detail=exc.message,
            instance=str(request.url.path),
        )

    @app.exception_handler(InvalidGameActionError)
    async def handle_invalid_action(
        request: Request, exc: InvalidGameActionError
    ) -> JSONResponse:
        return _problem_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code=exc.code,
            title="Invalid Game Action",
            detail=exc.message,
            instance=str(request.url.path),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _problem_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="validation_error",
            title="Request Validation Error",
            detail=str(exc.errors()),
            instance=str(request.url.path),
        )

    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        return _problem_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=exc.code,
            title="Domain Error",
            detail=exc.message,
            instance=str(request.url.path),
        )
