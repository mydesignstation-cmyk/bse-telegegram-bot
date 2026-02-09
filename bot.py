import requests
import json
import os
import time
import re
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

# In-memory secrets storage (useful for tests/sandbox)
SECRETS = {
    "BOT_TOKEN": BOT_TOKEN,
    "CHAT_ID": str(CHAT_ID) if CHAT_ID is not None else None,
}


def set_secrets(bot_token=None, chat_id=None):
    """Set BOT_TOKEN and CHAT_ID in-memory and update module globals.

    This also writes the values to os.environ so subprocesses and other
    code that reads env vars can see them. Use this in tests to avoid
    depending on external environment configuration.
    """
    global BOT_TOKEN, CHAT_ID
    if bot_token is not None:
        SECRETS["BOT_TOKEN"] = bot_token
        os.environ["BOT_TOKEN"] = bot_token
        BOT_TOKEN = bot_token
    if chat_id is not None:
        SECRETS["CHAT_ID"] = str(chat_id)
        os.environ["CHAT_ID"] = str(chat_id)
        try:
            CHAT_ID = int(chat_id)
        except Exception:
            CHAT_ID = chat_id


def reload_secrets_from_dotenv(dotenv_path=".env"):
    """Reload `.env` into os.environ and update in-memory secrets."""
    load_dotenv_override(dotenv_path)
    set_secrets(os.getenv("BOT_TOKEN"), os.getenv("CHAT_ID"))

STATE_FILE = "last_seen.json"
BSE_URL = "https://www.bseindia.com/corporates/ann.html"

HEADERS = {"User-Agent": "Mozilla/5.0"}

# Prefer BSE JSON API when available
NEWAPI_DOMAIN = "https://api.bseindia.com/BseIndiaAPI/api/"
API_ANN_ENDPOINT = "AnnSubCategoryGetData/w"

# Scrips to track (comma-separated NSE symbols). Can be overridden via env var TRACKED_SCRIP
# Default list requested by user
# Example: TRACKED_SCRIP="539594,VPRPL,OLECTRA,TITAGARH,ASTRAL,AGI,JIOFIN,BLS"
_default_tracked = "539594,VPRPL,OLECTRA,TITAGARH,ASTRAL,AGI,JIOFIN,BLS,CDSL,UNOMINDA,HSCL,MAZDOCK,COCHINSHIP,TDPOWERSYS,PIXTRANS,ASTRAMICRO,CAMS,IOC,AIAENG,TRITRUBINE,AWHCL,SONACOMS,ZAGGLE,OFSS,IRFC,SAMMANCAP"
_env_tracked = os.getenv("TRACKED_SCRIP")
# Treat empty string as "not set" so an empty env var does NOT override the default list
TRACKED_SCRIP = _env_tracked if _env_tracked is not None and _env_tracked.strip() else _default_tracked
# Normalize to a list of uppercase symbols (ignore empty entries)
TRACKED_SCRIP_LIST = [s.strip().upper() for s in TRACKED_SCRIP.split(",") if s.strip()]


def get_tracked_display():
    """Return a human-friendly, comma-separated display of tracked scripts.
    Falls back to the raw `TRACKED_SCRIP` string if the list is empty.
    """
    return ", ".join(TRACKED_SCRIP_LIST) if TRACKED_SCRIP_LIST else TRACKED_SCRIP


def _looks_like_attachment(url):
    if not url:
        return False
    u = url.lower()
    # common direct attachment indicators
    if u.endswith('.pdf') or '/xml-data/' in u or 'attachdownload' in u or 'attachmenturl' in u or 'xbrl' in u:
        return True
    # heuristic: explicit file extension in url
    if '.' in u and (u.split('.')[-1] in ('pdf', 'xml')):
        return True
    return False


def _fetch_xbrl_attachment_for_scrip(s, api_headers=None):
    try:
        xbrl_url = "https://www.bseindia.com/Msource/90D/CorpXbrlGen.aspx"
        params_x = {"Scripcode": s}
        rx = fetch_with_retries(xbrl_url, headers=api_headers or HEADERS, timeout=10, max_attempts=1, params=params_x)
        body = rx.text
        if not body or '<xbrli:xbrl' not in body:
            return ""
        m_attach = re.search(r'<in-bse-co:AttachmentURL[^>]*>(.*?)</', body, re.S)
        return m_attach.group(1).strip() if m_attach else ""
    except Exception:
        return ""


def get_latest_announcement_from_api():
    """Return a dict with keys date, scrip, title, pdf when API returns results.
    Returns None on failure or if no announcements.
    """
    try:
        today = time.strftime("%Y%m%d")
        # Request all announcements and filter locally for our tracked scrips
        params = {
            "pageno": 1,
            "strScrip": "",
            "strCat": "",
            "strPrevDate": today,
            "strToDate": today,
            "strSearch": "P",
            "strType": "C",
            "subcategory": "",
        }
        url = NEWAPI_DOMAIN + API_ANN_ENDPOINT
        # Use stronger headers (Accept + Referer + Origin) to prompt JSON response
        api_headers = HEADERS.copy()
        api_headers.update({
            "Accept": "application/json",
            "Referer": BSE_URL,
            "Origin": "https://www.bseindia.com",
        })
        # Use fetch_with_retries to get same retry behavior
        r = fetch_with_retries(url, headers=api_headers, timeout=10, max_attempts=2, params=params)
        try:
            data = r.json()
        except Exception as exc:
            print(f"🔁 API parse failed (not JSON): {exc}")
            return None

        if not data or "Table" not in data or not data["Table"]:
            print("🔁 API returned no table data; falling back to HTML")
            return None

        # Helper to tokenize text for robust matching (same logic as check_bse)
        def _tokens(text):
            return re.findall(r"\w+", (text or "").upper())

        # If no tracked names configured, return the first row as before
        def _looks_like_attachment(url):
            if not url:
                return False
            u = url.lower()
            # common direct attachment indicators
            if u.endswith('.pdf') or '/xml-data/' in u or 'attachdownload' in u or 'attachmenturl' in u or 'xbrl' in u:
                return True
            # heuristic: explicit file extension in url
            if '.' in u and (u.split('.')[-1] in ('pdf', 'xml')):
                return True
            return False

        def _fetch_xbrl_attachment_for_scrip(s):
            try:
                xbrl_url = "https://www.bseindia.com/Msource/90D/CorpXbrlGen.aspx"
                params_x = {"Scripcode": s}
                rx = fetch_with_retries(xbrl_url, headers=api_headers, timeout=10, max_attempts=1, params=params_x)
                body = rx.text
                if not body or '<xbrli:xbrl' not in body:
                    return ""
                m_attach = re.search(r'<in-bse-co:AttachmentURL[^>]*>(.*?)</', body, re.S)
                return m_attach.group(1).strip() if m_attach else ""
            except Exception:
                return ""

        if not TRACKED_SCRIP_LIST:
            first = data["Table"][0]
            date = first.get("NEWS_DT", "")
            scrip = str(first.get("SCRIP_CD") or first.get("SLONGNAME") or "").strip()
            title = (first.get("NEWSSUB") or first.get("HEADLINE") or "").strip()
            pdf = first.get("NSURL") or ""
            return {"date": date, "scrip": scrip, "title": title, "pdf": pdf}

        # Otherwise, scan the returned table for the first row that matches our tracked list
        for row in data["Table"]:
            scrip_val = str(row.get("SCRIP_CD") or row.get("SLONGNAME") or "").strip()
            title_val = (row.get("NEWSSUB") or row.get("HEADLINE") or "").strip()
            s_tokens = _tokens(scrip_val)
            t_tokens = _tokens(title_val)
            is_for_tracked = any((t in s_tokens) or (t in t_tokens) for t in TRACKED_SCRIP_LIST)
            if is_for_tracked:
                date = row.get("NEWS_DT", "")
                scrip = scrip_val
                title = title_val
                pdf = row.get("NSURL") or ""
                # If NSURL doesn't look like a direct attachment, try XBRL AttachmentURL for this scrip
                if not _looks_like_attachment(pdf):
                    try:
                        import re as _re
                        pdf_x = _fetch_xbrl_attachment_for_scrip(scrip)
                        if pdf_x:
                            pdf = pdf_x
                    except Exception:
                        pass
                return {"date": date, "scrip": scrip, "title": title, "pdf": pdf}

        # If none of the JSON rows matched tracked scrips, try XBRL endpoint per tracked scrip
        try:
            for s in TRACKED_SCRIP_LIST:
                try:
                    xbrl_url = "https://www.bseindia.com/Msource/90D/CorpXbrlGen.aspx"
                    params_x = {"Scripcode": s}
                    rx = fetch_with_retries(xbrl_url, headers=api_headers, timeout=10, max_attempts=1, params=params_x)
                    body = rx.text
                    if not body or '<xbrli:xbrl' not in body:
                        continue
                    # extract ScripCode and other fields via regex (robust to namespaces)
                    m_s = re.search(r'<[^>]*ScripCode[^>]*>(.*?)</', body)
                    if not m_s:
                        continue
                    scrip_code = m_s.group(1).strip()
                    if scrip_code != s:
                        continue
                    m_date = re.search(r'<xbrli:instant>(.*?)</xbrli:instant>', body)
                    m_subj = re.search(r'<in-bse-co:SubjectOfAnnouncement[^>]*>(.*?)</', body, re.S)
                    m_attach = re.search(r'<in-bse-co:AttachmentURL[^>]*>(.*?)</', body, re.S)
                    date = m_date.group(1).strip() if m_date else ""
                    title = (m_subj.group(1).strip() if m_subj else "").replace('\n', ' ')
                    pdf = m_attach.group(1).strip() if m_attach else ""
                    return {"date": date, "scrip": scrip_code, "title": title, "pdf": pdf}
                except Exception:
                    continue
        except Exception:
            pass

        print("🔁 API returned announcements but none matched tracked scrips; returning None to trigger 'no updates' path")
        return None
    except Exception as exc:
        print(f"🔁 API fetch failed: {exc}")
        return None

def fetch_with_retries(url, headers=None, timeout=20, max_attempts=5, backoff_factor=1, params=None):
    """
    Fetch a URL with exponential backoff retries for transient failures.
    Returns a requests.Response on success or raises Exception after retries.
    """
    attempt = 1
    while attempt <= max_attempts:
        try:
            print(f"⏳ API attempt {attempt} for {url}")
            r = requests.get(url, headers=headers, timeout=timeout, params=params)
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
    # Try API-first
    api_row = get_latest_announcement_from_api()
    if api_row:
        date = api_row["date"]
        scrip = api_row["scrip"]
        title = api_row["title"]
        pdf = api_row["pdf"]
        current = {"date": date, "scrip": scrip, "title": title, "pdf": pdf}
        print(f"ℹ️ Latest announcement (from API): {scrip} - {title[:80]}")
    else:
        try:
            r = fetch_with_retries(BSE_URL, headers=HEADERS, timeout=20, max_attempts=5, backoff_factor=1)
            soup = BeautifulSoup(r.text, "html.parser")
        except Exception as exc:
            print(f"❌ Error fetching BSE page after retries: {exc}")
            tracked = get_tracked_display()
            message = f"No New anouncement for NSE Symbol : {tracked}"
            send_telegram(message)
            return

        table = soup.find("table")
        if not table:
            print("⚠️ No table found on BSE page")
            tracked = get_tracked_display()
            message = f"No New anouncement for NSE Symbol : {tracked}"
            send_telegram(message)
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
            tracked = get_tracked_display()
            message = f"No New anouncement for NSE Symbol : {tracked}"
            send_telegram(message)
            return

        cols = target_row.find_all("td")
        print(f"ℹ️ Found {len(cols)} columns in selected announcement row")

        # Table layouts vary. Find the most likely title cell and any numeric scrip code inside the row.
        col_texts = [c.get_text(" ", strip=True) for c in cols]
        # Choose title candidate as the longest text column
        title_idx = max(range(len(col_texts)), key=lambda i: len(col_texts[i]))
        title = col_texts[title_idx]
        # Try to find a 5-6 digit scrip code anywhere in the columns or title
        scrip = ""
        for txt in col_texts:
            m = re.search(r"\b(\d{5,6})\b", txt)
            if m:
                scrip = m.group(1)
                break
        # If no numeric scrip found, fall back to common scrip column (index 1)
        if not scrip and len(col_texts) > 1:
            scrip = col_texts[1]
        # Attempt to find a pdf link in any column
        pdf = ""
        for c in cols:
            a = c.find("a")
            if a and a.get("href"):
                pdf = a.get("href")
                break
        # If the found link is not an actual attachment, try XBRL AttachmentURL for the scrip
        if not _looks_like_attachment(pdf):
            try:
                pdf_x = _fetch_xbrl_attachment_for_scrip(scrip, api_headers=api_headers if 'api_headers' in globals() else None)
                if pdf_x:
                    pdf = pdf_x
            except Exception:
                pass
        # Date: try to parse a date-like token from any column or from subsequent rows
        date = ""
        date_re = re.compile(r"\d{2}-\d{2}-\d{4}")
        for txt in col_texts:
            dm = date_re.search(txt)
            if dm:
                date = dm.group(0)
                break
        if not date:
            # Look ahead a couple of rows for Exchange Received Time
            next_rows = rows[rows.index(target_row) + 1: rows.index(target_row) + 4]
            for nr in next_rows:
                dm = date_re.search(nr.get_text())
                if dm:
                    date = dm.group(0)
                    break

        current = {"date": date, "scrip": scrip, "title": title, "pdf": pdf}
        print(f"ℹ️ Latest announcement: {scrip} - {title[:80]}")


    # Quick guard: detect templated / placeholder content (e.g., server-side templates left in HTML)
    def is_templated(text):
        if not text:
            return False
        # Common markers observed: `{{ ... }}` templates and identifiers like 'CorpannData' or 'cann.'
        templ_markers = ["{{", "}}", "CorpannData", "cann.", "CorpannData.Table"]
        for m in templ_markers:
            if m in text:
                return True
        return False

    if is_templated(date) or is_templated(scrip) or is_templated(title) or is_templated(pdf):
        print("⚠️ Templated content detected in scraped fields; sending 'no updates' message and updating state")
        tracked = get_tracked_display()
        message = f"No New anouncement for NSE Symbol : {tracked}"
        send_telegram(message)
        save_last_seen(current)
        return

    # Only care about our tracked scrip(s). If latest announcement is not about any of them, send a 'no updates' message.
    tracked_names = TRACKED_SCRIP_LIST if 'TRACKED_SCRIP_LIST' in globals() else []
    scrip_upper = (scrip or "").upper()
    title_upper = (title or "").upper()

    # Helper: split text into 'word' tokens and match tracked names exactly (avoid substring false-positives)
    def _tokens(text):
        return re.findall(r"\w+", (text or "").upper())

    is_for_tracked = any((t in _tokens(scrip_upper)) or (t in _tokens(title_upper)) for t in tracked_names) if tracked_names else False

    tracked = get_tracked_display()

    if not is_for_tracked:
        message = f"No New anouncement for NSE Symbol : {tracked}"
        send_telegram(message)
        return

    if current == load_last_seen() and not FORCE_SEND:
        message = f"No New anouncement for NSE Symbol : {tracked}"
        send_telegram(message)
        return
    if FORCE_SEND and current == load_last_seen():
        print("⚠️ FORCE_SEND enabled — overriding last_seen and forcing send")

    emoji, tag = classify(title)
    print(f"ℹ️ Classification result: emoji={emoji} tag={tag}")
    if not emoji:
        print("ℹ️ Announcement ignored by keyword filters; updating state and exiting")
        save_last_seen(current)
        return

    # Message format per request:
    # Scrip Name : Announcement
    # ---
    # Date :
    # ---
    # Title :
    # ---
    # Link :
    prefix = f"{emoji} " if emoji else ""
    header = f"{prefix}{scrip} : Announcement"
    message = (
        f"{header}\n"
        f"---\n"
        f"Date : {date}\n"
        f"---\n"
        f"Title : {title}\n"
        f"---\n"
        f"Link : {pdf}"
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
