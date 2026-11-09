"""Gerenciamento de conexão e operações de cache/debounce com Upstash Redis (REST e TCP)."""

import json
import logging
import urllib.error
import urllib.request
from typing import Optional, List, Any
import redis
from infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RedisClient:
    """Cliente resiliente com suporte duplo: Upstash REST API (HTTPS) e Redis TCP tradicional."""

    _tcp_instance: Optional[redis.Redis] = None

    @classmethod
    def _execute_rest_command(cls, command: List[Any]) -> tuple[bool, Optional[Any]]:
        """
        Executa um comando Redis via API REST do Upstash via HTTPS.
        Retorna uma tupla (sucesso: bool, resultado: Any).
        Ideal para ambientes serverless, dispensando manutenção de conexões TCP abertas.
        """
        if not (settings.UPSTASH_REDIS_REST_URL and settings.UPSTASH_REDIS_REST_TOKEN):
            return False, None

        url = settings.UPSTASH_REDIS_REST_URL.rstrip("/")
        headers = {
            "Authorization": f"Bearer {settings.UPSTASH_REDIS_REST_TOKEN}",
            "Content-Type": "application/json",
        }
        data = json.dumps(command).encode("utf-8")
        req = urllib.request.Request(url=url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=3.0) as response:
                result = json.loads(response.read().decode("utf-8"))
                return True, result.get("result")
        except Exception as exc:
            logger.error("Falha ao executar comando Upstash REST %s: %s", command[0], exc)
            return False, None

    @classmethod
    def get_tcp_client(cls) -> Optional[redis.Redis]:
        """Retorna uma conexão TCP ativa com o Redis se configurado."""
        if not settings.REDIS_URL:
            return None

        if cls._tcp_instance is None:
            try:
                cls._tcp_instance = redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_timeout=3.0,
                    socket_connect_timeout=3.0,
                )
                cls._tcp_instance.ping()
                logger.info("Conexão TCP com Redis (Upstash) validada com sucesso.")
            except Exception as exc:
                logger.warning(
                    "Conexão TCP com Redis falhou: %s. Tentando via REST API.",
                    str(exc),
                )
                cls._tcp_instance = None

        return cls._tcp_instance

    @classmethod
    def check_and_set_debounce(
        cls, key: str, ttl_seconds: int = 1800
    ) -> bool:
        """
        Verifica se a chave já existe no cache (debounce ativo de 30 minutos).
        Se NÃO existir, define com expiração e retorna True (permite disparar alerta).
        Se JÁ existir, retorna False (alerta suprimido pelo debounce).
        Em caso de falha de rede/serviço, realiza fallback para TCP e fail-open (True).
        """
        # 1. Tenta prioritariamente via REST API (Mais resiliente e sem pooling de sockets no Render)
        if settings.UPSTASH_REDIS_REST_URL and settings.UPSTASH_REDIS_REST_TOKEN:
            success, res = cls._execute_rest_command(["SET", key, "active", "EX", ttl_seconds, "NX"])
            if success:
                # Upstash REST retorna "OK" se adquiriu a chave ou None/null se a chave já existia
                if res == "OK":
                    return True
                elif res is None:
                    return False
            # Se success == False (falha de rede/HTTP), não suprime o alerta; cai para o fallback TCP!

        # 2. Fallback para TCP tradicional
        tcp_client = cls.get_tcp_client()
        if tcp_client is not None:
            try:
                acquired = tcp_client.set(key, "active", ex=ttl_seconds, nx=True)
                return bool(acquired)
            except Exception as exc:
                logger.error("Erro ao verificar debounce via TCP: %s", exc)

        # Em caso de falha de infraestrutura externa, fail-open (permite o alerta clínico passar)
        return True
