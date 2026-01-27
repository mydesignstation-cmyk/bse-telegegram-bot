import requests
import json
import os
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

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
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg}, timeout=10)

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
            return "🚨", label

    if any(k in text for k in CRITICAL_KEYWORDS):
        return "🚨", "CRITICAL"

    if any(k in text for k in IMPORTANT_KEYWORDS):
        return "⚠️", "IMPORTANT"

    if any(k in text for k in IGNORE_KEYWORDS):
        return None, None

    return "ℹ️", "INFO"

def check_bse():
    r = requests.get(BSE_URL, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")

    table = soup.find("table")
    if not table:
        return

    row = table.find_all("tr")[1]
    cols = row.find_all("td")

    date = cols[0].text.strip()
    scrip = cols[1].text.strip()
    title = cols[2].text.strip()
    link = cols[2].find("a")
    pdf = link["href"] if link else ""

    current = {"date": date, "scrip": scrip, "title": title, "pdf": pdf}
    if current == load_last_seen():
        return

    emoji, tag = classify(title)
    if not emoji:
        save_last_seen(current)
        return

    message = (
        f"{emoji} BSE ANNOUNCEMENT – {tag}\n\n"
        f"Date: {date}\n"
        f"Scrip: {scrip}\n"
        f"Title: {title}\n\n"
        f"{pdf}"
    )

    send_telegram(message)
    save_last_seen(current)

if __name__ == "__main__":
    check_bse()
