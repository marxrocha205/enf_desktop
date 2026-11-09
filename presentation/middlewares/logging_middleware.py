"""Middleware para logging e medição de tempo das requisições HTTP."""

import logging
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("api.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Intercepta requisições para medir tempo de resposta e registrar tráfego."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                "%s %s - Status: %d - Tempo: %.2fms - IP: %s",
                method,
                path,
                response.status_code,
                duration_ms,
                client_ip,
            )
            response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"
            return response
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "Falha na requisição %s %s após %.2fms: %s",
                method,
                path,
                duration_ms,
                str(exc),
                exc_info=True,
            )
            raise exc
