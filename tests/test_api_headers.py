import bot


def test_api_uses_expected_headers(monkeypatch):
    captured = {}
    def fake_fetch_with_retries(url, headers=None, timeout=None, max_attempts=None, **kwargs):
        captured['headers'] = headers
        class R: pass
        r = R()
        r.json = lambda: {"Table": [{"NEWS_DT": "d", "SCRIP_CD": 1, "NEWSSUB": "t", "NSURL": "u"}]}
        return r

    monkeypatch.setattr(bot, 'fetch_with_retries', fake_fetch_with_retries)
    res = bot.get_latest_announcement_from_api()
    assert 'Accept' in captured['headers'] and captured['headers']['Accept'] == 'application/json'
    assert 'Referer' in captured['headers'] and bot.BSE_URL in captured['headers']['Referer']
    assert 'Origin' in captured['headers'] and 'bseindia.com' in captured['headers']['Origin']
