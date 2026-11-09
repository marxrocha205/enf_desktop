"""Arquivo principal de configuração e inicialização da aplicação FastAPI."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from infrastructure.config.settings import get_settings
from infrastructure.logging.logger import setup_logging
from infrastructure.database.connection import init_db
from presentation.middlewares.logging_middleware import RequestLoggingMiddleware
from presentation.middlewares.error_handler import register_exception_handlers
from presentation.api.v1.routes import api_v1_router
from presentation.api.v1.endpoints.health import router as root_health_router
from presentation.portal import router as portal_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gerenciador de ciclo de vida (startup e shutdown) da aplicação."""
    # Inicialização: configurar logs e tabelas de banco de dados
    settings = get_settings()
    setup_logging(log_level=settings.LOG_LEVEL)
    init_db()
    yield
    # Finalização / Cleanup de recursos


def create_app() -> FastAPI:
    """Application Factory para construir e configurar a instância do FastAPI."""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "API RESTful de Telemetria IoT e Gestão de Estoque de Medicamentos. "
            "Gerencia o catálogo de medicamentos, movimentações de estoque, "
            "recebimento de telemetria corporal de sensores ESP32/Arduino e consumo pelo aplicativo."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # 1. Configuração de CORS (Cross-Origin Resource Sharing)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Middlewares de aplicação (Logging de requisições e latência)
    app.add_middleware(RequestLoggingMiddleware)

    # 3. Tratamento padronizado de exceções
    register_exception_handlers(app)

    # 4. Inclusão dos Roteadores
    app.include_router(portal_router)       # /portal e / para gestão visual de medicamentos e estoque
    app.include_router(root_health_router)  # /health na raiz para probes do Render
    app.include_router(api_v1_router)       # /api/v1/medications, /api/v1/telemetry e /api/v1/health

    return app


# Instância padrão utilizada por servidores ASGI (ex: uvicorn presentation.main:app)
app = create_app()
