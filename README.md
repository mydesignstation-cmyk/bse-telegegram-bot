# bse-telegegram-bot

This bot scrapes BSE announcements and sends important items to a Telegram chat.

Notes
-----
- The bot persists the last seen announcement to `last_seen.json` using UTF-8 and writes Unicode characters unescaped (emojis are preserved). This ensures emojis and non-ASCII characters are visible when inspecting the file.

- The bot uses an exponential backoff strategy (with retries) and an increased timeout when fetching the BSE announcements to handle transient network failures.
