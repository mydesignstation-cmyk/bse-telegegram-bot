import bot
import json


def test_sends_when_tracked_scrip(monkeypatch, tmp_path):
    # Simulate API returning an IDEA announcement
    monkeypatch.setattr(bot, 'get_latest_announcement_from_api', lambda: {"date":"d","scrip":"IDEA","title":"Some update","pdf":""})
    called = {}
    monkeypatch.setattr(bot, 'send_telegram', lambda msg: called.update({'msg': msg}))
    bot.STATE_FILE = str(tmp_path / 'last_seen.json')
    # explicitly set tracked symbols for this test
    monkeypatch.setattr(bot, 'TRACKED_SCRIP', "IDEA,VPRPL", raising=False)
    monkeypatch.setattr(bot, 'TRACKED_SCRIP_LIST', [s.strip().upper() for s in "IDEA,VPRPL".split(',') if s.strip()], raising=False)
    bot.check_bse()
    # Message should use the new format and include Scrip and Announcement
    assert 'IDEA : Announcement' in called['msg'] or 'Date :' in called['msg']


def test_sends_when_one_of_tracked_scrip(monkeypatch, tmp_path):
    # TRACKED_SCRIP supports comma-separated symbols; ensure one of them triggers a send
    monkeypatch.setattr(bot, 'get_latest_announcement_from_api', lambda: {"date":"d","scrip":"VPRPL","title":"Some update","pdf":""})
    called = {}
    monkeypatch.setattr(bot, 'send_telegram', lambda msg: called.update({'msg': msg}))
    bot.STATE_FILE = str(tmp_path / 'last_seen.json')
    # set multiple tracked symbols and update the list used by the module
    monkeypatch.setattr(bot, 'TRACKED_SCRIP', "IDEA,VPRPL", raising=False)
    monkeypatch.setattr(bot, 'TRACKED_SCRIP_LIST', [s.strip().upper() for s in "IDEA,VPRPL".split(',') if s.strip()], raising=False)
    bot.check_bse()
    assert 'VPRPL : Announcement' in called['msg'] or 'Date :' in called['msg']


def test_exact_matching_not_substring(monkeypatch, tmp_path):
    # Ensure exact matching: tracked 'AGI' should NOT match announcement for 'XAGIY'
    monkeypatch.setattr(bot, 'get_latest_announcement_from_api', lambda: {"date":"d","scrip":"XAGIY","title":"Some update","pdf":""})
    called = {'sent': False}
    monkeypatch.setattr(bot, 'send_telegram', lambda msg: called.update({'sent': True, 'msg': msg}))
    bot.STATE_FILE = str(tmp_path / 'last_seen.json')
    monkeypatch.setattr(bot, 'TRACKED_SCRIP', "AGI", raising=False)
    monkeypatch.setattr(bot, 'TRACKED_SCRIP_LIST', [s.strip().upper() for s in "AGI".split(',') if s.strip()], raising=False)
    bot.check_bse()
    assert called['sent'] is True
    assert 'No New anouncement for NSE Symbol' in called['msg']


def test_default_tracked_list_contains_user_items():
    # Ensure the default TRACKED_SCRIP_LIST contains the user-specified symbols
    # Reload the module to ensure we get the module defaults (unaffected by other tests)
    import importlib
    importlib.reload(bot)
    expected = {'539594', 'VPRPL', 'OLECTRA', 'TITAGARH', 'ASTRAL', 'AGI', 'JIOFIN', 'BLS'}
    assert expected.issubset(set(bot.TRACKED_SCRIP_LIST))


def test_no_updates_when_other_company(monkeypatch, tmp_path, capsys):
    # API returns announcement for another company
    monkeypatch.setattr(bot, 'get_latest_announcement_from_api', lambda: {"date":"d","scrip":"ACME","title":"Some update","pdf":""})
    called = {'sent': False}
    monkeypatch.setattr(bot, 'send_telegram', lambda msg: called.update({'sent': True, 'msg': msg}))
    bot.STATE_FILE = str(tmp_path / 'last_seen.json')
    bot.check_bse()
    assert called['sent'] is True
    assert 'No New anouncement for NSE Symbol' in called['msg']


def test_no_updates_when_same_as_last_seen(monkeypatch, tmp_path):
    # When current equals last_seen, should send no updates message
    current = {"date":"d","scrip":"IDEA","title":"Same","pdf":""}
    monkeypatch.setattr(bot, 'get_latest_announcement_from_api', lambda: current)
    monkeypatch.setattr(bot, 'load_last_seen', lambda: current)
    called = {}
    monkeypatch.setattr(bot, 'send_telegram', lambda msg: called.update({'msg': msg}))
    bot.STATE_FILE = str(tmp_path / 'last_seen.json')
    bot.check_bse()
    assert 'No New anouncement for NSE Symbol' in called['msg']
