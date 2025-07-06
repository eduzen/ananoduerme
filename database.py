import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Iterator, Optional


class Status(StrEnum):
    VERIFIED = "verified"
    PENDING = "pending"
    BLOCKED = "blocked"


@dataclass(slots=True)
class User:
    id: int
    name: str
    username: Optional[str]
    status: Status
    chat_id: Optional[int]
    created_at: str
    updated_at: str


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - no cleanup needed as connections are managed per-operation"""
        pass

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Context manager for database connections with optimized settings"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row

        # One-time setup per connection
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")  # faster writes + concurrency
        conn.execute("PRAGMA synchronous = NORMAL")  # good durability/speed balance
        conn.execute(
            "PRAGMA busy_timeout = 5000"
        )  # wait 5s before 'database is locked'

        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_database(self) -> None:
        """Initialize the SQLite database with required tables"""
        with self.connect() as conn:
            cursor = conn.cursor()

            # Create users table to track verification states
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    user_name TEXT NOT NULL,
                    username TEXT,
                    status TEXT NOT NULL CHECK (status IN ('verified', 'pending', 'blocked')),
                    chat_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create pending_verifications table for active captcha challenges
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pending_verifications (
                    user_id INTEGER PRIMARY KEY,
                    chat_id INTEGER NOT NULL,
                    user_name TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)

            # Create indexes for better performance
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_users_status ON users (status)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_pending_chat ON pending_verifications (chat_id)"
            )

            # Create trigger to automatically update updated_at timestamp
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS users_updated_at
                AFTER UPDATE ON users
                BEGIN
                    UPDATE users SET updated_at=CURRENT_TIMESTAMP WHERE rowid=NEW.rowid;
                END;
            """)

    def is_user_verified(self, user_id: int) -> bool:
        """Check if a user is verified"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT status FROM users WHERE user_id = ? AND status = ?",
                (user_id, Status.VERIFIED),
            )
            result = cursor.fetchone()
            return result is not None

    def is_user_blocked(self, user_id: int) -> bool:
        """Check if a user is blocked"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT status FROM users WHERE user_id = ? AND status = ?",
                (user_id, Status.BLOCKED),
            )
            result = cursor.fetchone()
            return result is not None

    def get_pending_verification(self, user_id: int) -> dict[str, Any] | None:
        """Get pending verification data for a user"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT chat_id, user_name, question, answer
                FROM pending_verifications
                WHERE user_id = ?
            """,
                (user_id,),
            )
            result = cursor.fetchone()

            if result:
                return {
                    "chat_id": result[0],
                    "user_name": result[1],
                    "question": result[2],
                    "answer": result[3],
                }
            return None

    def upsert_user(
        self,
        user_id: int,
        user_name: str,
        status: Status,
        username: str | None = None,
        chat_id: int | None = None,
    ) -> None:
        """Generic method to insert or update a user with given status"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO users (user_id, user_name, username, status, chat_id, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
                (user_id, user_name, username, status, chat_id),
            )

    def add_verified_user(
        self,
        user_id: int,
        user_name: str,
        username: str | None = None,
        chat_id: int | None = None,
    ) -> None:
        """Add a user as verified"""
        self.upsert_user(user_id, user_name, Status.VERIFIED, username, chat_id)

    def add_blocked_user(
        self,
        user_id: int,
        user_name: str,
        username: str | None = None,
        chat_id: int | None = None,
    ) -> None:
        """Add a user as blocked"""
        self.upsert_user(user_id, user_name, Status.BLOCKED, username, chat_id)

    def add_pending_verification(
        self, user_id: int, chat_id: int, user_name: str, question: str, answer: str
    ) -> None:
        """Add a pending verification"""
        # First add user as pending
        self.upsert_user(user_id, user_name, Status.PENDING, chat_id=chat_id)

        # Then add pending verification
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO pending_verifications (user_id, chat_id, user_name, question, answer)
                VALUES (?, ?, ?, ?, ?)
            """,
                (user_id, chat_id, user_name, question, answer),
            )

    def remove_pending_verification(self, user_id: int) -> None:
        """Remove a pending verification"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM pending_verifications WHERE user_id = ?", (user_id,)
            )

    def remove_user(self, user_id: int) -> None:
        """Remove a user from blocked status (when they leave)"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM users WHERE user_id = ? AND status = ?",
                (user_id, Status.BLOCKED),
            )
            cursor.execute(
                "DELETE FROM pending_verifications WHERE user_id = ?", (user_id,)
            )

    def get_user_counts(self) -> dict[str, int]:
        """Get counts of users by status"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT status, COUNT(*) FROM users GROUP BY status
            """)
            results = cursor.fetchall()
            cursor.execute("SELECT COUNT(*) FROM pending_verifications")
            pending_count = cursor.fetchone()[0]

            counts = {"verified": 0, "blocked": 0, "pending": 0}
            for status, count in results:
                counts[status] = count
            counts["pending_verifications"] = pending_count
            return counts

    def get_blocked_users(self) -> list[User]:
        """Get list of blocked users"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT user_id, user_name, username, status, chat_id, created_at, updated_at
                FROM users
                WHERE status = ?
                ORDER BY created_at DESC
            """,
                (Status.BLOCKED,),
            )
            results = cursor.fetchall()

            blocked_users = []
            for row in results:
                blocked_users.append(
                    User(
                        id=row[0],
                        name=row[1],
                        username=row[2],
                        status=Status(row[3]),
                        chat_id=row[4],
                        created_at=row[5],
                        updated_at=row[6],
                    )
                )
            return blocked_users

    def get_all_users_for_scanning(self) -> list[User]:
        """Get all users except blocked ones for bot scanning"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT user_id, user_name, username, status, chat_id, created_at, updated_at
                FROM users
                WHERE status != ?
                ORDER BY created_at DESC
                """,
                (Status.BLOCKED,),
            )
            results = cursor.fetchall()

            users = []
            for row in results:
                users.append(
                    User(
                        id=row[0],
                        name=row[1],
                        username=row[2],
                        status=Status(row[3]),
                        chat_id=row[4],
                        created_at=row[5],
                        updated_at=row[6],
                    )
                )
            return users
