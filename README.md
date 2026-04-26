# Who is next? — Telegram Check-in Bot

A Telegram bot that tracks check-ins in group chats using round-robin rotation. Each chat gets one tracker — no arguments needed on any command.

## Setup

1. Create a bot via [@BotFather](https://t.me/BotFather) and get the token
2. Clone this repo and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and fill in your bot token:

```bash
cp .env.example .env
# Edit .env with your TELEGRAM_BOT_TOKEN
```

4. Run the bot:

```bash
python -m bot.main
```

## Commands

| Command | Description |
|---------|-------------|
| `/create` | Create the tracker for this chat |
| `/join` | Join as a participant |
| `/leave` | Leave the tracker |
| `/checkin` | Check in |
| `/next` | Who's next? |
| `/history` | Check-in history (last 2 months) |
| `/participants` | List participants |
| `/delete` | Delete the tracker (creator only) |

All commands also appear in Telegram's `/` autocomplete menu. Key responses include inline buttons so you can tap instead of typing.

## How it works

- Add the bot to a group chat
- Create the tracker with `/create`
- Participants join with `/join`
- When it's your turn, check in with `/checkin`
- The bot announces who's next in round-robin order
- Tap the **Check in** or **Who's next?** buttons, or type `/next`

## Running tests

```bash
python -m pytest tests/ -v
```
