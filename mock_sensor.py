"""Simulador Mock do Hardware / Microcontrolador (Arduino / ESP32-C3).

Permite testar a ingestão de telemetria corporal, regras clínicas e debounce
sem a necessidade do circuito eletrônico físico ou porta serial conectada.

Uso:
    python mock_sensor.py --url http://localhost:8000/api/v1/telemetry/ --interval 2.5
    python mock_sensor.py --mode febre --interval 1.5
    python mock_sensor.py --dry-run
"""

import argparse
import random
import sys
import time
from datetime import datetime
from typing import Optional

# Evita erros de charmap/cp1252 no terminal do Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

try:
    import requests
except ImportError:
    print("A biblioteca 'requests' não foi encontrada. Instale com: pip install requests")
    sys.exit(1)


# ================= PALETA DE CORES ANSI PARA O TERMINAL =================
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
GRAY = "\033[90m"


def formatar_status_visual(temp: float) -> str:
    """Gera uma etiqueta colorida e formatada de acordo com a faixa clínica."""
    if temp < 35.0:
        return f"{CYAN}[HIPOTERMIA]{RESET}"
    elif temp < 37.5:
        return f"{GREEN}[NORMAL]{RESET}"
    elif 37.5 <= temp < 37.8:
        return f"{YELLOW}[ELEVADA/FEBRIL]{RESET}"
    else:
        return f"{RED}{BOLD}[🚨 FEBRE ALTA]{RESET}"


class SensorMock:
    """Gerador de dados de temperatura corporal simulando comportamento biológico."""

    def __init__(self, mode: str = "febre"):
        self.mode = mode
        self.step_idx = 0

        # Curva de evolução clínica simulando um episódio de febre
        self.fever_curve = [
            36.4, 36.5, 36.7, 37.1, 37.4,  # Temperatura normal/aquecimento
            37.6, 37.7,                    # Estado febril (ELEVATED)
            38.2, 38.6, 39.1, 39.4,        # Febre instalada (FEVER)
            38.8, 38.3,                    # Resposta a antitérmico
            37.6, 37.2, 36.6, 36.5         # Recuperação normal
        ]

    def obter_leitura(self) -> float:
        """Retorna a temperatura corporal simulada (°C) conforme o perfil escolhido."""
        if self.mode == "febre":
            temp_base = self.fever_curve[self.step_idx % len(self.fever_curve)]
            # Adiciona leve ruído térmico realista (+/- 0.05°C)
            ruido = random.uniform(-0.05, 0.05)
            self.step_idx += 1
            return round(temp_base + ruido, 2)

        elif self.mode == "normal":
            # Flutua normalmente em torno de 36.5°C
            return round(random.uniform(36.2, 36.9), 2)

        elif self.mode == "aleatorio":
            # Gera qualquer temperatura biológica entre 35.8°C e 40.2°C
            return round(random.uniform(35.8, 40.2), 2)

        else:
            return 36.5


def enviar_leitura(url: str, device_id: str, temperature: float, timeout: float = 3.0) -> Optional[dict]:
    """Envia o payload de telemetria para a API via requisição HTTP POST."""
    payload = {
        "device_id": device_id,
        "temperature": temperature
    }

    try:
        response = requests.post(url, json=payload, timeout=timeout)
        return {
            "status_code": response.status_code,
            "data": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
        }
    except requests.exceptions.ConnectionError:
        return {"error": "Conexão recusada. O servidor da API está em execução?"}
    except requests.exceptions.Timeout:
        return {"error": "Timeout ao conectar ao servidor da API."}
    except Exception as exc:
        return {"error": f"Erro inesperado: {str(exc)}"}


def main():
    parser = argparse.ArgumentParser(
        description="Simulador Mock de Hardware IoT para Envio de Temperatura Corporal"
    )
    parser.add_argument(
        "--url",
        type=str,
        default="http://localhost:8000/api/v1/telemetry/",
        help="URL completa do endpoint de ingestão da API",
    )
    parser.add_argument(
        "--device-id",
        type=str,
        default="arduino_sensor_mock_01",
        help="Identificador do dispositivo que está medindo a temperatura",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Intervalo em segundos entre as leituras (ex: 2.0)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["febre", "normal", "aleatorio"],
        default="febre",
        help="Perfil da simulação: 'febre' (curva clínica), 'normal' ou 'aleatorio'",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=0,
        help="Quantidade total de leituras a enviar (0 para contínuo até Ctrl+C)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas simula e exibe as leituras no terminal sem enviar requisições HTTP",
    )

    args = parser.parse_args()

    print("=" * 70)
    print(f"{BOLD}🌡️  MOCK DE HARDWARE IoT - MONITOR DE TEMPERATURA CORPORAL{RESET}")
    print("=" * 70)
    print(f"• Dispositivo Mock : {CYAN}{args.device_id}{RESET}")
    print(f"• Modo de Teste    : {YELLOW}{args.mode.upper()}{RESET}")
    print(f"• Intervalo        : {args.interval}s")
    print(f"• Destino da API   : {args.url if not args.dry_run else '[DRY-RUN - Apenas Local]'}")
    print("=" * 70)
    print("Pressione [Ctrl + C] para interromper a simulação a qualquer momento.\n")

    sensor = SensorMock(mode=args.mode)
    enviados = 0

    try:
        while True:
            temp = sensor.obter_leitura()
            horario = datetime.now().strftime("%H:%M:%S")
            badge = formatar_status_visual(temp)

            print(f"[{horario}] 📡 Temp: {BOLD}{temp:5.2f}°C{RESET} {badge}", end="")

            if args.dry_run:
                print(f" {GRAY}(Dry-Run: local){RESET}")
            else:
                resp = enviar_leitura(args.url, args.device_id, temp)
                if resp is None:
                    print(f" {RED}x Falha no envio{RESET}")
                elif "error" in resp:
                    print(f" {RED}x {resp['error']}{RESET}")
                else:
                    status_code = resp["status_code"]
                    data = resp.get("data", {})
                    if status_code in (200, 201):
                        msg = ""
                        if isinstance(data, dict) and data.get("message"):
                            msg = f" | {YELLOW}{data['message']}{RESET}"
                        print(f" {GREEN}✓ HTTP {status_code}{RESET}{msg}")
                    else:
                        print(f" {RED}x HTTP {status_code} - Resposta: {data}{RESET}")

            enviados += 1
            if args.count > 0 and enviados >= args.count:
                print(f"\n{GREEN}Simulação concluída ({enviados} leituras processadas).{RESET}")
                break

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Simulação interrompida com sucesso. Total de leituras: {enviados}{RESET}")


if __name__ == "__main__":
    main()
