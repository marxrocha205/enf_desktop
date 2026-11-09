"""Entrypoint raiz para execução do servidor ASGI."""

import sys
from pathlib import Path

# Garante que o diretório da API esteja no sys.path mesmo se chamado fora do diretório
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

import uvicorn
from infrastructure.config.settings import get_settings
from presentation.main import app

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "presentation.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
        log_level=settings.LOG_LEVEL.lower(),
    )
