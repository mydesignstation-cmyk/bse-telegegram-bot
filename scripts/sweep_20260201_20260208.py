import datetime, json
from bot import fetch_with_retries, NEWAPI_DOMAIN, API_ANN_ENDPOINT, HEADERS, TRACKED_SCRIP_LIST

api_headers = HEADERS.copy()
api_headers.update({"Accept": "application/json", "Referer": "https://www.bseindia.com", "Origin": "https://www.bseindia.com"})

start = datetime.date(2026, 2, 1)
end = datetime.date(2026, 2, 8)
cur = start
matches = []

while cur <= end:
    dstr = cur.strftime("%Y%m%d")
    print(f"=== Checking date: {dstr}")
    url = NEWAPI_DOMAIN + API_ANN_ENDPOINT
    params = {
        "pageno": 1,
        "strScrip": "",
        "strCat": "",
        "strPrevDate": dstr,
        "strToDate": dstr,
        "strSearch": "P",
        "strType": "C",
        "subcategory": "",
    }
    try:
        r = fetch_with_retries(url, headers=api_headers, timeout=6, max_attempts=1, params=params)
        try:
            data = r.json()
        except Exception as e:
            print(f"  API non-JSON for {dstr}: {e}")
            data = None
        found_for_date = []
        if data and isinstance(data, dict) and data.get("Table"):
            def _tokens(text):
                import re
                return re.findall(r"\w+", (text or "").upper())
            for row in data["Table"]:
                scrip_val = str(row.get("SCRIP_CD") or row.get("SLONGNAME") or "").strip()
                title_val = (row.get("NEWSSUB") or row.get("HEADLINE") or "").strip()
                s_tokens = _tokens(scrip_val)
                t_tokens = _tokens(title_val)
                is_for_tracked = any((t in s_tokens) or (t in t_tokens) for t in TRACKED_SCRIP_LIST)
                if is_for_tracked:
                    date = row.get("NEWS_DT") or dstr
                    pdf = row.get("NSURL") or ""
                    rec = {"date": date, "scrip": scrip_val, "title": title_val, "pdf": pdf, "source": "api"}
                    found_for_date.append(rec)
                    print(f"  API match: {rec['scrip']} - {rec['title'][:80]}")
        if not found_for_date:
            for s in TRACKED_SCRIP_LIST:
                try:
                    xbrl_url = "https://www.bseindia.com/Msource/90D/CorpXbrlGen.aspx"
                    params_x = {"Scripcode": s}
                    rx = fetch_with_retries(xbrl_url, headers=api_headers, timeout=6, max_attempts=1, params=params_x)
                    body = rx.text
                    if not body or '<xbrli:xbrl' not in body:
                        continue
                    import re
                    m_s = re.search(r'<[^>]*ScripCode[^>]*>(.*?)</', body)
                    if not m_s:
                        continue
                    scrip_code = m_s.group(1).strip()
                    if scrip_code != s:
                        continue
                    m_date = re.search(r'<xbrli:instant>(.*?)</xbrli:instant>', body)
                    m_subj = re.search(r'<in-bse-co:SubjectOfAnnouncement[^>]*>(.*?)</', body, re.S)
                    m_attach = re.search(r'<in-bse-co:AttachmentURL[^>]*>(.*?)</', body, re.S)
                    date = m_date.group(1).strip() if m_date else dstr
                    title = (m_subj.group(1).strip() if m_subj else "").replace('\n', ' ')
                    pdf = m_attach.group(1).strip() if m_attach else ""
                    rec = {"date": date, "scrip": scrip_code, "title": title, "pdf": pdf, "source": "xbrl"}
                    matches.append(rec)
                    found_for_date.append(rec)
                    print(f"  XBRL match: {rec['scrip']} - {rec['title'][:80]}")
                except Exception:
                    pass
        matches.extend(found_for_date)
    except Exception as e:
        print(f"  Fetch failed for {dstr}: {e}")
    cur = cur + datetime.timedelta(days=1)

seen = set()
uniq = []
for m in matches:
    key = (m.get('date'), m.get('scrip'), m.get('title'))
    if key in seen:
        continue
    seen.add(key)
    uniq.append(m)

out_file = 'sweep_2026-02-01_to_2026-02-08.json'
with open(out_file, 'w', encoding='utf-8') as f:
    json.dump(uniq, f, ensure_ascii=False, indent=2)

print(f"\nSweep complete. Found {len(uniq)} unique matches. Results saved to {out_file}")
for m in uniq:
    print(f"- {m['date']} | {m['scrip']} | {m['title'][:120]} | {m.get('pdf','')}")
