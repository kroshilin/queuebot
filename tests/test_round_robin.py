import pytest
import pytest_asyncio

from bot.database import Database
from bot.round_robin import get_next_participant, predict_queue


@pytest_asyncio.fixture
async def db(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    await database.connect()
    yield database
    await database.close()


@pytest.mark.asyncio
async def test_no_participants(db):
    tid = await db.create_tracker(100, 1)
    assert await get_next_participant(db, tid) is None


@pytest.mark.asyncio
async def test_no_checkins_returns_first(db):
    tid = await db.create_tracker(100, 1)
    await db.add_participant(tid, 10, "Alice")
    await db.add_participant(tid, 20, "Bob")
    await db.add_participant(tid, 30, "Charlie")

    nxt = await get_next_participant(db, tid)
    assert nxt["display_name"] == "Alice"


@pytest.mark.asyncio
async def test_round_robin_order(db):
    tid = await db.create_tracker(100, 1)
    await db.add_participant(tid, 10, "Alice")
    await db.add_participant(tid, 20, "Bob")
    await db.add_participant(tid, 30, "Charlie")

    await db.record_checkin(tid, 10)
    nxt = await get_next_participant(db, tid)
    assert nxt["display_name"] == "Bob"

    await db.record_checkin(tid, 20)
    nxt = await get_next_participant(db, tid)
    assert nxt["display_name"] == "Charlie"

    await db.record_checkin(tid, 30)
    nxt = await get_next_participant(db, tid)
    assert nxt["display_name"] == "Alice"


@pytest.mark.asyncio
async def test_out_of_order_checkin(db):
    """Charlie checks in first; Alice & Bob never checked in → Alice (lowest position)."""
    tid = await db.create_tracker(100, 1)
    await db.add_participant(tid, 10, "Alice")
    await db.add_participant(tid, 20, "Bob")
    await db.add_participant(tid, 30, "Charlie")

    await db.record_checkin(tid, 30)
    nxt = await get_next_participant(db, tid)
    assert nxt["display_name"] == "Alice"


@pytest.mark.asyncio
async def test_last_checker_left(db):
    tid = await db.create_tracker(100, 1)
    await db.add_participant(tid, 10, "Alice")
    await db.add_participant(tid, 20, "Bob")

    await db.record_checkin(tid, 20)
    await db.remove_participant(tid, 20)

    nxt = await get_next_participant(db, tid)
    assert nxt["display_name"] == "Alice"


@pytest.mark.asyncio
async def test_duplicate_checkin_advances(db):
    """Bum, X, Igor, Anton check in; Anton checks in again → Bum (oldest last-seen)."""
    tid = await db.create_tracker(100, 1)
    await db.add_participant(tid, 1, "Bum")
    await db.add_participant(tid, 2, "X")
    await db.add_participant(tid, 3, "Igor")
    await db.add_participant(tid, 4, "Anton")

    await db.record_checkin(tid, 1)   # Bum
    await db.record_checkin(tid, 2)   # X
    await db.record_checkin(tid, 3)   # Igor
    await db.record_checkin(tid, 4)   # Anton
    await db.record_checkin(tid, 4)   # Anton again

    nxt = await get_next_participant(db, tid)
    assert nxt["display_name"] == "Bum"


@pytest.mark.asyncio
async def test_never_checked_in_gets_priority(db):
    """Participants who never checked in are suggested first, tiebroken by position."""
    tid = await db.create_tracker(100, 1)
    await db.add_participant(tid, 10, "Alice")
    await db.add_participant(tid, 20, "Bob")
    await db.add_participant(tid, 30, "Charlie")

    # Only Bob checked in
    await db.record_checkin(tid, 20)

    nxt = await get_next_participant(db, tid)
    # Alice (pos 0) and Charlie (pos 2) never checked in; Alice wins by position
    assert nxt["display_name"] == "Alice"


@pytest.mark.asyncio
async def test_tiebreaker_by_position(db):
    """When multiple participants have the same last-checkin, lowest position wins."""
    tid = await db.create_tracker(100, 1)
    await db.add_participant(tid, 10, "Alice")
    await db.add_participant(tid, 20, "Bob")
    await db.add_participant(tid, 30, "Charlie")

    # All three never checked in → tied at -1, Alice (pos 0) wins
    nxt = await get_next_participant(db, tid)
    assert nxt["display_name"] == "Alice"

    # All three check in sequentially, then all tied with same-era checkins
    await db.record_checkin(tid, 10)
    await db.record_checkin(tid, 20)
    await db.record_checkin(tid, 30)

    # Alice has oldest checkin id → she's next
    nxt = await get_next_participant(db, tid)
    assert nxt["display_name"] == "Alice"


# --- predict_queue tests ---


@pytest.mark.asyncio
async def test_predict_queue_empty(db):
    tid = await db.create_tracker(100, 1)
    assert await predict_queue(db, tid) == []


@pytest.mark.asyncio
async def test_predict_queue_basic(db):
    tid = await db.create_tracker(100, 1)
    await db.add_participant(tid, 10, "Alice")
    await db.add_participant(tid, 20, "Bob")
    await db.add_participant(tid, 30, "Charlie")

    queue = await predict_queue(db, tid, turns=3)
    names = [p["display_name"] for p in queue]
    # All never checked in → by position: Alice, Bob, Charlie
    assert names == ["Alice", "Bob", "Charlie"]


@pytest.mark.asyncio
async def test_predict_queue_after_checkins(db):
    tid = await db.create_tracker(100, 1)
    await db.add_participant(tid, 10, "Alice")
    await db.add_participant(tid, 20, "Bob")
    await db.add_participant(tid, 30, "Charlie")

    await db.record_checkin(tid, 10)
    await db.record_checkin(tid, 20)

    queue = await predict_queue(db, tid, turns=3)
    names = [p["display_name"] for p in queue]
    # Charlie never checked in (highest priority), then Alice (oldest checkin), then Bob
    assert names == ["Charlie", "Alice", "Bob"]


@pytest.mark.asyncio
async def test_predict_queue_caps_at_participant_count(db):
    tid = await db.create_tracker(100, 1)
    await db.add_participant(tid, 10, "Alice")
    await db.add_participant(tid, 20, "Bob")

    queue = await predict_queue(db, tid, turns=3)
    assert len(queue) == 2
    names = [p["display_name"] for p in queue]
    assert names == ["Alice", "Bob"]


@pytest.mark.asyncio
async def test_predict_queue_single_participant(db):
    tid = await db.create_tracker(100, 1)
    await db.add_participant(tid, 10, "Alice")

    queue = await predict_queue(db, tid, turns=3)
    assert len(queue) == 1
    assert queue[0]["display_name"] == "Alice"
