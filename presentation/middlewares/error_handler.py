"""Tratamento centralizado de exceções e erros HTTP."""

import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("api.errors")


def register_exception_handlers(app: FastAPI) -> None:
    """Registra manipuladores de erro padronizados no FastAPI."""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Trata erros de validação de esquemas Pydantic (HTTP 422)."""
        logger.warning(
            "Erro de validação na rota %s: %s", request.url.path, exc.errors()
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Validation Error",
                "message": "Os dados enviados não atendem aos critérios de validação da API.",
                "details": exc.errors(),
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(
        request: Request, exc: ValueError
    ) -> JSONResponse:
        """Trata exceções de regras de domínio disparadas como ValueError (HTTP 400)."""
        logger.warning(
            "Violação de regra de negócio em %s: %s", request.url.path, str(exc)
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "Domain Rule Violation",
                "message": str(exc),
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """Trata exceções HTTP explícitas."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTP Error",
                "message": exc.detail,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Trata falhas inesperadas internas (HTTP 500) evitando vazamento de stacktrace."""
        logger.critical(
            "Erro não tratado na rota %s: %s", request.url.path, str(exc), exc_info=True
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "message": "Ocorreu um erro interno inesperado no servidor.",
            },
        )
