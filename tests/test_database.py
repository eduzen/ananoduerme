import pytest
from pathlib import Path
from database import Database, Status, User

@pytest.fixture
def db(tmp_path: Path):
    """Fixture to create a new database in a temporary file for each test."""
    db_path = tmp_path / "test.db"
    return Database(str(db_path))

def test_database_creation(db: Database):
    """Test that the database and tables are created."""
    with db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        assert cursor.fetchone() is not None
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pending_verifications'")
        assert cursor.fetchone() is not None

def test_upsert_user(db: Database):
    """Test inserting and updating a user."""
    db.upsert_user(1, "testuser", Status.PENDING, "testusername", 123)
    with db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = 1")
        user = cursor.fetchone()
        assert user is not None
        assert user["user_id"] == 1
        assert user["user_name"] == "testuser"
        assert user["status"] == Status.PENDING
        assert user["username"] == "testusername"
        assert user["chat_id"] == 123

    db.upsert_user(1, "testuser", Status.VERIFIED, "testusername", 123)
    with db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = 1")
        user = cursor.fetchone()
        assert user is not None
        assert user["status"] == Status.VERIFIED

def test_is_user_verified(db: Database):
    """Test checking if a user is verified."""
    db.add_verified_user(1, "verifieduser")
    assert db.is_user_verified(1) is True
    assert db.is_user_verified(2) is False

def test_is_user_blocked(db: Database):
    """Test checking if a user is blocked."""
    db.add_blocked_user(1, "blockeduser")
    assert db.is_user_blocked(1) is True
    assert db.is_user_blocked(2) is False

def test_pending_verification(db: Database):
    """Test adding and removing a pending verification."""
    db.add_pending_verification(1, 123, "pendinguser", "1+1", "2")
    verification = db.get_pending_verification(1)
    assert verification is not None
    assert verification["question"] == "1+1"
    assert verification["answer"] == "2"

    db.remove_pending_verification(1)
    assert db.get_pending_verification(1) is None

def test_get_user_counts(db: Database):
    """Test getting user counts."""
    db.add_verified_user(1, "user1")
    db.add_verified_user(2, "user2")
    db.add_blocked_user(3, "user3")
    db.add_pending_verification(4, 123, "user4", "1+1", "2")

    counts = db.get_user_counts()
    assert counts["verified"] == 2
    assert counts["blocked"] == 1
    assert counts["pending"] == 1
    assert counts["pending_verifications"] == 1

def test_get_blocked_users(db: Database):
    """Test getting a list of blocked users."""
    db.add_blocked_user(1, "user1", "user1_username")
    db.add_blocked_user(2, "user2", "user2_username")
    db.add_verified_user(3, "user3")

    blocked_users = db.get_blocked_users()
    assert len(blocked_users) == 2
    assert isinstance(blocked_users[0], User)
    # Check that we got the correct users, regardless of order
    blocked_user_ids = {user.id for user in blocked_users}
    assert blocked_user_ids == {1, 2}


def test_get_all_users_for_scanning(db: Database):
    """Test getting all users except blocked ones."""
    db.add_verified_user(1, "user1")
    db.add_pending_verification(2, 123, "user2", "q", "a")
    db.add_blocked_user(3, "user3")

    users_to_scan = db.get_all_users_for_scanning()
    assert len(users_to_scan) == 2
    user_ids = {user.id for user in users_to_scan}
    assert user_ids == {1, 2}

def test_remove_user(db: Database):
    """Test removing a user."""
    db.add_blocked_user(1, "user1")
    # This scenario (pending verification for a blocked user) shouldn't happen in practice,
    # but it's good for testing the cleanup.
    db.add_pending_verification(1, 123, "user1", "1+1", "2")
    db.remove_user(1)
    assert db.is_user_blocked(1) is False
    assert db.get_pending_verification(1) is None
