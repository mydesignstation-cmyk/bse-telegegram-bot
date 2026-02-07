import json
import bot
import types

def make_resp_json(data):
    r = types.SimpleNamespace()
    r._data = data
    def jsonfn():
        return r._data
    r.json = jsonfn
    return r


def test_api_success_uses_api(monkeypatch, tmp_path):
    sample = {"Table": [{
        "NEWS_DT": "2026-02-07T23:57:12.423",
        "SCRIP_CD": 531380,
        "NEWSSUB": "IDEA - 531380 - Board Meeting Intimation",
        "NSURL": "https://example.com/test.pdf",
        "SLONGNAME": "IDEA"
    }]}

    # Ensure send_telegram is called for API data
    sent = {"ok": False}
    def fake_send(msg):
        sent["ok"] = True
        assert "Test Co" in msg or "531380" in msg

    monkeypatch.setattr(bot, "send_telegram", fake_send)
    monkeypatch.setattr(bot, "fetch_with_retries", lambda *args, **kwargs: make_resp_json(sample))

    bot.STATE_FILE = str(tmp_path / "last_seen.json")
    bot.check_bse()
    assert sent["ok"] is True
    with open(bot.STATE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "Test Co" in data["scrip"] or "531380" in str(data["scrip"])


def test_api_failure_fallback_to_html(monkeypatch, tmp_path, capsys):
    # Simulate API failure by returning None
    monkeypatch.setattr(bot, "get_latest_announcement_from_api", lambda: None)

    # Return templated HTML (so fallback then uses templated guard and skips send)
    templ_html = """
    <html><body>
    <table>
      <tr></tr>
      <tr>
        <td>Security Code : {{CorpannData.Table[0].SCRIP_CD}}</td>
        <td>Company : {{CorpannData.Table[0].SLONGNAME }}</td>
        <td>{{CorpannData.Table[0].NEWS_DT}}</td>
      </tr>
    </table>
    </body></html>
    """
    class R: pass
    r = R()
    r.text = templ_html
    monkeypatch.setattr(bot, "fetch_with_retries", lambda *args, **kwargs: r)

    called = {"sent": False}
    monkeypatch.setattr(bot, "send_telegram", lambda msg: called.update({"sent": True}))

    bot.STATE_FILE = str(tmp_path / "last_seen.json")
    bot.check_bse()

    captured = capsys.readouterr()
    assert "Templated content detected" in captured.out
    assert called["sent"] is False
    with open(bot.STATE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "CorpannData" in data["title"] or "CorpannData" in data["scrip"]
