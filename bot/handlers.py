from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.database import Database
from bot.round_robin import get_next_participant, predict_queue

NO_TRACKER_MSG = "No tracker in this chat yet. Create one with /create"

ACTION_BUTTONS = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("Check in", callback_data="checkin"),
        InlineKeyboardButton("Who's next?", callback_data="next"),
        InlineKeyboardButton("History", callback_data="history"),
    ]
])


def _get_db(context: ContextTypes.DEFAULT_TYPE) -> Database:
    return context.bot_data["db"]


def _display_name(user) -> str:
    if user.first_name and user.last_name:
        return f"{user.first_name} {user.last_name}"
    return user.first_name or user.username or str(user.id)


async def _require_tracker(db: Database, chat_id: int, reply_fn) -> dict | None:
    tracker = await db.get_tracker(chat_id)
    if not tracker:
        await reply_fn(NO_TRACKER_MSG)
    return tracker


async def create_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = _get_db(context)
    tracker_id = await db.create_tracker(update.effective_chat.id, update.effective_user.id)
    if tracker_id is None:
        await update.message.reply_text("A tracker already exists in this chat.")
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Join", callback_data="join")]
    ])
    await update.message.reply_text(
        "Tracker created! Participants can join with /join",
        reply_markup=keyboard,
    )


async def join_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = _get_db(context)
    tracker = await _require_tracker(db, update.effective_chat.id, update.message.reply_text)
    if not tracker:
        return

    user = update.effective_user
    added = await db.add_participant(tracker["id"], user.id, _display_name(user))
    if not added:
        await update.message.reply_text("You've already joined.")
        return

    await update.message.reply_text(
        f"{_display_name(user)} joined!",
        reply_markup=ACTION_BUTTONS,
    )


async def leave_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = _get_db(context)
    tracker = await _require_tracker(db, update.effective_chat.id, update.message.reply_text)
    if not tracker:
        return

    removed = await db.remove_participant(tracker["id"], update.effective_user.id)
    if not removed:
        await update.message.reply_text("You're not a participant.")
        return

    await update.message.reply_text(f"{_display_name(update.effective_user)} left.")


async def checkin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = _get_db(context)
    tracker = await _require_tracker(db, update.effective_chat.id, update.message.reply_text)
    if not tracker:
        return

    user = update.effective_user
    participants = await db.get_participants(tracker["id"])
    if not any(p["user_id"] == user.id for p in participants):
        await update.message.reply_text("You're not a participant. Join first with /join")
        return

    await db.record_checkin(tracker["id"], user.id)

    next_p = await get_next_participant(db, tracker["id"])
    reply = f"{_display_name(user)} checked in!"
    if next_p:
        reply += f"\nNext up: {next_p['display_name']}"

    await update.message.reply_text(reply, reply_markup=ACTION_BUTTONS)


async def next_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = _get_db(context)
    tracker = await _require_tracker(db, update.effective_chat.id, update.message.reply_text)
    if not tracker:
        return

    queue = await predict_queue(db, tracker["id"], turns=3)
    if not queue:
        await update.message.reply_text("No participants yet. Join with /join")
        return

    lines = [f"{i}. {p['display_name']}" for i, p in enumerate(queue, 1)]
    await update.message.reply_text(
        "Who is next?\n" + "\n".join(lines),
        reply_markup=ACTION_BUTTONS,
    )


async def history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = _get_db(context)
    tracker = await _require_tracker(db, update.effective_chat.id, update.message.reply_text)
    if not tracker:
        return

    history = await db.get_checkin_history(tracker["id"])
    if not history:
        await update.message.reply_text("No check-ins in the last 2 months.")
        return

    lines = ["Check-in history (last 2 months):\n"]
    for entry in history[:50]:
        lines.append(f"  {entry['checked_in_at']} — {entry['display_name']}")

    if len(history) > 50:
        lines.append(f"\n...and {len(history) - 50} more")

    await update.message.reply_text("\n".join(lines), reply_markup=ACTION_BUTTONS)


async def participants_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = _get_db(context)
    tracker = await _require_tracker(db, update.effective_chat.id, update.message.reply_text)
    if not tracker:
        return

    participants = await db.get_participants(tracker["id"])
    if not participants:
        await update.message.reply_text("No participants yet. Join with /join")
        return

    lines = ["Participants:\n"]
    for i, p in enumerate(participants, 1):
        lines.append(f"  {i}. {p['display_name']}")

    await update.message.reply_text("\n".join(lines))


async def delete_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = _get_db(context)
    tracker = await _require_tracker(db, update.effective_chat.id, update.message.reply_text)
    if not tracker:
        return

    if tracker["created_by_user_id"] != update.effective_user.id:
        await update.message.reply_text("Only the creator of this tracker can delete it.")
        return

    await db.delete_tracker(tracker["id"])
    await update.message.reply_text("Tracker deleted.")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard button presses."""
    query = update.callback_query
    await query.answer()

    action = query.data
    db = _get_db(context)
    chat_id = query.message.chat_id
    tracker = await db.get_tracker(chat_id)

    if not tracker:
        await query.message.reply_text(NO_TRACKER_MSG)
        return

    if action == "join":
        user = query.from_user
        added = await db.add_participant(tracker["id"], user.id, _display_name(user))
        if not added:
            await query.message.reply_text(f"{_display_name(user)} has already joined.")
        else:
            await query.message.reply_text(
                f"{_display_name(user)} joined!",
                reply_markup=ACTION_BUTTONS,
            )

    elif action == "checkin":
        user = query.from_user
        participants = await db.get_participants(tracker["id"])
        if not any(p["user_id"] == user.id for p in participants):
            await query.message.reply_text(
                f"{_display_name(user)} is not a participant. Join first with /join"
            )
            return
        await db.record_checkin(tracker["id"], user.id)
        next_p = await get_next_participant(db, tracker["id"])
        reply = f"{_display_name(user)} checked in!"
        if next_p:
            reply += f"\nNext up: {next_p['display_name']}"
        await query.message.reply_text(reply, reply_markup=ACTION_BUTTONS)

    elif action == "next":
        queue = await predict_queue(db, tracker["id"], turns=3)
        if not queue:
            await query.message.reply_text("No participants yet.")
        else:
            lines = [f"{i}. {p['display_name']}" for i, p in enumerate(queue, 1)]
            await query.message.reply_text(
                "Who is next?\n" + "\n".join(lines),
                reply_markup=ACTION_BUTTONS,
            )

    elif action == "history":
        history = await db.get_checkin_history(tracker["id"])
        if not history:
            await query.message.reply_text("No check-ins in the last 2 months.")
        else:
            lines = ["Check-in history (last 2 months):\n"]
            for entry in history[:50]:
                lines.append(f"  {entry['checked_in_at']} — {entry['display_name']}")
            if len(history) > 50:
                lines.append(f"\n...and {len(history) - 50} more")
            await query.message.reply_text(
                "\n".join(lines),
                reply_markup=ACTION_BUTTONS,
            )
