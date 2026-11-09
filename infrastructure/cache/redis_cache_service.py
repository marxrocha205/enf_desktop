"""Implementação concreta de ICacheService integrada com Upstash Redis."""

from domain.interfaces.cache_service import ICacheService
from infrastructure.cache.redis import RedisClient


class RedisCacheService(ICacheService):
    """Serviço de cache e debounce utilizando Upstash Redis."""

    def check_and_set_debounce(self, key: str, ttl_seconds: int = 1800) -> bool:
        """Verifica e grava a trava de debounce no Redis."""
        return RedisClient.check_and_set_debounce(key=key, ttl_seconds=ttl_seconds)
