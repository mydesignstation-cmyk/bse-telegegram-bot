import json
import bot


def test_save_and_load_emoji(tmp_path):
    bot.STATE_FILE = str(tmp_path / "last_seen.json")
    data = {"title": "Test 🚀 Emoji", "scrip": "ACME", "date": "28 Jan 2026"}
    bot.save_last_seen(data)

    # Ensure the raw file bytes contain the emoji UTF-8 sequence
    with open(bot.STATE_FILE, "rb") as f:
        content = f.read()
    assert "🚀".encode("utf-8") in content

    loaded = bot.load_last_seen()
    assert loaded == data
