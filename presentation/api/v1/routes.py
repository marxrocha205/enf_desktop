"""Agregador de rotas da versão 1 (v1) da API."""

from fastapi import APIRouter
from presentation.api.v1.endpoints.telemetry import router as telemetry_router
from presentation.api.v1.endpoints.health import router as health_router
from presentation.api.v1.endpoints.medications import router as medications_router

api_v1_router = APIRouter(prefix="/api/v1")

# Inclusão dos roteadores de recursos
api_v1_router.include_router(medications_router)
api_v1_router.include_router(telemetry_router)
api_v1_router.include_router(health_router)
