import types
import bot
import json


def make_resp(text):
    r = types.SimpleNamespace()
    r.text = text
    return r


def test_templated_content_skipped(monkeypatch, tmp_path, capsys):
    # Create an HTML table that contains template placeholders
    html = """
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

    # Ensure .env values don't cause a real send; monkeypatch send_telegram to track calls
    called = {"sent": False}

    def fake_send(msg):
        called["sent"] = True

    monkeypatch.setattr(bot, "send_telegram", fake_send)
    # Make fetch_with_retries return our templated HTML
    monkeypatch.setattr(bot, "fetch_with_retries", lambda *args, **kwargs: make_resp(html))

    # Use a temp state file so we don't clobber repo file
    bot.STATE_FILE = str(tmp_path / "last_seen.json")

    # Run the check
    bot.check_bse()

    captured = capsys.readouterr()
    assert "Templated content detected" in captured.out

    # Ensure send_telegram was NOT called
    assert called["sent"] is False

    # The templated announcement should be recorded to last_seen to avoid repeated noisy runs
    with open(bot.STATE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "CorpannData" in data["title"] or "CorpannData" in data["scrip"]
