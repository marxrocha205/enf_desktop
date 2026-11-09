# 📡 Documentação de Integração: Payloads da API e Comunicação via Arduino

Este documento descreve detalhadamente o formato dos payloads de requisição e resposta da API FastAPI e o fluxo técnico de transmissão dos dados a partir do microcontrolador (Arduino / ESP32).

---

## 1. 📥 Payloads da API RESTful

A ingestão de telemetria é realizada através do endpoint de telemetria corporal.

### 1.1 Ingestão de Leitura de Temperatura

* **Método HTTP:** `POST`
* **Endpoint:** `/api/v1/telemetry/`
* **Headers:**
  * `Content-Type: application/json`

#### Payload de Requisição (Request Body)
Estrutura validada pelo DTO `TelemetryInputDTO`:

```json
{
  "device_id": "arduino_wifi_bridge_01",
  "temperature": 36.85
}
```

#### Especificação dos Campos
| Campo | Tipo | Obrigatório | Restrições | Descrição |
| :--- | :--- | :---: | :--- | :--- |
| `device_id` | `string` | Sim | Mín: 3 caracs / Máx: 64 caracs | Identificador único do dispositivo físico (ex: MAC address, número serial ou nome do nó). |
| `temperature` | `float` | Sim | $30.0 \le \text{temperatura} \le 45.0$ | Leitura de temperatura corporal em graus Celsius (°C). Leituras fora desse intervalo são rejeitadas por estarem fora da faixa fisiológica humana. |

---

#### Payload de Resposta (Response Body - HTTP 201 Created)
Estrutura retornada pelo DTO `TelemetryResponseDTO`:

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

#### Regras de Negócio e Classificação Clínica (`status`)
O domínio (`TelemetryReading.evaluate_status`) classifica a temperatura nas seguintes categorias:

| Status | Faixa Térmica | Comportamento Clínico |
| :--- | :--- | :--- |
| `NORMAL` | $< 37.5^\circ\text{C}$ | Temperatura em níveis saudáveis normais. |
| `ELEVATED` | $37.5^\circ\text{C} \le T < 37.8^\circ\text{C}$ | Estado subfebril / atenção. |
| `FEVER` | $\ge 37.8^\circ\text{C}$ | Estado de febre clínica. Dispara alerta com **debounce de 30 minutos** (1800s) via Redis para evitar saturação de notificações. |

> **Nota:** Quando o status for `FEVER` e o alerta for emitido, o campo `message` conterá:
> `"Alerta de febre emitido com sucesso."` ou `"Alerta de febre identificado (suprimido por debounce recente de 30 min)."`.

---

### 1.2 Consulta do Histórico de Telemetria (App Mobile Flutter)

* **Método HTTP:** `GET`
* **Endpoint:** `/api/v1/history/{device_id}?limit=100&hours=24`
* **Resposta (HTTP 200 OK):**
```json
[
  {
    "temperature": 36.85,
    "status": "NORMAL",
    "timestamp": "2026-09-25T13:35:10.123456Z"
  },
  {
    "temperature": 37.95,
    "status": "FEVER",
    "timestamp": "2026-09-25T13:30:00.000000Z"
  }
]
```

---

## 2. 🔌 Como os Dados Chegam via Arduino

O projeto contempla **duas arquiteturas de hardware** para enviar as leituras até a API:

```
[ARQUITETURA A: Arduino Clássico (Uno/Nano/Mega)]
[Sensor LM35/Analógico]
         │
         ▼
[Arduino Uno/Nano/Mega]
         │
         │ (Cabo USB - Serial 9600 baud: "36.85\r\n")
         ▼
[Ponte Python: bridge_arduino_wifi.py]
         │
         │ (HTTP POST com Payload JSON via Wi-Fi/Rede)
         ▼
[API FastAPI: /api/v1/telemetry/]


[ARQUITETURA B: Placa com Wi-Fi Integrado (ESP32 / ESP8266 / Uno R4 WiFi)]
[Sensor LM35/MAX30205]
         │
         ▼
[ESP32 / Arduino Uno R4]
         │
         │ (HTTP POST direto via Wi-Fi com HTTPClient)
         ▼
[API FastAPI: /api/v1/telemetry/]
```

---

### Arquitetura A: Arduino Tradicional via Cabo Serial + Ponte Python

Utilizada para placas sem módulo de rede nativo (Arduino Uno R3, Nano, Mega).

1. **Leitura no Arduino (`firmware_arduino_serial.ino`):**
   * O sensor de temperatura (ex: LM35 no pino `A0`) é lido 10 vezes consecutivas para suavizar flutuações e ruído elétrico.
   * Converte o sinal analógico em graus Celsius.
   * A cada 2 segundos, envia o valor puro formatado com duas casas decimais pela Serial a 9600 bps:
     ```text
     36.85\r\n
     ```

2. **Captura e Envio na Ponte (`bridge_arduino_wifi.py`):**
   * O script Python em execução no computador abre a porta serial (ex: `COM3`).
   * Faz o parse da linha recebida para `float`.
   * Monta o payload JSON exigido pela API:
     ```python
     payload = {
         "device_id": args.device_id,  # Ex: "arduino_wifi_bridge_01"
         "temperature": round(temp, 2)
     }
     ```
   * Realiza a requisição `POST` para `http://<IP_DO_SERVIDOR>:8000/api/v1/telemetry/`.

---

### Arquitetura B: Envio Direto via Wi-Fi (ESP32 / ESP8266 / Arduino Uno R4 WiFi)

Utilizada quando o microcontrolador possui interface Wi-Fi integrada (`firmware_esp32_wifi.ino`).

1. **Conexão de Rede:** O microcontrolador conecta-se ao roteador local de 2.4 GHz utilizando as credenciais definidas (`WIFI_SSID` e `WIFI_PASSWORD`).
2. **Leitura e Processamento:** Realiza amostragem de 10 leituras do sensor e calcula a temperatura.
3. **Serialização JSON:** Monta a string JSON no padrão da API:
   ```cpp
   String jsonPayload = "{\"device_id\":\"" + String(DEVICE_ID) + "\",\"temperature\":" + String(temperatura, 2) + "}";
   ```
4. **Despacho HTTP:** Utiliza a biblioteca `HTTPClient` para enviar diretamente a requisição com o cabeçalho `Content-Type: application/json` para o IP e porta da API.

---

## 3. 🧪 Exemplos de Teste e Validação

### Teste via cURL (Terminal)
```bash
curl -X POST "http://localhost:8000/api/v1/telemetry/" \
  -H "Content-Type: application/json" \
  -d "{\"device_id\": \"arduino_uno_01\", \"temperature\": 36.8}"
```

### Teste via Python (`requests`)
```python
import requests

url = "http://localhost:8000/api/v1/telemetry/"
payload = {
    "device_id": "arduino_uno_01",
    "temperature": 36.8
}

response = requests.post(url, json=payload)
print(response.status_code, response.json())
```
