"""Endpoint de verificação de integridade e saúde da aplicação (Liveness/Readiness)."""

from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from infrastructure.database.connection import get_db
from infrastructure.config.settings import get_settings

router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get("/health", summary="Health Check")
def check_health(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Retorna o status operacional da API e da conexão com o banco de dados."""
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"unhealthy: {str(exc)}"

    return {
        "status": "online" if db_status == "ok" else "degraded",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database": db_status,
    }
