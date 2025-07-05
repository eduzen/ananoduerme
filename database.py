import sqlite3
from typing import Any


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()

    def init_database(self) -> None:
        """Initialize the SQLite database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create users table to track verification states
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                user_name TEXT NOT NULL,
                username TEXT,
                status TEXT NOT NULL CHECK (status IN ('verified', 'pending', 'blocked')),
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
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_status ON users (status)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_pending_chat ON pending_verifications (chat_id)"
        )

        conn.commit()
        conn.close()

    def is_user_verified(self, user_id: int) -> bool:
        """Check if a user is verified"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT status FROM users WHERE user_id = ? AND status = "verified"',
            (user_id,),
        )
        result = cursor.fetchone()
        conn.close()
        return result is not None

    def is_user_blocked(self, user_id: int) -> bool:
        """Check if a user is blocked"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT status FROM users WHERE user_id = ? AND status = "blocked"',
            (user_id,),
        )
        result = cursor.fetchone()
        conn.close()
        return result is not None

    def get_pending_verification(self, user_id: int) -> dict[str, Any] | None:
        """Get pending verification data for a user"""
        conn = sqlite3.connect(self.db_path)
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
        conn.close()

        if result:
            return {
                "chat_id": result[0],
                "user_name": result[1],
                "question": result[2],
                "answer": result[3],
            }
        return None

    def add_verified_user(
        self, user_id: int, user_name: str, username: str | None = None
    ) -> None:
        """Add a user as verified"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO users (user_id, user_name, username, status, updated_at)
            VALUES (?, ?, ?, "verified", CURRENT_TIMESTAMP)
        """,
            (user_id, user_name, username),
        )
        conn.commit()
        conn.close()

    def add_blocked_user(
        self, user_id: int, user_name: str, username: str | None = None
    ) -> None:
        """Add a user as blocked"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO users (user_id, user_name, username, status, updated_at)
            VALUES (?, ?, ?, "blocked", CURRENT_TIMESTAMP)
        """,
            (user_id, user_name, username),
        )
        conn.commit()
        conn.close()

    def add_pending_verification(
        self, user_id: int, chat_id: int, user_name: str, question: str, answer: str
    ) -> None:
        """Add a pending verification"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # First add user as pending
        cursor.execute(
            """
            INSERT OR REPLACE INTO users (user_id, user_name, status, updated_at)
            VALUES (?, ?, "pending", CURRENT_TIMESTAMP)
        """,
            (user_id, user_name),
        )

        # Then add pending verification
        cursor.execute(
            """
            INSERT OR REPLACE INTO pending_verifications (user_id, chat_id, user_name, question, answer)
            VALUES (?, ?, ?, ?, ?)
        """,
            (user_id, chat_id, user_name, question, answer),
        )

        conn.commit()
        conn.close()

    def remove_pending_verification(self, user_id: int) -> None:
        """Remove a pending verification"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM pending_verifications WHERE user_id = ?", (user_id,)
        )
        conn.commit()
        conn.close()

    def remove_user(self, user_id: int) -> None:
        """Remove a user from blocked status (when they leave)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'DELETE FROM users WHERE user_id = ? AND status = "blocked"', (user_id,)
        )
        cursor.execute(
            "DELETE FROM pending_verifications WHERE user_id = ?", (user_id,)
        )
        conn.commit()
        conn.close()

    def get_user_counts(self) -> dict[str, int]:
        """Get counts of users by status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT status, COUNT(*) FROM users GROUP BY status
        """)
        results = cursor.fetchall()
        cursor.execute("SELECT COUNT(*) FROM pending_verifications")
        pending_count = cursor.fetchone()[0]
        conn.close()

        counts = {"verified": 0, "blocked": 0, "pending": 0}
        for status, count in results:
            counts[status] = count
        counts["pending_verifications"] = pending_count
        return counts

    def get_blocked_users(self) -> list[dict[str, Any]]:
        """Get list of blocked users"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, user_name, username, created_at
            FROM users
            WHERE status = 'blocked'
            ORDER BY created_at DESC
        """)
        results = cursor.fetchall()
        conn.close()

        blocked_users = []
        for row in results:
            blocked_users.append(
                {
                    "user_id": row[0],
                    "user_name": row[1],
                    "username": row[2],
                    "created_at": row[3],
                }
            )
        return blocked_users
