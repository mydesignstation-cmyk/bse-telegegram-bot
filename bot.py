import requests
import json
import os
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Vishnu Prakash R Punglia Ltd BSE scrip code
SCRIP_CODE = "543974"

STATE_FILE = "last_seen.json"

BSE_URL = f"https://www.bseindia.com/corporates/ann.html?scripcode={SCRIP_CODE}&flag=ANN"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    requests.post(url, json=payload, timeout=10)

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
    r = requests.get(BSE_URL, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")

    rows = soup.select("table.table tr")[1:]
    if not rows:
        return

    cols = rows[0].find_all("td")
    date = cols[0].text.strip()
    title = cols[2].text.strip()
    pdf = cols[2].find("a")["href"]

    current = {
        "date": date,
        "title": title,
        "pdf": pdf
    }

    last_seen = load_last_seen()

    if current != last_seen:
        message = (
            "🚨 *NEW BSE ANNOUNCEMENT*\n\n"
            "*Company:* Vishnu Prakash R Punglia Ltd\n"
            f"*Date:* {date}\n"
            f"*Title:* {title}\n\n"
            f"📄 {pdf}"
        )
        send_telegram(message)
        save_last_seen(current)

if __name__ == "__main__":
    check_bse()
