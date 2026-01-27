import requests
import json
import os
from bs4 import BeautifulSoup

# --- ENV ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))  # MUST be int

STATE_FILE = "last_seen.json"
BSE_URL = "https://www.bseindia.com/corporates/ann.html"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# --- TELEGRAM ---
def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "disable_web_page_preview": True
    }
    requests.post(url, json=payload, timeout=10)

# --- STATE ---
def load_last_seen():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_last_seen(data):
    with open(STATE_FILE, "w") as f:
        json.dump(data, f)

# --- CORE LOGIC ---
def check_bse():
    response = requests.get(BSE_URL, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(response.text, "html.parser")

    table = soup.find("table")
    if not table:
        return

    rows = table.find_all("tr")[1:]
    if not rows:
        return

    last_seen_list = load_last_seen()
    new_announcements = []

    # Check all rows for new announcements
    for row in rows[:10]:  # Check first 10 announcements
        cols = row.find_all("td")
        if len(cols) < 3:
            continue

        date = cols[0].text.strip()
        scrip = cols[1].text.strip()
        title = cols[2].text.strip()

        link_tag = cols[2].find("a")
        pdf = link_tag["href"] if link_tag else ""

        announcement = {
            "date": date,
            "scrip": scrip,
            "title": title,
            "pdf": pdf
        }

        # Check if this announcement is new
        if announcement not in last_seen_list:
            new_announcements.append(announcement)

    # Send notifications for new announcements (in reverse order - oldest first)
    for announcement in reversed(new_announcements):
        message = (
            "📢 NEW BSE ANNOUNCEMENT\n\n"
            f"Date: {announcement['date']}\n"
            f"Scrip: {announcement['scrip']}\n"
            f"Title: {announcement['title']}\n\n"
            f"{announcement['pdf']}"
        )
        send_telegram(message)

    # Update last_seen with current announcements
    if rows:
        current_announcements = []
        for row in rows[:10]:
            cols = row.find_all("td")
            if len(cols) < 3:
                continue

            date = cols[0].text.strip()
            scrip = cols[1].text.strip()
            title = cols[2].text.strip()

            link_tag = cols[2].find("a")
            pdf = link_tag["href"] if link_tag else ""

            current_announcements.append({
                "date": date,
                "scrip": scrip,
                "title": title,
                "pdf": pdf
            })

        save_last_seen(current_announcements)

# --- ENTRY ---
if __name__ == "__main__":
    check_bse()
