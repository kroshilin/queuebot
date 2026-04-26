# Who is next? — Telegram Check-in Bot

A Telegram bot that tracks check-ins in group chats using round-robin rotation. Create trackers for recurring activities (standup, coffee runs, etc.), and the bot tells you who's next.

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
| `/create <name>` | Create a new tracker |
| `/join <name>` | Join a tracker as a participant |
| `/leave <name>` | Leave a tracker |
| `/checkin <name>` | Record your check-in |
| `/next <name>` | See who should check in next |
| `/history <name>` | View check-in history (last 2 months) |
| `/trackers` | List all trackers in the chat |
| `/participants <name>` | List participants in a tracker |
| `/delete <name>` | Delete a tracker (creator only) |

## How it works

- Add the bot to a group chat
- Create a tracker (e.g., `/create standup`)
- Participants join with `/join standup`
- When it's your turn, check in with `/checkin standup`
- The bot announces who's next in round-robin order
- Ask `/next standup` anytime to see who should go

## Running tests

```bash
python -m pytest tests/ -v
```
