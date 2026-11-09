# 🌡️ IoT Body Temperature API - Backend

API RESTful desenvolvida com **Python 3.11+**, **FastAPI**, **Pydantic** e **SQLAlchemy**, projetada segundo os princípios de **Clean Architecture**, **SOLID** e **Clean Code**.

O sistema atua como o motor de regras de um ecossistema IoT vestível para monitoramento de temperatura corporal:
- **Ingestão:** Recebe pacotes de telemetria via HTTP POST enviados por um microcontrolador **ESP32-C3 SuperMini** integrado ao sensor **MAX30205**.
- **Processamento Clínico:** Classifica o estado térmico (`NORMAL`, `ELEVATED`, `FEVER`).
- **Resiliência e Debounce:** Controle de frequência de alertas de febre integrado com **Upstash Redis**.
- **Persistência Relacional:** Suporte a **Neon PostgreSQL** em produção e SQLite local para desenvolvimento.
- **Consumo:** Fornece histórico e telemetria para aplicativo móvel em **Flutter**.

---

## 🏛️ Arquitetura do Software

A estrutura do projeto adota a separação rigorosa em camadas da **Clean Architecture**:

- `domain/`: Entidades de negócio puras (`TelemetryReading`), classificadores clínicos e interfaces abstratas de repositório (`ITelemetryRepository`).
- `application/`: Casos de uso (`IngestTelemetryUseCase`, `GetHistoryUseCase`) e schemas/DTOs Pydantic.
- `infrastructure/`: Implementação concreta do banco de dados SQLAlchemy, cliente Redis Upstash, logging e configurações (`pydantic-settings`).
- `presentation/`: Endpoints FastAPI (`/api/v1/telemetry`, `/api/v1/history`, `/health`), middlewares de latência e tratamento centralizado de exceções.

---

## 🌿 Estratégia de Branches Git

O repositório opera estritamente com duas branches:
- `main`: Ambiente de produção (deploy contínuo automático no Render). Não aceita commits diretos.
- `develop`: Ambiente de desenvolvimento e integração contínua (CI). Todo desenvolvimento de novas features e sprints deve ser comitado nesta branch.

---

## 🚀 Como Executar Localmente

### 1. Criar e ativar o ambiente virtual:
```bash
python -m venv .venv
# No Windows PowerShell:
.venv\Scripts\Activate.ps1
# No Linux/macOS:
source .venv/bin/activate
```

### 2. Instalar as dependências:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configurar variáveis de ambiente:
Copie o arquivo de exemplo e ajuste as variáveis:
```bash
cp .env.example .env
```

### 4. Iniciar a API:
```bash
python main.py
# Ou diretamente via Uvicorn com live reload:
uvicorn presentation.main:app --reload --host 0.0.0.0 --port 8000
```
- Documentação Swagger Interativa: [http://localhost:8000/docs](http://localhost:8000/docs)
- Portal Web da Porta de Entrada: [http://localhost:8000/portal](http://localhost:8000/portal)
- Health Check: [http://localhost:8000/health](http://localhost:8000/health)

---

## 🔐 Porta de Entrada: Cadastro e Autenticação de Usuários

O sistema possui uma **Porta de Entrada** robusta baseada em **JWT (JSON Web Tokens)** e **PBKDF2-HMAC-SHA256**:

### 1. Interface Web Interativa (`/portal` ou `/`)
Interface moderna em Dark Mode com Glassmorphism para cadastro rápido e login direto pelo navegador:
- Alternância entre abas de **Cadastro** e **Login**.
- Emissão e exibição do Bearer Token JWT.
- Botão de validação imediata da rota protegida `/api/v1/auth/me`.

### 2. Endpoints da API

- **`POST /api/v1/auth/register`**: Cadastro de usuário com validação de força de senha e e-mail único.
  ```json
  {
    "name": "Dr. Carlos Silva",
    "email": "carlos.silva@hospital.com",
    "password": "SenhaForte@2026",
    "role": "CAREGIVER"
  }
  ```
- **`POST /api/v1/auth/login`**: Autenticação na porta de entrada (retorna `access_token` JWT).
- **`GET /api/v1/auth/me`**: Retorna os dados do usuário autenticado (requer cabeçalho `Authorization: Bearer <token>`).
- **`GET /api/v1/auth/users`**: Listagem de usuários (requer perfil `CAREGIVER` ou `ADMIN`).

### 3. Teste Automatizado do Fluxo de Autenticação
```bash
python test_auth_flow.py
```

---

## 💊 Sistema de Gestão de Medicamentos & Controle de Estoque

O sistema possui um módulo completo para cadastro de medicamentos com **comando automático de entrada de estoque** e rastreabilidade total de movimentações (Entrada, Saída e Ajuste).

### 1. Comandos via Linha de Comando (CLI)
Um utilitário de terminal [`manage_medications.py`](manage_medications.py) permite cadastrar medicamentos e executar comandos de estoque diretamente:

```bash
# 1. Cadastrar medicamento (dispara automaticamente a entrada do estoque inicial):
python manage_medications.py add --name "Dipirona Monoidratada" --dosage "500mg" --stock 100 --min-stock 20 --desc "Antitérmico para febre"

# 2. Executar comando de atualização de estoque (ENTRADA, SAIDA ou AJUSTE):
python manage_medications.py update-stock --name "Dipirona" --quantity 30 --type SAIDA --reason "Administrado a pacientes com febre"

# 3. Listar medicamentos e saldos de estoque:
python manage_medications.py list
# Apenas medicamentos com estoque baixo:
python manage_medications.py list --low-stock

# 4. Consultar histórico e auditoria de movimentações:
python manage_medications.py history --name "Dipirona"
```

### 2. Endpoints da API REST

- **`POST /api/v1/medications/`**: Cadastra o medicamento e registra automaticamente a movimentação de estoque inicial no histórico:
  ```json
  {
    "name": "Paracetamol",
    "dosage": "750mg",
    "unit": "comprimido",
    "initial_stock": 50,
    "minimum_stock": 15,
    "description": "Antitérmico para episódios de febre"
  }
  ```
- **`POST /api/v1/medications/{id}/stock`**: Executa comando de movimentação (`ENTRADA`, `SAIDA` ou `AJUSTE`):
  ```json
  {
    "movement_type": "ENTRADA",
    "quantity": 25,
    "reason": "Reposição de estoque da enfermaria"
  }
  ```
- **`GET /api/v1/medications/`**: Catálogo com status de criticidade (`OK`, `LOW`, `OUT_OF_STOCK`).
- **`GET /api/v1/medications/{id}/movements`**: Histórico cronológico de movimentações.

### 3. Testes Automatizados de Medicamentos & Estoque
```bash
python test_medication_stock.py
```

---

## 🔌 Integração com Hardware (Arduino & ESP32)

O ecossistema suporta duas modalidades de envio de dados:

1. **Arduino Tradicional (Uno R3, Nano, Mega):**
   * Firmware: [`firmware_arduino_serial.ino`](firmware_arduino_serial.ino)
   * Leitura do sensor corporal (LM35 na porta `A0`) com oversampling.
   * Transmissão serial (9600 bps) para o script ponte:
     ```bash
     python bridge_arduino_wifi.py --port COM3 --api-url http://localhost:8000/api/v1/telemetry/
     ```

2. **Microcontrolador com Wi-Fi (ESP32, ESP8266, Arduino Uno R4 WiFi):**
   * Firmware: [`firmware_esp32_wifi.ino`](firmware_esp32_wifi.ino)
   * Envio direto via Wi-Fi (`HTTPClient` POST) para o endpoint `/api/v1/telemetry/`.

> 📘 Para mais detalhes sobre os esquemas de dados, regras clínicas e diagramas de fluxo, consulte [`INTEGRACAO_ARDUINO_E_PAYLOADS.md`](INTEGRACAO_ARDUINO_E_PAYLOADS.md).

---

## 📦 Payloads da API

### `POST /api/v1/telemetry/`
Ingestão de leitura de temperatura corporal (30.0°C a 45.0°C):
```json
{
  "device_id": "arduino_wifi_bridge_01",
  "temperature": 36.85
}
```

Resposta (`HTTP 201 Created`):
```json
{
  "id": "e7b2f349-43c2-4cf4-912b-365d95e0c52a",
  "device_id": "arduino_wifi_bridge_01",
  "temperature": 36.85,
  "status": "NORMAL",
  "timestamp": "2026-09-25T13:35:10.123456Z",
  "message": null
}
```

### `GET /api/v1/history/{device_id}?limit=100&hours=24`
Consulta das últimas leituras ordenadas cronologicamente para exibição no aplicativo Flutter.

---

## 📡 Simulador do Hardware (ESP32 / Mock)

Para testar a ingestão sem o circuito físico, execute o script simulador:
```bash
python mock_sensor.py --url http://localhost:8000/api/v1/telemetry/ --interval 2.5
```

Para testar a ponte serial simulando um Arduino virtual conectado a uma porta COM emulada:
```bash
python test_serial_mock.py
```

---

## ☁️ Deploy no Render

O repositório já contém os arquivos de configuração para deploy automático:
- Arquivo de infraestrutura: [`render.yaml`](render.yaml)
- Inicializador do container: [`Procfile`](Procfile)
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn presentation.main:app --host 0.0.0.0 --port $PORT`

