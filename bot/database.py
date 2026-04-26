import aiosqlite
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_DB_PATH = "checkin_bot.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS trackers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    created_by_user_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(chat_id, name)
);

CREATE TABLE IF NOT EXISTS participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tracker_id INTEGER NOT NULL REFERENCES trackers(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL,
    display_name TEXT NOT NULL,
    position INTEGER NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tracker_id, user_id)
);

CREATE TABLE IF NOT EXISTS checkins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tracker_id INTEGER NOT NULL REFERENCES trackers(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL,
    checked_in_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


class Database:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def connect(self):
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA foreign_keys = ON")
        await self._db.executescript(SCHEMA)
        await self._db.commit()

    async def close(self):
        if self._db:
            await self._db.close()

    # --- Trackers ---

    async def create_tracker(self, chat_id: int, name: str, user_id: int) -> int | None:
        """Create a tracker. Returns tracker id, or None if name already taken."""
        try:
            cursor = await self._db.execute(
                "INSERT INTO trackers (chat_id, name, created_by_user_id) VALUES (?, ?, ?)",
                (chat_id, name.lower(), user_id),
            )
            await self._db.commit()
            return cursor.lastrowid
        except aiosqlite.IntegrityError:
            return None

    async def get_tracker(self, chat_id: int, name: str) -> dict | None:
        cursor = await self._db.execute(
            "SELECT * FROM trackers WHERE chat_id = ? AND name = ?",
            (chat_id, name.lower()),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def list_trackers(self, chat_id: int) -> list[dict]:
        cursor = await self._db.execute(
            "SELECT * FROM trackers WHERE chat_id = ? ORDER BY created_at",
            (chat_id,),
        )
        return [dict(row) for row in await cursor.fetchall()]

    async def delete_tracker(self, tracker_id: int) -> None:
        await self._db.execute("DELETE FROM trackers WHERE id = ?", (tracker_id,))
        await self._db.commit()

    # --- Participants ---

    async def add_participant(
        self, tracker_id: int, user_id: int, display_name: str
    ) -> bool:
        """Add a participant. Returns True on success, False if already joined."""
        try:
            # Get next position
            cursor = await self._db.execute(
                "SELECT COALESCE(MAX(position), -1) + 1 FROM participants WHERE tracker_id = ?",
                (tracker_id,),
            )
            (next_pos,) = await cursor.fetchone()
            await self._db.execute(
                "INSERT INTO participants (tracker_id, user_id, display_name, position) VALUES (?, ?, ?, ?)",
                (tracker_id, user_id, display_name, next_pos),
            )
            await self._db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

    async def remove_participant(self, tracker_id: int, user_id: int) -> bool:
        cursor = await self._db.execute(
            "DELETE FROM participants WHERE tracker_id = ? AND user_id = ?",
            (tracker_id, user_id),
        )
        await self._db.commit()
        return cursor.rowcount > 0

    async def get_participants(self, tracker_id: int) -> list[dict]:
        cursor = await self._db.execute(
            "SELECT * FROM participants WHERE tracker_id = ? ORDER BY position",
            (tracker_id,),
        )
        return [dict(row) for row in await cursor.fetchall()]

    # --- Check-ins ---

    async def record_checkin(self, tracker_id: int, user_id: int) -> int:
        cursor = await self._db.execute(
            "INSERT INTO checkins (tracker_id, user_id) VALUES (?, ?)",
            (tracker_id, user_id),
        )
        await self._db.commit()
        return cursor.lastrowid

    async def get_last_checkin(self, tracker_id: int) -> dict | None:
        cursor = await self._db.execute(
            "SELECT * FROM checkins WHERE tracker_id = ? ORDER BY id DESC LIMIT 1",
            (tracker_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_checkin_history(self, tracker_id: int, days: int = 60) -> list[dict]:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        cursor = await self._db.execute(
            """SELECT c.*, p.display_name
               FROM checkins c
               JOIN participants p ON p.tracker_id = c.tracker_id AND p.user_id = c.user_id
               WHERE c.tracker_id = ? AND c.checked_in_at >= ?
               ORDER BY c.id DESC""",
            (tracker_id, cutoff),
        )
        return [dict(row) for row in await cursor.fetchall()]
