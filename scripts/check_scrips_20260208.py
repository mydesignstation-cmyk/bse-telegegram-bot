import requests, pprint

url = "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w"
params = {
    "pageno": 1,
    "strScrip": "",
    "strCat": "",
    "strPrevDate": "20260208",
    "strToDate": "20260208",
    "strSearch": "P",
    "strType": "C",
    "subcategory": "",
}
headers = {
    "Accept": "application/json",
    "Referer": "https://www.bseindia.com",
    "Origin": "https://www.bseindia.com",
    "User-Agent": "Mozilla/5.0",
}

try:
    r = requests.get(url, params=params, headers=headers, timeout=30)
except Exception as e:
    print('Request failed:', e)
    raise SystemExit(1)

print('HTTP', r.status_code)
ct = r.headers.get('Content-Type','')
print('Content-Type:', ct)

try:
    data = r.json()
except Exception as exc:
    print('JSON parse error:', exc)
    print('\nBody preview:\n', r.text[:2000])
    raise SystemExit(1)

if 'Table' not in data:
    print('No Table in response')
    raise SystemExit(0)

table = data['Table']
print('Total rows returned:', len(table))

targets = {'512279','538540'}
matches = []
for row in table:
    scrip_cd = row.get('SCRIP_CD')
    scrip_str = str(scrip_cd) if scrip_cd is not None else ''
    # also check SLONGNAME and NEWSSUB tokens
    if scrip_str in targets:
        matches.append(row)

print('Matches found:', len(matches))
for m in matches:
    pprint.pprint({k: m.get(k) for k in ('NEWS_DT','SCRIP_CD','SLONGNAME','NEWSSUB','NSURL')})
