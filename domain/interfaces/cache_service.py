"""Interface para serviços de cache e controle de taxa / debounce."""

from abc import ABC, abstractmethod


class ICacheService(ABC):
    """Contrato abstrato para cache temporário e controle de debounce."""

    @abstractmethod
    def check_and_set_debounce(self, key: str, ttl_seconds: int = 1800) -> bool:
        """
        Retorna True se o alerta deve ser processado (chave não existia).
        Retorna False se o alerta deve ser suprimido (debounce ativo).
        """
        raise NotImplementedError
