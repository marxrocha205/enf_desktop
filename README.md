# 💊 Sistema Desktop & IoT de Gestão de Medicamentos, Estoque e Dispensação (FEFO)

Sistema completo para **Farmácia e Enfermaria**, focado no controle de estoque de medicamentos, rastreabilidade de lotes, controle de validade (**FEFO — First Expired, First Out**) e estação de dispensação integrada com **Scanner de Código de Barras/QR Code** e **Arduino / ESP32 (Display OLED 128x64 + Teclado Matricial 4x4 + LEDs de Alerta)**.

Desenvolvido em **Python 3.11+** com interface gráfica nativa (**Tkinter/TTK**), **FastAPI**, **Pydantic** e **SQLAlchemy**, projetado segundo os princípios de **Clean Architecture** e funcionamento **100% offline** (SQLite local por padrão ou PostgreSQL configurável).

---

## ✨ Principais Funcionalidades

- **🖥️ Aplicação Desktop Nativa (`app_desktop.py`):**
  - Operação 100% local/offline sem necessidade de internet.
  - Leitura contínua de **Scanner USB de Código de Barras / QR Code**.
  - Três modos de operação: **Saída / Dispensação FEFO**, **Entrada de Lote / Reposição** e **Consulta Rápida**.
  - **Simulador Visual em Tempo Real:** Exibe na tela do PC exatamente o que aparece no Display OLED 128x64, os 3 LEDs físicos (Verde, Amarelo e Vermelho) e um Teclado Matricial 4x4 clicável.
  - Gestão completa do catálogo de medicamentos, lotes, datas de validade e histórico de movimentações.

- **📦 Controle Rigoroso de Lotes e Validade (FEFO):**
  - Baixa automática priorizando o lote válido que vence primeiro (**First Expired, First Out**).
  - **Bloqueio automático** de dispensação para lotes vencidos.
  - Alertas visuais de lotes próximos do vencimento (≤ 30 dias) e de estoque abaixo do mínimo.

- **🔌 Integração Hardware via Serial (`firmware_oled_medicamentos.ino`):**
  - **Display OLED SSD1306 (128x64 I2C):** Exibe o medicamento, lote, validade e saldo atualizado.
  - **Teclado Matricial 4x4:** Permite digitar quantidades e alternar modos diretamente no hardware (`A`: Saída, `B`: Entrada, `C`: Consulta, `D`: Alertas, `*`: Limpar, `#`: Confirmar).
  - **3 LEDs de Aviso:**
    - 🟢 **Verde:** Lote válido e estoque normal (`OK`).
    - 🟡 **Amarelo:** Atenção — lote próximo do vencimento (≤ 30 dias) ou estoque baixo (`WARN`).
    - 🔴 **Vermelho:** Crítico/Bloqueio — lote vencido ou estoque esgotado (`RED`/`EXPIRED`).

- **🌐 API RESTful & CLI (`main.py` / `manage_medications.py`):**
  - Endpoints FastAPI para integração externa e portal web (`/portal` e `/docs`).
  - Utilitário de linha de comando para gestão rápida e estação de scanner via terminal (`scanner_station.py`).

---

## 🏛️ Arquitetura do Projeto

O projeto organiza suas responsabilidades seguindo a **Clean Architecture**:

- `app_desktop.py`: Interface Gráfica Desktop completa (Tkinter/TTK) com banco local integrado, simulador OLED/LEDs/Teclado 4x4 e comunicação Serial com Arduino.
- `scanner_station.py`: Estação de dispensação e leitura de código de barras via terminal integrada ao Arduino.
- `manage_medications.py`: CLI para cadastro de medicamentos, consulta de saldos, atualização de estoque e auditoria de histórico.
- `firmware_oled_medicamentos.ino`: Código C++/Arduino para o microcontrolador com Display OLED SSD1306, Teclado Matricial 4x4 e LEDs de status.
- `domain/`: Entidades de negócio (`Medication`, `MedicationBatch`, `StockMovement`), regras FEFO, status de validade e contratos de repositório (`IMedicationRepository`).
- `application/`: Casos de uso (`CreateMedicationUseCase`, `UpdateMedicationUseCase`, `DeleteMedicationUseCase`, `ListMedicationsUseCase`, `UpdateStockCommandUseCase`) e DTOs.
- `infrastructure/`: Persistência SQLAlchemy (`SQLite` / `PostgreSQL`), modelos relacionais e repositórios concretos.
- `presentation/`: Servidor FastAPI (`/api/v1/medications`) e Portal Web (`/portal`).

---

## 🚀 Como Executar

### 1. Criar e ativar o ambiente virtual
```bash
python -m venv .venv
# No Windows:
.venv\Scripts\activate
# No Linux/macOS:
source .venv/bin/activate
```

### 2. Instalar as dependências
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Iniciar a Aplicação Desktop (Recomendado)
No Windows, basta dar dois cliques em [`iniciar_sistema.bat`](iniciar_sistema.bat) ou executar pelo terminal em qualquer sistema operacional:
```bash
python app_desktop.py
```

### 4. Executar a Estação de Scanner no Terminal (Opcional)
```bash
python scanner_station.py --port COM3
# Ou apenas em modo simulação/consulta sem Arduino conectado:
python scanner_station.py --mode consulta
```

### 5. Executar a API REST (Opcional)
```bash
python main.py
# Ou via Uvicorn:
uvicorn presentation.main:app --reload --host 0.0.0.0 --port 8000
```
- **Swagger UI:** `http://localhost:8000/docs`
- **Portal Web:** `http://localhost:8000/portal`

---

## 💻 Uso via Linha de Comando (CLI)

O utilitário [`manage_medications.py`](manage_medications.py) permite gerenciar medicamentos diretamente pelo terminal:

```bash
# 1. Cadastrar medicamento com estoque inicial:
python manage_medications.py add --name "Dipirona Monoidratada" --dosage "500mg" --stock 100 --min-stock 20 --desc "Analgésico e antitérmico"

# 2. Executar movimentação de estoque (ENTRADA, SAIDA ou AJUSTE):
python manage_medications.py update-stock --name "Dipirona" --quantity 30 --type SAIDA --reason "Dispensação na enfermaria"

# 3. Listar medicamentos e saldos de estoque:
python manage_medications.py list
python manage_medications.py list --low-stock

# 4. Consultar histórico e auditoria de movimentações:
python manage_medications.py history --name "Dipirona"
```

---

## 🌐 Endpoints da API de Medicamentos

- **`POST /api/v1/medications/`**: Cadastra um medicamento (e opcionalmente o lote inicial) registrando a movimentação inicial no histórico:
  ```json
  {
    "name": "Paracetamol",
    "dosage": "750mg",
    "unit": "comprimido",
    "barcode": "7891234560012",
    "initial_stock": 50,
    "minimum_stock": 15,
    "batch_number": "LOTE-2026A",
    "expiration_date": "2027-08-15",
    "description": "Analgésico e antitérmico"
  }
  ```
- **`GET /api/v1/medications/`**: Lista todos os medicamentos com status de estoque (`OK`, `LOW`, `OUT_OF_STOCK`), validade dos lotes e cor de alerta do LED (`GREEN`, `YELLOW`, `RED`).
- **`PUT /api/v1/medications/{id}`**: Atualiza dados cadastrais do medicamento.
- **`DELETE /api/v1/medications/{id}`**: Remove um medicamento e seu histórico.
- **`POST /api/v1/medications/{id}/stock`**: Executa movimentação de estoque (`ENTRADA`, `SAIDA` com baixa FEFO automática ou `AJUSTE`):
  ```json
  {
    "movement_type": "SAIDA",
    "quantity": 5,
    "reason": "Dispensação para paciente"
  }
  ```
- **`GET /api/v1/medications/{id}/movements`**: Retorna o histórico cronológico de movimentações do medicamento.

---

## 🔧 Esquema de Ligação do Hardware (Arduino / ESP32)

Firmware principal: [`firmware_oled_medicamentos.ino`](firmware_oled_medicamentos.ino) (Serial `115200 bps`).

1. **Display OLED 0.96" SSD1306 (I2C):**
   - `VCC` → 3.3V ou 5V | `GND` → GND
   - `SDA` → `A4` (Arduino Uno) ou `GPIO 21` (ESP32)
   - `SCL` → `A5` (Arduino Uno) ou `GPIO 22` (ESP32)

2. **LEDs de Aviso de Estoque e Validade (com resistor de 220 Ω):**
   - **LED Verde (`Pino 10`):** Lote válido e estoque OK
   - **LED Amarelo (`Pino 11`):** Lote vence em ≤ 30 dias ou estoque baixo
   - **LED Vermelho (`Pino 12`):** Lote VENCIDO (bloqueado) ou estoque esgotado

3. **Teclado Matricial 4x4:**
   - **Linhas (`R1..R4`):** Pinos `2, 3, 4, 5`
   - **Colunas (`C1..C4`):** Pinos `6, 7, A2, A3`
   - **Teclas:**
     - `0` a `9`: Digita a quantidade
     - `A`: Modo **SAÍDA** (Dispensação FEFO)
     - `B`: Modo **ENTRADA** (Recebimento de Lote)
     - `C`: Modo **CONSULTA** (Conferir Lote e Validade)
     - `D`: Resumo de lotes críticos/vencendo
     - `*`: Limpa a quantidade digitada
     - `#`: Confirma e envia o comando para o sistema Python

---

## 🧪 Testes Automatizados

Para rodar a suíte de testes do sistema de medicamentos, estoque e lotes:
```bash
python test_medication_stock.py
```
