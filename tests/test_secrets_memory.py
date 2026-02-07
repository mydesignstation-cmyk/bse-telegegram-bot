import os
import bot
import requests
import types


def test_set_secrets_and_send(monkeypatch, tmp_path):
    # Remove env vars to simulate their absence
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.delenv("CHAT_ID", raising=False)

    # Install fake requests.post to capture calls
    called = {}
    def fake_post(url, json=None, timeout=None):
        called['url'] = url
        called['json'] = json
        class R: pass
        r = R()
        r.status_code = 200
        r.text = '{}'
        return r

    monkeypatch.setattr(requests, 'post', fake_post)

    # Set secrets in memory
    bot.set_secrets(bot_token='TEST_TOKEN_123', chat_id='-999')

    # Call send_telegram which should use in-memory secret
    bot.send_telegram('Hello')

    assert 'TEST_TOKEN_123' in called['url']
    assert called['json']['chat_id'] == '-999' or called['json']['chat_id'] == -999


def test_reload_secrets_from_dotenv(tmp_path, monkeypatch):
    # Create a temporary .env file
    env_file = tmp_path / 'local.env'
    env_file.write_text('BOT_TOKEN=ENV_TOKEN\nCHAT_ID=12345\n')

    # Ensure current secrets are different
    bot.set_secrets(bot_token='OLD', chat_id='0')

    # Reload from the temporary env and assert secrets updated
    bot.reload_secrets_from_dotenv(str(env_file))
    assert bot.SECRETS['BOT_TOKEN'] == 'ENV_TOKEN'
    assert bot.SECRETS['CHAT_ID'] == '12345'

    # Also ensure module globals were updated
    assert bot.BOT_TOKEN == 'ENV_TOKEN'
    assert str(bot.CHAT_ID) == '12345'
