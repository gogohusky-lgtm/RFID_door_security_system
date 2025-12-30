#include <FS.h>
#include <SPIFFS.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include "esp_camera.h"
#include "base64.h"

// ====== WiFi 設定 ======
const char* ssid = "xxx";
const char* password = "xxx";

// ====== MQTT broker ======
const char* mqtt_server = "192.x.x.x";
const int   mqtt_port   = 8883;

// MQTT Topics
const char* topic_command       = "esp32cam/capture";
const char* topic_image_start   = "esp32cam/image/start";
const char* topic_image_chunk   = "esp32cam/image/chunk";
const char* topic_image_end     = "esp32cam/image/end";

// ====== ESP32 專用 client ID ======
const char* esp32_client_id = "ESP32Client";

WiFiClientSecure espClient;
PubSubClient client(espClient);

// 儲存 RPi 發來的 timestamp
String pending_timestamp = "";

// ====== global Strings（避免 stack 爆掉） ======
String ca_str;
String cert_str;
String key_str;

// 分片大小（維持你原版 CHUNK_SIZE 命名）
const int CHUNK_SIZE = 3000;
const int PUB_DELAY_MS = 10;

// ====== SPIFFS 讀文字檔 ======
String readFileToString(const char* path) {
  File f = SPIFFS.open(path, "r");
  if (!f) {
    Serial.printf("? 無法開啟檔案 %s\n", path);
    return "";
  }
  String out;
  while (f.available()) {
    out += (char)f.read();
  }
  f.close();
  return out;
}

// ====== 分片傳送 ======
void sendImageChunked(const String& imgBase64) {
  int totalLen = imgBase64.length();

  // Start 訊息
  String startMsg =
      "{\"timestamp\":\"" + pending_timestamp +
      "\",\"total\":" + String(totalLen) + "}";

  client.publish(topic_image_start, startMsg.c_str(), false);
  delay(PUB_DELAY_MS);

  // 分片發送
  for (int offset = 0; offset < totalLen; offset += CHUNK_SIZE) {
    int end = offset + CHUNK_SIZE;
    if (end > totalLen) end = totalLen;

    String chunk = imgBase64.substring(offset, end);

    String payload =
        "{\"timestamp\":\"" + pending_timestamp +
        "\",\"offset\":" + String(offset) +
        ",\"data\":\"" + chunk + "\"}";

    client.publish(topic_image_chunk, payload.c_str(), false);
    delay(PUB_DELAY_MS);
  }

  // End 訊息
  String endMsg = "{\"timestamp\":\"" + pending_timestamp + "\"}";

  client.publish(topic_image_end, endMsg.c_str(), false);
  delay(PUB_DELAY_MS);

  Serial.println("?? 分片傳輸完成");
}


// ====== 拍照並回傳 ======
void captureAndSend() {
    Serial.println("?? 開始拍照...");

  // warm-up frame
    camera_fb_t *fb = esp_camera_fb_get();
    if (fb) esp_camera_fb_return(fb);
    delay(150);

    fb = esp_camera_fb_get();
    if (!fb) {
        Serial.println("? Camera capture failed");
        return;
    }

  if (fb->format != PIXFORMAT_JPEG) {
    Serial.println("?? 非 JPEG 格式");
    esp_camera_fb_return(fb);
    return;
  }

  // Base64
  String imageBase64 = base64::encode(fb->buf, fb->len);
  esp_camera_fb_return(fb);

    // 分片上傳
    sendImageChunked(imageBase64);
}

// ====== MQTT callback ======
void callback(char* topic, byte* payload, unsigned int length) {
    if (String(topic) == topic_command) {

        pending_timestamp = "";
        for (unsigned int i = 0; i < length; i++) {
            pending_timestamp += (char)payload[i];
        }

        Serial.println("?? 拍照指令：" + pending_timestamp);

        captureAndSend();
    }
}

// ====== MQTT 初始化 ======
void initMQTT() {

    // 讀憑證（避免 stack overflow）
    ca_str   = readFileToString("/ca.crt");
    cert_str = readFileToString("/esp32.crt");
    key_str  = readFileToString("/esp32.key");

    if (ca_str.length() == 0 || cert_str.length() == 0 || key_str.length() == 0){
        Serial.println ("X 憑證讀取失敗");
        return;
    } 

    espClient.setCACert(ca_str.c_str());
    espClient.setCertificate(cert_str.c_str());
    espClient.setPrivateKey(key_str.c_str());

  client.setServer(mqtt_server, mqtt_port);
    client.setCallback(callback);

    // **你要求的 bufferSize（必須放在 setServer 後、connect 前）**
    client.setBufferSize(20000);   // 20 KB，足夠 QVGA base64 分片
}

// ====== MQTT 連線確保 ======
void reconnectMQTT() {
    while (!client.connected()) {
        Serial.print("?? MQTT...");
        if (client.connect("ESP32Client")) {
            Serial.println("? Connected");
            client.subscribe(topic_command);
        } else {
            Serial.print("? Error: ");
            Serial.println(client.state());
            delay(2000);
        }
    }
}

// ====== 系統初始化 ======
void setup() {
    Serial.begin(115200);
    Serial.println("Booting...");

    // ====== WiFi ======
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\n? WiFi connected");

    // ====== Camera Config ======
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer   = LEDC_TIMER_0;
    config.pin_d0       = 5;
    config.pin_d1       = 18;
    config.pin_d2       = 19;
    config.pin_d3       = 21;
    config.pin_d4       = 36;
    config.pin_d5       = 39;
    config.pin_d6       = 34;
    config.pin_d7       = 35;
    config.pin_xclk     = 0;
    config.pin_pclk     = 22;
    config.pin_vsync    = 25;
    config.pin_href     = 23;
    config.pin_sccb_sda = 26;
    config.pin_sccb_scl = 27;
    config.pin_pwdn     = 32;
    config.pin_reset    = -1;
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;

    config.frame_size   = FRAMESIZE_QVGA;
    config.jpeg_quality = 12;
    config.fb_count     = 1;
    config.grab_mode    = CAMERA_GRAB_WHEN_EMPTY;

    if (esp_camera_init(&config) != ESP_OK) {
        Serial.println("? Camera init failed");
        return;
    }
    Serial.println("? Camera initialized");

    // ====== 啟動 SPIFFS + MQTT ======
    if (!SPIFFS.begin(true)) {
        Serial.println("? SPIFFS mount failed");
        return;
    }

    initMQTT();
}

// ====== 主迴圈 ======
unsigned long lastReconnectAttempt = 0;
void loop() {
    if (!client.connected()){
        unsigned long now = millis();
        if (now - lastReconnectAttempt > 5000){
            lastReconnectAttempt = now;
            if (client.connect("ESP32Client")){
                client.subscribe(topic_command);
                Serial.println("--MQTT Connected--");
            }
        }
    } else {
        client.loop();
    }
}
