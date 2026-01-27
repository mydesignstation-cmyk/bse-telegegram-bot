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
    print("🔍 Fetching BSE page...")
    response = requests.get(BSE_URL, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(response.text, "html.parser")

    table = soup.find("table")
    if not table:
        print("❌ No table found")
        return

    rows = table.find_all("tr")[1:]
    if not rows:
        print("❌ No rows found")
        return

    print(f"✅ Found {len(rows)} total rows")

    last_seen_list = load_last_seen()
    print(f"📋 Previously tracked: {len(last_seen_list)} announcements")
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
            print(f"🆕 New: {scrip} - {title[:50]}")

    print(f"📢 Total new announcements: {len(new_announcements)}")

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
        print(f"✅ Sent notification for {announcement['scrip']}")

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
        print(f"💾 Saved {len(current_announcements)} announcements to state")

        # If no new announcements, send top 3 latest as heartbeat
        if len(new_announcements) == 0 and len(current_announcements) > 0:
            print("💓 No new announcements. Sending top 3 latest as heartbeat...")
            heartbeat_message = "💓 BOT HEARTBEAT - Top 3 Latest BSE Announcements:\n\n"
            for i, announcement in enumerate(current_announcements[:3], 1):
                heartbeat_message += (
                    f"{i}. {announcement['scrip']} ({announcement['date']})\n"
                    f"   {announcement['title'][:60]}...\n\n"
                )
            send_telegram(heartbeat_message)
            print("✅ Heartbeat sent")

# --- ENTRY ---
if __name__ == "__main__":
    check_bse()
