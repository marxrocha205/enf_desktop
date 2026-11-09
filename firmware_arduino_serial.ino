/*
  Firmware para Arduino (Uno R3, Nano, Mega, Pro Mini) via Cabo USB / Serial.
  
  Trabalha em conjunto complementar com a ponte Python (bridge_arduino_wifi.py).
  
  Como funciona:
    1. O Arduino lê o sensor analógico de temperatura corporal (LM35 na porta A0).
    2. Realiza amostragem (oversampling de 10 leituras) para suavizar ruídos elétricos.
    3. Converte a tensão analógica (10 mV/°C) em graus Celsius.
    4. Envia o valor puro pela porta Serial a cada 2 segundos.
    5. A ponte 'bridge_arduino_wifi.py' no computador recebe pela porta COM e 
       despacha via Wi-Fi / HTTP POST para a API FastAPI do sistema.

  Conexões do Sensor LM35:
    - Pino 1 (+Vs)  -> Conectar ao 5V do Arduino
    - Pino 2 (Vout) -> Conectar ao pino Analógico A0 do Arduino
    - Pino 3 (GND)  -> Conectar ao GND do Arduino
*/

const int PINO_SENSOR = A0;
const unsigned long INTERVALO_MS = 2000; // 2 segundos entre leituras
unsigned long ultimaLeitura = 0;

void setup() {
  // Inicializa comunicação serial com o mesmo baud rate da ponte Python (9600 bps)
  Serial.begin(9600);
  delay(500);
}

float lerTemperaturaCorporal() {
  // Faz 10 leituras consecutivas para filtrar ruídos e instabilidades elétricas
  long soma = 0;
  for (int i = 0; i < 10; i++) {
    soma += analogRead(PINO_SENSOR);
    delay(10);
  }
  float mediaLeitura = (float)soma / 10.0;

  // Conversão para Arduino padrão (ATmega328P de 5V e ADC de 10 bits: 0 a 1023)
  float tensao_mV = (mediaLeitura * 5000.0) / 1023.0;

  // Sensor LM35: 10 mV equivale a 1.0 °C
  float temperatura = tensao_mV / 10.0;

  return temperatura;
}

void loop() {
  unsigned long agora = millis();

  if (agora - ultimaLeitura >= INTERVALO_MS) {
    ultimaLeitura = agora;

    float temp = lerTemperaturaCorporal();

    // Imprime na Serial o número puro com 2 casas decimais.
    // Esse formato é exatamente o esperado pelo parser da bridge_arduino_wifi.py
    Serial.println(temp, 2);
  }
}
