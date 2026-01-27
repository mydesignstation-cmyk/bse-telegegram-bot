import requests
import json
import os
from datetime import datetime

# --- ENV ---
# Hardcoded for debugging - ROTATE THESE AFTER TESTING!
BOT_TOKEN = "8218210704:AAH-yaFbYCd-L8bWrUqySGnDq9KLKOgjZrI"
CHAT_ID = -1003770513009  # Must be int

STATE_FILE = "last_seen.json"
BSE_API_URL = "https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.bseindia.com/",
    "Origin": "https://www.bseindia.com"
}

# --- TELEGRAM ---
def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "disable_web_page_preview": True
    }
    resp = requests.post(url, json=payload, timeout=10)
    print(f"Telegram API Response: {resp.status_code}")
    print(f"Telegram Response Body: {resp.text}")
    return resp

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

# --- HELPERS ---
def clean_text(value, fallback=""):
    """Return a stripped string or a fallback if value is falsy/None."""
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def parse_date(raw_value):
    if not raw_value:
        return "Unknown"
    try:
        return datetime.fromisoformat(str(raw_value).replace('Z', '')).strftime('%d %b %Y %H:%M:%S')
    except Exception:
        return str(raw_value)


# --- CORE LOGIC ---
def check_bse():
    print(f"🔧 Debug - BOT_TOKEN exists: {BOT_TOKEN is not None}")
    print(f"🔧 Debug - CHAT_ID: {CHAT_ID}")
    print("🔍 Fetching BSE announcements via API...")
    
    today = datetime.now().strftime('%Y%m%d')
    params = {
        'strCat': '-1',
        'strPrevDate': today,
        'strScrip': '',
        'strSearch': 'P',
        'strToDate': today,
        'strType': 'C'
    }

    response = None
    for attempt in range(3):
        try:
            response = requests.get(BSE_API_URL, params=params, headers=HEADERS, timeout=20)
            if response.status_code == 200:
                break
            else:
                print(f"⚠️ API attempt {attempt+1} failed with status {response.status_code}")
        except requests.exceptions.Timeout:
            print(f"⏳ API attempt {attempt+1} timed out, retrying...")
        except Exception as exc:
            print(f"❌ API attempt {attempt+1} error: {exc}")
        
    if response is None or response.status_code != 200:
        print("❌ API request failed after retries")
        return

    data = response.json()
    announcements = data.get('Table', [])
    
    if not announcements:
        print("❌ No announcements found")
        return
    
    print(f"✅ Found {len(announcements)} total announcements")

    last_seen_list = load_last_seen()
    print(f"📋 Previously tracked: {len(last_seen_list)} announcements")
    new_announcements = []

    # Check first 10 announcements for new ones
    for ann in announcements[:10]:
        news_id = clean_text(ann.get('NEWSID'))
        scrip = clean_text(ann.get('SLONGNAME'))
        title = clean_text(ann.get('NEWSSUB'))
        category = clean_text(ann.get('CATEGORYNAME'), "Unspecified")
        news_dt = parse_date(ann.get('NEWS_DT'))
        attachment = clean_text(ann.get('ATTACHMENTNAME'))

        pdf_url = f"https://www.bseindia.com/xml-data/corpfiling/AttachLive/{attachment}" if attachment else ""
        
        announcement = {
            "news_id": news_id,
            "scrip": scrip,
            "title": title,
            "category": category,
            "date": news_dt,
            "pdf": pdf_url
        }

        if announcement not in last_seen_list:
            new_announcements.append(announcement)
            print(f"🆕 New: {scrip} - {title[:50]}")

    print(f"📢 Total new announcements: {len(new_announcements)}")

    for announcement in reversed(new_announcements):
        message = (
            "📢 NEW BSE ANNOUNCEMENT\n"
            "——————————————\n"
            f"Category : {announcement['category']}\n"
            f"When     : {announcement['date']}\n"
            f"Scrip    : {announcement['scrip']}\n"
            f"Title    : {announcement['title']}\n"
            f"PDF      : {announcement['pdf']}"
        )
        send_telegram(message)
        print(f"✅ Sent notification for {announcement['scrip']}")

    if announcements:
        current_announcements = [
            {
                "news_id": clean_text(ann.get('NEWSID')),
                "scrip": clean_text(ann.get('SLONGNAME')),
                "title": clean_text(ann.get('NEWSSUB')),
                "category": clean_text(ann.get('CATEGORYNAME'), "Unspecified"),
                "date": parse_date(ann.get('NEWS_DT')),
                "pdf": f"https://www.bseindia.com/xml-data/corpfiling/AttachLive/{clean_text(ann.get('ATTACHMENTNAME'))}" if clean_text(ann.get('ATTACHMENTNAME')) else ""
            }
            for ann in announcements[:10]
        ]

        save_last_seen(current_announcements)
        print(f"💾 Saved {len(current_announcements)} announcements to state")

        if len(new_announcements) == 0 and len(current_announcements) > 0:
            print("💓 No new announcements. Sending top 3 latest as heartbeat...")
            heartbeat_message = "💓 BOT HEARTBEAT - Top 3 Latest BSE Announcements:\n\n"
            for i, announcement in enumerate(current_announcements[:3], 1):
                heartbeat_message += (
                    f"{i}. {announcement['scrip']}\n"
                    f"   {announcement['category']} | {announcement['date'][:19]}\n"
                    f"   {announcement['title'][:90]}\n"
                    f"   PDF: {announcement['pdf']}\n\n"
                )
            send_telegram(heartbeat_message)
            print("✅ Heartbeat sent")

# --- ENTRY ---
if __name__ == "__main__":
    check_bse()
