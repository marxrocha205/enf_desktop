"""Gerenciamento de conexões e sessões do SQLAlchemy com suporte a SQLite e PostgreSQL."""

from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from infrastructure.config.settings import get_settings

settings = get_settings()

db_url = settings.DATABASE_URL
# Normalização para SQLAlchemy 2.0 caso a URL do Render venha como postgres://
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif db_url.startswith("postgresql://") and "+psycopg2" not in db_url:
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

# Configurações de conexão específicas para SQLite vs PostgreSQL
connect_args = {}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency injection para fornecer a sessão do SQLAlchemy nas rotas."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Cria tabelas necessárias no banco de dados e garante colunas de migração."""
    import infrastructure.database.models  # noqa: F401 - Garante registro dos modelos no metadata

    Base.metadata.create_all(bind=engine)

    # Migração leve caso o arquivo SQLite já existisse antes da criação de lotes
    migrations = [
        "ALTER TABLE medications ADD COLUMN barcode VARCHAR(100)",
        "ALTER TABLE stock_movements ADD COLUMN batch_id VARCHAR(36)",
        "ALTER TABLE stock_movements ADD COLUMN batch_number VARCHAR(80)",
    ]
    for stmt in migrations:
        try:
            with engine.connect() as conn:
                conn.execute(text(stmt))
                conn.commit()
        except Exception:
            pass
