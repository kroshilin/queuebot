import pytest
import pytest_asyncio

from bot.database import Database


@pytest_asyncio.fixture
async def db(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    await database.connect()
    yield database
    await database.close()


@pytest.mark.asyncio
async def test_create_tracker(db):
    tid = await db.create_tracker(chat_id=100, user_id=1)
    assert tid is not None

    # Duplicate in same chat fails
    dup = await db.create_tracker(chat_id=100, user_id=2)
    assert dup is None

    # Different chat succeeds
    tid2 = await db.create_tracker(chat_id=200, user_id=1)
    assert tid2 is not None


@pytest.mark.asyncio
async def test_get_tracker(db):
    await db.create_tracker(100, 1)
    t = await db.get_tracker(100)
    assert t is not None
    assert t["chat_id"] == 100

    assert await db.get_tracker(999) is None


@pytest.mark.asyncio
async def test_delete_tracker(db):
    tid = await db.create_tracker(100, 1)
    await db.delete_tracker(tid)
    assert await db.get_tracker(100) is None


@pytest.mark.asyncio
async def test_add_and_remove_participant(db):
    tid = await db.create_tracker(100, 1)

    assert await db.add_participant(tid, 10, "Alice") is True
    assert await db.add_participant(tid, 20, "Bob") is True

    # Duplicate
    assert await db.add_participant(tid, 10, "Alice") is False

    participants = await db.get_participants(tid)
    assert len(participants) == 2
    assert participants[0]["display_name"] == "Alice"
    assert participants[0]["position"] == 0
    assert participants[1]["position"] == 1

    # Remove
    assert await db.remove_participant(tid, 10) is True
    assert await db.remove_participant(tid, 10) is False
    assert len(await db.get_participants(tid)) == 1


@pytest.mark.asyncio
async def test_checkin_and_history(db):
    tid = await db.create_tracker(100, 1)
    await db.add_participant(tid, 10, "Alice")
    await db.add_participant(tid, 20, "Bob")

    await db.record_checkin(tid, 10)
    await db.record_checkin(tid, 20)

    last = await db.get_last_checkin(tid)
    assert last["user_id"] == 20

    history = await db.get_checkin_history(tid)
    assert len(history) == 2
    assert history[0]["user_id"] == 20  # Most recent first


@pytest.mark.asyncio
async def test_no_checkins(db):
    tid = await db.create_tracker(100, 1)
    assert await db.get_last_checkin(tid) is None
    assert await db.get_checkin_history(tid) == []
