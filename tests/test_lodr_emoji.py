import os
import bot


def test_inject_lodr_emoji_enabled(monkeypatch):
    monkeypatch.setenv("TEMP_LODR_TEST", "1")
    monkeypatch.setenv("TEMP_LODR_EMOJI", "🧪")
    msg = "Original"
    res = bot.inject_lodr_test_emoji("Regulation 30 (LODR) - Notice", msg) if hasattr(bot, 'inject_lodr_test_emoji') else None
    # Ensure function exists and emoji injected
    assert res is not None
    assert res.startswith("🧪 ")


def test_inject_lodr_emoji_disabled(monkeypatch):
    monkeypatch.setenv("TEMP_LODR_TEST", "0")
    msg = "Original"
    res = bot.inject_lodr_test_emoji("LODR update", msg) if hasattr(bot, 'inject_lodr_test_emoji') else None
    assert res == msg
