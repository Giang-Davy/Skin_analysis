#!/usr/bin/env python3
import logging

from db.mysql import get_connection

logger = logging.getLogger(__name__)


def init_db():
    """Initialize the MySQL schema if the database is configured and reachable."""
    try:
        conn = get_connection()
    except RuntimeError as exc:
        logger.warning("MySQL initialization skipped: %s", exc)
        return
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.warning("MySQL initialization skipped because the database could not be reached: %s", exc)
        return

    cursor = conn.cursor()

    try:
        # User table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            email VARCHAR(100) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL
        )
        """)
        # Ensure GDPR consent columns exist (best-effort; ignore if already present)
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN consent_given BOOLEAN DEFAULT FALSE")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN consent_ts TIMESTAMP NULL DEFAULT NULL")
        except Exception:
            pass

        # History Table (for each users)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            file_name VARCHAR(255),
            caption TEXT,
            is_animal BOOLEAN DEFAULT FALSE,
            is_food BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """)

        conn.commit()
        logger.info("Tables initialized successfully!")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    init_db()