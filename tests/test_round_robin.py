import pytest
import pytest_asyncio

from bot.database import Database
from bot.round_robin import get_next_participant


@pytest_asyncio.fixture
async def db(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    await database.connect()
    yield database
    await database.close()


@pytest.mark.asyncio
async def test_no_participants(db):
    tid = await db.create_tracker(100, "standup", 1)
    assert await get_next_participant(db, tid) is None


@pytest.mark.asyncio
async def test_no_checkins_returns_first(db):
    tid = await db.create_tracker(100, "standup", 1)
    await db.add_participant(tid, 10, "Alice")
    await db.add_participant(tid, 20, "Bob")
    await db.add_participant(tid, 30, "Charlie")

    nxt = await get_next_participant(db, tid)
    assert nxt["display_name"] == "Alice"


@pytest.mark.asyncio
async def test_round_robin_order(db):
    tid = await db.create_tracker(100, "standup", 1)
    await db.add_participant(tid, 10, "Alice")
    await db.add_participant(tid, 20, "Bob")
    await db.add_participant(tid, 30, "Charlie")

    # Alice checks in -> next is Bob
    await db.record_checkin(tid, 10)
    nxt = await get_next_participant(db, tid)
    assert nxt["display_name"] == "Bob"

    # Bob checks in -> next is Charlie
    await db.record_checkin(tid, 20)
    nxt = await get_next_participant(db, tid)
    assert nxt["display_name"] == "Charlie"

    # Charlie checks in -> wraps to Alice
    await db.record_checkin(tid, 30)
    nxt = await get_next_participant(db, tid)
    assert nxt["display_name"] == "Alice"


@pytest.mark.asyncio
async def test_out_of_order_checkin(db):
    tid = await db.create_tracker(100, "standup", 1)
    await db.add_participant(tid, 10, "Alice")
    await db.add_participant(tid, 20, "Bob")
    await db.add_participant(tid, 30, "Charlie")

    # Charlie checks in out of order -> next is Alice (wraps)
    await db.record_checkin(tid, 30)
    nxt = await get_next_participant(db, tid)
    assert nxt["display_name"] == "Alice"


@pytest.mark.asyncio
async def test_last_checker_left(db):
    tid = await db.create_tracker(100, "standup", 1)
    await db.add_participant(tid, 10, "Alice")
    await db.add_participant(tid, 20, "Bob")

    # Bob checks in, then leaves
    await db.record_checkin(tid, 20)
    await db.remove_participant(tid, 20)

    # Last checker no longer a participant -> fallback to first
    nxt = await get_next_participant(db, tid)
    assert nxt["display_name"] == "Alice"
