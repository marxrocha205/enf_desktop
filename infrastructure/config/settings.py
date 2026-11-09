"""Configurações centralizadas da aplicação utilizando pydantic-settings."""

from functools import lru_cache
from typing import List, Optional, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações globais e carregamento de variáveis de ambiente."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Medica - Sentinela Enf"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Banco de Dados: Suporte a PostgreSQL (Neon) e SQLite local
    DATABASE_URL: str = Field(
        default="sqlite:///./iot_telemetry.db",
        description="URL de conexão com o banco de dados (Neon PostgreSQL ou SQLite)",
    )

    # Redis (Upstash) para Debounce de Alertas e Cache (TCP e REST)
    REDIS_URL: Optional[str] = Field(
        default=None,
        description="URL de conexão TCP com o Redis/Upstash (ex: rediss://default:TOKEN@endpoint:6379)",
    )
    UPSTASH_REDIS_REST_URL: Optional[str] = Field(
        default=None,
        description="URL da API REST do Upstash Redis (ex: https://endpoint.upstash.io)",
    )
    UPSTASH_REDIS_REST_TOKEN: Optional[str] = Field(
        default=None,
        description="Token de autenticação da API REST do Upstash Redis",
    )

    ALLOWED_ORIGINS: Union[str, List[str]] = "*"

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Converte string de origens separadas por vírgula em lista."""
        if isinstance(v, str):
            if v == "*":
                return ["*"]
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


@lru_cache()
def get_settings() -> Settings:
    """Instância singleton com cache das configurações."""
    return Settings()
