from bot.database import Database


def _rank_participants(participants: list[dict], last_checkins: dict[int, int]) -> list[dict]:
    """Sort participants by oldest last check-in (longest-unseen first).

    Participants who never checked in get highest priority (sort key -1).
    Tiebreaker: join position ASC.
    """
    return sorted(
        participants,
        key=lambda p: (last_checkins.get(p["user_id"], -1), p["position"]),
    )


async def get_next_participant(db: Database, tracker_id: int) -> dict | None:
    """Determine who should check in next using longest-unseen-first.

    Returns the next participant dict, or None if there are no participants.
    """
    participants = await db.get_participants(tracker_id)
    if not participants:
        return None

    last_checkins = await db.get_last_checkin_per_participant(tracker_id)
    ranked = _rank_participants(participants, last_checkins)
    return ranked[0]


async def predict_queue(db: Database, tracker_id: int, turns: int = 3) -> list[dict]:
    """Predict the next `turns` participants by simulating consecutive check-ins.

    Each turn assumes the predicted person checks in, shifting the last-seen state.
    Returns up to min(turns, len(participants)) participant dicts.
    """
    participants = await db.get_participants(tracker_id)
    if not participants:
        return []

    last_checkins = await db.get_last_checkin_per_participant(tracker_id)
    turns = min(turns, len(participants))

    # Use a synthetic counter beyond any real checkin id for simulation
    max_id = max(last_checkins.values()) if last_checkins else 0
    simulated = dict(last_checkins)
    result = []

    for _ in range(turns):
        ranked = _rank_participants(participants, simulated)
        winner = ranked[0]
        result.append(winner)
        max_id += 1
        simulated[winner["user_id"]] = max_id

    return result
