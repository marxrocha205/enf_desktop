r"""Bridge Arduino -> Rede Wi-Fi / API do Sistema.

Lê as medições de temperatura corporal enviadas pelo Arduino via cabo USB (Serial)
e despacha instantaneamente via rede Wi-Fi / HTTP para o backend do sistema (FastAPI).

Uso:
    .venv\Scripts\python.exe bridge_arduino_wifi.py --port COM3 --api-url http://192.168.1.50:8000/api/v1/telemetry/
"""

import argparse
import json
import socket
import sys
import time
from datetime import datetime
from typing import Optional

# Configuração de encoding para compatibilidade com terminal Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

try:
    import requests
except ImportError:
    print("A biblioteca 'requests' é necessária. Instale com: pip install requests")
    sys.exit(1)

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None


# ================= PALETA DE CORES ANSI =================
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
GRAY = "\033[90m"


def obter_ip_local_wifi() -> str:
    """Descobre o endereço IP local da máquina na rede Wi-Fi."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Não precisa ser alcançável, apenas determina a interface de saída
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def listar_portas_disponiveis():
    """Lista portas COM/USB disponíveis no sistema."""
    if not serial:
        return []
    return [p.device for p in list_ports.comports()]


def classificar_status(temp: float) -> str:
    """Classifica a temperatura corporal conforme o domínio clínico."""
    if temp < 35.0:
        return f"{CYAN}[HIPOTERMIA]{RESET}"
    elif temp < 37.5:
        return f"{GREEN}[NORMAL]{RESET}"
    elif 37.5 <= temp < 37.8:
        return f"{YELLOW}[ELEVADA/FEBRIL]{RESET}"
    else:
        return f"{RED}{BOLD}[🚨 FEBRE]{RESET}"


def enviar_via_wifi(api_url: str, device_id: str, temp: float, timeout: float = 3.0) -> bool:
    """Envia a leitura de temperatura pela rede Wi-Fi via HTTP POST para o sistema."""
    payload = {
        "device_id": device_id,
        "temperature": round(temp, 2)
    }

    try:
        response = requests.post(api_url, json=payload, timeout=timeout)
        if response.status_code in (200, 201):
            dados = response.json()
            msg = dados.get("message")
            info_alerta = f" | {YELLOW}{msg}{RESET}" if msg else ""
            print(f" -> {GREEN}Enviado via Wi-Fi [HTTP {response.status_code}]{RESET}{info_alerta}")
            return True
        else:
            print(f" -> {RED}Erro da API [HTTP {response.status_code}]: {response.text}{RESET}")
            return False
    except requests.exceptions.ConnectionError:
        print(f" -> {RED}Falha de conexão Wi-Fi com a API em {api_url}. Servidor offline?{RESET}")
        return False
    except requests.exceptions.Timeout:
        print(f" -> {RED}Timeout na rede ao enviar para {api_url}{RESET}")
        return False
    except Exception as exc:
        print(f" -> {RED}Erro inesperado: {exc}{RESET}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Ponte Arduino -> Rede Wi-Fi para o sistema de monitoramento de temperatura"
    )
    parser.add_argument(
        "--port",
        type=str,
        default="COM3",
        help="Porta serial do Arduino (ex: COM3, COM4 ou /dev/ttyUSB0)",
    )
    parser.add_argument(
        "--baud",
        type=int,
        default=9600,
        help="Baud rate configurado no Arduino (padrão: 9600)",
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default="http://localhost:8000/api/v1/telemetry/",
        help="URL do endpoint de telemetria da API na rede Wi-Fi",
    )
    parser.add_argument(
        "--device-id",
        type=str,
        default="arduino_wifi_bridge_01",
        help="Identificador do dispositivo",
    )

    args = parser.parse_args()

    ip_local = obter_ip_local_wifi()

    print("=" * 70)
    print(f"{BOLD}📡 PONTE ARDUINO -> REDE WI-FI / API DE TELEMETRIA{RESET}")
    print("=" * 70)
    print(f"• IP desta máquina na rede Wi-Fi : {CYAN}{ip_local}{RESET}")
    print(f"• Porta Serial do Arduino        : {YELLOW}{args.port}{RESET} ({args.baud} bps)")
    print(f"• Destino no Sistema (API)       : {CYAN}{args.api_url}{RESET}")
    print(f"• Identificador do Dispositivo   : {args.device_id}")
    print("=" * 70)

    if not serial:
        print(f"{RED}AVISO: O pacote 'pyserial' não está instalado no ambiente.{RESET}")
        print("Para instalar: pip install pyserial\n")
        sys.exit(1)

    portas = listar_portas_disponiveis()
    if portas:
        print(f"Portas seriais detectadas no computador: {', '.join(portas)}")
    else:
        print(f"{YELLOW}Aviso: Nenhuma porta serial detectada no momento. Conecte o Arduino.{RESET}")

    print(f"\nAbrindo porta {args.port}...")

    try:
        conexao_serial = serial.Serial(args.port, args.baud, timeout=2.0)
        time.sleep(2.0)  # Tempo para o Arduino reiniciar após abertura da porta
        print(f"{GREEN}✓ Conectado ao Arduino com sucesso! Aguardando leituras...{RESET}\n")

        while True:
            linha = conexao_serial.readline().decode("utf-8", errors="ignore").strip()
            if not linha:
                continue

            try:
                temperatura = float(linha)

                # Validação clínica de escala biológica
                if not (30.0 <= temperatura <= 45.0):
                    print(f"{GRAY}[Ignorado] Leitura fora da faixa corporal humana: {temperatura:.2f}°C{RESET}")
                    continue

                horario = datetime.now().strftime("%H:%M:%S")
                badge = classificar_status(temperatura)

                print(f"[{horario}] 🌡️  Aferição Arduino: {BOLD}{temperatura:5.2f}°C{RESET} {badge}", end="")

                # Envia instantaneamente pela rede Wi-Fi para o sistema
                enviar_via_wifi(args.api_url, args.device_id, temperatura)

            except ValueError:
                # Linha recebida continha texto/log do Arduino e não número
                print(f"{GRAY}[Serial Arduino] {linha}{RESET}")

    except serial.SerialException as erro:
        print(f"\n{RED}Erro ao acessar a porta serial {args.port}: {erro}{RESET}")
        print("Dica: Verifique se o Arduino está conectado e se o Monitor Serial da IDE Arduino está fechado.")
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Ponte encerrada pelo usuário.{RESET}")
    finally:
        if "conexao_serial" in locals() and conexao_serial.is_open:
            conexao_serial.close()


if __name__ == "__main__":
    main()
