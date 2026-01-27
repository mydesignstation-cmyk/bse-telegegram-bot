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
        "text": message,
        "disable_web_page_preview": True
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
    # Heartbeat (TEMPORARY)
    send_telegram("🧪 Bot heartbeat: GitHub Actions is running")

    print("Fetching BSE page…")
    r = requests.get(BSE_URL, headers=HEADERS, timeout=15)
    print("HTTP status:", r.status_code)

    soup = BeautifulSoup(r.text, "html.parser")

    table = soup.find("table")
    if not table:
        print("❌ No table found on page")
        return

    rows = table.find_all("tr")[1:]
    print("Announcement rows found:", len(rows))

    if not rows:
        print("❌ No announcement rows")
        return

    cols = rows[0].find_all("td")
    if len(cols) < 3:
        print("❌ Unexpected column structure")
        return

    date = cols[0].text.strip()
    scrip = cols[1].text.strip()
    title = cols[2].text.strip()

    link_tag = cols[2].find("a")
    pdf = link_tag["href"] if link_tag else ""

    current = {
        "date": date,
        "scrip": scrip,
        "title": title,
        "pdf": pdf
    }

    last_seen = load_last_seen()

    if current != last_seen:
        message = (
            "🧪 TEST MODE – NEW BSE ANNOUNCEMENT\n\n"
            f"Date: {date}\n"
            f"Scrip: {scrip}\n"
            f"Title: {title}\n\n"
            f"{pdf}"
        )
        send_telegram(message)
        save_last_seen(current)
        print("✅ New announcement sent")
    else:
        print("ℹ️ No new announcement")

if __name__ == "__main__":
    check_bse()
