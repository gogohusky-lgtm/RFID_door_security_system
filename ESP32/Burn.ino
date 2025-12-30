#include "SPIFFS.h"

const char* ca_crt = R"EOF(
-----BEGIN CERTIFICATE-----

-----END CERTIFICATE-----
)EOF";

const char* esp32_crt = R"EOF(
-----BEGIN CERTIFICATE-----

-----END CERTIFICATE-----
)EOF";

const char* esp32_key = R"EOF(
-----BEGIN PRIVATE KEY-----

-----END PRIVATE KEY-----
)EOF";

void writeToSPIFFS(const char* path, const char* content) {
  File file = SPIFFS.open(path, FILE_WRITE);
  if (!file) {
    Serial.printf("無法開啟 %s\n", path);
    return;
  }
  size_t written = file.print(content);
  file.close();
  if (written == 0){
    Serial.printf("寫入 %s 失敗\n", path);
  } else {
    Serial.printf("寫入完成 (%s bytes)\n", path, written);
  }
}

void setup() {
  Serial.begin(115200);
  if (!SPIFFS.begin(true)) {
    Serial.println("SPIFFS 初始化失敗");
    return;
  }

  writeToSPIFFS("/ca.crt", ca_crt);
  writeToSPIFFS("/esp32.crt", esp32_crt);
  writeToSPIFFS("/esp32.key", esp32_key);
  Serial.println("憑證寫入完成");
  // 其他憑證也可在此寫入
}

void loop() {}