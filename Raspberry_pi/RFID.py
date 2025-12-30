#!/usr/bin/env python3
import time, json, lgpio
from mfrc522 import SimpleMFRC522
from Encoding import hmac_uid
from TakePicture import capture_photo

# --- 授權檔載入 ---
with open("authorized_uids.json") as f:
    AUTHORIZED_UIDS = json.load(f)


# Relay 設定 (BCM)
CHIP = 0
RELAY_PIN = 17
ACTIVE_ON = 1
ACTIVE_OFF = 0
RELAY_TIME = 2  # 秒

# 建立 Chip 與 Relay
h = lgpio.gpiochip_open(CHIP)
lgpio.gpio_claim_output(h, RELAY_PIN)
lgpio.gpio_write(h, RELAY_PIN, ACTIVE_OFF)

def relay_activate():
    lgpio.gpio_write(h, RELAY_PIN, ACTIVE_ON)
    time.sleep(RELAY_TIME)
    lgpio.gpio_write(h, RELAY_PIN, ACTIVE_OFF)

reader = SimpleMFRC522()
print("等待 RFID 卡片靠近...\nCtrl+C 離開")

try:
    while True:
        id, text = reader.read()
        uid = str(id).strip()
        print(f"卡片 UID: {uid}")

        # 加密 UID並比對
        encrypted_uid = hmac_uid(uid)
        # 判斷
        authorized = encrypted_uid in AUTHORIZED_UIDS

        if authorized:
            print("✅ Authorized — 開啟 Relay")
            relay_activate()
        else:
            print("❌ Not Authorized to Enter.")

        # 不論合法與否都拍照
        photo_path = capture_photo(uid, authorized)
        if photo_path:
            print(f" 圖片已儲存： {photo_path}")
        time.sleep(5)

except KeyboardInterrupt:
    print("\n程式結束")

finally:
    lgpio.gpiochip_close(h)
