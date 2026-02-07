import requests
import json
import os
import time
from requests.exceptions import RequestException
from bs4 import BeautifulSoup

# Load variables from .env and override environment variables (sandbox/testing mode)
def load_dotenv_override(dotenv_path=".env"):
    try:
        with open(dotenv_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                os.environ[key] = val
        print(f"ℹ️ Loaded environment variables from {dotenv_path}")
    except FileNotFoundError:
        pass

# Force-load .env values and override any existing environment variables (permanent for sandbox/testing)
load_dotenv_override()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID_STR = os.getenv("CHAT_ID")
try:
    CHAT_ID = int(CHAT_ID_STR) if CHAT_ID_STR else None
except ValueError:
    # If CHAT_ID isn't an int for some reason, keep the raw string
    CHAT_ID = CHAT_ID_STR

FORCE_SEND = os.getenv("FORCE_SEND", "0").lower() in ("1", "true", "yes")

STATE_FILE = "last_seen.json"
BSE_URL = "https://www.bseindia.com/corporates/ann.html"

HEADERS = {"User-Agent": "Mozilla/5.0"}

def fetch_with_retries(url, headers=None, timeout=20, max_attempts=5, backoff_factor=1):
    """
    Fetch a URL with exponential backoff retries for transient failures.
    Returns a requests.Response on success or raises Exception after retries.
    """
    attempt = 1
    while attempt <= max_attempts:
        try:
            print(f"⏳ API attempt {attempt} for {url}")
            r = requests.get(url, headers=headers, timeout=timeout)
            print(f"🔁 Fetch status: {r.status_code}")
            if r.status_code == 200:
                return r
            # Retry on server errors
            if 500 <= r.status_code < 600:
                print(f"⏳ Server error {r.status_code}, will retry")
            else:
                r.raise_for_status()
        except RequestException as exc:
            print(f"⏳ API attempt {attempt} failed: {exc}")
        if attempt == max_attempts:
            break
        sleep_time = backoff_factor * (2 ** (attempt - 1))
        print(f"⏳ Sleeping {sleep_time}s before retry")
        time.sleep(sleep_time)
        attempt += 1
    raise Exception(f"Failed to fetch {url} after {max_attempts} attempts")


# Temporary helper: inject an emoji into the message when the announcement title mentions LODR.
# This is intended for short-term verification and controlled via env vars:
# - TEMP_LODR_TEST (default: "1") enables the injection
# - TEMP_LODR_EMOJI sets the emoji used (default: "🧪")
def inject_lodr_test_emoji(title_text, msg_text):
    enabled = os.getenv("TEMP_LODR_TEST", "1").lower() in ("1", "true", "yes")
    emoji_char = os.getenv("TEMP_LODR_EMOJI", "🧪")
    if enabled and "lodr" in title_text.lower():
        print("🔬 LODR detected - injecting test emoji into message")
        return f"{emoji_char} {msg_text}"
    return msg_text

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
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_last_seen(data):
    # write JSON using UTF-8 and preserve unicode characters (emojis)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

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
        r = fetch_with_retries(BSE_URL, headers=HEADERS, timeout=20, max_attempts=5, backoff_factor=1)
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception as exc:
        print(f"❌ Error fetching BSE page after retries: {exc}")
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

    # Temporary: inject a test emoji when title mentions LODR so we can verify emoji rendering.
    # Controlled by TEMP_LODR_TEST and TEMP_LODR_EMOJI env vars; this is intended to be removed later.
    message = inject_lodr_test_emoji(title, message)

    print(f"📨 Payload: {message}")
    print("📨 Sending Telegram message...")
    send_telegram(message)
    print("💾 Updating last_seen.json")
    save_last_seen(current)

if __name__ == "__main__":
    check_bse()
