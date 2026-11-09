"""Estação de Dispensação, Controle de Lotes/Validade (FEFO), Teclado Matricial e LEDs no Arduino.

Integração Completa:
1. Scanner USB (Código de Barras / QR Code): Lê medicamento ou lote específico.
2. Teclado Matricial 4x4 no Arduino: Permite digitar a quantidade (ex: 50 caixas) e alternar modo (A=Saída, B=Entrada, C=Consulta, D=Alertas).
3. Banco de Dados (SQLite / PostgreSQL): Verifica validade do lote, bloqueia lotes vencidos e aplica baixa FEFO (First Expired, First Out).
4. Arduino com Display OLED + 3 LEDs de Aviso (Verde, Amarelo, Vermelho): Acende o LED correspondente à validade/estoque e exibe os detalhes do lote.

Uso:
    python scanner_station.py --port COM3
    python scanner_station.py --mode consulta
    python scanner_station.py --mode saida --quantity 1
"""

import argparse
import sys
import threading
import time
from typing import Optional

# Configura encoding UTF-8 no Windows para evitar erros no terminal
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None

from infrastructure.database.connection import SessionLocal, init_db
from infrastructure.database.models import MedicationModel
from infrastructure.repositories.sqlalchemy_medication_repository import (
    SqlAlchemyMedicationRepository,
)
from application.use_cases.list_medications import ListMedicationsUseCase
from application.use_cases.update_stock import UpdateStockCommandUseCase
from application.dtos.medication_dto import (
    StockUpdateCommandDTO,
    build_medication_response_dto,
)
from domain.entities.medication import (
    AlertLedColor,
    ExpirationStatus,
    StockMovementType,
)


# ================= PALETA DE CORES ANSI PARA TERMINAL =================
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
GRAY = "\033[90m"


def detectar_portas_seriais():
    """Detecta portas COM/USB conectadas ao sistema."""
    if not serial:
        return []
    return [p.device for p in list_ports.comports()]


def formatar_led_terminal(led: AlertLedColor) -> str:
    """Retorna representação visual colorida do LED acionado no Arduino."""
    if led == AlertLedColor.RED:
        return f"{RED}{BOLD}🔴 LED VERMELHO (CRÍTICO / LOTE VENCIDO OU ZERADO){RESET}"
    elif led == AlertLedColor.YELLOW:
        return f"{YELLOW}{BOLD}🟡 LED AMARELO (ATENÇÃO / VENCE EM <= 30 DIAS OU ESTOQUE BAIXO){RESET}"
    return f"{GREEN}{BOLD}🟢 LED VERDE (LOTE VÁLIDO & ESTOQUE OK){RESET}"


class ArduinoOledBridge:
    """Gerencia a comunicação serial bidirecional com o Arduino (OLED + LEDs + Teclado Matricial)."""

    def __init__(self, port: Optional[str] = None, baud: int = 115200):
        self.port = port
        self.baud = baud
        self.conn: Optional[serial.Serial] = None
        self.running = False
        self.current_mode = "saida"
        self.current_quantity = 1

    def conectar(self, initial_mode: str = "saida", initial_qty: int = 1) -> bool:
        """Abre a conexão com o Arduino e inicia thread de escuta do Teclado Matricial."""
        self.current_mode = initial_mode
        self.current_quantity = initial_qty

        if not serial:
            print(f"{YELLOW}Aviso: Pacote 'pyserial' não instalado. Executando em modo simulação sem Arduino.{RESET}")
            return False

        if not self.port:
            portas = detectar_portas_seriais()
            if not portas:
                print(f"{YELLOW}Nenhuma porta serial detectada. Executando em modo sem display/LEDs físicos.{RESET}")
                return False
            self.port = portas[0]
            print(f"{CYAN}Porta serial auto-detectada: {self.port}{RESET}")

        try:
            self.conn = serial.Serial(self.port, self.baud, timeout=0.5)
            time.sleep(2.0)
            print(f"{GREEN}✓ Conectado ao Arduino na porta {self.port} ({self.baud} baud)!{RESET}")
            self.enviar_para_oled(
                "SISTEMA PRONTO\nModo: " + self.current_mode.upper() + f" (Qtd: {self.current_quantity})\nUse Scanner ou Teclado",
                led_color=AlertLedColor.GREEN,
            )
            self.running = True
            threading.Thread(target=self._escutar_teclado_matricial, daemon=True).start()
            return True
        except Exception as exc:
            print(f"{RED}Não foi possível abrir a porta serial {self.port}: {exc}{RESET}")
            self.conn = None
            return False

    def _escutar_teclado_matricial(self) -> None:
        """Lê comandos enviados pelo Teclado Matricial 4x4 do Arduino (ex: KEY:SAIDA:5)."""
        while self.running and self.conn and self.conn.is_open:
            try:
                if self.conn.in_waiting > 0:
                    linha = self.conn.readline().decode("utf-8", errors="ignore").strip()
                    if linha.startswith("KEY:"):
                        partes = linha.split(":")
                        if len(partes) >= 3:
                            modo_teclado = partes[1].strip().lower()
                            qtd_teclado = int(partes[2]) if partes[2].isdigit() else 1
                            if modo_teclado == "alerta":
                                print(f"\n{YELLOW}[TECLADO ARDUINO] Tecla 'D' pressionada: Consultando alertas de lotes e validade...{RESET}")
                                exibir_resumo_alertas(self)
                            elif modo_teclado in ("saida", "entrada", "consulta"):
                                self.current_mode = modo_teclado
                                self.current_quantity = max(1, qtd_teclado)
                                print(
                                    f"\n{CYAN}{BOLD}[TECLADO MATRICIAL ARDUINO]{RESET} "
                                    f"Novo Modo: {BOLD}{self.current_mode.upper()}{RESET} | "
                                    f"Quantidade configurada: {BOLD}{self.current_quantity}{RESET}"
                                )
            except Exception:
                pass
            time.sleep(0.1)

    def enviar_para_oled(
        self, texto: str, led_color: AlertLedColor = AlertLedColor.GREEN
    ) -> None:
        """Envia cor do LED de aviso + texto formatado para o display OLED via porta serial."""
        if not self.conn or not self.conn.is_open:
            return

        try:
            linhas = [linha.strip() for linha in texto.strip().split("\n") if linha.strip()]
            payload = f"LED:{led_color.value}|" + " | ".join(linhas) + "\n"
            self.conn.write(payload.encode("utf-8", errors="replace"))
            self.conn.flush()
        except Exception as exc:
            print(f"{RED}Erro ao enviar mensagem para o Arduino: {exc}{RESET}")

    def fechar(self):
        """Fecha a conexão serial com segurança."""
        self.running = False
        if self.conn and self.conn.is_open:
            self.conn.close()


def exibir_resumo_alertas(oled_bridge: ArduinoOledBridge) -> None:
    """Verifica no banco se há lotes vencidos, vencendo em breve ou com estoque baixo."""
    db = SessionLocal()
    try:
        repo = SqlAlchemyMedicationRepository(db=db)
        list_uc = ListMedicationsUseCase(repository=repo)
        all_meds = list_uc.list_all(limit=100)

        vencidos = [m for m in all_meds if m.expiration_status == ExpirationStatus.EXPIRED]
        vencendo = [m for m in all_meds if m.expiration_status == ExpirationStatus.EXPIRING_SOON]
        baixos = [m for m in all_meds if m.stock_status.value != "OK"]

        if vencidos:
            m = vencidos[0]
            msg = f"LOTE VENCIDO!\n{m.name[:18]}\nQtd Vencida: {m.expired_stock}\nVal: {m.nearest_expiration_date}"
            oled_bridge.enviar_para_oled(msg, led_color=AlertLedColor.RED)
        elif vencendo or baixos:
            m = (vencendo or baixos)[0]
            msg = f"ATENCAO ESTOQUE/VAL\n{m.name[:18]}\nSaldo: {m.current_stock} {m.unit}\nVal: {m.nearest_expiration_date or 'N/A'}"
            oled_bridge.enviar_para_oled(msg, led_color=AlertLedColor.YELLOW)
        else:
            oled_bridge.enviar_para_oled(
                "TUDO EM ORDEM!\nNenhum lote vencido\nEstoque regular",
                led_color=AlertLedColor.GREEN,
            )
    finally:
        db.close()


def processar_codigo_scanner(
    raw_code: str,
    mode: str,
    quantity: int,
    reason: str,
    oled_bridge: ArduinoOledBridge,
    batch_number: Optional[str] = None,
) -> None:
    """Processa a leitura vinda do leitor de código de barras/QR Code verificando lotes e validade."""
    code = raw_code.strip()
    if not code:
        return

    db = SessionLocal()
    try:
        repo = SqlAlchemyMedicationRepository(db=db)
        list_use_case = ListMedicationsUseCase(repository=repo)
        stock_use_case = UpdateStockCommandUseCase(repository=repo)

        medication = None
        detected_batch = batch_number

        # 1. Verifica se o código lido é diretamente o número de um lote (ex: LOTE-2026A)
        batch_entity = repo.find_batch_by_code(code)
        if batch_entity:
            med_entity = repo.get_by_id(str(batch_entity.medication_id))
            if med_entity:
                batches = repo.list_batches(str(med_entity.id))
                medication = build_medication_response_dto(med_entity, batches)
                detected_batch = batch_entity.batch_number

        # 2. Busca por Código de Barras / EAN direto
        if not medication:
            med_model = db.query(MedicationModel).filter(MedicationModel.barcode == code).first()
            if med_model:
                med_entity = repo._to_entity(med_model)
                batches = repo.list_batches(str(med_entity.id))
                medication = build_medication_response_dto(med_entity, batches)

        # 3. Tenta resolver via interpretador de QR Code (suporta JSON, Pipe ou ID/Nome)
        if not medication:
            resolved = list_use_case.resolve_qrcode(code)
            if resolved.found and resolved.medication:
                medication = resolved.medication
                if resolved.parsed_data.batch_number and not detected_batch:
                    detected_batch = resolved.parsed_data.batch_number
            else:
                med_entity = repo.get_by_id(code)
                if not med_entity:
                    all_meds = repo.list_all(limit=100)
                    matches = [m for m in all_meds if code.lower() in m.name.lower()]
                    if matches:
                        med_entity = matches[0]
                if med_entity:
                    batches = repo.list_batches(str(med_entity.id))
                    medication = build_medication_response_dto(med_entity, batches)

        # SE NÃO ENCONTRADO -> LED VERMELHO
        if not medication:
            print(f"\n{RED}{BOLD}✗ MEDICAMENTO OU LOTE NÃO ENCONTRADO NO BANCO!{RESET}")
            print(f" Código lido: {YELLOW}'{code}'{RESET}")
            print(f" Arduino:     {formatar_led_terminal(AlertLedColor.RED)}\n")

            oled_bridge.enviar_para_oled(
                "NAO ENCONTRADO!\nCadastre o item\nou lote no sistema",
                led_color=AlertLedColor.RED,
            )
            return

        # SE ENCONTRADO: Exibe dados atuais + Lotes e Validade
        val_str = (
            medication.nearest_expiration_date.strftime("%d/%m/%Y")
            if medication.nearest_expiration_date
            else "Sem lote"
        )
        lote_principal = (
            detected_batch
            or (medication.batches[0].batch_number if medication.batches else "PADRAO")
        )

        print("\n" + "=" * 70)
        print(f"{GREEN}{BOLD}✓ MEDICAMENTO & LOTE IDENTIFICADOS!{RESET}")
        print("=" * 70)
        print(f" Nome:             {BOLD}{medication.name}{RESET} ({medication.dosage})")
        print(f" Saldo Total:      {BOLD}{medication.current_stock} {medication.unit}(s){RESET} (Mín: {medication.minimum_stock})")
        print(f" Lote em Foco:     {CYAN}{lote_principal}{RESET} (Total de lotes: {len(medication.batches)})")
        print(f" Próx. Validade:   {BOLD}{val_str}{RESET} [{medication.expiration_status.value}]")
        print(f" Sinalização LED:  {formatar_led_terminal(medication.alert_led)}")

        if medication.batches:
            print(" Lotes Cadastrados:")
            for b in medication.batches:
                cor_b = RED if b.is_expired else (YELLOW if b.expiration_status == ExpirationStatus.EXPIRING_SOON else GREEN)
                print(
                    f"   • Lote {BOLD}{b.batch_number}{RESET}: {b.quantity} {medication.unit}(s) | "
                    f"Validade: {b.expiration_date.strftime('%d/%m/%Y')} "
                    f"({cor_b}{b.expiration_status.value} / {b.days_until_expiration}d{RESET})"
                )

        # Se o modo for apenas consulta, exibe na tela OLED e aciona o LED correspondente
        if mode == "consulta":
            print(f" Modo:             {CYAN}[APENAS CONSULTA DE LOTE & VALIDADE]{RESET}")
            print("=" * 70 + "\n")

            oled_msg = (
                f"{medication.name[:18]}\n"
                f"Lote: {lote_principal[:12]}\n"
                f"Saldo: {medication.current_stock} {medication.unit[:6]}\n"
                f"Val: {val_str}"
            )
            oled_bridge.enviar_para_oled(oled_msg, led_color=medication.alert_led)
            return

        # SE FOR MODO DE MOVIMENTAÇÃO (SAÍDA FEFO OU ENTRADA DE LOTE)
        mov_type = StockMovementType.SAIDA if mode == "saida" else StockMovementType.ENTRADA
        command = StockUpdateCommandDTO(
            movement_type=mov_type,
            quantity=quantity,
            batch_number=detected_batch,
            reason=reason or f"Dispensação via Scanner/Teclado ({mode.upper()})",
        )

        try:
            updated_med, movement = stock_use_case.execute(
                medication_id=str(medication.id),
                command=command,
            )

            lote_usado = movement.batch_number or lote_principal
            val_atualizada = (
                updated_med.nearest_expiration_date.strftime("%d/%m/%Y")
                if updated_med.nearest_expiration_date
                else "OK"
            )

            print("-" * 70)
            print(f"{MAGENTA}{BOLD}COMANDO DE ESTOQUE EXECUTADO: {mov_type.value}{RESET}")
            print(f" Lote Movimentado: {BOLD}{lote_usado}{RESET}")
            print(f" Quantidade:       {quantity} {updated_med.unit}(s)")
            print(f" Saldo Anterior:   {movement.previous_stock} -> Novo Saldo: {BOLD}{updated_med.current_stock}{RESET}")
            print(f" LED no Arduino:   {formatar_led_terminal(updated_med.alert_led)}")
            print("=" * 70 + "\n")

            sinal = "-" if mov_type == StockMovementType.SAIDA else "+"
            oled_msg = (
                f"{updated_med.name[:18]}\n"
                f"Lote:{lote_usado[:10]} ({sinal}{quantity})\n"
                f"Saldo: {updated_med.current_stock} {updated_med.unit[:6]}\n"
                f"Val: {val_atualizada}"
            )
            oled_bridge.enviar_para_oled(oled_msg, led_color=updated_med.alert_led)

        except ValueError as err:
            print(f"\n{RED}{BOLD}🚨 BLOQUEIO / ERRO AO ATUALIZAR ESTOQUE:{RESET} {err}")
            print(f" Arduino: {formatar_led_terminal(AlertLedColor.RED)}\n")
            if "VENCIDO" in str(err).upper():
                oled_bridge.enviar_para_oled(
                    f"! LOTE VENCIDO !\n{medication.name[:18]}\nLote: {lote_principal[:12]}\nSAIDA BLOQUEADA!",
                    led_color=AlertLedColor.RED,
                )
            else:
                oled_bridge.enviar_para_oled(
                    f"ESTOQUE ESGOTADO!\n{medication.name[:18]}\nSaldo: {medication.current_stock}\nImpossivel baixar",
                    led_color=AlertLedColor.RED,
                )

    except Exception as exc:
        print(f"{RED}Erro inesperado ao consultar banco de dados: {exc}{RESET}")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Estação de Leitura de Código de Barras / QR Code com Lotes, Validade, Teclado Matricial e LEDs no Arduino"
    )
    parser.add_argument(
        "--port",
        type=str,
        default=None,
        help="Porta serial do Arduino (ex: COM3, COM4). Se omitido, tenta auto-detectar.",
    )
    parser.add_argument(
        "--baud",
        type=int,
        default=115200,
        help="Taxa de comunicação serial com o Arduino (padrão: 115200)",
    )
    parser.add_argument(
        "--mode",
        choices=["saida", "entrada", "consulta"],
        default="saida",
        help="Ação padrão ao bipar: 'saida' (baixa FEFO), 'entrada' (repõe lote) ou 'consulta' (verifica validade)",
    )
    parser.add_argument(
        "--quantity",
        type=int,
        default=1,
        help="Quantidade padrão a movimentar (pode ser alterada pelo Teclado Matricial do Arduino)",
    )
    parser.add_argument(
        "--reason",
        type=str,
        default=None,
        help="Motivo registrado no histórico de movimentações",
    )

    args = parser.parse_args()

    # Inicializa tabelas do banco de dados se necessário
    init_db()

    print("=" * 75)
    print(f"{BOLD}🏥 MEDICA - SENTINELA ENF: LOTES, VALIDADE, TECLADO MATRICIAL & LEDS{RESET}")
    print("=" * 75)
    print(f"• Modo Inicial       : {CYAN}{args.mode.upper()}{RESET} (Qtd padrão: {args.quantity} un/caixas)")
    print(f"• Controle de Lotes  : {GREEN}FEFO Ativo (Bloqueio automático de lotes vencidos){RESET}")
    print(f"• Teclado Matricial  : {YELLOW}A=Saída | B=Entrada Lote | C=Consulta | D=Alertas | #=Confirmar{RESET}")
    print(f"• LEDs de Aviso      : {GREEN}🟢 Verde (OK){RESET} | {YELLOW}🟡 Amarelo (<=30d/Baixo){RESET} | {RED}🔴 Vermelho (Vencido/Zero){RESET}")
    print("=" * 75)

    oled = ArduinoOledBridge(port=args.port, baud=args.baud)
    oled.conectar(initial_mode=args.mode, initial_qty=args.quantity)

    print(f"\n{BOLD}👉 Bipe o código do Medicamento/Lote ou digite no Teclado Matricial do Arduino.{RESET}")
    print(f"{GRAY}Para sair a qualquer momento, pressione Ctrl + C.{RESET}\n")

    try:
        while True:
            try:
                prompt_label = (
                    f"{GREEN}{BOLD}SCANNER [{oled.current_mode.upper()} | Qtd: {oled.current_quantity}] > {RESET}"
                )
                codigo_lido = input(prompt_label).strip()

                if not codigo_lido:
                    continue

                processar_codigo_scanner(
                    raw_code=codigo_lido,
                    mode=oled.current_mode,
                    quantity=oled.current_quantity,
                    reason=args.reason or f"Dispensação via Scanner ({oled.current_mode.upper()})",
                    oled_bridge=oled,
                )

            except EOFError:
                break

    except KeyboardInterrupt:
        print(f"\n{YELLOW}Estação de dispensação encerrada pelo usuário.{RESET}")
    finally:
        oled.enviar_para_oled("SISTEMA OFFLINE\nDesconectado", led_color=AlertLedColor.YELLOW)
        time.sleep(0.5)
        oled.fechar()


if __name__ == "__main__":
    main()
