from enum import Enum
from typing import Optional
import sqlite3
import logging

logger = logging.getLogger(__name__)


class ComplianceStatus(Enum):
    COMPLIANT = "Compliant"
    NON_COMPLIANT = "Non Compliant"
    NON_APPLICABLE = "Non Applicable"
    NOT_REVIEWED = "Not Reviewed"

    @classmethod
    def from_string(cls, value: str) -> "ComplianceStatus":
        for status in cls:
            if status.value == value:
                return status
        return cls.NOT_REVIEWED

    def __str__(self):
        return self.value


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def extend_devices_schema(self, conn: sqlite3.Connection) -> None:
        """Add new columns to devices table if they are missing."""
        cur = conn.execute("PRAGMA table_info(devices);")
        existing_cols = {row[1] for row in cur.fetchall()}

        new_columns = {
            "mgmt_ip": "TEXT",
            "ssh_user": "TEXT",
        }

        for col_name, col_type in new_columns.items():
            if col_name not in existing_cols:
                # Safe because col_name and col_type are controlled by us
                conn.execute(f"ALTER TABLE devices ADD COLUMN {col_name} {col_type};")

        conn.commit()

    def init_db(self) -> None:
        """Initialize database schema."""
        conn = self.get_connection()

        # Devices table - removed ssh_password column entirely
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS devices (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                name     TEXT NOT NULL,
                hostname TEXT,
                notes    TEXT
            );
            """
        )
        conn.commit()

        self.extend_devices_schema(conn)

        # Per-device reviews
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reviews (
                device_id  INTEGER NOT NULL,
                item_index INTEGER NOT NULL,
                status     TEXT NOT NULL,
                note       TEXT,
                PRIMARY KEY (device_id, item_index),
                FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
            );
            """
        )

        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")

    def get_device(self, device_id: int) -> Optional[dict]:
        """Retrieve a single device by ID."""
        conn = self.get_connection()
        try:
            cur = conn.execute("SELECT * FROM devices WHERE id = ?;", (device_id,))
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_all_devices(self) -> list[dict]:
        """Retrieve all devices."""
        conn = self.get_connection()
        try:
            cur = conn.execute("SELECT * FROM devices ORDER BY id;")
            rows = cur.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def create_device(
        self, name: str, hostname: str, notes: str, mgmt_ip: str, ssh_user: str
    ) -> int:
        """Create a new device."""
        conn = self.get_connection()
        try:
            cur = conn.execute(
                """
                INSERT INTO devices (name, hostname, notes, mgmt_ip, ssh_user)
                VALUES (?, ?, ?, ?, ?);
                """,
                (name, hostname or None, notes or None, mgmt_ip or None, ssh_user or None),
            )
            conn.commit()
            device_id = cur.lastrowid
            logger.info(f"Created device {device_id}: {name}")
            return device_id
        finally:
            conn.close()

    def update_device(
        self, device_id: int, name: str, hostname: str, notes: str, mgmt_ip: str, ssh_user: str
    ) -> None:
        """Update an existing device."""
        conn = self.get_connection()
        try:
            conn.execute(
                """
                UPDATE devices
                SET name = ?, hostname = ?, notes = ?, mgmt_ip = ?, ssh_user = ?
                WHERE id = ?;
                """,
                (name, hostname or None, notes or None, mgmt_ip or None, ssh_user or None, device_id),
            )
            conn.commit()
            logger.info(f"Updated device {device_id}")
        finally:
            conn.close()

    def delete_device_and_reviews(self, device_id: int) -> None:
        """Delete a device and all its reviews."""
        conn = self.get_connection()
        try:
            conn.execute("DELETE FROM reviews WHERE device_id = ?;", (device_id,))
            conn.execute("DELETE FROM devices WHERE id = ?;", (device_id,))
            conn.commit()
            logger.info(f"Deleted device {device_id} and its reviews")
        finally:
            conn.close()

    def get_reviews_for_device(self, device_id: int) -> dict[int, dict]:
        """Return dict: item_index -> {status, note}."""
        conn = self.get_connection()
        try:
            cur = conn.execute(
                "SELECT item_index, status, note FROM reviews WHERE device_id = ?;",
                (device_id,),
            )
            rows = cur.fetchall()
            return {
                r["item_index"]: {"status": r["status"], "note": r["note"]}
                for r in rows
            }
        finally:
            conn.close()

    def save_review(
        self, device_id: int, item_index: int, status: str, note: Optional[str]
    ) -> None:
        """Save or update a review for a specific item."""
        conn = self.get_connection()
        try:
            conn.execute(
                """
                INSERT INTO reviews (device_id, item_index, status, note)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(device_id, item_index) DO UPDATE SET
                    status = excluded.status,
                    note   = excluded.note;
                """,
                (device_id, item_index, status, note),
            )
            conn.commit()
            logger.debug(f"Saved review for device {device_id}, item {item_index}: {status}")
        finally:
            conn.close()
