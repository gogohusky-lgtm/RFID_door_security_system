import os
import json
import base64
import sqlite3
from datetime import datetime
from threading import Event, Lock
from paho.mqtt.client import Client

# === 設定 ===
SAVE_DIR = "/home/pi/Desktop/RFID_door/photos"
os.makedirs(SAVE_DIR, exist_ok=True)

DB_PATH = "/home/pi/Desktop/RFID_door/Log/rfid_log.db"

BROKER = "localhost"
PORT = 8883
TOPIC_COMMAND = "esp32cam/capture"

TOPIC_START = "esp32cam/image/start"
TOPIC_CHUNK = "esp32cam/image/chunk"
TOPIC_END   = "esp32cam/image/end"

CA_PATH = "/home/pi/Desktop/RFID_door/certs/ca.crt"
CERT_PATH = "/home/pi/Desktop/RFID_door/certs/pyclient.crt"
KEY_PATH = "/home/pi/Desktop/RFID_door/certs/pyclient.key"

# === 狀態控制 ===
capture_lock = Lock()
capture_event = Event()

expected_timestamp = None
total_length = 0
chunks = {}  # offset → data

# ============================
#   SQLite 初始化
# ============================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS logs (
            ts TEXT,
            uid TEXT,
            authorized INTEGER,
            photo TEXT
        )
        """
    )
    conn.commit()
    conn.close()

# ============================
#   紀錄事件
# ============================
def log_event(uid, authorized, photo_path):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO logs VALUES (?, ?, ?, ?)",
        (datetime.now().isoformat(), uid, int(authorized), photo_path)
    )
    conn.commit()
    conn.close()


# ============================
#   MQTT Callback
# ============================
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✔ MQTT 已連線")
        client.subscribe(TOPIC_START, 1)
        client.subscribe(TOPIC_CHUNK, 1)
        client.subscribe(TOPIC_END, 1)
    else:
        print("❌ MQTT 連線失敗", rc)


def on_message(client, userdata, msg):
    global chunks, total_length

    try:
        payload = json.loads(msg.payload.decode())
        ts = payload.get("timestamp")
        
        # 僅接受與目前請求相同的 timestamp
        if ts != expected_timestamp:
            return

        # START ───────────────────────────────────────
        if msg.topic == TOPIC_START:
            total_length = payload.get("total", 0)
            chunks.clear()
            print(f"📥 START：timestamp={ts}, total={total_length}")

        # CHUNK ───────────────────────────────────────
        elif msg.topic == TOPIC_CHUNK:
            offset = payload.get("offset")
            data = payload.get("data")
            if offset is not None and data is not None:
                chunks[offset] = data
                print(f"   ➕ chunk {offset} ({len(data)} bytes)")

        # END ─────────────────────────────────────────
        elif msg.topic == TOPIC_END:
            print("📥 END：接收完成")
            capture_event.set()

    except Exception as e:
        print("❌ 解碼錯誤:", e)


# ============================
#   MQTT 初始化
# ============================
client = Client(client_id="RPI_CLIENT")
client.tls_set(ca_certs=CA_PATH, certfile=CERT_PATH, keyfile=KEY_PATH)
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT, 60)
client.loop_start()


# ============================
#   發送拍照指令
# ============================
def send_capture_command(ts):
    client.publish(TOPIC_COMMAND, ts, qos=1)
    print(f"📤 已送出拍照指令：{ts}")


# ============================
#   儲存影像
# ============================
def save_photo(base64_str, ts):
    img = base64.b64decode(base64_str)
    filename = f"photo_{ts}.jpg"
    path = os.path.join(SAVE_DIR, filename)

    with open(path, "wb") as f:
        f.write(img)

    print(f"📸 已儲存圖片：{path}")
    return path


# ============================
#   拍照流程（給 RFID.py 呼叫）
# ============================
def capture_photo(uid=None, authorized=None):
    global expected_timestamp, chunks, total_length

    with capture_lock:
        expected_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        chunks.clear()
        total_length = 0
        capture_event.clear()

        # 送出拍照請求
        send_capture_command(expected_timestamp)

        # 等待 ESP32 拍照完成
        if not capture_event.wait(timeout=15):
            print("⚠️ 接收逾時（可能 WiFi 慢或 ESP32 無回應）")

            if uid is not None:
                log_event(uid, authorized, "TIMEOUT")
            return None

        # 分片重組
        print("🔧 重組影像資料…")

        if len(chunks) == 0:
            print("X 未收到任何分片")
            return None
        
        full_base64 = ""
        for offset in sorted(chunks.keys()):
            full_base64 += chunks[offset]

        if len(full_base64) != total_length:
            print(f"⚠️ 長度不符：expect={total_length}, got={len(full_base64)}")

        photo_path = save_photo(full_base64, expected_timestamp)

        if uid is not None:
            log_event(uid, authorized, photo_path)

        return photo_path


# ============================
#   清理
# ============================
def cleanup():
    client.loop_stop()
    client.disconnect()


# ============================
#   啟動 SQLite
# ============================
init_db()

# ============================
#   產生 Daily CSV檢查表
# ============================
import threading
import time
from datetime import datetime, date

DAILY_CSV_TIME = "23:50"  # 你可改成 "03:00"、"00:00"

_last_export_date = None


def export_csv(csv_path="/home/pi/Desktop/RFID_door/rfid_log_daily.csv"):
    """將 SQLite logs 資料匯出成 CSV"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT ts, uid, authorized, photo FROM logs")
        rows = c.fetchall()
        conn.close()

        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("timestamp,uid,authorized,photo\n")
            for r in rows:
                line = f"{r[0]},{r[1]},{r[2]},{r[3]}\n"
                f.write(line)

        print(f"📄 CSV 已成功匯出：{csv_path}")

    except Exception as e:
        print("❌ 匯出 CSV 時發生錯誤：", e)


def daily_csv_scheduler(csv_path="/home/pi/Desktop/RFID_door/rfid_log_daily.csv"):
    global _last_export_date

    while True:
        now = datetime.now()
        current_time_str = now.strftime("%H:%M")

        # 時間到＋今天還沒匯出過
        if current_time_str == DAILY_CSV_TIME and _last_export_date != date.today():
            print(f"⏰ 每日排程：時間到達 {DAILY_CSV_TIME} → 匯出 CSV")
            export_csv(csv_path)
            _last_export_date = date.today()

        time.sleep(1)  # 每秒檢查一次


def start_daily_csv_task():
    t = threading.Thread(target=daily_csv_scheduler, daemon=True)
    t.start()

# ============================
#   啟動 Daily
# ============================
start_daily_csv_task()
