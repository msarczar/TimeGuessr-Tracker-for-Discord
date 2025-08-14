# TimeGuessr Discord Bot

A lightweight Discord bot that auto-detects **TimeGuessr** score posts in a channel, stores them in SQLite, and provides leaderboards, daily highs, weekly/monthly averages, and personal stats with streaks.

> Example score message it detects: `TimeGuessr #712 47,890/50,000`

---

## Features

- **Auto-ingestion** of scores via regex when users post: `TimeGuessr #<gameNumber> <score>/<maxScore>` (e.g., `TimeGuessr #123 46,415/50,000`).
- **Leaderboards**: overall average, past 7 days (avg), past 30 days (avg).
- **Daily view**: highest scores posted **today**.
- **Personal stats**: games played, average/best/worst, and **streaks** (current + longest).
- **History import** from the channel to backfill scores (admin-only).
- **SQLite storage** with duplicate protection (unique message_id).

---

## Commands

- `!leaderboard` (aliases: `!lb`, `!overall`) – Overall average leaderboard (server).
- `!today` (alias: `!daily`) – Today’s scores ranked by highest.
- `!week` (alias: `!weekly`) – Past 7 days average leaderboard.
- `!month` (alias: `!monthly`) – Past 30 days average leaderboard.
- `!my_stats` (aliases: `!mystats`, `!stats`) – Your stats + streaks (server-scoped).
- `!import_history [limit]` – Import historical messages in the current channel (requires **Manage Server**). Default 500, max 10,000+.


---

## How it Works

1. **Listening scope**: The bot only parses messages in the configured **score channel** (`SCORE_CHANNEL_ID`).
2. **Regex parsing**: `TimeGuessr #(\d+)\s+(\d{1,3}(?:,\d{3})*)/(\d{1,3}(?:,\d{3})*)` – extracts game number, score, and max.
3. **Persisting**: On match, the bot writes one row per score to SQLite with a unique `message_id`. Duplicate messages are skipped.
4. **Stats**: Leaderboards aggregate by player; personal streaks are computed from distinct posting dates.


---

## Quick Start

### Prerequisites
- Python 3.10+
- A Discord application + bot token
- **Message Content Intent** must be enabled in *Discord Developer Portal → Bot → Privileged Gateway Intents*

### Environment
Set your token as an environment variable:

```bash
# .env or host env
export DISCORD_BOT_TOKEN=your-bot-token
```

### Configure your Score Channel
- In Discord: enable Developer Mode → right-click the **score channel** → **Copy ID**.
- Open `bot.py` and set:
  ```python
  SCORE_CHANNEL_ID = 123456789012345678  # replace with your channel ID (no quotes)
  ```

### Install & Run

```bash
pip install -U discord.py
python main.py
```

`main.py` verifies the token and starts the bot.


---

## File Structure

- `bot.py` — Discord bot, commands, regex, streaks, ingestion.
- `database.py` — SQLite setup & helpers (`add_score`, `get_scores`, `init_db`).
- `main.py` — Entrypoint that runs the bot (checks env).


---

## Database

SQLite file: `timeguessr_scores.db` with table:

```sql
CREATE TABLE IF NOT EXISTS scores (
  player_id   TEXT NOT NULL,
  player_name TEXT NOT NULL,
  game_date   TEXT NOT NULL,
  score       INTEGER NOT NULL,
  max_score   INTEGER NOT NULL,
  game_number INTEGER,
  message_id  TEXT UNIQUE NOT NULL
);
```

- Uniqueness is enforced on `message_id` to avoid duplicates on re-import.


---

## Usage Examples

Post a score in the score channel:

```
TimeGuessr #712 47,890/50,000
```

Check stats:

```
!my_stats
!week
!today
```


---

## Admin Backfill

To import historic scores from the current channel:

```
!import_history           # last 500 messages
!import_history 5000      # last 5000 messages
```

- Requires **Manage Server** permission.
- Progress updates during import; duplicates and non-matching messages are skipped.


---

## Troubleshooting

- **Bot doesn’t respond**
  - Ensure `DISCORD_BOT_TOKEN` is set; `main.py` logs a fatal error if missing.
  - Confirm the bot has access to the score channel and the Message Content Intent is enabled.
- **Scores not detected**
  - Check your post matches the regex format (e.g., `TimeGuessr #123 46,415/50,000`).
- **Duplicate warnings**
  - Re-imports of the same Discord message are skipped due to unique `message_id`.


---

## Known Limitations / TODOs

- **Guild scoping mismatch**: If you plan to run the bot on multiple servers, add a `guild_id` column to the `scores` table and include it in a composite unique index like `UNIQUE(message_id, guild_id)`. Update `add_score`/`get_scores` to accept and filter by `guild_id`.
- **Single-channel ingestion**: Only the configured channel is parsed. Widening scope requires removing the channel ID check or supporting multiple IDs.


---

## License

MIT.
