from telegram import Update
from telegram.ext import ContextTypes

from bot.database import Database
from bot.round_robin import get_next_participant


def _get_db(context: ContextTypes.DEFAULT_TYPE) -> Database:
    return context.bot_data["db"]


def _get_tracker_name(context: ContextTypes.DEFAULT_TYPE) -> str | None:
    if context.args:
        return " ".join(context.args).strip().lower()
    return None


def _display_name(user) -> str:
    if user.first_name and user.last_name:
        return f"{user.first_name} {user.last_name}"
    return user.first_name or user.username or str(user.id)


async def create_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = _get_tracker_name(context)
    if not name:
        await update.message.reply_text("Usage: /create <tracker_name>")
        return

    db = _get_db(context)
    tracker_id = await db.create_tracker(
        update.effective_chat.id, name, update.effective_user.id
    )
    if tracker_id is None:
        await update.message.reply_text(f'Tracker "{name}" already exists in this chat.')
        return

    await update.message.reply_text(
        f'Tracker "{name}" created! Participants can join with /join {name}'
    )


async def join_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = _get_tracker_name(context)
    if not name:
        await update.message.reply_text("Usage: /join <tracker_name>")
        return

    db = _get_db(context)
    tracker = await db.get_tracker(update.effective_chat.id, name)
    if not tracker:
        await update.message.reply_text(f'Tracker "{name}" not found.')
        return

    user = update.effective_user
    added = await db.add_participant(tracker["id"], user.id, _display_name(user))
    if not added:
        await update.message.reply_text(f"You're already in \"{name}\".")
        return

    await update.message.reply_text(f"{_display_name(user)} joined \"{name}\"!")


async def leave_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = _get_tracker_name(context)
    if not name:
        await update.message.reply_text("Usage: /leave <tracker_name>")
        return

    db = _get_db(context)
    tracker = await db.get_tracker(update.effective_chat.id, name)
    if not tracker:
        await update.message.reply_text(f'Tracker "{name}" not found.')
        return

    removed = await db.remove_participant(tracker["id"], update.effective_user.id)
    if not removed:
        await update.message.reply_text(f"You're not in \"{name}\".")
        return

    await update.message.reply_text(
        f"{_display_name(update.effective_user)} left \"{name}\"."
    )


async def checkin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = _get_tracker_name(context)
    if not name:
        await update.message.reply_text("Usage: /checkin <tracker_name>")
        return

    db = _get_db(context)
    tracker = await db.get_tracker(update.effective_chat.id, name)
    if not tracker:
        await update.message.reply_text(f'Tracker "{name}" not found.')
        return

    user = update.effective_user
    participants = await db.get_participants(tracker["id"])
    if not any(p["user_id"] == user.id for p in participants):
        await update.message.reply_text(
            f"You're not a participant in \"{name}\". Join first with /join {name}"
        )
        return

    await db.record_checkin(tracker["id"], user.id)

    next_p = await get_next_participant(db, tracker["id"])
    reply = f"{_display_name(user)} checked in for \"{name}\"!"
    if next_p:
        reply += f"\nNext up: {next_p['display_name']}"

    await update.message.reply_text(reply)


async def next_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = _get_tracker_name(context)
    if not name:
        await update.message.reply_text("Usage: /next <tracker_name>")
        return

    db = _get_db(context)
    tracker = await db.get_tracker(update.effective_chat.id, name)
    if not tracker:
        await update.message.reply_text(f'Tracker "{name}" not found.')
        return

    next_p = await get_next_participant(db, tracker["id"])
    if not next_p:
        await update.message.reply_text(f'No participants in "{name}" yet.')
        return

    await update.message.reply_text(
        f'Who is next for "{name}"? {next_p["display_name"]}!'
    )


async def history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = _get_tracker_name(context)
    if not name:
        await update.message.reply_text("Usage: /history <tracker_name>")
        return

    db = _get_db(context)
    tracker = await db.get_tracker(update.effective_chat.id, name)
    if not tracker:
        await update.message.reply_text(f'Tracker "{name}" not found.')
        return

    history = await db.get_checkin_history(tracker["id"])
    if not history:
        await update.message.reply_text(f'No check-ins for "{name}" in the last 2 months.')
        return

    lines = [f'Check-in history for "{name}" (last 2 months):\n']
    for entry in history[:50]:  # Cap at 50 to avoid message size limits
        lines.append(f"  {entry['checked_in_at']} — {entry['display_name']}")

    if len(history) > 50:
        lines.append(f"\n...and {len(history) - 50} more")

    await update.message.reply_text("\n".join(lines))


async def trackers_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = _get_db(context)
    trackers = await db.list_trackers(update.effective_chat.id)
    if not trackers:
        await update.message.reply_text("No trackers in this chat. Create one with /create <name>")
        return

    lines = ["Trackers in this chat:\n"]
    for t in trackers:
        lines.append(f"  • {t['name']}")

    await update.message.reply_text("\n".join(lines))


async def participants_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = _get_tracker_name(context)
    if not name:
        await update.message.reply_text("Usage: /participants <tracker_name>")
        return

    db = _get_db(context)
    tracker = await db.get_tracker(update.effective_chat.id, name)
    if not tracker:
        await update.message.reply_text(f'Tracker "{name}" not found.')
        return

    participants = await db.get_participants(tracker["id"])
    if not participants:
        await update.message.reply_text(f'No participants in "{name}" yet. Join with /join {name}')
        return

    lines = [f'Participants in "{name}":\n']
    for i, p in enumerate(participants, 1):
        lines.append(f"  {i}. {p['display_name']}")

    await update.message.reply_text("\n".join(lines))


async def delete_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = _get_tracker_name(context)
    if not name:
        await update.message.reply_text("Usage: /delete <tracker_name>")
        return

    db = _get_db(context)
    tracker = await db.get_tracker(update.effective_chat.id, name)
    if not tracker:
        await update.message.reply_text(f'Tracker "{name}" not found.')
        return

    if tracker["created_by_user_id"] != update.effective_user.id:
        await update.message.reply_text("Only the creator of this tracker can delete it.")
        return

    await db.delete_tracker(tracker["id"])
    await update.message.reply_text(f'Tracker "{name}" deleted.')
