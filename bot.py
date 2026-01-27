import requests
import json
import os
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID_STR = os.getenv("CHAT_ID")
CHAT_ID = int(CHAT_ID_STR) if CHAT_ID_STR else None
FORCE_SEND = os.getenv("FORCE_SEND", "0").lower() in ("1", "true", "yes")

STATE_FILE = "last_seen.json"
BSE_URL = "https://www.bseindia.com/corporates/ann.html"

HEADERS = {"User-Agent": "Mozilla/5.0"}

CRITICAL_KEYWORDS = [
    "resignation", "auditor", "default", "delay", "overdue",
    "liquidity", "insolvency", "ibc", "nclt", "nclat",
    "pledge", "invocation", "credit rating", "downgrade",
    "withdrawn", "fraud", "investigation", "sebi",
    "penalty", "arbitration", "termination", "cancelled",
    "blacklist", "debarred"
]

IMPORTANT_KEYWORDS = [
    "board meeting", "fund raise", "preferential",
    "rights issue", "qip", "warrant", "allotment",
    "merger", "demerger", "acquisition", "divestment",
    "order received", "order cancellation", "contract",
    "award of work", "project", "capex", "expansion"
]

IGNORE_KEYWORDS = [
    "agm", "egm", "postal ballot", "voting results",
    "newspaper publication", "advertisement",
    "regulation", "compliance", "certificate",
    "reconciliation", "rta", "demat", "isin"
]

COMBINATION_RULES = [
    (["auditor", "resignation"], "🚨🚨 AUDITOR EXIT"),
    (["delay", "project"], "🚨 PROJECT DELAY"),
    (["delay", "payment"], "🚨 PAYMENT DELAY"),
    (["credit rating", "downgrade"], "🚨 RATING DOWNGRADE"),
    (["pledge", "invocation"], "🚨 PLEDGE INVOCATION"),
]

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        print("⚠️ send_telegram: missing BOT_TOKEN or CHAT_ID; message not sent")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, json={"chat_id": CHAT_ID, "text": msg}, timeout=10)
        print(f"📤 Telegram send status: {resp.status_code}")
        try:
            print(f"📥 Telegram response: {resp.text}")
        except Exception:
            pass
    except Exception as exc:
        print(f"❌ Telegram send failed: {exc}")

def load_last_seen():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except:
        return {}

def save_last_seen(data):
    with open(STATE_FILE, "w") as f:
        json.dump(data, f)

def classify(title):
    text = title.lower()

    for words, label in COMBINATION_RULES:
        if all(w in text for w in words):
            print(f"🔎 classify: matched combination rule {words} -> {label}")
            return "🚨", label

    if any(k in text for k in CRITICAL_KEYWORDS):
        print(f"🔎 classify: matched CRITICAL keyword in title")
        return "🚨", "CRITICAL"

    if any(k in text for k in IMPORTANT_KEYWORDS):
        print(f"🔎 classify: matched IMPORTANT keyword in title")
        return "⚠️", "IMPORTANT"

    if any(k in text for k in IGNORE_KEYWORDS):
        print(f"🔎 classify: matched IGNORE keyword in title; will skip")
        return None, None

    print(f"🔎 classify: no keywords matched; defaulting to INFO")
    return "ℹ️", "INFO"

def check_bse():
    print("🔍 Fetching BSE announcements...")
    try:
        r = requests.get(BSE_URL, headers=HEADERS, timeout=15)
        print(f"🔁 Fetch status: {r.status_code}")
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception as exc:
        print(f"❌ Error fetching BSE page: {exc}")
        return

    table = soup.find("table")
    if not table:
        print("⚠️ No table found on BSE page")
        return

    rows = table.find_all("tr")
    print(f"ℹ️ Found {len(rows)} rows in announcements table")

    # find the first row that looks like an announcement (has at least 3 columns)
    target_row = None
    for r in rows[1:]:
        cols = r.find_all("td")
        if len(cols) >= 3:
            target_row = r
            break

    if not target_row:
        print("⚠️ No suitable announcement row found")
        return

    cols = target_row.find_all("td")
    print(f"ℹ️ Found {len(cols)} columns in selected announcement row")

    date = cols[0].text.strip()
    scrip = cols[1].text.strip()
    title = cols[2].text.strip()
    link = cols[2].find("a")
    pdf = link["href"] if link else ""

    current = {"date": date, "scrip": scrip, "title": title, "pdf": pdf}
    print(f"ℹ️ Latest announcement: {scrip} - {title[:80]}")

    if current == load_last_seen() and not FORCE_SEND:
        print("ℹ️ Announcement matches last_seen; no action taken")
        return
    if FORCE_SEND and current == load_last_seen():
        print("⚠️ FORCE_SEND enabled — overriding last_seen and forcing send")

    emoji, tag = classify(title)
    print(f"ℹ️ Classification result: emoji={emoji} tag={tag}")
    if not emoji:
        print("ℹ️ Announcement ignored by keyword filters; updating state and exiting")
        save_last_seen(current)
        return

    message = (
        f"{emoji} BSE ANNOUNCEMENT – {tag}\n\n"
        f"Date: {date}\n"
        f"Scrip: {scrip}\n"
        f"Title: {title}\n\n"
        f"{pdf}"
    )

    print(f"📨 Payload: {message}")
    print("📨 Sending Telegram message...")
    send_telegram(message)
    print("💾 Updating last_seen.json")
    save_last_seen(current)

if __name__ == "__main__":
    check_bse()
