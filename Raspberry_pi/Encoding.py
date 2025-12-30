# Encoding.py
import hmac, hashlib, json

SECRET = b"this_should_be_a_strong_random_key_kept_secret"

def hmac_uid(uid_str: str) -> str:
    """回傳 UID 的 HMAC-SHA256 雜湊值"""
    return hmac.new(SECRET, uid_str.encode(), hashlib.sha256).hexdigest()

def generate_authorized_file(uids, filename="authorized_uids.json"):
    """輸入 UID 清單並產生 JSON 授權檔"""
    hashed_uids = [hmac_uid(uid) for uid in uids]
    with open(filename, "w") as f:
        json.dump(hashed_uids, f, indent=2)
    print(f"已產生授權檔 {filename}")
    return hashed_uids

# 若直接執行此檔案（例如 python3 Encoding.py），則產生一次授權檔
if __name__ == "__main__":
    uids = ["413369794588", "3208714727"]
    generate_authorized_file(uids)
