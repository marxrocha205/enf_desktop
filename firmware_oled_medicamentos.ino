/*
  Firmware Arduino / ESP32:
  - Display OLED SSD1306 (128x64) via I2C
  - Teclado Matricial 4x4 (Digitação de Quantidade e Seleção de Modo)
  - 3 LEDs de Aviso (Verde, Amarelo e Vermelho para Estoque e Validade de Lotes)

  Integrado com a Estação Python (scanner_station.py / app_desktop.py)
  e o Banco de Dados de Medicamentos, Lotes e Validade (FEFO).

  1. Conexões do Display OLED (0.96" I2C):
     - VCC -> 3.3V ou 5V | GND -> GND
     - SDA -> A4 (Uno) ou Pino 8/21 (ESP32)
     - SCL -> A5 (Uno) ou Pino 9/22 (ESP32)

  2. Conexões dos LEDs de Aviso (com resistor de 220 ohms):
     - LED_VERDE    (Pino 10): Lote válido e estoque OK
     - LED_AMARELO  (Pino 11): Alerta! Lote vence em <= 30 dias ou estoque baixo
     - LED_VERMELHO (Pino 12): Bloqueio! Lote VENCIDO ou estoque esgotado

  3. Conexões do Teclado Matricial 4x4:
     - Linhas (R1..R4)  -> Pinos 2, 3, 4, 5
     - Colunas (C1..C4) -> Pinos 6, 7, A2, A3
     - Funções das Teclas:
       * '0' a '9' : Digita a quantidade (ex: 50 caixas do lote)
       * 'A'       : Muda para Modo SAÍDA (Dispensação FEFO)
       * 'B'       : Muda para Modo ENTRADA (Recebimento de Lote)
       * 'C'       : Muda para Modo CONSULTA (Conferir Lote e Validade)
       * 'D'       : Solicita resumo de lotes críticos/vencendo
       * '*'       : Limpa a quantidade digitada
       * '#'       : Confirma e envia comando para o sistema Python

  Velocidade Serial: 115200 bps
*/

#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Keypad.h>

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET    -1

// Pinos dos LEDs de Aviso de Validade e Estoque
#define LED_VERDE     10
#define LED_AMARELO   11
#define LED_VERMELHO  12

// Configuração do Teclado Matricial 4x4
const byte LINHAS = 4;
const byte COLUNAS = 4;

char mapaTeclas[LINHAS][COLUNAS] = {
  {'1', '2', '3', 'A'},
  {'4', '5', '6', 'B'},
  {'7', '8', '9', 'C'},
  {'*', '0', '#', 'D'}
};

byte pinosLinhas[LINHAS] = {2, 3, 4, 5};
byte pinosColunas[COLUNAS] = {6, 7, A2, A3};

Keypad teclado = Keypad(makeKeymap(mapaTeclas), pinosLinhas, pinosColunas, LINHAS, COLUNAS);
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

String modoOperacao = "SAIDA";
String bufferQuantidade = "";

// Aciona os LEDs físicos conforme o status de Validade e Estoque recebido do sistema
void acionarLedsAviso(String corLed) {
  digitalWrite(LED_VERDE, LOW);
  digitalWrite(LED_AMARELO, LOW);
  digitalWrite(LED_VERMELHO, LOW);

  corLed.trim();
  corLed.toUpperCase();

  if (corLed == "GREEN" || corLed == "OK") {
    digitalWrite(LED_VERDE, HIGH);
  } else if (corLed == "YELLOW" || corLed == "WARN") {
    digitalWrite(LED_AMARELO, HIGH);
  } else if (corLed == "RED" || corLed == "EXPIRED" || corLed == "ERROR") {
    // Pisca o LED Vermelho 3 vezes rápido para chamar atenção de Lote Vencido / Bloqueado
    for (int i = 0; i < 3; i++) {
      digitalWrite(LED_VERMELHO, HIGH);
      delay(150);
      digitalWrite(LED_VERMELHO, LOW);
      delay(150);
    }
    digitalWrite(LED_VERMELHO, HIGH);
  }
}

// Renderiza cabeçalho e conteúdo no Display OLED 128x64
void exibirNoOled(String titulo, String conteudo) {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);

  display.setCursor(0, 0);
  display.println(titulo);
  display.drawLine(0, 10, 127, 10, SSD1306_WHITE);

  display.setCursor(0, 14);
  display.println(conteudo);
  display.display();
}

// Atualiza a tela quando o operador está digitando no teclado matricial
void atualizarTelaTeclado() {
  String qtdTexto = bufferQuantidade.length() > 0 ? bufferQuantidade : "1 (padrao)";
  String info = "Modo: " + modoOperacao + "\n";
  info += "Qtd digitada: " + qtdTexto + "\n";
  info += "[#] Confirmar [*] Limpar\n";
  info += "A:Saida B:Lote C:Ver";
  exibirNoOled("[ TECLADO MATRICIAL ]", info);
}

void setup() {
  Serial.begin(115200);

  pinMode(LED_VERDE, OUTPUT);
  pinMode(LED_AMARELO, OUTPUT);
  pinMode(LED_VERMELHO, OUTPUT);

  // Teste rápido dos 3 LEDs ao ligar (auto-diagnóstico)
  digitalWrite(LED_VERDE, HIGH);    delay(200); digitalWrite(LED_VERDE, LOW);
  digitalWrite(LED_AMARELO, HIGH);  delay(200); digitalWrite(LED_AMARELO, LOW);
  digitalWrite(LED_VERMELHO, HIGH); delay(200); digitalWrite(LED_VERMELHO, LOW);
  digitalWrite(LED_VERDE, HIGH); // Inicia com LED Verde indicando sistema pronto

  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("ERR:OLED_NOT_FOUND"));
    for (;;);
  }

  // Tela de Carregamento (Splash Screen) no Display OLED antes de iniciar
  for (int progresso = 0; progresso <= 100; progresso += 25) {
    display.clearDisplay();
    display.setTextColor(SSD1306_WHITE);
    display.setTextSize(1);
    display.setCursor(4, 6);
    display.println(F("MEDICA SENTINELA ENF"));
    display.setCursor(14, 20);
    display.println(F("Carregando Lotes..."));
    display.drawRect(14, 36, 100, 10, SSD1306_WHITE);
    display.fillRect(14, 36, progresso, 10, SSD1306_WHITE);
    display.setCursor(48, 50);
    display.print(progresso);
    display.println(F("%"));
    display.display();
    delay(180);
  }

  exibirNoOled(
    "[ MEDICA SENTINELA ]",
    "Sistema Pronto!\nModo: SAIDA (Qtd: 1)\nUse Teclado ou Scanner"
  );
}

void loop() {
  // 1. Leitura em tempo real do Teclado Matricial 4x4
  char tecla = teclado.getKey();
  if (tecla) {
    if (tecla >= '0' && tecla <= '9') {
      if (bufferQuantidade.length() < 4) {
        bufferQuantidade += tecla;
      }
      atualizarTelaTeclado();
    } else if (tecla == 'A') {
      modoOperacao = "SAIDA";
      atualizarTelaTeclado();
    } else if (tecla == 'B') {
      modoOperacao = "ENTRADA";
      atualizarTelaTeclado();
    } else if (tecla == 'C') {
      modoOperacao = "CONSULTA";
      atualizarTelaTeclado();
    } else if (tecla == 'D') {
      Serial.println("KEY:ALERTA:0");
      exibirNoOled("[ CONSULTANDO... ]", "Buscando lotes\nvencidos ou baixos...");
    } else if (tecla == '*') {
      bufferQuantidade = "";
      atualizarTelaTeclado();
    } else if (tecla == '#') {
      int qtd = bufferQuantidade.length() > 0 ? bufferQuantidade.toInt() : 1;
      if (qtd <= 0) qtd = 1;

      // Envia comando estruturado para o Python via Serial
      Serial.print("KEY:");
      Serial.print(modoOperacao);
      Serial.print(":");
      Serial.println(qtd);

      String resumo = "Modo: " + modoOperacao + "\nQtd: " + String(qtd) + " un/caixas\n\nBipe o Lote/Remedio!";
      exibirNoOled("[ COMANDO ENVIADO ]", resumo);
      bufferQuantidade = "";
    }
  }

  // 2. Recebimento de respostas e alertas vindos do Sistema Python
  // Formato esperado: "LED:GREEN|Dipirona 500mg|Lote: LOTE-26A (50 cx)|Val: 15/08/2027 [OK]"
  // Também suporta mensagens simples separadas por '|'
  if (Serial.available() > 0) {
    String msg = Serial.readStringUntil('\n');
    msg.trim();
    if (msg.length() == 0) return;

    String corLed = "GREEN";
    if (msg.startsWith("LED:")) {
      int fimLed = msg.indexOf('|');
      if (fimLed > 4) {
        corLed = msg.substring(4, fimLed);
        msg = msg.substring(fimLed + 1);
      }
    }

    acionarLedsAviso(corLed);
    msg.replace(" | ", "\n");
    msg.replace("|", "\n");

    String cabecalho = "[ FARMACIA & LOTES ]";
    if (corLed == "RED") {
      cabecalho = "[ ! ALERTA CRITICO ! ]";
    } else if (corLed == "YELLOW") {
      cabecalho = "[ ! ATENCAO LOTE ! ]";
    }

    exibirNoOled(cabecalho, msg);
  }
}
