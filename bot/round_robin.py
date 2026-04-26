from bot.database import Database


async def get_next_participant(db: Database, tracker_id: int) -> dict | None:
    """Determine who should check in next based on round-robin order.

    Returns the next participant dict, or None if there are no participants.
    """
    participants = await db.get_participants(tracker_id)
    if not participants:
        return None

    last_checkin = await db.get_last_checkin(tracker_id)
    if not last_checkin:
        return participants[0]

    last_user_id = last_checkin["user_id"]

    # Find the position of the last person who checked in
    for i, p in enumerate(participants):
        if p["user_id"] == last_user_id:
            # Next person in rotation (wrap around)
            return participants[(i + 1) % len(participants)]

    # Last check-in user is no longer a participant; start from the top
    return participants[0]
