"""Configuração do subsistema nativo de logging da aplicação."""

import logging
import sys


def setup_logging(log_level: str = "INFO") -> None:
    """Configura o logger nativo com formato padronizado e saída no stdout."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    log_format = (
        "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s"
    )
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )

    # Reduz ruído de logs de dependências de terceiros
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
