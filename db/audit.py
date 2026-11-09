from db.mysql import get_connection


def record_event(event_type, actor_user_id=None, actor_username=None, details=""):
    """Persist an auditable application event without storing secrets."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO event_logs (event_type, actor_user_id, actor_username, details)
            VALUES (%s, %s, %s, %s)
            """,
            (
                event_type[:50],
                actor_user_id,
                actor_username[:100] if actor_username else None,
                details[:500],
            ),
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()
