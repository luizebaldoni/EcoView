#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <SPI.h>
#include <MFRC522.h>

// ======================
// CONFIGURAÇÕES DE REDE
// ======================
const char* WIFI_SSID = "SUA_REDE_WIFI";
const char* WIFI_PASSWORD = "SUA_SENHA_WIFI";

// Troque pelo IP/host do seu servidor Django
// Ex.: http://192.168.0.10:8000/api/ponto/
const char* PONTO_API_URL = "http://192.168.0.10:8000/api/ponto/";

// ======================
// PINAGEM RFID (MFRC522)
// ======================
// ESP8266 NodeMCU/Wemos D1 mini (ajuste se necessário)
#define SS_PIN  D8
#define RST_PIN D0

MFRC522 mfrc522(SS_PIN, RST_PIN);
WiFiClient wifiClient;

// Evita múltiplas leituras seguidas do mesmo cartão
unsigned long lastReadAt = 0;
const unsigned long READ_COOLDOWN_MS = 3500;

String uidToHex(const byte *buffer, byte bufferSize) {
  String uid = "";
  for (byte i = 0; i < bufferSize; i++) {
    if (buffer[i] < 0x10) uid += "0";
    uid += String(buffer[i], HEX);
  }
  uid.toUpperCase();
  return uid;
}

bool enviarUIDParaServidor(const String& uid) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[ERRO] Wi-Fi desconectado.");
    return false;
  }

  HTTPClient http;
  if (!http.begin(wifiClient, PONTO_API_URL)) {
    Serial.println("[ERRO] Falha ao iniciar HTTPClient.");
    return false;
  }

  http.addHeader("Content-Type", "text/plain");
  int httpCode = http.POST(uid);
  String response = http.getString();

  Serial.printf("[HTTP] Código: %d\n", httpCode);
  Serial.printf("[HTTP] Resposta: %s\n", response.c_str());

  http.end();
  return httpCode > 0 && httpCode < 400;
}

void conectarWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.print("Conectando ao Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print('.');
  }
  Serial.println();
  Serial.print("Wi-Fi conectado. IP: ");
  Serial.println(WiFi.localIP());
}

void setup() {
  Serial.begin(115200);
  delay(300);

  SPI.begin();
  mfrc522.PCD_Init();

  conectarWiFi();
  Serial.println("Aproxime o cartão RFID do leitor...");
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    conectarWiFi();
  }

  // Aguarda um cartão novo
  if (!mfrc522.PICC_IsNewCardPresent()) {
    return;
  }

  if (!mfrc522.PICC_ReadCardSerial()) {
    return;
  }

  unsigned long now = millis();
  if (now - lastReadAt < READ_COOLDOWN_MS) {
    mfrc522.PICC_HaltA();
    mfrc522.PCD_StopCrypto1();
    return;
  }

  String uid = uidToHex(mfrc522.uid.uidByte, mfrc522.uid.size);
  Serial.print("UID lido: ");
  Serial.println(uid);

  bool ok = enviarUIDParaServidor(uid);
  if (ok) {
    Serial.println("[OK] Ponto enviado com sucesso.");
    lastReadAt = now;
  } else {
    Serial.println("[ERRO] Falha ao enviar ponto.");
  }

  // Finaliza a comunicação com o cartão
  mfrc522.PICC_HaltA();
  mfrc522.PCD_StopCrypto1();

  delay(250);
}

