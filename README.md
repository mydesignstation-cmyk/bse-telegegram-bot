# bse-telegegram-bot

This bot scrapes BSE announcements and sends important items to a Telegram chat.

Notes
-----
- The bot persists the last seen announcement to `last_seen.json` using UTF-8 and writes Unicode characters unescaped (emojis are preserved). This ensures emojis and non-ASCII characters are visible when inspecting the file.

- The bot uses an exponential backoff strategy (with retries) and an increased timeout when fetching the BSE announcements to handle transient network failures.

- For sandbox/testing, the bot will load a local `.env` file at startup and **override** environment variables with values found there (e.g., `BOT_TOKEN` and `CHAT_ID`). Remove or edit `.env` to change this behaviour.
