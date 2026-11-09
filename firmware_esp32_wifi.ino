/*
  Firmware para Arduino / ESP32 com envio direto de temperatura via Wi-Fi.
  
  Placas compatíveis:
    - ESP32 / ESP32-C3 SuperMini (compatível com a API do projeto)
    - ESP8266 (NodeMCU / D1 Mini)
    - Arduino Uno R4 WiFi
  
  Sensores suportados:
    - Sensor analógico de temperatura corporal (LM35 no pino A0 ou GPIO 0/1/4)
    - Sensor digital DS18B20 ou MAX30205 (I2C)
*/

#if defined(ESP8266)
  #include <ESP8266WiFi.h>
  #include <ESP8266HTTPClient.h>
  #include <WiFiClient.h>
#else
  #include <WiFi.h>
  #include <HTTPClient.h>
#endif

// =================== CONFIGURAÇÕES DA REDE WI-FI ===================
const char* WIFI_SSID     = "SUA_REDE_WIFI";       // Nome da sua rede Wi-Fi (2.4GHz)
const char* WIFI_PASSWORD = "SUA_SENHA_WIFI";      // Senha da rede Wi-Fi

// =================== CONFIGURAÇÕES DO SISTEMA (API) ===================
// Substitua pelo endereço IP do computador onde a API FastAPI está rodando
// Dica: No computador, digite 'ipconfig' no terminal para ver seu IPv4 (ex: 192.168.1.100)
const char* API_URL   = "http://192.168.1.100:8000/api/v1/telemetry/";
const char* DEVICE_ID = "esp32_c3_mini_001";

// Pino do sensor de temperatura
#if defined(CONFIG_IDF_TARGET_ESP32C3) || defined(ARDUINO_ESP32C3_DEV)
  const int PINO_SENSOR = 1;   // GPIO 1 (ADC1_CH1) no ESP32-C3 SuperMini (evita GPIO 0 que é pino de boot strapping)
#elif defined(ESP8266)
  const int PINO_SENSOR = A0;  // Pino analógico único no ESP8266
#else
  const int PINO_SENSOR = 34;  // GPIO 34 ou A0 no ESP32 convencional
#endif

const unsigned long INTERVALO_LEITURA_MS = 3000; // Intervalo de 3 segundos entre envios
unsigned long ultimaLeitura = 0;

void conectarWiFi() {
  Serial.println();
  Serial.print("Conectando ao Wi-Fi: ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int tentativas = 0;
  while (WiFi.status() != WL_CONNECTED && tentativas < 25) {
    delay(500);
    Serial.print(".");
    tentativas++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✓ Wi-Fi conectado com sucesso!");
    Serial.print("Endereço IP da placa: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n✗ Falha ao conectar ao Wi-Fi. Verifique SSID e senha.");
  }
}

float lerTemperaturaCorporal() {
  // Realiza 10 leituras para suavizar oscilações e ruídos elétricos
  long soma = 0;
  for (int i = 0; i < 10; i++) {
    soma += analogRead(PINO_SENSOR);
    delay(10);
  }
  float mediaLeitura = (float)soma / 10.0;

  // Conversão ADC de 12 bits do ESP32 (0 a 4095) com tensão de 3.3V
  float tensao_mV = (mediaLeitura * 3300.0) / 4095.0;

  // Sensor LM35: 10 mV equivale a 1°C
  float temperatura = tensao_mV / 10.0;

  return temperatura;
}

void enviarTelemetria(float temperatura) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Wi-Fi desconectado! Tentando reconectar...");
    conectarWiFi();
    if (WiFi.status() != WL_CONNECTED) return;
  }

  HTTPClient http;
#if defined(ESP8266)
  WiFiClient client;
  http.begin(client, API_URL);
#else
  http.begin(API_URL);
#endif
  http.addHeader("Content-Type", "application/json");

  // Montagem do payload JSON esperado pela API (DTO do Pydantic)
  String jsonPayload = "{\"device_id\":\"" + String(DEVICE_ID) + "\",\"temperature\":" + String(temperatura, 2) + "}";

  Serial.print("Enviando via Wi-Fi para o sistema: ");
  Serial.println(jsonPayload);

  int httpResponseCode = http.POST(jsonPayload);

  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.print("✓ Resposta do Sistema [HTTP ");
    Serial.print(httpResponseCode);
    Serial.print("]: ");
    Serial.println(response);
  } else {
    Serial.print("✗ Erro no envio HTTP: ");
    Serial.println(http.errorToString(httpResponseCode).c_str());
  }

  http.end();
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n--- Inicializando Monitor de Temperatura Wi-Fi ---");

#if defined(ESP32)
  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);
#endif

  conectarWiFi();
}

void loop() {
  unsigned long agora = millis();

  if (agora - ultimaLeitura >= INTERVALO_LEITURA_MS) {
    ultimaLeitura = agora;

    float temp = lerTemperaturaCorporal();

    Serial.print("Temperatura aferida no Arduino/ESP32: ");
    Serial.print(temp, 2);
    Serial.println(" °C");

    // Valida se a temperatura está na faixa corporal humana biológica (30°C a 45°C)
    if (temp >= 30.0 && temp <= 45.0) {
      if (temp >= 37.8) {
        Serial.println("🚨 ALERTA: Estado de febre detectado!");
      } else if (temp >= 37.5) {
        Serial.println("⚠️ AVISO: Estado febril.");
      } else {
        Serial.println("✅ Temperatura normal.");
      }

      // Transmite pela rede Wi-Fi
      enviarTelemetria(temp);
    } else {
      Serial.println("[Aviso] Leitura descartada: fora do intervalo fisiológico humano.");
    }
  }
}
