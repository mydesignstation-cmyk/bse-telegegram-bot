import importlib
import os

import bot


def test_empty_env_uses_default_list(monkeypatch):
    # If TRACKED_SCRIP is set to an empty string in the environment, the module
    # should fall back to the default list rather than using an empty list.
    monkeypatch.setenv("TRACKED_SCRIP", "")
    importlib.reload(bot)
    expected = {"539594", "VPRPL", "OLECTRA", "TITAGARH", "ASTRAL", "AGI", "JIOFIN", "BLS"}
    assert expected.issubset(set(bot.TRACKED_SCRIP_LIST))
