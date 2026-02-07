import bot
import json


def test_sends_when_tracked_scrip(monkeypatch, tmp_path):
    # Simulate API returning an IDEA announcement
    monkeypatch.setattr(bot, 'get_latest_announcement_from_api', lambda: {"date":"d","scrip":"IDEA","title":"Some update","pdf":""})
    called = {}
    monkeypatch.setattr(bot, 'send_telegram', lambda msg: called.update({'msg': msg}))
    bot.STATE_FILE = str(tmp_path / 'last_seen.json')
    bot.check_bse()
    # Message should use the new format and include Scrip and Announcement
    assert 'IDEA : Announcement' in called['msg'] or 'Date :' in called['msg']


def test_no_updates_when_other_company(monkeypatch, tmp_path, capsys):
    # API returns announcement for another company
    monkeypatch.setattr(bot, 'get_latest_announcement_from_api', lambda: {"date":"d","scrip":"ACME","title":"Some update","pdf":""})
    called = {'sent': False}
    monkeypatch.setattr(bot, 'send_telegram', lambda msg: called.update({'sent': True, 'msg': msg}))
    bot.STATE_FILE = str(tmp_path / 'last_seen.json')
    bot.check_bse()
    assert called['sent'] is True
    assert 'No new announcements for NSE Symbol' in called['msg']


def test_no_updates_when_same_as_last_seen(monkeypatch, tmp_path):
    # When current equals last_seen, should send no updates message
    current = {"date":"d","scrip":"IDEA","title":"Same","pdf":""}
    monkeypatch.setattr(bot, 'get_latest_announcement_from_api', lambda: current)
    monkeypatch.setattr(bot, 'load_last_seen', lambda: current)
    called = {}
    monkeypatch.setattr(bot, 'send_telegram', lambda msg: called.update({'msg': msg}))
    bot.STATE_FILE = str(tmp_path / 'last_seen.json')
    bot.check_bse()
    assert 'No new announcements for NSE Symbol' in called['msg']
