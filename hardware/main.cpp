/*
 * Código ESP32 para envio de dados de sensores ao servidor Django
 * Compatível com a view receive_sensor_data do Django
 * Este código permite que um dispositivo ESP32 colete dados simulados de vários sensores e envie essas informações para um servidor Django via HTTP POST.
 *
 * FUNCIONALIDADES:
 * - Conexão Wi-Fi com rede configurada
 * - Simulação de 13 tipos de sensores (temperatura, umidade, UV, vento)
 * - Simulação de nível de bateria entre 30% e 100%
 * - Envio de dados ao servidor Django em intervalos regulares (a cada 5 minutos)
 * - Exibição de informações do dispositivo (MAC, IP, etc.)
 *
 * CONFIGURAÇÃO:
 * - Definir credenciais Wi-Fi (SSID e senha)
 * - Definir a URL do servidor Django para receber os dados
 * - Intervalo de envio configurado para 5 minutos (300000 ms)
 *
 * EXEMPLO DE DADOS ENVIADOS:
 * - Sensor 1 a 6: Temperatura simulada (DS18B20)
 * - Sensor 7 a 9: Umidade simulada (DHT11)
 * - Sensor 10 a 11: UV simulada (GYML8511)
 * - Sensor 12 a 13: Velocidade do vento simulada (Anemômetro)
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClient.h>
#include <ArduinoJson.h>
#include <WiFiUdp.h>

///// CONFIGURAÇÕES DE REDE /////
const char* ssid = "ap-sl1109";              // Nome da rede Wi-Fi
const char* password = "danielgremista";       // Senha da rede Wi-Fi

// Endpoints do servidor Django
const char* serverUrl = "http://10.5.1.113:8000/api/receive/"; // URL para receber dados do sensor

///// INTERVALOS DE ENVIO /////
const unsigned long postingInterval = 30000;  // Intervalo de 5 minutos para envio de dados
unsigned long lastSendTime = 0;                // Armazena o último tempo de envio

///// FUNÇÕES PRINCIPAIS /////
void connectToWiFi();
void readSimulatedSensors(float* values);
float simulateBatteryLevel();
void sendSensorData(float* sensorValues, float batteryLevel);
void printDeviceInfo();
//& Função de inicialização (setup) do dispositivo.
void setup() {
  Serial.begin(115200);                      // Inicia a comunicação serial
  Serial.println("\nIniciando dispositivo...");

  connectToWiFi(); // Conecta ao Wi-Fi
  printDeviceInfo(); // Exibe informações do dispositivo

  // Diagnóstico extra: teste de conexão TCP antes do HTTP
  Serial.println("Testando conexão TCP com o servidor...");
  WiFiClient tcpClient;
  if (tcpClient.connect("10.5.1.113", 8000)) {
    Serial.println("Conexão TCP estabelecida com o servidor!");
    tcpClient.stop();
  } else {
    Serial.println("Falha na conexão TCP! Verifique IP, porta e rede.");
  }

  // Diagnóstico extra: teste de conexão HTTP ao servidor
  Serial.println("Testando conexão HTTP com o servidor...");
  HTTPClient http;
  http.begin(serverUrl);
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

//& Função principal que é chamada repetidamente para verificar a conexão e enviar dados.
void loop() {
  // Verifica a conexão Wi-Fi periodicamente
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi desconectado! Reconectando...");
    connectToWiFi();  // Reconecta ao Wi-Fi caso a conexão seja perdida
  }

  //& Envia dados no intervalo configurado
  if (millis() - lastSendTime > postingInterval) {
    //& Simula a leitura dos sensores
    float sensorValues[13];
    readSimulatedSensors(sensorValues);  // Função que gera os dados simulados

    float batteryLevel = simulateBatteryLevel();  // Simula o nível de bateria (de 0 a 100%)

    sendSensorData(sensorValues, batteryLevel); // Envia os dados ao servidor Django

    lastSendTime = millis(); // Atualiza o tempo da última transmissão de dados
  }

  delay(1000);  // Pequeno delay entre verificações
}

//& Função que conecta o dispositivo ao Wi-Fi utilizando as credenciais fornecidas.
void connectToWiFi() {
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

//& Função que exibe as informações do dispositivo, como MAC Address e IP local.
void printDeviceInfo() {
  Serial.println("\n=== Informações do Dispositivo ===");
  Serial.print("MAC Address: ");
  Serial.println(WiFi.macAddress());        // Exibe o MAC Address do dispositivo
  Serial.print("Endereço IP: ");
  Serial.println(WiFi.localIP());           // Exibe o IP local do dispositivo
  Serial.printf("Intervalo de envio: %d minutos\n", postingInterval / 60000);  // Exibe o intervalo de envio
  Serial.println("=================================\n");
}

//& Função que simula a leitura de 13 sensores e preenche um vetor com os valores simulados.
//& Simula sensores de temperatura (DS18B20), umidade (DHT11), UV (GYML8511) e velocidade do vento (Anemômetro).
//& @param values Vetor para armazenar os valores simulados dos sensores.
void readSimulatedSensors(float* values) {
  // Gera valores simulados para os 13 sensores
  for (int i = 0; i < 13; i++) {
    if (i < 6) { // Sensores 1 a 6 - Simulação de temperatura (DS18B20)
      values[i] = 20.0 + (i * 0.5) + (random(0, 10) / 10.0);  // Temperatura entre 20 e 23°C
    }
    else if (i < 9) { // Sensores 7 a 9 - Simulação de umidade (DHT11)
      values[i] = 50.0 + (i * 2) + random(0, 10);  // Umidade entre 50 e 60%
    }
    else if (i < 11) { // Sensores 10 a 11 - Simulação de UV (GYML8511)
      values[i] = 1.0 + (i * 0.3) + (random(0, 5) / 10.0);  // UV entre 1.0 e 1.6
    }
    else { // Sensores 12 e 13 - Simulação de velocidade do vento (Anemômetro)
      values[i] = 0.5 + (i * 0.2) + (random(0, 8) / 10.0);  // Velocidade do vento entre 0.5 e 1.0 m/s
    }
  }

  //& Exibe os valores no serial para depuração
  Serial.println("Valores simulados dos sensores:");
  for (int i = 0; i < 13; i++) {
    Serial.printf("Sensor %d: %.2f\n", i+1, values[i]);
  }
}

//& Função que simula o nível de bateria, retornando um valor aleatório entre 30% e 100%.
//& @return Nível de bateria simulado.
float simulateBatteryLevel() {
  //& Simula bateria entre 30% e 100%
  float level = 30.0 + random(0, 70);  // Gera um valor entre 30 e 100%
  Serial.printf("Nível de bateria simulado: %.1f%%\n", level);
  return level;
}

//& Função que envia os dados dos sensores e o nível de bateria para o servidor Django via HTTP POST.
//& @param sensorValues Valores simulados dos 13 sensores.
//& @param batteryLevel Nível de bateria do dispositivo.

void sendSensorData(float* sensorValues, float batteryLevel) {
  if (WiFi.status() != WL_CONNECTED) {  // Verifica se o Wi-Fi está desconectado
    Serial.println("WiFi desconectado!");
    connectToWiFi();  // Reconnecta ao Wi-Fi
    return;
  }

  HTTPClient http;               // Cria um cliente HTTP
  http.begin(serverUrl);         // Inicia a requisição para o servidor Django
  http.addHeader("Content-Type", "application/json");  // Define o tipo de conteúdo como JSON

  JsonDocument doc;  // Cria o documento JSON para armazenar os dados

  //& Adiciona os valores dos sensores ao JSON
  for (int i = 0; i < 13; i++) {
    char sensorKey[10];
    sprintf(sensorKey, "sensor%d", i+1);  // Cria uma chave para cada sensor
    doc[sensorKey] = sensorValues[i];  // Adiciona o valor do sensor ao documento JSON
  }

  //& Adiciona metadados (ID do dispositivo e nível de bateria)
  doc["device_id"] = WiFi.macAddress();  // Adiciona o MAC Address do dispositivo
  doc["battery"] = batteryLevel;         // Adiciona o nível de bateria ao JSON

  //& Serializa o JSON em uma string e envia
  String payload;
  serializeJson(doc, payload);  // Converte o JSON para uma string

  int httpCode = http.POST(payload);  // Envia a requisição HTTP POST com os dados

  if (httpCode == HTTP_CODE_OK) {
    String response = http.getString();
    Serial.println("✅ Dados enviados com sucesso ao servidor!");
    Serial.println("📋 Resposta do servidor: " + response);
} else {
    Serial.println("❌ Erro ao enviar dados para o servidor:");

    // Detailed error messages
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
            Serial.println("alha ao enviar cabeçalhos - Problema na rede");
            break;
        case HTTPC_ERROR_SEND_PAYLOAD_FAILED:
            Serial.println("   📦 Falha ao enviar dados - Rede instável");
            break;
        case HTTPC_ERROR_NOT_CONNECTED:
            Serial.println("WiFi desconectado - Reconectando...");
            connectToWiFi(); // Attempt to reconnect
            break;
        case HTTPC_ERROR_READ_TIMEOUT:
            Serial.println(" Timeout excedido - Servidor não respondeu a tempo");
            break;
        case 400:
            Serial.println(" Erro 400 (Bad Request) - Verifique o formato dos dados");
            break;
        case 401:
            Serial.println("Erro 401 (Unauthorized) - Falha na autenticação");
            break;
        case 404:
            Serial.println(" Erro 404 (Not Found) - URL do endpoint incorreta");
            Serial.println("      Endpoint atual: " + String(serverUrl));
            break;
        case 500:
            Serial.println("Erro 500 (Server Error) - Problema no servidor Django");
            break;
        default:
            Serial.print("Código de erro HTTP: ");
            Serial.println(httpCode);
    }

    // Get server response if available
    if (httpCode > 0) {
        String errorResponse = http.getString();
        if (errorResponse.length() > 0) {
            Serial.println("Resposta do servidor: " + errorResponse);
        }
    }

    // Network diagnostics
    Serial.println("\nDiagnóstico de rede:");
    Serial.println("Força do sinal WiFi: " + String(WiFi.RSSI()) + " dBm");
    Serial.println("IP local: " + WiFi.localIP().toString());
    Serial.println("IP do servidor: " + String(serverUrl));
}

  http.end();  // Finaliza a requisição HTTP
}
