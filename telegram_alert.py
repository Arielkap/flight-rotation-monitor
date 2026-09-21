#!/usr/bin/env python3
"""
Telegram Alert Sender for Flight Monitor
Reads TELEGRAM_BOT_TOKEN from /docker/hermes-agent-umxh/data/.env
Zero LLM tokens used.
"""

import os
import sys
import json
import urllib.request
import urllib.error

ENV_PATHS = [
    "/docker/hermes-agent-umxh/data/.env",
    "/opt/data/.env",
    os.path.expanduser("~/.env")
]

DEFAULT_CHAT_ID = "8929130284"

def get_telegram_token():
    # 1. Try environment variable
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if token:
        return token.strip("\"'")

    # 2. Try .env files
    for p in ENV_PATHS:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("TELEGRAM_BOT_TOKEN="):
                            return line.split("=", 1)[1].strip("\"' ")
            except Exception:
                pass
    return None

def send_alert(message: str, chat_id: str = DEFAULT_CHAT_ID) -> bool:
    token = get_telegram_token()
    if not token:
        print("[ERROR] Nie znaleziono TELEGRAM_BOT_TOKEN w środowisku ani .env")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except urllib.error.HTTPError as e:
        print(f"[ERROR] Błąd wysyłania na Telegram: {e.code} - {e.read().decode('utf-8')}")
        return False
    except Exception as e:
        print(f"[ERROR] Błąd sieciowy Telegram: {e}")
        return False

if __name__ == "__main__":
    test_msg = "✈️ <b>Test Monitora Lotów</b>\nPołączenie z botem Telegrama działa idealnie! 🤖"
    if len(sys.argv) > 1:
        test_msg = sys.argv[1]
    ok = send_alert(test_msg)
    print("Wynik wysyłki:", "OK" if ok else "FAIL")
