# **RFID door security system**
## Executive Summary

This project implements a secure RFID-based door access control system using a Raspberry Pi 5 and an ESP32-CAM. The system integrates RFID authentication, relay-based door control, distributed image capture, and secure data transmission via TLS-enabled MQTT.

The Raspberry Pi 5 acts as the central controller, responsible for RFID UID verification (HMAC-SHA256), access decision logic, relay control, and event logging. The ESP32-CAM is dedicated to image capture and transmits photos back to the Raspberry Pi in fragmented Base64 format over MQTT.

The system is designed with security and hardware constraints in mind, including the RP1 I/O architecture of Raspberry Pi 5 and the current limitations of RC522 Python libraries. This project demonstrates practical multi-device integration, secure communication, event tracking, and architectural trade-off handling in a real-world IoT scenario.

------

## RFID 門禁系統 (Raspberry Pi 5 + ESP32-CAM)

本專案實作一套基於 RFID 的照相門禁系統，整合 RFID 驗證、繼電器控制、ESP32-CAM 拍照、TLS MQTT 傳輸，以及事件紀錄與查詢。

## 系統架構
！[系統架構圖](docs/system_architecture.png)

## Demo video
本影片展示 1.RFID 讀取及驗證，2.合法通行時之 Relay 控制，3.ESP32-CAM 影像截取及 MQTT TLS 傳輸

https://youtu.be/tfpOGa3I91k

**資料流程概覽：**

RFID Tag  
→ Raspberry Pi 5 (`RFID.py`)  
→ ESP32-CAM (`ESP32.ino`)  
→ Raspberry Pi 5 (`TakePicture.py`)

## 硬體配置

### Raspberry Pi 5

負責以下功能：

- RC522 RFID 讀取
- UID 的 HMAC-SHA256 驗證
- Relay（門鎖）控制
- 發送拍照命令至 ESP32-CAM
- 接收並儲存照片
- SQLite 事件紀錄
- 產生 CSV 檔案供快速查詢

### ESP32-CAM

- 執行拍照
- 將影像轉為 Base64
- 以分片方式透過 MQTT 傳送影像資料

## 軟體元件

- Python 3
- paho-mqtt
- Mosquitto MQTT Broker
- SQLite

## 啟動順序

1. 啟動 Mosquitto MQTT Broker
2. ESP32-CAM 上電
3. Raspberry Pi 執行主程式：`python RFID.py`

預期之結果：
- MQTT 主題接收 UID 與 Base64 圖像片段
- 繼電器於合法通行存取時之切換
- SQLite 產生事件日誌

## 設計決策 & 已知限制

### 設計決策

- Raspberry Pi 5 負責系統控制與資料整合（RFID、Relay、拍照流程、資料庫）
- ESP32-CAM 專職於影像擷取，避免在 Raspberry Pi 上直接處理攝影模組
- 採用 MQTT 作為裝置間通訊協定，並使用 雙向 TLS 確保傳輸安全
- RFID UID 不以明文儲存或比對：
    - UID 先以 HMAC-SHA256 雜湊
    - 授權清單僅儲存雜湊值 (authorized_uids.json)

### GPIO 架構說明（重要）
此專案運行於 Raspberry Pi 5 (使用**RP1 I/O 架構**).

- **Relay 控制** 使用 `lgpio` (RP1-native GPIO).
- **RC522 RFID** 使用現有 Python 函式庫 (`mfrc522`, `pi-rc522`)。
    - 目前 RC522 的 Python 生態仍依賴 **legacy RPi.GPIO backend**，尚未支援純 **RP1-native GPIO stack**。

因此本專案採用 混合 GPIO backend 設計：
- RP1-native (lgpio) → Relay
- Legacy (RPi.GPIO) → RC522 RFID
- 此為目前 RC522 Python 函式庫在 RP1 上的當前限制；未來若支援 RP1 原生 GPIO，則可簡化
-----

## Security Note

- authorized_uids.json 僅包含 HMAC 雜湊值

- TLS 私鑰與 SECRET 不會提交至 GitHub

- `Encoding.py` 說明，其有兩個功能:

    1. **離線工具**  
    由明碼 RFID UID **離線一次性**產生 `authorized_uids.json`。該步驟僅用於初始化授權清單，產生後明碼 UID 會被移除，不參與任何 runtime 驗證流程。


    2. **提供程式執行之輔助功能模組**  
    提供 `hmac_uid()` 函式以加密讀入之 UID，供 `RFID.py` 使用以比對 json 檔資料。

    明碼 UID 不會被儲存、傳輸或上傳至此 repo。

- 此專案刻意避免儲存或傳輸敏感的 RFID 識別碼

## 檔案目錄結構

```text
RFID_door_security/
├── docs/
│   ├── wiring.md
|   ├── requirements.txt
│   └── system_architecture.png
│
├── ESP32/
|   ├── ESP32.ino            # 拍照 + MQTT 傳輸
|   └── Burn.ino             # TLS 憑證寫入 SPIFFS
|
├── Log/
│   └── rfid_log_daily.csv.png          # 每日自動匯出 CSV 之截圖
│
├── photos/
|   ├── photo_20251230_081852.jpg  # 拍攝的照片＃１
|   ├── photo_20251230_081908.jpg  # 拍攝的照片＃２
|   └── photo_20251230_081922.jpg  # 拍攝的照片＃３
|
├── Raspberry_pi/
│   ├── RFID.py                     # 讀卡 → 比對 → 開門 → 呼叫拍照
│   ├── TakePicture.py              # MQTT TLS 收圖 + 儲存 + SQLite + CSV
│   ├── Encoding.py                 # HMAC-SHA256 UID → 建立授權檔
│   └── authorized_uids.json        # 已授權的 UID (HMAC)
│
└── README.md
```
## License Notice

The source code in this repository is released under the MIT License.

Demo materials, including videos, photos, logs, and generated data under the following directories are provided for demonstration purposes only and are NOT covered by the MIT License:

- photos/
- Log/

These materials may not be redistributed or reused without explicit permission.
