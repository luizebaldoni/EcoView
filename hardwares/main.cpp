/*
 * ============================================================================
 * Projeto: Monitoramento do Brise Vegetal - Ecotecnologias
 * Arquivo: main.cpp
 * Autor: Luize Baldoni de Oliveira
 * Data: 04/09/2025
 * ============================================================================
 * Descrição:
 *   Código para ESP32 que realiza a leitura de sensores ambientais (temperatura
 *   do solo, umidade do ar, radiação UV e velocidade do vento) e envia os dados
 *   para um servidor Django via HTTP POST e para o ThingSpeak via HTTP GET.
 * ============================================================================
 * Funcionalidades:
 *   - Conexão Wi-Fi automática
 *   - Leitura de 13 sensores reais:
 *       [0-5]  Temperatura do solo (DS18B20)
 *       [6-8]  Umidade do ar (DHT11)
 *       [9-10] Radiação UV (GYML8511)
 *       [11-12] Velocidade do vento (Anemômetro)
 *   - Envio periódico dos dados ao servidor Django e ao ThingSpeak
 *   - Diagnóstico detalhado via Serial (MAC, IP, status de sensores, erros)
 * ============================================================================
 * Hardware:
 *   - ESP32
 *   - 6x DS18B20 (temperatura do solo)
 *   - 1x DHT11 (umidade do ar) - apenas o sensor em DHTPIN1 (GPIO14) está conectado
 *   - 2x GYML8511 (radiação UV)
 *   - 2x Anemômetro (velocidade do vento)
 *
 * ============================================================================
 */

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClient.h>
#include <ArduinoJson.h>
#include <WiFiUdp.h>
#include <DHT.h>
#include <OneWire.h>
#include <DallasTemperature.h>

////======== CONFIGURAÇÕES DE REDE E SERVIDORES ===========/////

const char* ssid = "CasaPopularEficiente";              // Nome da rede Wi-Fi
const char* password = "CPE2013@";       // Senha da rede Wi-Fi

// Endpoints do servidor Django
// Ajuste: usar o endpoint da API Django que aceita POST JSON (receive_sensor_data)
const char* serverReceiveUrl = "http://10.5.1.100:8000/api/receive/"; // POST para receber leituras
const char* serverLatestUrl = "http://10.5.1.100:8000/api/latest/";   // GET último registro (opcional)
const char* serverVerificaCartaoUrl = "http://10.5.1.100:8000/api/verifica_cartao/"; // POST para verificar UID RFID

const unsigned long postingInterval = 30000;  // Intervalo de 5 minutos para envio de dados
unsigned long lastSendTime = 0;                // Armazena o último tempo de envio

////======== CONFIGURAÇÕES THINGSPEAK ===========/////

const char* thingspeakApiKey1 = "GL4W6L1MFFO57Y57"; // Chave API do canal DS18B20
const char* thingspeakApiKey2 = "CCQ5GHPNY7D9PEQB"; // Chave API do canal dos demais sensores
const char* thingspeakUrl = "http://api.thingspeak.com/update";
void sendToThingSpeakChannels(float* sensorValues);

////======== DEFINIÇÃO DE PINOS E OBJETOS DOS SENSORES ===========/////
#//~ DHT-11
#define DHTTYPE DHT11
#define DHTPIN1  14
#define DHTPIN2  27
#define DHTPIN3  26
DHT dht1(DHTPIN1, DHTTYPE);
DHT dht2(DHTPIN2, DHTTYPE);
DHT dht3(DHTPIN3, DHTTYPE);

//~ DS18B20
#define ONE_WIRE_BUS 0
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature ds18b20(&oneWire);
DeviceAddress dsAddresses[6];

//~ Anemometro
#define ANEMO_PIN1 32
#define ANEMO_PIN2 33
volatile unsigned long anemoPulses1 = 0;
volatile unsigned long anemoPulses2 = 0;

//~ GYML8511
#define UV_PIN1 34
#define UV_PIN2 35

////======== FUNÇÕES AUXILIARES ===========/////

void enviarThingSpeakCanais(float* valoresSensores);
void conectarWiFi();
void ler_sensores(float* valores);
void enviarDadosServidor(float* valoresSensores);
void imprimirInfoDispositivo();
void IRAM_ATTR anemometroISR1() { anemoPulses1++; }
void IRAM_ATTR anemometroISR2() { anemoPulses2++; }

////======== FUNÇÃO DE INICIALIZAÇÃO (setup) ===========/////

void setup() {
  Serial.begin(115200);
  Serial.println("\nIniciando dispositivo...");

  conectarWiFi();
  imprimirInfoDispositivo();

  // Inicialização dos sensores
  dht1.begin();
  dht2.begin();
  dht3.begin();
  ds18b20.begin();
  int dsCount = ds18b20.getDeviceCount();
  Serial.println("==============================");
  Serial.print("DS18B20 encontrados: ");
  Serial.println(dsCount);
  Serial.println("------------------------------");

  // Mostra os endereços dos sensores DS18B20 encontrados
  for (int i = 0; i < dsCount && i < 6; i++) {
    if (ds18b20.getAddress(dsAddresses[i], i)) {
      Serial.print("Sensor ");
      Serial.print(i);
      Serial.print(" (Solo ");
      Serial.print(i+1);
      Serial.print(") -> Endereço: ");
      for (uint8_t j = 0; j < 8; j++) {
        if (dsAddresses[i][j] < 16) Serial.print("0");
        Serial.print(dsAddresses[i][j], HEX);
        if (j < 7) Serial.print(":");
      }
      Serial.println();
    } else {
      Serial.print("[ERRO] Falha ao obter endereço do sensor DS18B20 ");
      Serial.println(i);
    }
  }
  pinMode(ANEMO_PIN1, INPUT_PULLUP);
  pinMode(ANEMO_PIN2, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(ANEMO_PIN1), anemometroISR1, FALLING);
  attachInterrupt(digitalPinToInterrupt(ANEMO_PIN2), anemometroISR2, FALLING);

  // Configuração ADC para leituras dos sensores UV (melhora estabilidade/consistência)
  // GPIO34 e GPIO35 pertencem ao ADC1 no ESP32; definir resolução e atenuação
  analogReadResolution(12); // 12 bits (0-4095)
  analogSetPinAttenuation(UV_PIN1, ADC_11db);
  analogSetPinAttenuation(UV_PIN2, ADC_11db);
  Serial.println("Configuração ADC aplicada: resolução 12 bits, atenuação 11dB para pinos UV.");

  // Diagnóstico extra: teste de conexão TCP antes do HTTP
  Serial.println("Testando conexão TCP com o servidor...");
  WiFiClient tcpClient;
  if (tcpClient.connect("10.5.1.100", 22)) {
    Serial.println("Conexão TCP estabelecida com o servidor!");
    tcpClient.stop();
  } else {
    Serial.println("Falha na conexão TCP! Verifique IP, porta e rede.");
  }

  // Diagnóstico extra: teste de conexão HTTP ao servidor
  Serial.println("Testando conexão HTTP com o servidor...");
  HTTPClient http;
  http.begin(serverReceiveUrl);
  int httpCode = http.GET();
  if (httpCode > 0) {
    Serial.printf("Conexão HTTP estabelecida! Código: %d\n", httpCode);
    String payload = http.getString();
    Serial.println("Resposta do servidor: " + payload);
  } else {
    Serial.printf("Falha na conexão HTTP! Código: %d\n", httpCode);
    Serial.println("Verifique se o servidor está rodando e acessível pelo IP/porta.");
  }
  http.end();
}

// Nota: o barramento OneWire está definido em ONE_WIRE_BUS = 0.
// GPIO0 é um pino de boot no ESP32 — se você notar problemas de boot, considere
// mover o barramento OneWire para um pino não-crítico (ex.: GPIO4) e ajustar
// a constante ONE_WIRE_BUS no código. Não alterei automaticamente para
// evitar mudanças que exigiriam reconexão física sem sua confirmação.


////======== LOOP PRINCIPAL ===========/////

void loop() {
  // Verifica a conexão Wi-Fi periodicamente
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi desconectado! Reconectando...");
    conectarWiFi();  // Reconecta ao Wi-Fi caso a conexão seja perdida
  }

  // Envia dados no intervalo configurado
  if (millis() - lastSendTime > postingInterval) {
    float valoresSensores[13];
    ler_sensores(valoresSensores);
    enviarDadosServidor(valoresSensores);
    enviarThingSpeakCanais(valoresSensores);
    lastSendTime = millis();
  }
  delay(1000);
}

////======== ENVIO PARA THINGSPEAK ===========/////

/**
 * @brief Envia até 8 campos para cada canal do ThingSpeak.
 * @param valoresSensores Vetor com os valores dos sensores.
 */

void enviarThingSpeakCanais(float* valoresSensores){
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi não conectado, não foi possível enviar ao ThingSpeak.");
    return;
  }

  // Helper: converte NaN para 0.00 e formata com 2 casas
  auto safe = [](float v)->String { if (isnan(v)) return String(0.0, 2); return String(v, 2); };

  // Canal 1: mapear conforme painel ThingSpeak (anexo):
  // Field1 = DHT1 (valoresSensores[6])
  // Field2 = DHT2 (valoresSensores[7])
  // Field3 = UV1   (valoresSensores[9])
  // Field4 = UV2   (valoresSensores[10])
  // Field5 = ANEMO1 (valoresSensores[11])
  // Field6 = ANEMO2 (valoresSensores[12])
  // Field7/8 permanecem 0
  String url1 = String(thingspeakUrl) + "?api_key=" + thingspeakApiKey1;
  url1 += "&field1=" + safe(valoresSensores[6]);
  url1 += "&field2=" + safe(valoresSensores[7]);
  url1 += "&field3=" + safe(valoresSensores[9]);
  url1 += "&field4=" + safe(valoresSensores[10]);
  url1 += "&field5=" + safe(valoresSensores[11]);
  url1 += "&field6=" + safe(valoresSensores[12]);
  url1 += "&field7=0&field8=0";

  HTTPClient http1;
  http1.begin(url1);
  int httpCode1 = http1.GET();
  if (httpCode1 > 0) {
    Serial.printf("[ThingSpeak Canal 1] Dados enviados! Código: %d\n", httpCode1);
  } else {
    Serial.printf("[ThingSpeak Canal 1] Falha ao enviar! Código: %d\n", httpCode1);
  }
  http1.end();

  // Canal 2: enviar apenas primeiros 6 campos (Field1..Field6)
  // Mapear como: Field1 = valores[8], Field2 = valores[9], Field3 = valores[10]
  // Field4 = valores[11], Field5 = valores[12], Field6 = 0 (nenhum dado adicional)
  String url2 = String(thingspeakUrl) + "?api_key=" + thingspeakApiKey2;
  url2 += "&field1=" + safe(valoresSensores[8]);
  url2 += "&field2=" + safe(valoresSensores[9]);
  url2 += "&field3=" + safe(valoresSensores[10]);
  url2 += "&field4=" + safe(valoresSensores[11]);
  url2 += "&field5=" + safe(valoresSensores[12]);
  url2 += "&field6=0";

  HTTPClient http2;
  http2.begin(url2);
  int httpCode2 = http2.GET();
  if (httpCode2 > 0) {
    Serial.printf("[ThingSpeak Canal 2] Dados enviados! Código: %d\n", httpCode2);
  } else {
    Serial.printf("[ThingSpeak Canal 2] Falha ao enviar! Código: %d\n", httpCode2);
  }
  http2.end();
}

////======== CONEXÃO WI-FI ===========/////

/**
 * @brief Conecta o dispositivo ao Wi-Fi utilizando as credenciais fornecidas.
 */

void conectarWiFi() {

  Serial.print("Conectando a ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {  // Tenta se conectar até 20 vezes
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nConectado com sucesso!");
    Serial.print("Endereço IP: ");
    Serial.println(WiFi.localIP());  // Exibe o IP atribuído ao dispositivo
  } else {
    Serial.println("\nFalha na conexão WiFi");
  }
}

////======== INFORMAÇÕES DO DISPOSITIVO ===========/////

/**
 * @brief Exibe informações do dispositivo, como MAC Address e IP local.
 */

void imprimirInfoDispositivo() {
  Serial.println("\n=== Informações do Dispositivo ===");
  Serial.print("MAC Address: ");
  Serial.println(WiFi.macAddress());        // Exibe o MAC Address do dispositivo
  Serial.print("Endereço IP: ");
  Serial.println(WiFi.localIP());           // Exibe o IP local do dispositivo
  Serial.printf("Intervalo de envio: %d minutos\n", postingInterval / 60000);  // Exibe o intervalo de envio
  Serial.println("=================================\n");
}

////======== LEITURA DOS SENSORES ===========/////

/**
 * @brief Lê todos os sensores conectados ao ESP32.
 * @param valores Vetor de floats para armazenar os valores lidos.
 *
 * Mapeamento dos índices:
 *   [0-5]  Temperatura (DS18B20)
 *   [6-8]  Umidade do ar (DHT11)
 *   [9-10] Radiação UV (GYML8511)
 *   [11-12] Velocidade do vento (Anemômetro)
 */

void ler_sensores(float* valores) {

  //~ DS18B20 - Temperatura
  ds18b20.requestTemperatures();
    Serial.println("\n======= Temperaturas (DS18B20) =======");
    for (int i = 0; i < 6; i++) {
      float temp = ds18b20.getTempC(dsAddresses[i]);
      valores[i] = temp;
      Serial.print("Temperatura ");
      Serial.print(i+1);
      Serial.print(": ");
      if (temp == -127.0) {
        Serial.print("[ERRO] Falha na leitura");
      } else {
        Serial.print(temp, 2);
        Serial.print(" °C");
      }
      Serial.println();
    }
    Serial.println("------------------------------------");
    // Leitura das umidades (DHT11)
    valores[6] = dht1.readHumidity();
    valores[7] = dht2.readHumidity();
    valores[8] = dht3.readHumidity();

    Serial.println("Umidade (DHT11):");
    Serial.print("Umidade 1: ");
    if (isnan(valores[6])) {
      Serial.println("[ERRO] Falha na leitura (NaN) - verifique alimentação/pino 14");
    } else {
      Serial.print(valores[6], 2);
      Serial.println(" %");
    }
    Serial.print("Umidade 2: ");
    if (isnan(valores[7])) {
      Serial.println("[ERRO] Falha na leitura (NaN) - verifique alimentação/pino 27");
    } else {
      Serial.print(valores[7], 2);
      Serial.println(" %");
    }
    Serial.print("Umidade 3: ");
    if (isnan(valores[8])) {
      Serial.println("[ERRO] Falha na leitura (NaN) - verifique alimentação/pino 26");
    } else {
      Serial.print(valores[8], 2);
      Serial.println(" %");
    }
    Serial.println("------------------------------------");

    //~ GYML8511 - Radiação UV (tensão em V)
    valores[9]  = analogRead(UV_PIN1) * (3.3 / 4095.0); // tensão
    valores[10] = analogRead(UV_PIN2) * (3.3 / 4095.0);
    Serial.println("UV (GYML8511):");
    for (int i = 0; i < 2; i++) {
      Serial.print("UV ");
      Serial.print(i+1);
      Serial.print(": ");
      Serial.print(valores[9+i], 2);
      Serial.println(" V");
    }
    Serial.println("------------------------------------");

    //~ Anemômetro - Velocidade do vento (pulsos por segundo)
    // Faz leitura atômica dos contadores incrementados nas ISRs
    static unsigned long ultimoMillis = 0;
    static unsigned long ultimosPulsos1 = 0, ultimosPulsos2 = 0;
    unsigned long agora = millis();

    unsigned long copiaPulsos1 = 0, copiaPulsos2 = 0;
    noInterrupts();
    copiaPulsos1 = anemoPulses1;
    copiaPulsos2 = anemoPulses2;
    interrupts();

    unsigned long deltaPulsos1 = copiaPulsos1 - ultimosPulsos1;
    unsigned long deltaPulsos2 = copiaPulsos2 - ultimosPulsos2;
    unsigned long deltaMillis = (ultimoMillis == 0) ? 0 : (agora - ultimoMillis);

    // Calcula pulsos por segundo; se esta é a primeira leitura (deltaMillis==0)
    // assume-se que o intervalo é o delta entre Leituras (em ms). Caso seja 0,
    // guardamos 0 para evitar divisão por zero.
    if (deltaMillis > 0) {
      valores[11] = (float)deltaPulsos1 * 1000.0f / (float)deltaMillis; // pulsos/s
      valores[12] = (float)deltaPulsos2 * 1000.0f / (float)deltaMillis;
    } else {
      // Na primeira leitura, mostre a taxa média considerando o tempo desde boot
      valores[11] = 0.0f;
      valores[12] = 0.0f;
    }

    // Atualiza marcadores para próxima medição
    ultimosPulsos1 = copiaPulsos1;
    ultimosPulsos2 = copiaPulsos2;
    ultimoMillis = agora;

    Serial.println("Vento (Anemômetro):");
    for (int i = 0; i < 2; i++) {
      Serial.print("Vento ");
      Serial.print(i+1);
      Serial.print(": ");
      Serial.print(valores[11 + i], 2);
      Serial.println(" pulsos/s");
    }
    Serial.println("------------------------------------");
}

////======== ENVIO PARA SERVIDOR DJANGO ===========/////

/**
 * @brief Envia os dados dos sensores para o servidor Django via HTTP POST.
 * @param valoresSensores Vetor com os valores dos sensores.
 */

void enviarDadosServidor(float* valoresSensores) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi desconectado!");
    conectarWiFi();
    return;
  }

  HTTPClient http;
  http.begin(serverReceiveUrl);
  http.addHeader("Content-Type", "application/json");

  // Monta JSON nomeado esperado pelo Django (monitoring = "brise")
  StaticJsonDocument<512> doc;
  doc["monitoring"] = "brise";

  // DS18B20 (6)
  for (int i = 0; i < 6; i++) {
    char key[16];
    sprintf(key, "ds18b20_%d", i+1);
    if (!isnan(valoresSensores[i])) doc[key] = valoresSensores[i];
    else doc[key] = 0.0; // envia 0.0 se leitura inválida
  }

  // DHT11: vamos obter temperatura e umidade dos dois primeiros DHTs
  float dht1_temp = dht1.readTemperature();
  float dht1_hum  = dht1.readHumidity();
  float dht2_temp = dht2.readTemperature();
  float dht2_hum  = dht2.readHumidity();
  // Preenche chaves nomeadas
  doc["dht11_1_temp"] = isnan(dht1_temp) ? 0.0 : dht1_temp;
  doc["dht11_1_hum"]  = isnan(dht1_hum)  ? 0.0 : dht1_hum;
  doc["dht11_2_temp"] = isnan(dht2_temp) ? 0.0 : dht2_temp;
  doc["dht11_2_hum"]  = isnan(dht2_hum)  ? 0.0 : dht2_hum;

  // UV (assume valoresSensores[9], [10])
  doc["uv_1"] = valoresSensores[9];
  doc["uv_2"] = valoresSensores[10];

  // Anemômetro (pulsos/s) -> wind_1, wind_2
  doc["wind_1"] = valoresSensores[11];
  doc["wind_2"] = valoresSensores[12];

  // Metadados
  doc["device_id"] = WiFi.macAddress();
  doc["battery"] = (int)round(simulateBatteryLevel());

  String payload;
  serializeJson(doc, payload);

  int httpCode = http.POST(payload);

  if (httpCode == HTTP_CODE_OK) {
     String response = http.getString();
     Serial.println("Dados enviados com sucesso ao servidor!");
     Serial.println("Resposta do servidor: " + response);
   } else {
    Serial.println("Erro ao enviar dados para o servidor:");
    switch(httpCode) {
      case -1:
        Serial.println("Falha na conexão - Verifique:");
        Serial.println("      • Se o servidor está rodando");
        Serial.println("      • Se o IP/porta estão corretos");
        Serial.println("      • Se o WiFi está estável");
        break;
      case HTTPC_ERROR_CONNECTION_LOST:
        Serial.println("Conexão recusada - Servidor pode estar offline ou porta bloqueada");
        break;
      case HTTPC_ERROR_SEND_HEADER_FAILED:
        Serial.println("Falha ao enviar cabeçalhos - Problema na rede");
        break;
      case HTTPC_ERROR_SEND_PAYLOAD_FAILED:
        Serial.println("Falha ao enviar dados - Rede instável");
        break;
      case HTTPC_ERROR_NOT_CONNECTED:
        Serial.println("WiFi desconectado - Reconectando...");
        conectarWiFi();
        break;
      case HTTPC_ERROR_READ_TIMEOUT:
        Serial.println("Timeout excedido - Servidor não respondeu a tempo");
        break;
      case 400:
        Serial.println("Erro 400 (Bad Request) - Verifique o formato dos dados");
        break;
      case 401:
        Serial.println("Erro 401 (Unauthorized) - Falha na autenticação");
        break;
      case 404:
        Serial.println("Erro 404 (Not Found) - URL do endpoint incorreta");
        Serial.println((String)"      Endpoint atual: " + serverUrl);
        break;
      case 500:
        Serial.println("Erro 500 (Server Error) - Problema no servidor Django");
        break;
      default:
        Serial.print("Código de erro HTTP: ");
        Serial.println(httpCode);
    }
    if (httpCode > 0) {
      String errorResponse = http.getString();
      if (errorResponse.length() > 0) {
        Serial.println("Resposta do servidor: " + errorResponse);
      }
    }
    Serial.println("\nDiagnóstico de rede:");
    Serial.print("Força do sinal WiFi: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
    Serial.print("IP local: ");
    Serial.println(WiFi.localIP());
    Serial.print("Endpoint de envio: ");
    Serial.println(serverReceiveUrl);
   }
   http.end();
}
////======== END CODE ===========/////