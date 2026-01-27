import requests
import json
import os
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

STATE_FILE = "last_seen.json"
BSE_URL = "https://www.bseindia.com/corporates/ann.html"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }

    resp = requests.post(url, json=payload, timeout=10)

    print("Telegram status code:", resp.status_code)
    print("Telegram response:", resp.text)

def load_last_seen():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_last_seen(data):
    with open(STATE_FILE, "w") as f:
        json.dump(data, f)

def check_bse():
    print("Sending forced Telegram test message…")
    send_telegram("🧪 FORCE TEST: Telegram delivery check")

if __name__ == "__main__":
    check_bse()
