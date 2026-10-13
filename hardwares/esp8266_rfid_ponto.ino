#include <SPI.h>
#include <MFRC522.h>
#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClientSecure.h>

// ======================
// CONFIGURAÇÕES DE REDE
// ======================
const char* WIFI_SSID = "SUA_REDE_WIFI";
const char* WIFI_PASSWORD = "SUA_SENHA_WIFI";

// Endpoint do Django (EcoView)
// IMPORTANTE: ajuste o protocolo conforme seu proxy.
// Se o nginx estiver em TLS, use https://... (como abaixo).
// Se estiver sem SSL, troque para http://... e use WiFiClient normal.
const char* ECOVIEW_API_URL = "https://10.5.1.100/api/ponto/";

// Opcional: Google Script (deixe "" se não quiser enviar para a planilha)
const char* GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxb43LXybJYLuo2Fw8ZmjzBh0GhgHLwwZ2T9sCTTLs1Z_wF30op_9UMEMwB_7fklK5B/exec";

// ======================
// PINAGEM RFID + BUZZER
// ======================
// ESP8266 NodeMCU/Wemos D1 mini
// D1 = GPIO5 | D2 = GPIO4 | D8 = GPIO15
#define BUZZER_PIN 5   // D1
#define SS_PIN 15      // D8
#define RST_PIN 4      // D2

MFRC522 mfrc522(SS_PIN, RST_PIN);
WiFiClient wifiClient;
WiFiClientSecure secureClient;

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

void emitirBip() {
  // Lógica invertida: LOW = liga, HIGH = desliga
  digitalWrite(BUZZER_PIN, LOW);
  delay(100);
  digitalWrite(BUZZER_PIN, HIGH);
}

bool enviarUIDParaServidor(const String& uid) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[ERRO] Wi-Fi desconectado.");
    return false;
  }

  HTTPClient http;
  secureClient.setInsecure();

  if (!http.begin(secureClient, ECOVIEW_API_URL)) {
    Serial.println("[ERRO] Falha ao iniciar HTTPS client para o servidor Django.");
    return false;
  }

  http.addHeader("Content-Type", "text/plain");
  int httpCode = http.POST(uid);
  String response = http.getString();

  Serial.printf("[HTTP] Código: %d\n", httpCode);
  Serial.printf("[HTTP] Resposta: %s\n", response.c_str());

  if (httpCode == -1) {
    Serial.println("[DICA] Verifique se a URL está em HTTPS e se o nginx está ouvindo na porta correta.");
  }

  http.end();
  return httpCode > 0 && httpCode < 400;
}

bool enviarUIDParaGoogleScript(const String& uid) {
  if (String(GOOGLE_SCRIPT_URL).length() == 0) {
    return true;
  }

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[ERRO] Wi-Fi desconectado.");
    return false;
  }

  WiFiClientSecure secureClient;
  secureClient.setInsecure();

  HTTPClient http;
  String fullUrl = String(GOOGLE_SCRIPT_URL) + "?uid=" + uid;

  if (!http.begin(secureClient, fullUrl)) {
    Serial.println("[ERRO] Falha ao iniciar HTTPS com Google Script.");
    return false;
  }

  http.setFollowRedirects(HTTPC_STRICT_FOLLOW_REDIRECTS);
  int httpCode = http.GET();
  String response = http.getString();

  Serial.printf("[GOOGLE] Código: %d\n", httpCode);
  Serial.printf("[GOOGLE] Resposta: %s\n", response.c_str());

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

  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, HIGH); // silêncio no boot

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

  emitirBip();

  bool okServidor = enviarUIDParaServidor(uid);
  bool okGoogle = enviarUIDParaGoogleScript(uid);

  if (okServidor) {
    Serial.println("[OK] Ponto enviado ao servidor com sucesso.");
  } else {
    Serial.println("[ERRO] Falha ao enviar ponto ao servidor.");
  }

  if (okGoogle) {
    Serial.println("[OK] UID enviado ao Google Script.");
  } else {
    Serial.println("[ERRO] Falha ao enviar UID ao Google Script.");
  }

  if (okServidor || okGoogle) {
    lastReadAt = now;
  }

  // Finaliza a comunicação com o cartão
  mfrc522.PICC_HaltA();
  mfrc522.PCD_StopCrypto1();

  delay(250);
}

