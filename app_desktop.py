"""Sistema Desktop Local de Farmácia, Gestão de Estoque e Dispensação com Arduino OLED.

Funciona 100% offline sem precisar de internet ou rede externa (usa SQLite local por padrão
ou PostgreSQL se configurado).

Recursos:
- Interface gráfica nativa (Tkinter/TTK) moderna e responsiva.
- Leitura contínua de Scanner de Código de Barras / QR Code USB (emulação de teclado).
- Modos: Baixa Automática (-1 un), Consulta Rápida e Entrada de Reposição.
- Conexão Serial com Arduino / ESP32 (115200 baud) com detecção automática de portas COM.
- Simulador visual na tela do display OLED 128x64 mostrando exatamente o que o Arduino exibe.
- Catálogo completo de medicamentos com busca instantânea, alertas de estoque baixo e cadastro.
"""

import os
import sys
import threading
import time
from datetime import date, datetime, timedelta, timezone
from typing import Optional, List
import uuid

# Configura encoding no Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

import tkinter as tk
from tkinter import ttk, messagebox

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None

from sqlalchemy import create_engine, Column, String, Integer, Date, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# ================= CONFIGURAÇÃO DO BANCO DE DADOS LOCAL OFFLINE =================
LOCAL_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "iot_telemetry.db"))
LOCAL_DB_URL = f"sqlite:///{LOCAL_DB_PATH}"

engine = create_engine(
    LOCAL_DB_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class MedicationModel(Base):
    __tablename__ = "medications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    barcode = Column(String(100), nullable=True, index=True)
    name = Column(String(150), nullable=False, index=True)
    dosage = Column(String(50), nullable=False)
    unit = Column(String(30), default="comprimido", nullable=False)
    current_stock = Column(Integer, default=0, nullable=False)
    minimum_stock = Column(Integer, default=10, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=True)


class MedicationBatchModel(Base):
    __tablename__ = "medication_batches"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    medication_id = Column(String(36), ForeignKey("medications.id"), nullable=False, index=True)
    batch_number = Column(String(80), nullable=False, index=True)
    quantity = Column(Integer, default=0, nullable=False)
    expiration_date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class StockMovementModel(Base):
    __tablename__ = "stock_movements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    medication_id = Column(String(36), nullable=False, index=True)
    batch_id = Column(String(36), nullable=True, index=True)
    batch_number = Column(String(80), nullable=True)
    movement_type = Column(String(20), nullable=False)  # ENTRADA, SAIDA, AJUSTE
    quantity = Column(Integer, nullable=False)
    previous_stock = Column(Integer, nullable=False)
    new_stock = Column(Integer, nullable=False)
    reason = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


# Inicializa as tabelas no banco de dados local
Base.metadata.create_all(bind=engine)

# Garante a existência das colunas de migração se o banco já existia antes
for _sql in (
    "ALTER TABLE medications ADD COLUMN barcode VARCHAR(100)",
    "ALTER TABLE stock_movements ADD COLUMN batch_id VARCHAR(36)",
    "ALTER TABLE stock_movements ADD COLUMN batch_number VARCHAR(80)",
):
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text(_sql))
            conn.commit()
    except Exception:
        pass


def parse_data_validade(texto_data: str) -> Optional[date]:
    """Interpreta data de validade nos formatos DD/MM/AAAA ou AAAA-MM-DD."""
    limpo = (texto_data or "").strip()
    if not limpo:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(limpo, fmt).date()
        except ValueError:
            continue
    return None


# ================= PALETA DE CORES MODERNA (TEMA HOSPITALAR / DARK CLEAN) =================
COLOR_BG_DARK = "#0f172a"      # Slate 900
COLOR_PANEL_BG = "#1e293b"     # Slate 800
COLOR_CARD_BG = "#334155"      # Slate 700
COLOR_ACCENT = "#06b6d4"       # Cyan
COLOR_ACCENT_HOVER = "#0891b2"
COLOR_SUCCESS = "#10b981"      # Emerald
COLOR_WARNING = "#f59e0b"      # Amber
COLOR_DANGER = "#ef4444"       # Red
COLOR_TEXT_WHITE = "#f8fafc"   # White clean
COLOR_TEXT_MUTED = "#94a3b8"   # Slate 400
COLOR_OLED_BG = "#05070a"      # Tela preta OLED
COLOR_OLED_TXT = "#38bdf8"     # Azul ciano OLED aceso


class ArduinoSerialManager:
    """Gerencia a comunicação serial bidirecional com o Arduino."""

    def __init__(self):
        self.conn: Optional[serial.Serial] = None
        self.port: Optional[str] = None
        self.baud: int = 115200

    def listar_portas(self) -> List[str]:
        if not serial:
            return []
        return [p.device for p in list_ports.comports()]

    def conectar(self, port: str, baud: int = 115200) -> tuple[bool, str]:
        if not serial:
            return False, "Biblioteca pyserial não instalada."

        self.desconectar()
        try:
            self.conn = serial.Serial(port, baud, timeout=1.0)
            time.sleep(1.8)  # Tempo de bootloader
            self.port = port
            self.baud = baud
            self.enviar_para_oled("SISTEMA PRONTO\nAPROXIME O SCANNER")
            return True, f"Conectado com sucesso em {port}!"
        except Exception as exc:
            self.conn = None
            return False, f"Falha ao abrir {port}: {exc}"

    def desconectar(self):
        if self.conn and self.conn.is_open:
            try:
                self.enviar_para_oled("SISTEMA OFFLINE\nDesconectado")
                time.sleep(0.3)
                self.conn.close()
            except Exception:
                pass
        self.conn = None
        self.port = None

    def is_conectado(self) -> bool:
        return self.conn is not None and self.conn.is_open

    def enviar_para_oled(self, texto: str, cor_led: str = "GREEN"):
        if not self.is_conectado():
            return
        try:
            # Envia o comando do LED (GREEN, YELLOW, RED) + texto separado por '|'
            linhas = [l.strip() for l in texto.strip().split("\n") if l.strip()]
            payload = f"LED:{cor_led}|" + " | ".join(linhas) + "\n"
            self.conn.write(payload.encode("utf-8", errors="replace"))
            self.conn.flush()
        except Exception as exc:
            print("Erro ao enviar serial:", exc)


class DesktopApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Medica - Sentinela Enf • Gestão de Enfermagem, Lotes e Estoque IoT")
        self.root.geometry("1100x720")
        self.root.minsize(980, 640)
        self.root.configure(bg=COLOR_BG_DARK)

        # Ícone ou título
        self.arduino = ArduinoSerialManager()
        self.current_mode = tk.StringVar(value="saida")  # 'saida', 'consulta', 'entrada'
        self.quantity_var = tk.IntVar(value=1)

        self._setup_styles()
        self._build_header()
        self._build_scanner_bar()
        self._build_main_content()
        self._build_status_bar()

        # Popula a lista e atualiza portas seriais
        self.refresh_ports()
        self.load_medications()

        # Foca automaticamente no campo do scanner
        self.root.after(300, lambda: self.scanner_entry.focus_set())

        # Protocolo de fechamento
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        # Customiza Treeview (Tabela)
        style.configure(
            "Custom.Treeview",
            background=COLOR_PANEL_BG,
            foreground=COLOR_TEXT_WHITE,
            fieldbackground=COLOR_PANEL_BG,
            rowheight=32,
            font=("Segoe UI", 10),
            borderwidth=0,
        )
        style.configure(
            "Custom.Treeview.Heading",
            background="#0f172a",
            foreground="#38bdf8",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
        )
        style.map(
            "Custom.Treeview",
            background=[("selected", "#0284c7")],
            foreground=[("selected", "#ffffff")],
        )

        style.configure(
            "TCombobox",
            fieldbackground=COLOR_CARD_BG,
            background=COLOR_CARD_BG,
            foreground="#ffffff",
            arrowcolor="#38bdf8",
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", COLOR_CARD_BG)],
            foreground=[("readonly", "#ffffff")],
        )

        # Estilos de Botões TTK compatíveis com macOS, Windows e Linux (tema 'clam')
        base_btn_cfg = {
            "font": ("Segoe UI", 10, "bold"),
            "borderwidth": 0,
            "focusthickness": 0,
            "padding": (12, 6),
        }

        style.configure(
            "Primary.TButton",
            background="#0284c7",
            foreground="#ffffff",
            **base_btn_cfg,
        )
        style.map(
            "Primary.TButton",
            background=[("active", "#0369a1"), ("pressed", "#075985")],
            foreground=[("active", "#ffffff"), ("pressed", "#ffffff")],
        )

        style.configure(
            "Accent.TButton",
            background=COLOR_ACCENT,
            foreground="#0f172a",
            **base_btn_cfg,
        )
        style.map(
            "Accent.TButton",
            background=[("active", COLOR_ACCENT_HOVER), ("pressed", "#0e7490")],
            foreground=[("active", "#0f172a"), ("pressed", "#ffffff")],
        )

        style.configure(
            "Success.TButton",
            background="#059669",
            foreground="#ffffff",
            **base_btn_cfg,
        )
        style.map(
            "Success.TButton",
            background=[("active", "#047857"), ("pressed", "#065f46")],
            foreground=[("active", "#ffffff"), ("pressed", "#ffffff")],
        )

        style.configure(
            "Danger.TButton",
            background="#dc2626",
            foreground="#ffffff",
            **base_btn_cfg,
        )
        style.map(
            "Danger.TButton",
            background=[("active", "#b91c1c"), ("pressed", "#991b1b")],
            foreground=[("active", "#ffffff"), ("pressed", "#ffffff")],
        )

        style.configure(
            "Secondary.TButton",
            background=COLOR_CARD_BG,
            foreground="#ffffff",
            font=("Segoe UI", 10, "bold"),
            borderwidth=0,
            padding=(8, 5),
        )
        style.map(
            "Secondary.TButton",
            background=[("active", "#475569"), ("pressed", "#1e293b")],
            foreground=[("active", "#ffffff"), ("pressed", "#ffffff")],
        )

        style.configure(
            "OutlineDanger.TButton",
            background=COLOR_CARD_BG,
            foreground="#fca5a5",
            **base_btn_cfg,
        )
        style.map(
            "OutlineDanger.TButton",
            background=[("active", "#7f1d1d"), ("pressed", "#991b1b")],
            foreground=[("active", "#ffffff"), ("pressed", "#ffffff")],
        )

    def _build_header(self):
        header = tk.Frame(self.root, bg=COLOR_PANEL_BG, height=64, padx=20, pady=12)
        header.pack(fill="x")

        # Título e Ícone
        title_box = tk.Frame(header, bg=COLOR_PANEL_BG)
        title_box.pack(side="left")

        lbl_badge = tk.Label(
            title_box,
            text="● MEDICA - SENTINELA ENF",
            font=("Segoe UI", 8, "bold"),
            bg="#064e3b",
            fg="#34d399",
            padx=8,
            pady=2,
        )
        lbl_badge.pack(anchor="w")

        lbl_title = tk.Label(
            title_box,
            text="Medica - Sentinela Enf • Controle de Medicamentos, Lotes e Validade",
            font=("Segoe UI", 14, "bold"),
            bg=COLOR_PANEL_BG,
            fg=COLOR_TEXT_WHITE,
        )
        lbl_title.pack(anchor="w")

        # Conexão Arduino (Lado Direito)
        serial_box = tk.Frame(header, bg=COLOR_PANEL_BG)
        serial_box.pack(side="right")

        tk.Label(
            serial_box,
            text="Porta Arduino:",
            font=("Segoe UI", 9),
            bg=COLOR_PANEL_BG,
            fg=COLOR_TEXT_MUTED,
        ).pack(side="left", padx=4)

        self.port_combo = ttk.Combobox(serial_box, width=10, state="readonly")
        self.port_combo.pack(side="left", padx=4)

        btn_refresh = ttk.Button(
            serial_box,
            text="↻ Atualizar",
            style="Secondary.TButton",
            cursor="hand2",
            command=self.refresh_ports,
        )
        btn_refresh.pack(side="left", padx=2)

        self.btn_serial_toggle = ttk.Button(
            serial_box,
            text="Conectar Display",
            style="Accent.TButton",
            cursor="hand2",
            command=self.toggle_serial,
        )
        self.btn_serial_toggle.pack(side="left", padx=8)

    def _build_scanner_bar(self):
        """Barra de destaque para captura de código de barras ou QR Code."""
        bar_frame = tk.Frame(self.root, bg=COLOR_BG_DARK, padx=20, pady=14)
        bar_frame.pack(fill="x")

        # Container interno estilizado
        scanner_card = tk.Frame(bar_frame, bg=COLOR_PANEL_BG, padx=16, pady=12, relief="flat")
        scanner_card.pack(fill="x")

        # Seletor de Modo (Baixa, Consulta, Entrada)
        modes_box = tk.Frame(scanner_card, bg=COLOR_PANEL_BG)
        modes_box.pack(side="left", padx=(0, 20))

        tk.Label(
            modes_box,
            text="Modo ao Bipar:",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_PANEL_BG,
            fg=COLOR_TEXT_MUTED,
        ).pack(anchor="w", pady=(0, 4))

        mode_radios = tk.Frame(modes_box, bg=COLOR_PANEL_BG)
        mode_radios.pack(anchor="w")

        tk.Radiobutton(
            mode_radios,
            text="Baixa (-1 un)",
            variable=self.current_mode,
            value="saida",
            bg=COLOR_PANEL_BG,
            fg="#ef4444",
            activebackground=COLOR_PANEL_BG,
            selectcolor=COLOR_BG_DARK,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
        ).pack(side="left", padx=4)

        tk.Radiobutton(
            mode_radios,
            text="Consulta",
            variable=self.current_mode,
            value="consulta",
            bg=COLOR_PANEL_BG,
            fg="#38bdf8",
            activebackground=COLOR_PANEL_BG,
            selectcolor=COLOR_BG_DARK,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
        ).pack(side="left", padx=4)

        tk.Radiobutton(
            mode_radios,
            text="Entrada (+un)",
            variable=self.current_mode,
            value="entrada",
            bg=COLOR_PANEL_BG,
            fg="#10b981",
            activebackground=COLOR_PANEL_BG,
            selectcolor=COLOR_BG_DARK,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
        ).pack(side="left", padx=4)

        # Campo de Input do Scanner
        input_box = tk.Frame(scanner_card, bg=COLOR_PANEL_BG)
        input_box.pack(side="left", fill="x", expand=True)

        tk.Label(
            input_box,
            text="📷 Leitor USB / Scanner (Aproxime o código do medicamento):",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_PANEL_BG,
            fg="#e2e8f0",
        ).pack(anchor="w", pady=(0, 4))

        self.scanner_entry = tk.Entry(
            input_box,
            font=("Consolas", 14),
            bg=COLOR_BG_DARK,
            fg="#38bdf8",
            insertbackground="#38bdf8",
            relief="flat",
            highlightthickness=2,
            highlightbackground="#475569",
            highlightcolor=COLOR_ACCENT,
        )
        self.scanner_entry.pack(fill="x", ipady=6)
        self.scanner_entry.bind("<Return>", lambda e: self.on_scanner_submit())

        # Botão de processar manual
        btn_scan = ttk.Button(
            scanner_card,
            text="Bipar / Buscar",
            style="Primary.TButton",
            cursor="hand2",
            command=self.on_scanner_submit,
        )
        btn_scan.pack(side="right", padx=(16, 0), pady=(18, 0))

    def _build_main_content(self):
        """Área central: Cartão de feedback + Simulador OLED + Tabela do Catálogo."""
        main_frame = tk.Frame(self.root, bg=COLOR_BG_DARK, padx=20, pady=6)
        main_frame.pack(fill="both", expand=True)

        # Painel Esquerdo: Card de Resultado + Prévia do Display OLED
        left_panel = tk.Frame(main_frame, bg=COLOR_BG_DARK, width=340)
        left_panel.pack(side="left", fill="y", padx=(0, 16))

        # 1. Card do Medicamento Selecionado
        card_title = tk.Label(
            left_panel,
            text="Medicamento Lido / Selecionado",
            font=("Segoe UI", 10, "bold"),
            bg=COLOR_BG_DARK,
            fg=COLOR_TEXT_MUTED,
        )
        card_title.pack(anchor="w", pady=(0, 4))

        self.med_card = tk.Frame(left_panel, bg=COLOR_PANEL_BG, padx=14, pady=12)
        self.med_card.pack(fill="x", pady=(0, 14))

        self.lbl_med_name = tk.Label(
            self.med_card,
            text="Nenhum item lido",
            font=("Segoe UI", 13, "bold"),
            bg=COLOR_PANEL_BG,
            fg=COLOR_TEXT_WHITE,
            wraplength=300,
            justify="left",
        )
        self.lbl_med_name.pack(anchor="w")

        self.lbl_med_dosage = tk.Label(
            self.med_card,
            text="Aguardando bip do scanner...",
            font=("Segoe UI", 10),
            bg=COLOR_PANEL_BG,
            fg=COLOR_TEXT_MUTED,
        )
        self.lbl_med_dosage.pack(anchor="w", pady=(2, 2))

        self.lbl_med_validity = tk.Label(
            self.med_card,
            text="Lote: --  •  Validade: --/--/----",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_PANEL_BG,
            fg="#38bdf8",
        )
        self.lbl_med_validity.pack(anchor="w", pady=(0, 6))

        self.lbl_stock_badge = tk.Label(
            self.med_card,
            text="SALDO: --",
            font=("Segoe UI", 11, "bold"),
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT_WHITE,
            padx=8,
            pady=4,
        )
        self.lbl_stock_badge.pack(anchor="w", pady=(4, 6))

        # Simulador dos 3 LEDs de Aviso + Buzzer do Arduino (Verde, Amarelo, Vermelho)
        leds_frame = tk.Frame(self.med_card, bg=COLOR_PANEL_BG)
        leds_frame.pack(fill="x", pady=(4, 0))
        tk.Label(
            leds_frame,
            text="LED / Buzzer Arduino:",
            font=("Segoe UI", 8, "bold"),
            bg=COLOR_PANEL_BG,
            fg=COLOR_TEXT_MUTED,
        ).pack(side="left", padx=(0, 6))
        self.lbl_led_indicator = tk.Label(
            leds_frame,
            text="🟢 VERDE | 🔊 1 Bipe (Lote Válido & Estoque OK)",
            font=("Segoe UI", 8, "bold"),
            bg="#064e3b",
            fg="#34d399",
            padx=6,
            pady=2,
        )
        self.lbl_led_indicator.pack(side="left")

        # 2. Simulador Visual do Display OLED do Arduino
        tk.Label(
            left_panel,
            text="📺 Prévia Display OLED (SSD1306 128x64)",
            font=("Segoe UI", 10, "bold"),
            bg=COLOR_BG_DARK,
            fg=COLOR_TEXT_MUTED,
        ).pack(anchor="w", pady=(0, 4))

        oled_bezel = tk.Frame(
            left_panel,
            bg="#111827",
            padx=8,
            pady=8,
            relief="groove",
            highlightthickness=1,
            highlightbackground="#374151",
        )
        oled_bezel.pack(fill="x")

        self.oled_screen = tk.Label(
            oled_bezel,
            text="[ FARMACIA & ESTOQUE ]\n---------------------\nAguardando Leitura...",
            font=("Consolas", 10, "bold"),
            bg=COLOR_OLED_BG,
            fg=COLOR_OLED_TXT,
            justify="left",
            anchor="nw",
            padx=10,
            pady=10,
            height=6,
        )
        self.oled_screen.pack(fill="both", expand=True)

        # Painel Direito: Catálogo de Medicamentos & Ações
        right_panel = tk.Frame(main_frame, bg=COLOR_PANEL_BG, padx=16, pady=14)
        right_panel.pack(side="right", fill="both", expand=True)

        # Barra Superior da Tabela: Título + Busca + Botão Novo
        table_top = tk.Frame(right_panel, bg=COLOR_PANEL_BG)
        table_top.pack(fill="x", pady=(0, 10))

        tk.Label(
            table_top,
            text="Catálogo de Medicamentos",
            font=("Segoe UI", 12, "bold"),
            bg=COLOR_PANEL_BG,
            fg=COLOR_TEXT_WHITE,
        ).pack(side="left")

        btn_new_med = ttk.Button(
            table_top,
            text="+ Novo Medicamento",
            style="Success.TButton",
            cursor="hand2",
            command=self.open_add_modal,
        )
        btn_new_med.pack(side="right")

        # Campo de Busca
        self.search_entry = tk.Entry(
            table_top,
            font=("Segoe UI", 9),
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT_WHITE,
            insertbackground=COLOR_TEXT_WHITE,
            relief="flat",
            width=22,
        )
        self.search_entry.pack(side="right", padx=10, ipady=3)
        self.search_entry.bind("<KeyRelease>", lambda e: self.filter_medications())
        tk.Label(
            table_top,
            text="Filtrar:",
            font=("Segoe UI", 9),
            bg=COLOR_PANEL_BG,
            fg=COLOR_TEXT_MUTED,
        ).pack(side="right")

        # Tabela Treeview
        tree_container = tk.Frame(right_panel, bg=COLOR_PANEL_BG)
        tree_container.pack(fill="both", expand=True)

        columns = ("batch", "name", "dosage", "validity", "stock", "status")
        self.tree = ttk.Treeview(
            tree_container,
            columns=columns,
            show="headings",
            style="Custom.Treeview",
            selectmode="browse",
        )

        self.tree.heading("batch", text="Lote / Cód.")
        self.tree.heading("name", text="Medicamento")
        self.tree.heading("dosage", text="Dosagem")
        self.tree.heading("validity", text="Validade (FEFO)")
        self.tree.heading("stock", text="Saldo Atual")
        self.tree.heading("status", text="Status & Validade")

        self.tree.column("batch", width=115, anchor="w")
        self.tree.column("name", width=165, anchor="w")
        self.tree.column("dosage", width=75, anchor="w")
        self.tree.column("validity", width=110, anchor="center")
        self.tree.column("stock", width=90, anchor="center")
        self.tree.column("status", width=130, anchor="center")

        scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # Botões de Ação Rápida sob a tabela
        action_bar = tk.Frame(right_panel, bg=COLOR_PANEL_BG, pady=10)
        action_bar.pack(fill="x")

        ttk.Button(
            action_bar,
            text="- Baixa FEFO (-1)",
            style="Danger.TButton",
            cursor="hand2",
            command=lambda: self.quick_action_selected("saida", 1),
        ).pack(side="left", padx=4)

        ttk.Button(
            action_bar,
            text="+ Novo Lote / Validade",
            style="Success.TButton",
            cursor="hand2",
            command=self.open_add_batch_modal,
        ).pack(side="left", padx=4)

        ttk.Button(
            action_bar,
            text="Excluir Item",
            style="OutlineDanger.TButton",
            cursor="hand2",
            command=self.delete_selected,
        ).pack(side="right", padx=4)

    def _build_status_bar(self):
        """Barra de status inferior."""
        self.status_bar = tk.Frame(self.root, bg="#0b0f19", height=26, padx=20)
        self.status_bar.pack(fill="x", side="bottom")

        self.lbl_status = tk.Label(
            self.status_bar,
            text="Sistema pronto. Conecte o leitor USB e o Arduino para iniciar.",
            font=("Segoe UI", 8),
            bg="#0b0f19",
            fg=COLOR_TEXT_MUTED,
        )
        self.lbl_status.pack(side="left", pady=4)

        self.lbl_db_info = tk.Label(
            self.status_bar,
            text=f"Banco: SQLite Local ({LOCAL_DB_PATH})",
            font=("Segoe UI", 8),
            bg="#0b0f19",
            fg="#64748b",
        )
        self.lbl_db_info.pack(side="right", pady=4)

    # ================= LOGICA DE BANCO DE DADOS E SCANNER =================
    def refresh_ports(self):
        portas = self.arduino.listar_portas()
        self.port_combo["values"] = portas
        if portas:
            self.port_combo.current(0)
            self.lbl_status.config(text=f"Portas detectadas: {', '.join(portas)}")
        else:
            self.port_combo.set("Nenhuma")
            self.lbl_status.config(text="Nenhum Arduino detectado nas portas COM.")

    def toggle_serial(self):
        if self.arduino.is_conectado():
            self.arduino.desconectar()
            self.btn_serial_toggle.config(text="Conectar Display", style="Accent.TButton")
            self.lbl_status.config(text="Arduino desconectado.")
        else:
            porta = self.port_combo.get()
            if not porta or porta == "Nenhuma":
                messagebox.showwarning("Aviso", "Selecione uma porta COM válida.")
                return

            sucesso, msg = self.arduino.conectar(porta, 115200)
            if sucesso:
                self.btn_serial_toggle.config(text="Desconectar", style="Danger.TButton")
                self.lbl_status.config(text=f"Conectado ao Arduino em {porta} (115200 bps).")
            else:
                messagebox.showerror("Erro de Conexão", msg)

    def on_scanner_submit(self):
        codigo = self.scanner_entry.get().strip()
        self.scanner_entry.delete(0, tk.END)
        if not codigo:
            return

        self.process_code(codigo)
        # Mantém o foco no campo de texto para o próximo bip
        self.scanner_entry.focus_set()

    def _get_batches_for_med(self, db: Session, med_id: str) -> List[MedicationBatchModel]:
        return (
            db.query(MedicationBatchModel)
            .filter(MedicationBatchModel.medication_id == med_id)
            .order_by(MedicationBatchModel.expiration_date.asc())
            .all()
        )

    def _get_validity_summary(self, db: Session, med: MedicationModel) -> tuple[str, str, str, str]:
        """Retorna (lote_str, validade_str, status_combinado, cor_led_arduino)."""
        batches = self._get_batches_for_med(db, med.id)
        active = [b for b in batches if b.quantity > 0]
        target_list = active if active else batches

        hoje = date.today()
        lote_str = med.barcode or "-"
        val_str = "Sem validade"
        tem_vencido = False
        tem_vencendo = False

        if target_list:
            b_first = target_list[0]
            lote_str = f"{b_first.batch_number} ({len(active or batches)}x)" if len(batches) > 1 else b_first.batch_number
            val_str = b_first.expiration_date.strftime("%d/%m/%Y")
            for b in active:
                dias = (b.expiration_date - hoje).days
                if dias < 0:
                    tem_vencido = True
                elif dias <= 30:
                    tem_vencendo = True
            if not active:
                dias_first = (b_first.expiration_date - hoje).days
                if dias_first < 0:
                    tem_vencido = True
                elif dias_first <= 30:
                    tem_vencendo = True

        est_status = self.get_status_text(med)
        if tem_vencido:
            return lote_str, val_str, "🔴 LOTE VENCIDO", "RED"
        if est_status == "ESGOTADO":
            return lote_str, val_str, "🔴 ESGOTADO", "RED"
        if tem_vencendo:
            return lote_str, val_str, "🟡 VENCE <=30d", "YELLOW"
        if est_status == "BAIXO":
            return lote_str, val_str, "🟡 EST. BAIXO", "YELLOW"
        return lote_str, val_str, "🟢 OK / VÁLIDO", "GREEN"

    def _emit_buzzer_sound(self, beeps: int = 1):
        """Simula no PC os bipes do Buzzer do Arduino (Pino D8)."""
        for i in range(beeps):
            self.after(i * 180, self.bell)

    def _update_led_ui(self, cor_led: str):
        if cor_led == "RED":
            self.lbl_led_indicator.config(
                text="🔴 VERMELHO | 🚨 Alarme 3x Bipes (Lote Vencido / Sem Estoque)",
                bg="#7f1d1d",
                fg="#fca5a5",
            )
            self._emit_buzzer_sound(3)
        elif cor_led == "YELLOW":
            self.lbl_led_indicator.config(
                text="🟡 AMARELO | 🔊 Alerta 2x Bipes (Vence <=30d / Estoque Baixo)",
                bg="#78350f",
                fg="#fcd34d",
            )
            self._emit_buzzer_sound(2)
        else:
            self.lbl_led_indicator.config(
                text="🟢 VERDE | 🔊 1 Bipe OK (Lote Válido & Estoque OK)",
                bg="#064e3b",
                fg="#34d399",
            )
            self._emit_buzzer_sound(1)

    def process_code(self, code: str):
        db: Session = SessionLocal()
        try:
            lote_bipado = (
                db.query(MedicationBatchModel)
                .filter(MedicationBatchModel.batch_number.ilike(code))
                .first()
            )
            med = None
            if lote_bipado:
                med = db.query(MedicationModel).filter(MedicationModel.id == lote_bipado.medication_id).first()

            if not med:
                med = db.query(MedicationModel).filter(MedicationModel.barcode == code).first()
            if not med:
                med = db.query(MedicationModel).filter(MedicationModel.id == code).first()
            if not med and ("|" in code or ";" in code):
                partes = code.split("|" if "|" in code else ";")
                nome_busca = partes[0].strip()
                med = db.query(MedicationModel).filter(MedicationModel.name.ilike(f"%{nome_busca}%")).first()
            if not med:
                med = db.query(MedicationModel).filter(MedicationModel.name.ilike(f"%{code}%")).first()

            if not med:
                self.lbl_med_name.config(text="Não Encontrado!")
                self.lbl_med_dosage.config(text=f"Código lido: '{code}' não cadastrado.")
                self.lbl_med_validity.config(text="Lote: --  •  Validade: --/--/----", fg="#f87171")
                self.lbl_stock_badge.config(text="CÓDIGO NÃO CADASTRADO", bg=COLOR_DANGER)
                self._update_led_ui("RED")

                oled_texto = f"NAO ENCONTRADO!\nCod: {code[:12]}\nCadastre o item"
                self.update_oled_preview(oled_texto)
                self.arduino.enviar_para_oled(oled_texto, cor_led="RED")
                self.lbl_status.config(text=f"Código '{code}' não localizado.")

                deseja_cadastrar = messagebox.askyesno(
                    "Código Não Cadastrado",
                    f"O código '{code}' lido pelo scanner não está cadastrado no sistema.\n\nDeseja cadastrar um novo medicamento/lote com este código agora?",
                )
                if deseja_cadastrar:
                    self.open_add_modal(prefill_barcode=code)
                return

            modo = self.current_mode.get()
            qtd = 1
            lote_str, val_str, status_comb, cor_led = self._get_validity_summary(db, med)

            if modo == "consulta":
                self.show_med_info(med, db)
                oled_texto = f"{med.name[:18]}\nLote: {lote_str[:12]}\nVal: {val_str}\nSaldo: {med.current_stock} {med.unit}"
                self.update_oled_preview(oled_texto)
                self.arduino.enviar_para_oled(oled_texto, cor_led=cor_led)
                self.lbl_status.config(text=f"Consulta: '{med.name}' | Lote: {lote_str} | Validade: {val_str}")

            elif modo == "saida":
                batches = self._get_batches_for_med(db, med.id)
                active_batches = [b for b in batches if b.quantity > 0]
                hoje = date.today()

                # Se bipou um lote específico e ele está vencido -> bloqueia
                if lote_bipado and lote_bipado.expiration_date < hoje:
                    self.show_med_info(med, db)
                    self._update_led_ui("RED")
                    oled_texto = f"! LOTE VENCIDO !\n{med.name[:18]}\nLote: {lote_bipado.batch_number}\nVal: {lote_bipado.expiration_date.strftime('%d/%m/%Y')}"
                    self.update_oled_preview(oled_texto)
                    self.arduino.enviar_para_oled(oled_texto, cor_led="RED")
                    messagebox.showerror(
                        "Bloqueio de Segurança — Lote Vencido",
                        f"O lote '{lote_bipado.batch_number}' de '{med.name}' está VENCIDO desde {lote_bipado.expiration_date.strftime('%d/%m/%Y')}!\n\nA saída foi bloqueada e o LED Vermelho foi acionado.",
                    )
                    return

                valid_batches = [b for b in active_batches if b.expiration_date >= hoje]
                expired_batches = [b for b in active_batches if b.expiration_date < hoje]

                if active_batches and not valid_batches and expired_batches:
                    b_exp = expired_batches[0]
                    self.show_med_info(med, db)
                    self._update_led_ui("RED")
                    oled_texto = f"! LOTE VENCIDO !\n{med.name[:18]}\nLote: {b_exp.batch_number}\nVal: {b_exp.expiration_date.strftime('%d/%m/%Y')}"
                    self.update_oled_preview(oled_texto)
                    self.arduino.enviar_para_oled(oled_texto, cor_led="RED")
                    messagebox.showerror(
                        "Bloqueio de Segurança — Lote Vencido",
                        f"As unidades disponíveis de '{med.name}' pertencem ao lote VENCIDO '{b_exp.batch_number}' (Validade: {b_exp.expiration_date.strftime('%d/%m/%Y')})!\n\nA saída foi bloqueada.",
                    )
                    return

                if med.current_stock < qtd:
                    self._update_led_ui("RED")
                    messagebox.showwarning(
                        "Estoque Insuficiente",
                        f"O medicamento '{med.name}' está com saldo {med.current_stock}. Impossível retirar {qtd} unidade(s)!",
                    )
                    oled_texto = f"{med.name[:18]}\nESTOQUE ESGOTADO!\nSaldo: {med.current_stock}"
                    self.update_oled_preview(oled_texto)
                    self.arduino.enviar_para_oled(oled_texto, cor_led="RED")
                    return

                alvo_lote = lote_bipado if (lote_bipado and lote_bipado.quantity >= qtd) else (valid_batches[0] if valid_batches else None)
                lote_usado_num = None
                if alvo_lote:
                    alvo_lote.quantity = max(0, alvo_lote.quantity - qtd)
                    lote_usado_num = alvo_lote.batch_number

                prev = med.current_stock
                med.current_stock -= qtd
                med.updated_at = datetime.now(timezone.utc)

                mov = StockMovementModel(
                    medication_id=med.id,
                    batch_id=alvo_lote.id if alvo_lote else None,
                    batch_number=lote_usado_num,
                    movement_type="SAIDA",
                    quantity=qtd,
                    previous_stock=prev,
                    new_stock=med.current_stock,
                    reason=f"Baixa FEFO via Scanner [Lote: {lote_usado_num or 'Padrão'}]",
                )
                db.add(mov)
                db.commit()
                db.refresh(med)

                self.show_med_info(med, db)
                lote_str, val_str, _, cor_led = self._get_validity_summary(db, med)
                oled_texto = f"{med.name[:18]}\nLote:{(lote_usado_num or lote_str)[:10]} (-{qtd})\nVal: {val_str}\nSaldo: {med.current_stock}"
                self.update_oled_preview(oled_texto)
                self.arduino.enviar_para_oled(oled_texto, cor_led=cor_led)
                self.lbl_status.config(text=f"Baixa FEFO: '{med.name}' (Lote: {lote_usado_num or lote_str}) | Novo saldo: {med.current_stock}")

            elif modo == "entrada":
                batches = self._get_batches_for_med(db, med.id)
                alvo_lote = lote_bipado or (batches[-1] if batches else None)
                if alvo_lote:
                    alvo_lote.quantity += qtd

                prev = med.current_stock
                med.current_stock += qtd
                med.updated_at = datetime.now(timezone.utc)

                mov = StockMovementModel(
                    medication_id=med.id,
                    batch_id=alvo_lote.id if alvo_lote else None,
                    batch_number=alvo_lote.batch_number if alvo_lote else None,
                    movement_type="ENTRADA",
                    quantity=qtd,
                    previous_stock=prev,
                    new_stock=med.current_stock,
                    reason="Reposição de estoque via Scanner",
                )
                db.add(mov)
                db.commit()
                db.refresh(med)

                self.show_med_info(med, db)
                lote_str, val_str, _, cor_led = self._get_validity_summary(db, med)
                oled_texto = f"{med.name[:18]}\nLote: {lote_str[:12]} (+{qtd})\nVal: {val_str}\nSaldo: {med.current_stock}"
                self.update_oled_preview(oled_texto)
                self.arduino.enviar_para_oled(oled_texto, cor_led=cor_led)
                self.lbl_status.config(text=f"Entrada registrada: '{med.name}' | Novo saldo: {med.current_stock}")

            self.load_medications()
        finally:
            db.close()

    def show_med_info(self, med: MedicationModel, db: Optional[Session] = None):
        own_db = False
        if db is None:
            db = SessionLocal()
            own_db = True
        try:
            self.lbl_med_name.config(text=med.name)
            bar_text = f"Cód: {med.barcode} • " if med.barcode else ""
            self.lbl_med_dosage.config(text=f"{bar_text}Dosagem: {med.dosage} ({med.unit})")

            lote_str, val_str, status_comb, cor_led = self._get_validity_summary(db, med)
            cor_val = "#34d399" if cor_led == "GREEN" else ("#fbbf24" if cor_led == "YELLOW" else "#f87171")
            self.lbl_med_validity.config(
                text=f"Lote: {lote_str}  •  Validade: {val_str}",
                fg=cor_val,
            )
            self._update_led_ui(cor_led)

            cor_badge = COLOR_SUCCESS if cor_led == "GREEN" else (COLOR_WARNING if cor_led == "YELLOW" else COLOR_DANGER)
            self.lbl_stock_badge.config(
                text=f"SALDO: {med.current_stock} {med.unit.upper()}  [{status_comb}]",
                bg=cor_badge,
            )
        finally:
            if own_db:
                db.close()

    def get_status_text(self, med: MedicationModel) -> str:
        if med.current_stock <= 0:
            return "ESGOTADO"
        elif med.current_stock <= med.minimum_stock:
            return "BAIXO"
        return "OK"

    def update_oled_preview(self, texto: str):
        header = "[ MEDICA SENTINELA ]\n---------------------\n"
        self.oled_screen.config(text=header + texto)

    def load_medications(self):
        """Carrega e renderiza o catálogo de medicamentos com Lote e Validade na tabela."""
        for row in self.tree.get_children():
            self.tree.delete(row)

        db: Session = SessionLocal()
        try:
            meds = db.query(MedicationModel).order_by(MedicationModel.name.asc()).all()
            for m in meds:
                lote_str, val_str, status_comb, _ = self._get_validity_summary(db, m)
                self.tree.insert(
                    "",
                    "end",
                    iid=m.id,
                    values=(
                        lote_str,
                        m.name,
                        m.dosage,
                        val_str,
                        f"{m.current_stock} {m.unit}",
                        status_comb,
                    ),
                )
        finally:
            db.close()

    def filter_medications(self):
        filtro = self.search_entry.get().strip().lower()
        db: Session = SessionLocal()
        try:
            query = db.query(MedicationModel)
            if filtro:
                query = query.filter(
                    (MedicationModel.name.ilike(f"%{filtro}%")) |
                    (MedicationModel.barcode.ilike(f"%{filtro}%"))
                )
            meds = query.order_by(MedicationModel.name.asc()).all()

            for row in self.tree.get_children():
                self.tree.delete(row)

            for m in meds:
                lote_str, val_str, status_comb, _ = self._get_validity_summary(db, m)
                self.tree.insert(
                    "",
                    "end",
                    iid=m.id,
                    values=(
                        lote_str,
                        m.name,
                        m.dosage,
                        val_str,
                        f"{m.current_stock} {m.unit}",
                        status_comb,
                    ),
                )
        finally:
            db.close()

    def on_tree_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        med_id = selected[0]
        db: Session = SessionLocal()
        try:
            med = db.query(MedicationModel).filter(MedicationModel.id == med_id).first()
            if med:
                self.show_med_info(med, db)
                lote_str, val_str, _, cor_led = self._get_validity_summary(db, med)
                oled_texto = f"{med.name[:18]}\nLote: {lote_str[:12]}\nVal: {val_str}\nSaldo: {med.current_stock} {med.unit}"
                self.update_oled_preview(oled_texto)
                self.arduino.enviar_para_oled(oled_texto, cor_led=cor_led)
        finally:
            db.close()

    def quick_action_selected(self, mov_type: str, qty: int):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Aviso", "Selecione um medicamento na tabela primeiro.")
            return

        med_id = selected[0]
        db: Session = SessionLocal()
        try:
            med = db.query(MedicationModel).filter(MedicationModel.id == med_id).first()
            if not med:
                return

            batches = self._get_batches_for_med(db, med.id)
            active_batches = [b for b in batches if b.quantity > 0]
            hoje = date.today()
            valid_batches = [b for b in active_batches if b.expiration_date >= hoje]
            expired_batches = [b for b in active_batches if b.expiration_date < hoje]

            if mov_type == "saida":
                if active_batches and not valid_batches and expired_batches:
                    b_exp = expired_batches[0]
                    self._update_led_ui("RED")
                    oled_texto = f"! LOTE VENCIDO !\n{med.name[:18]}\nLote: {b_exp.batch_number}\nVal: {b_exp.expiration_date.strftime('%d/%m/%Y')}"
                    self.update_oled_preview(oled_texto)
                    self.arduino.enviar_para_oled(oled_texto, cor_led="RED")
                    messagebox.showerror(
                        "Bloqueio de Segurança — Lote Vencido",
                        f"O lote '{b_exp.batch_number}' de '{med.name}' está VENCIDO desde {b_exp.expiration_date.strftime('%d/%m/%Y')}!\n\nA saída foi bloqueada e o LED Vermelho foi acionado.",
                    )
                    return

                if med.current_stock < qty:
                    messagebox.showwarning(
                        "Saldo Insuficiente",
                        f"Estoque insuficiente ({med.current_stock}). Impossível retirar {qty} unidade(s).",
                    )
                    return

            lote_usado_num = None
            alvo_lote = None
            prev = med.current_stock
            if mov_type == "saida":
                med.current_stock -= qty
                if valid_batches:
                    alvo_lote = valid_batches[0]
                    alvo_lote.quantity = max(0, alvo_lote.quantity - qty)
                    lote_usado_num = alvo_lote.batch_number
            else:
                med.current_stock += qty
                if batches:
                    alvo_lote = batches[-1]
                    alvo_lote.quantity += qty
                    lote_usado_num = alvo_lote.batch_number

            med.updated_at = datetime.now(timezone.utc)
            mov = StockMovementModel(
                medication_id=med.id,
                batch_id=alvo_lote.id if alvo_lote else None,
                batch_number=lote_usado_num,
                movement_type=mov_type.upper(),
                quantity=qty,
                previous_stock=prev,
                new_stock=med.current_stock,
                reason=f"Operação FEFO ({mov_type.upper()}) [Lote: {lote_usado_num or 'Padrão'}]",
            )
            db.add(mov)
            db.commit()
            db.refresh(med)

            self.show_med_info(med, db)
            lote_str, val_str, _, cor_led = self._get_validity_summary(db, med)
            oled_texto = (
                f"{med.name[:18]}\n"
                f"Lote:{(lote_usado_num or lote_str)[:10]} ({'-' if mov_type=='saida' else '+'}{qty})\n"
                f"Val: {val_str}\n"
                f"Novo Saldo: {med.current_stock}"
            )
            self.update_oled_preview(oled_texto)
            self.arduino.enviar_para_oled(oled_texto, cor_led=cor_led)
            self.load_medications()
        finally:
            db.close()

    def open_add_batch_modal(self):
        """Modal para adicionar um novo lote com validade a um medicamento existente."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Selecione um Medicamento", "Selecione um medicamento na tabela para adicionar um novo lote com validade.")
            return

        med_id = selected[0]
        db: Session = SessionLocal()
        try:
            med = db.query(MedicationModel).filter(MedicationModel.id == med_id).first()
            if not med:
                return
            med_nome = f"{med.name} ({med.dosage})"
            med_unit = med.unit
        finally:
            db.close()

        modal = tk.Toplevel(self.root)
        modal.title(f"Novo Lote & Validade • {med_nome}")
        modal.geometry("430x360")
        modal.configure(bg=COLOR_PANEL_BG)
        modal.transient(self.root)
        modal.grab_set()

        tk.Label(
            modal,
            text=f"+ Novo Lote para {med_nome}",
            font=("Segoe UI", 12, "bold"),
            bg=COLOR_PANEL_BG,
            fg=COLOR_TEXT_WHITE,
        ).pack(pady=(14, 10))

        form = tk.Frame(modal, bg=COLOR_PANEL_BG, padx=20)
        form.pack(fill="both", expand=True)

        def add_field(label_text, default=""):
            tk.Label(
                form,
                text=label_text,
                font=("Segoe UI", 9, "bold"),
                bg=COLOR_PANEL_BG,
                fg=COLOR_TEXT_MUTED,
            ).pack(anchor="w", pady=(4, 1))
            entry = tk.Entry(
                form,
                font=("Segoe UI", 10),
                bg=COLOR_CARD_BG,
                fg=COLOR_TEXT_WHITE,
                insertbackground=COLOR_TEXT_WHITE,
                relief="flat",
            )
            entry.pack(fill="x", ipady=3)
            if default:
                entry.insert(0, default)
            return entry

        sugestao_lote = f"LOTE-{date.today().strftime('%Y%m')}-B"
        sugestao_val = (date.today() + timedelta(days=365)).strftime("%d/%m/%Y")

        ent_batch = add_field("Código do Lote (ex: LOTE-2026B)", default=sugestao_lote)
        ent_qty = add_field(f"Quantidade no Lote ({med_unit}s - ex: 50 caixas)", default="50")
        ent_exp = add_field("Data de Validade (DD/MM/AAAA ou AAAA-MM-DD)", default=sugestao_val)

        def salvar_lote():
            cod_lote = ent_batch.get().strip().upper()
            if not cod_lote:
                messagebox.showerror("Erro", "Informe o código do lote.", parent=modal)
                return
            try:
                qtd = int(ent_qty.get().strip())
                if qtd <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Erro", "A quantidade do lote deve ser um número maior que zero.", parent=modal)
                return

            dt_val = parse_data_validade(ent_exp.get())
            if not dt_val:
                messagebox.showerror(
                    "Data de Validade Inválida",
                    "Informe a Data de Validade no formato DD/MM/AAAA (ex: 15/08/2027) ou AAAA-MM-DD.",
                    parent=modal,
                )
                return

            db_s: Session = SessionLocal()
            try:
                m_obj = db_s.query(MedicationModel).filter(MedicationModel.id == med_id).first()
                if not m_obj:
                    return
                novo_lote = MedicationBatchModel(
                    medication_id=m_obj.id,
                    batch_number=cod_lote,
                    quantity=qtd,
                    expiration_date=dt_val,
                )
                db_s.add(novo_lote)

                prev = m_obj.current_stock
                m_obj.current_stock += qtd
                m_obj.updated_at = datetime.now(timezone.utc)

                mov = StockMovementModel(
                    medication_id=m_obj.id,
                    batch_id=novo_lote.id,
                    batch_number=cod_lote,
                    movement_type="ENTRADA",
                    quantity=qtd,
                    previous_stock=prev,
                    new_stock=m_obj.current_stock,
                    reason=f"Entrada do lote {cod_lote} (Val: {dt_val.strftime('%d/%m/%Y')})",
                )
                db_s.add(mov)
                db_s.commit()
                db_s.refresh(m_obj)

                self.show_med_info(m_obj, db_s)
                modal.destroy()
                self.load_medications()
                self.lbl_status.config(
                    text=f"Lote '{cod_lote}' ({qtd} {med_unit}s | Val: {dt_val.strftime('%d/%m/%Y')}) adicionado!"
                )
            finally:
                db_s.close()

        ttk.Button(
            form,
            text="Salvar Novo Lote & Validade",
            style="Success.TButton",
            cursor="hand2",
            command=salvar_lote,
        ).pack(fill="x", pady=18)

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Aviso", "Selecione um medicamento para excluir.")
            return

        med_id = selected[0]
        db: Session = SessionLocal()
        try:
            med = db.query(MedicationModel).filter(MedicationModel.id == med_id).first()
            if not med:
                return

            ok = messagebox.askyesno(
                "Confirmar Exclusão",
                f"Tem certeza que deseja apagar '{med.name} ({med.dosage})' e todos os seus lotes/histórico?",
            )
            if not ok:
                return

            db.query(MedicationBatchModel).filter(MedicationBatchModel.medication_id == med.id).delete()
            db.delete(med)
            db.commit()
            self.lbl_status.config(text=f"Medicamento '{med.name}' excluído.")
            self.load_medications()
        finally:
            db.close()

    def open_add_modal(self, prefill_barcode: str = ""):
        """Janela modal para cadastrar novo medicamento com Lote Inicial e Data de Validade."""
        modal = tk.Toplevel(self.root)
        modal.title("Cadastrar Medicamento, Lote & Validade")
        modal.geometry("460x640")
        modal.configure(bg=COLOR_PANEL_BG)
        modal.transient(self.root)
        modal.grab_set()

        tk.Label(
            modal,
            text="Novo Medicamento + Lote & Validade",
            font=("Segoe UI", 12, "bold"),
            bg=COLOR_PANEL_BG,
            fg=COLOR_TEXT_WHITE,
        ).pack(pady=(12, 8))

        form = tk.Frame(modal, bg=COLOR_PANEL_BG, padx=20)
        form.pack(fill="both", expand=True)

        def add_field(label_text, default=""):
            tk.Label(
                form,
                text=label_text,
                font=("Segoe UI", 9, "bold"),
                bg=COLOR_PANEL_BG,
                fg=COLOR_TEXT_MUTED,
            ).pack(anchor="w", pady=(3, 1))
            entry = tk.Entry(
                form,
                font=("Segoe UI", 10),
                bg=COLOR_CARD_BG,
                fg=COLOR_TEXT_WHITE,
                insertbackground=COLOR_TEXT_WHITE,
                relief="flat",
            )
            entry.pack(fill="x", ipady=3)
            if default:
                entry.insert(0, default)
            return entry

        sugestao_lote = f"LOTE-{date.today().strftime('%Y%m')}-01"
        sugestao_validade = (date.today() + timedelta(days=365)).strftime("%d/%m/%Y")

        ent_barcode = add_field("Código de Barras / QR Code (EAN ou Scanner)", default=prefill_barcode)
        ent_name = add_field("Nome do Medicamento (ex: Dipirona)")
        ent_dosage = add_field("Dosagem (ex: 500mg ou 100mg/ml)")
        ent_unit = add_field("Unidade de Apresentação (ex: caixa, comprimido)", default="caixa")
        ent_batch = add_field("Código do Lote Inicial (ex: LOTE-2026A)", default=sugestao_lote)
        ent_validity = add_field("Data de Validade do Lote (DD/MM/AAAA) *", default=sugestao_validade)
        ent_stock = add_field("Quantidade neste Lote (ex: 50 caixas)", default="50")
        ent_min = add_field("Estoque Mínimo de Alerta", default="15")
        ent_desc = add_field("Descrição / Modo de Uso", default="Dispensação sob prescrição")

        if prefill_barcode:
            modal.after(100, lambda: ent_name.focus_set())
        else:
            modal.after(100, lambda: ent_barcode.focus_set())

        def salvar():
            barcode = ent_barcode.get().strip() or None
            nome = ent_name.get().strip()
            dosagem = ent_dosage.get().strip()
            unidade = ent_unit.get().strip() or "caixa"
            cod_lote = ent_batch.get().strip().upper() or sugestao_lote
            dt_validade = parse_data_validade(ent_validity.get())

            if not dt_validade:
                messagebox.showerror(
                    "Data de Validade Obrigatória",
                    "Informe uma Data de Validade válida no formato DD/MM/AAAA (ex: 15/08/2027) ou AAAA-MM-DD.",
                    parent=modal,
                )
                return

            try:
                estoque = int(ent_stock.get().strip() or "0")
                minimo = int(ent_min.get().strip() or "10")
            except ValueError:
                messagebox.showerror("Erro", "Quantidade do lote e estoque mínimo devem ser números inteiros.", parent=modal)
                return

            if len(nome) < 2 or not dosagem:
                messagebox.showerror("Erro", "Nome e dosagem são obrigatórios.", parent=modal)
                return

            db: Session = SessionLocal()
            try:
                if barcode:
                    existe_cod = db.query(MedicationModel).filter(MedicationModel.barcode == barcode).first()
                    if existe_cod:
                        messagebox.showerror(
                            "Código Duplicado",
                            f"O código de barras '{barcode}' já está cadastrado para '{existe_cod.name} ({existe_cod.dosage})'.",
                            parent=modal,
                        )
                        return

                existe = db.query(MedicationModel).filter(
                    MedicationModel.name.ilike(nome),
                    MedicationModel.dosage.ilike(dosagem),
                ).first()
                if existe:
                    messagebox.showerror("Erro", f"Já existe medicamento com este nome e dosagem (ID: {existe.id})", parent=modal)
                    return

                novo = MedicationModel(
                    barcode=barcode,
                    name=nome,
                    dosage=dosagem,
                    unit=unidade,
                    current_stock=estoque,
                    minimum_stock=minimo,
                    description=ent_desc.get().strip() or None,
                )
                db.add(novo)
                db.commit()
                db.refresh(novo)

                lote_inicial = MedicationBatchModel(
                    medication_id=novo.id,
                    batch_number=cod_lote,
                    quantity=estoque,
                    expiration_date=dt_validade,
                )
                db.add(lote_inicial)
                db.commit()
                db.refresh(lote_inicial)

                if estoque > 0:
                    mov = StockMovementModel(
                        medication_id=novo.id,
                        batch_id=lote_inicial.id,
                        batch_number=cod_lote,
                        movement_type="ENTRADA",
                        quantity=estoque,
                        previous_stock=0,
                        new_stock=estoque,
                        reason=f"Entrada inicial do lote {cod_lote} (Validade: {dt_validade.strftime('%d/%m/%Y')})",
                    )
                    db.add(mov)
                    db.commit()

                modal.destroy()
                self.load_medications()
                self.lbl_status.config(
                    text=f"Medicamento '{nome}' cadastrado com Lote {cod_lote} (Validade: {dt_validade.strftime('%d/%m/%Y')})!"
                )
            finally:
                db.close()

        ttk.Button(
            form,
            text="Salvar Medicamento",
            style="Success.TButton",
            cursor="hand2",
            command=salvar,
        ).pack(fill="x", pady=16)

    def on_close(self):
        self.arduino.desconectar()
        self.root.destroy()


def exibir_splash_carregamento(root: tk.Tk, ao_concluir):
    """Exibe uma tela de carregamento (Splash Screen) antes de iniciar o Medica - Sentinela Enf."""
    root.withdraw()

    splash = tk.Toplevel(root)
    splash.overrideredirect(True)
    splash.configure(bg="#0b0f19", highlightbackground="#06b6d4", highlightthickness=2)

    largura, altura = 460, 250
    pos_x = (splash.winfo_screenwidth() // 2) - (largura // 2)
    pos_y = (splash.winfo_screenheight() // 2) - (altura // 2)
    splash.geometry(f"{largura}x{altura}+{pos_x}+{pos_y}")

    tk.Label(
        splash,
        text="✚ MEDICA - SENTINELA ENF",
        font=("Segoe UI", 17, "bold"),
        bg="#0b0f19",
        fg="#38bdf8",
    ).pack(pady=(34, 6))

    tk.Label(
        splash,
        text="Sistema de Enfermagem • Controle de Lotes, Validade (FEFO) & Arduino IoT",
        font=("Segoe UI", 9),
        bg="#0b0f19",
        fg="#94a3b8",
    ).pack(pady=(0, 24))

    barra_fundo = tk.Canvas(splash, width=360, height=12, bg="#1e293b", highlightthickness=0)
    barra_fundo.pack(pady=(0, 12))
    retangulo_progresso = barra_fundo.create_rectangle(0, 0, 0, 12, fill="#06b6d4", width=0)

    lbl_etapa = tk.Label(
        splash,
        text="Inicializando banco de dados local...",
        font=("Consolas", 9),
        bg="#0b0f19",
        fg="#34d399",
    )
    lbl_etapa.pack()

    etapas = [
        (90, "Carregando catálogo de medicamentos e lotes..."),
        (190, "Verificando prazos de validade (FEFO)..."),
        (285, "Preparando interface de Teclado Matricial e LEDs Arduino..."),
        (360, "Medica - Sentinela Enf pronto!"),
    ]

    def avancar(indice=0):
        if indice < len(etapas):
            larg, msg = etapas[indice]
            barra_fundo.coords(retangulo_progresso, 0, 0, larg, 12)
            lbl_etapa.config(text=msg)
            splash.after(350, lambda: avancar(indice + 1))
        else:
            splash.destroy()
            root.deiconify()
            ao_concluir()

    splash.after(150, lambda: avancar(0))


def main():
    root = tk.Tk()
    app = DesktopApp(root)
    exibir_splash_carregamento(root, lambda: app.scanner_entry.focus_set())
    root.mainloop()


if __name__ == "__main__":
    main()
