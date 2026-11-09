"""Testes unitários automatizados com Mock para o leitor serial do Arduino.

Simula a porta serial e testa a classificação térmica sem necessitar de hardware conectado.
"""

import sys
import unittest
from unittest.mock import MagicMock, patch

# Configura encoding no Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass


def classificar_temperatura(temp: float) -> str:
    """Classificação clínica da temperatura corporal."""
    if temp < 35.0:
        return "HIPOTERMIA"
    elif temp < 37.5:
        return "NORMAL"
    elif 37.5 <= temp < 37.8:
        return "ELEVATED"
    else:
        return "FEVER"


def processar_linha_serial(linha: str) -> dict:
    """Processa uma linha de texto lida da porta serial do Arduino."""
    linha_limpa = linha.strip()
    try:
        temp = float(linha_limpa)
    except ValueError:
        raise ValueError(f"Leitura inválida: '{linha_limpa}' não é um número.")

    if not (30.0 <= temp <= 45.0):
        raise ValueError(f"Temperatura ({temp}°C) fora da faixa biológica humana (30°C - 45°C).")

    return {
        "temperature": round(temp, 2),
        "status": classificar_temperatura(temp)
    }


class TestLeitorSerialArduinoMock(unittest.TestCase):
    """Bateria de testes simulando o comportamento da porta Serial do Arduino."""

    def test_classificacao_temperatura_normal(self):
        resultado = processar_linha_serial("36.6\n")
        self.assertEqual(resultado["temperature"], 36.6)
        self.assertEqual(resultado["status"], "NORMAL")

    def test_classificacao_temperatura_elevada(self):
        resultado = processar_linha_serial("37.6\r\n")
        self.assertEqual(resultado["temperature"], 37.6)
        self.assertEqual(resultado["status"], "ELEVATED")

    def test_classificacao_temperatura_febre(self):
        resultado = processar_linha_serial("38.9\n")
        self.assertEqual(resultado["temperature"], 38.9)
        self.assertEqual(resultado["status"], "FEVER")

    def test_rejeicao_temperatura_fora_de_escala(self):
        # Ex: sensor desconectado marcando temperatura ambiente ou ruído
        with self.assertRaises(ValueError):
            processar_linha_serial("18.5\n")
        with self.assertRaises(ValueError):
            processar_linha_serial("50.0\n")

    def test_rejeicao_texto_invalido(self):
        # Ex: mensagem de inicialização do Arduino como "Arduino Inicializado..."
        with self.assertRaises(ValueError):
            processar_linha_serial("Arduino pronto!\n")

    def test_mock_fluxo_porta_serial(self):
        """Simula a porta serial enviando 3 leituras consecutivas do Arduino usando Mock nativo."""
        mock_porta = MagicMock()
        # Simula o readline() do Arduino entregando bytes pela serial
        mock_porta.readline.side_effect = [
            b"36.4\r\n",
            b"37.7\r\n",
            b"38.8\r\n",
        ]

        leituras_processadas = []
        for _ in range(3):
            linha = mock_porta.readline().decode("utf-8")
            dados = processar_linha_serial(linha)
            leituras_processadas.append(dados)

        self.assertEqual(len(leituras_processadas), 3)
        self.assertEqual(leituras_processadas[0]["status"], "NORMAL")
        self.assertEqual(leituras_processadas[1]["status"], "ELEVATED")
        self.assertEqual(leituras_processadas[2]["status"], "FEVER")


if __name__ == "__main__":
    unittest.main()
